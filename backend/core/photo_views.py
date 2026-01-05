"""
Photo API views with S3 integration and tenant isolation.

This module provides secure photo upload and access APIs with:
- Multi-tenant isolation
- S3 private storage
- Signed URL generation
- Upload validation and security
"""

import logging
from typing import Dict, Any

from django.core.exceptions import ValidationError, PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Photo, Album, User
from .s3_service import s3_service
from .tenant_views import TenantModelViewSet
from .authentication import CookieJWTAuthentication
from .tenant_isolation import TenantIsolationPermission

logger = logging.getLogger(__name__)


class PhotoUploadView(APIView):
    """
    Secure photo upload API with S3 integration and tenant isolation.
    
    Features:
    - Direct S3 upload with tenant-scoped paths
    - File validation and security checks
    - Automatic metadata extraction
    - Tenant isolation enforcement
    """
    
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [TenantIsolationPermission]
    parser_classes = [MultiPartParser, FormParser]
    
    def post(self, request, *args, **kwargs):
        """
        Upload a photo file to S3 and create database record.
        
        Expected form data:
        - image: Image file
        - title: Photo title
        - description: Optional description
        - album_id: Optional album ID
        - is_public: Boolean for public visibility
        """
        try:
            # Validate required fields
            if 'image' not in request.FILES:
                return Response(
                    {'error': 'Image file is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            image_file = request.FILES['image']
            title = request.data.get('title', '').strip()
            description = request.data.get('description', '').strip()
            album_id = request.data.get('album_id')
            is_public = request.data.get('is_public', 'false').lower() == 'true'
            
            if not title:
                title = image_file.name  # Use filename as title if none provided
            
            # Get user's church for tenant isolation
            church = request.user.church
            if not church:
                return Response(
                    {'error': 'User must belong to a church'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Validate album if specified
            album = None
            if album_id:
                try:
                    album = Album.objects.tenant_scoped(church).get(id=album_id)
                except Album.DoesNotExist:
                    return Response(
                        {'error': 'Album not found or access denied'},
                        status=status.HTTP_404_NOT_FOUND
                    )
            
            # Validate file type
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
            if image_file.content_type not in allowed_types:
                return Response(
                    {'error': f'Unsupported file type: {image_file.content_type}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Upload to S3
            logger.info(f"Uploading photo '{title}' for church {church.id}")
            s3_key, metadata = s3_service.upload_photo(
                church=church,
                file_obj=image_file,
                filename=image_file.name,
                content_type=image_file.content_type
            )
            
            # Extract image dimensions if available
            width, height = None, None
            if hasattr(image_file, 'width') and hasattr(image_file, 'height'):
                width = image_file.width
                height = image_file.height
            
            # Create Photo record
            photo = Photo.objects.create(
                church=church,
                album=album,
                title=title,
                description=description,
                filename=image_file.name,
                s3_key=s3_key,
                file_size=image_file.size,
                content_type=image_file.content_type,
                width=width,
                height=height,
                uploaded_by=request.user,
                is_public=is_public
            )
            
            logger.info(f"Photo created successfully: {photo.id}")
            
            # Return photo details with signed URL
            return Response({
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'filename': photo.filename,
                'file_size': photo.file_size,
                'file_size_mb': photo.file_size_mb,
                'content_type': photo.content_type,
                'width': photo.width,
                'height': photo.height,
                'is_public': photo.is_public,
                'album_id': photo.album.id if photo.album else None,
                'uploaded_at': photo.created_at,
                'secure_url': photo.get_secure_url(expiry_minutes=10),
                'url_expires_in_minutes': 10
            }, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            logger.warning(f"Photo upload validation error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            logger.warning(f"Photo upload permission denied: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Photo upload failed: {e}")
            return Response(
                {'error': 'Upload failed. Please try again.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PhotoAccessView(APIView):
    """
    Generate signed URLs for secure photo access.
    
    This endpoint provides secure, time-limited access to private photos
    with full tenant isolation enforcement.
    """
    
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [TenantIsolationPermission]
    
    def get(self, request, photo_id, *args, **kwargs):
        """
        Generate a signed URL for photo access.
        
        Args:
            photo_id: ID of the photo to access
            
        Query parameters:
            - expiry_minutes: URL expiration (5-10 minutes, default 10)
        """
        try:
            # Get user's church for tenant isolation
            church = request.user.church
            if not church:
                return Response(
                    {'error': 'User must belong to a church'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Get photo with tenant scoping
            photo = get_object_or_404(
                Photo.objects.tenant_scoped(church),
                id=photo_id
            )
            
            # Check if photo has a file
            if not photo.has_file:
                return Response(
                    {'error': 'Photo has no associated file'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Get expiry parameter (5-10 minutes)
            try:
                expiry_minutes = int(request.GET.get('expiry_minutes', 10))
                expiry_minutes = max(5, min(expiry_minutes, 10))  # Clamp to 5-10 minutes
            except (ValueError, TypeError):
                expiry_minutes = 10
            
            # Generate signed URL
            signed_url = photo.get_secure_url(expiry_minutes)
            
            logger.info(f"Generated signed URL for photo {photo_id} (church {church.id})")
            
            return Response({
                'photo_id': photo.id,
                'secure_url': signed_url,
                'expires_in_minutes': expiry_minutes,
                'expires_at': photo.created_at.timestamp() + (expiry_minutes * 60),
                'title': photo.title,
                'filename': photo.filename
            })
            
        except ValidationError as e:
            logger.warning(f"Signed URL generation validation error: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except PermissionDenied as e:
            logger.warning(f"Signed URL access denied: {e}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_403_FORBIDDEN
            )
        except Exception as e:
            logger.error(f"Signed URL generation failed: {e}")
            return Response(
                {'error': 'Failed to generate secure URL'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PhotoViewSet(TenantModelViewSet):
    """
    Photo management API with tenant isolation.
    
    Provides CRUD operations for photos with automatic tenant scoping
    and secure file access through signed URLs.
    """
    
    model = Photo
    tenant_field = 'church'
    
    def get_queryset(self):
        """Get tenant-scoped photo queryset."""
        church = getattr(self.request.user, 'church', None)
        if not church:
            return Photo.objects.none()
        
        return Photo.objects.tenant_scoped(church).select_related(
            'album', 'uploaded_by'
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """List photos with secure URLs."""
        queryset = self.get_queryset()
        
        # Optional filtering
        album_id = request.GET.get('album_id')
        if album_id:
            queryset = queryset.filter(album_id=album_id)
        
        is_public = request.GET.get('is_public')
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')
        
        # Pagination (simple limit/offset)
        limit = min(int(request.GET.get('limit', 50)), 100)  # Max 100 photos per request
        offset = int(request.GET.get('offset', 0))
        
        total_count = queryset.count()
        photos = queryset[offset:offset + limit]
        
        # Generate signed URLs for photos with files
        photo_data = []
        for photo in photos:
            data = {
                'id': photo.id,
                'title': photo.title,
                'description': photo.description,
                'filename': photo.filename,
                'file_size': photo.file_size,
                'file_size_mb': photo.file_size_mb,
                'content_type': photo.content_type,
                'width': photo.width,
                'height': photo.height,
                'is_public': photo.is_public,
                'album_id': photo.album.id if photo.album else None,
                'album_title': photo.album.title if photo.album else None,
                'uploaded_by': photo.uploaded_by.full_name,
                'uploaded_at': photo.created_at,
                'has_file': photo.has_file
            }
            
            # Add signed URL if file exists
            if photo.has_file:
                try:
                    data['secure_url'] = photo.get_secure_url(expiry_minutes=10)
                    data['url_expires_in_minutes'] = 10
                except Exception as e:
                    logger.warning(f"Failed to generate signed URL for photo {photo.id}: {e}")
                    data['secure_url'] = None
                    data['url_error'] = 'Failed to generate secure URL'
            
            photo_data.append(data)
        
        return Response({
            'photos': photo_data,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'has_next': offset + limit < total_count
        })
    
    @action(detail=True, methods=['delete'])
    def delete_photo(self, request, pk=None):
        """Delete photo and its S3 file."""
        try:
            photo = self.get_object()
            
            # Delete from S3 first
            if photo.has_file:
                photo.delete_from_s3()
            
            # Delete database record
            photo.delete()
            
            logger.info(f"Photo {pk} deleted successfully")
            
            return Response(
                {'message': 'Photo deleted successfully'},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except Exception as e:
            logger.error(f"Photo deletion failed: {e}")
            return Response(
                {'error': 'Failed to delete photo'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )