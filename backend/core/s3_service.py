"""
AWS S3 service for PhotoShare media storage.

This module provides secure, tenant-aware S3 operations including:
- Private file uploads with tenant isolation
- Signed URL generation with short expiration
- Tenant permission checks before access
"""

import boto3
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from botocore.exceptions import ClientError, NoCredentialsError

from tenants.models import Church


class S3MediaService:
    """
    Service for handling S3 operations with tenant isolation and security.
    
    Features:
    - Private bucket access only
    - Tenant-scoped file paths
    - Short-lived signed URLs (5-10 minutes)
    - Upload validation and security checks
    """
    
    def __init__(self):
        """Initialize S3 client with configured credentials."""
        self.bucket_name = settings.AWS_STORAGE_BUCKET_NAME
        self.region = settings.AWS_S3_REGION_NAME
        self.signed_url_expiry = getattr(settings, 'AWS_QUERYSTRING_EXPIRE', 600)  # 10 minutes default
        
        try:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=self.region
            )
        except (NoCredentialsError, ClientError) as e:
            raise ValidationError(f"AWS S3 configuration error: {e}")
    
    def _generate_tenant_file_path(self, church: Church, filename: str, subfolder: str = 'photos') -> str:
        """
        Generate a tenant-scoped file path for S3.
        
        Path format: tenants/{church_id}/{subfolder}/{uuid}_{filename}
        
        Args:
            church: Church instance for tenant isolation
            filename: Original filename
            subfolder: S3 subfolder (photos, thumbnails, etc.)
            
        Returns:
            str: Secure S3 file path with tenant isolation
        """
        # Generate unique filename to prevent collisions
        file_uuid = str(uuid.uuid4())
        clean_filename = os.path.basename(filename).replace(' ', '_')
        
        return f"tenants/{church.id}/{subfolder}/{file_uuid}_{clean_filename}"
    
    def upload_photo(self, church: Church, file_obj, filename: str, content_type: str = 'image/jpeg') -> Tuple[str, dict]:
        """
        Upload a photo file to S3 with tenant isolation.
        
        Args:
            church: Church instance for tenant scoping
            file_obj: File object to upload
            filename: Original filename
            content_type: MIME type of the file
            
        Returns:
            Tuple[str, dict]: (S3 key, metadata dict)
            
        Raises:
            ValidationError: If upload fails or validation errors occur
            PermissionDenied: If church validation fails
        """
        if not church or not church.is_active:
            raise PermissionDenied("Invalid or inactive church")
        
        # Validate file size
        max_size = getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024)  # 50MB default
        if hasattr(file_obj, 'size') and file_obj.size > max_size:
            raise ValidationError(f"File size exceeds maximum allowed size of {max_size // (1024*1024)}MB")
        
        # Generate secure S3 path
        s3_key = self._generate_tenant_file_path(church, filename)
        
        # Prepare metadata
        metadata = {
            'church-id': str(church.id),
            'original-filename': filename,
            'upload-timestamp': datetime.utcnow().isoformat(),
            'content-type': content_type
        }
        
        try:
            # Upload to S3
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'Metadata': metadata,
                    'ServerSideEncryption': 'AES256'  # Encrypt at rest
                }
            )
            
            return s3_key, metadata
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise ValidationError(f"S3 upload failed [{error_code}]: {e}")
    
    def generate_signed_url(self, s3_key: str, church: Church, expiry_minutes: int = 10) -> str:
        """
        Generate a signed URL for private S3 object access.
        
        Args:
            s3_key: S3 object key
            church: Church instance for tenant validation
            expiry_minutes: URL expiration time in minutes (5-10 minutes)
            
        Returns:
            str: Pre-signed URL for secure access
            
        Raises:
            PermissionDenied: If tenant validation fails
            ValidationError: If URL generation fails
        """
        if not church or not church.is_active:
            raise PermissionDenied("Invalid or inactive church")
        
        # Validate tenant access to this file
        if not self._validate_tenant_file_access(s3_key, church):
            raise PermissionDenied("Access denied: File does not belong to your church")
        
        # Clamp expiry to reasonable bounds (5-10 minutes)
        expiry_minutes = max(5, min(expiry_minutes, 10))
        expiry_seconds = expiry_minutes * 60
        
        try:
            signed_url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiry_seconds
            )
            
            return signed_url
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise ValidationError(f"Failed to generate signed URL [{error_code}]: {e}")
    
    def _validate_tenant_file_access(self, s3_key: str, church: Church) -> bool:
        """
        Validate that a file belongs to the specified church tenant.
        
        Args:
            s3_key: S3 object key to validate
            church: Church instance to check against
            
        Returns:
            bool: True if church has access to this file
        """
        # Check if file path starts with correct tenant prefix
        expected_prefix = f"tenants/{church.id}/"
        if not s3_key.startswith(expected_prefix):
            return False
        
        try:
            # Get object metadata to double-check church ID
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            # Check metadata church-id if available
            metadata = response.get('Metadata', {})
            metadata_church_id = metadata.get('church-id')
            
            if metadata_church_id and metadata_church_id != str(church.id):
                return False
                
            return True
            
        except ClientError:
            # If we can't access the object metadata, deny access
            return False
    
    def delete_file(self, s3_key: str, church: Church) -> bool:
        """
        Delete a file from S3 with tenant validation.
        
        Args:
            s3_key: S3 object key to delete
            church: Church instance for validation
            
        Returns:
            bool: True if deletion successful
            
        Raises:
            PermissionDenied: If tenant validation fails
        """
        if not church or not church.is_active:
            raise PermissionDenied("Invalid or inactive church")
        
        # Validate tenant access before deletion
        if not self._validate_tenant_file_access(s3_key, church):
            raise PermissionDenied("Access denied: Cannot delete file that doesn't belong to your church")
        
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            return True
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            raise ValidationError(f"Failed to delete file [{error_code}]: {e}")
    
    def get_file_info(self, s3_key: str, church: Church) -> Optional[dict]:
        """
        Get file information from S3 with tenant validation.
        
        Args:
            s3_key: S3 object key
            church: Church instance for validation
            
        Returns:
            dict: File information including size, last_modified, etc.
            
        Raises:
            PermissionDenied: If tenant validation fails
        """
        if not church or not church.is_active:
            raise PermissionDenied("Invalid or inactive church")
        
        # Validate tenant access
        if not self._validate_tenant_file_access(s3_key, church):
            raise PermissionDenied("Access denied: File does not belong to your church")
        
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )
            
            return {
                'size': response.get('ContentLength'),
                'last_modified': response.get('LastModified'),
                'content_type': response.get('ContentType'),
                'metadata': response.get('Metadata', {})
            }
            
        except ClientError:
            return None


# Global service instance
s3_service = S3MediaService()