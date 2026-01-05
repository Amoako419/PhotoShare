#!/usr/bin/env python3
"""
AWS S3 Bucket Setup for PhotoShare Church Media Platform

This script creates and configures an S3 bucket for storing church media files
with appropriate permissions and settings for a multi-tenant application.

Prerequisites:
- AWS credentials configured (via ~/.aws/credentials, environment variables, or IAM role)
- boto3 library installed: pip install boto3
- Sufficient AWS permissions to create and configure S3 buckets

Usage:
    python setup_s3_bucket.py
"""

import boto3
import json
import sys
from botocore.exceptions import ClientError, BotoCoreError


# Configuration
BUCKET_NAME =   #
AWS_REGION = 'us-east-1'  # Change this to your preferred region


def get_s3_client():
    """
    Create and return an S3 client with AWS credentials.
    
    Boto3 automatically looks for credentials in the following order:
    1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    2. ~/.aws/credentials file
    3. ~/.aws/config file
    4. IAM roles (if running on EC2)
    """
    try:
        s3_client = boto3.client('s3', region_name=AWS_REGION)
        
        # Test credentials by listing buckets
        s3_client.list_buckets()
        print("✅ AWS credentials validated successfully")
        return s3_client
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            print("❌ AWS credentials are invalid or lack sufficient permissions")
        elif error_code == 'SignatureDoesNotMatch':
            print("❌ AWS credentials are incorrect")
        else:
            print(f"❌ AWS error: {e}")
        return None
        
    except BotoCoreError as e:
        print(f"❌ AWS configuration error: {e}")
        print("Make sure AWS credentials are configured properly")
        return None


def bucket_exists(s3_client, bucket_name):
    """Check if the S3 bucket already exists."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        return True
    except ClientError as e:
        error_code = int(e.response['Error']['Code'])
        if error_code == 404:
            return False
        else:
            print(f"❌ Error checking bucket existence: {e}")
            return None


def create_s3_bucket(s3_client, bucket_name, region):
    """
    Create an S3 bucket with appropriate configuration for PhotoShare.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the bucket to create
        region: AWS region for the bucket
    """
    try:
        # Check if bucket already exists
        if bucket_exists(s3_client, bucket_name):
            print(f"📦 Bucket '{bucket_name}' already exists")
            return True
        
        print(f"🚀 Creating S3 bucket: {bucket_name}")
        
        # Create bucket configuration
        create_bucket_config = {}
        
        # Note: us-east-1 doesn't need LocationConstraint
        if region != 'us-east-1':
            create_bucket_config['LocationConstraint'] = region
        
        # Create the bucket
        if create_bucket_config:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration=create_bucket_config
            )
        else:
            s3_client.create_bucket(Bucket=bucket_name)
        
        print(f"✅ Successfully created bucket: {bucket_name}")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'BucketAlreadyExists':
            print(f"❌ Bucket name '{bucket_name}' is already taken globally")
            print("Try a different bucket name (S3 bucket names must be globally unique)")
        elif error_code == 'BucketAlreadyOwnedByYou':
            print(f"✅ Bucket '{bucket_name}' already exists and is owned by you")
            return True
        else:
            print(f"❌ Failed to create bucket: {e}")
        return False


def configure_bucket_versioning(s3_client, bucket_name):
    """Enable versioning on the S3 bucket for data protection."""
    try:
        print("🔧 Enabling bucket versioning...")
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        print("✅ Bucket versioning enabled")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to enable versioning: {e}")
        return False


def configure_bucket_encryption(s3_client, bucket_name):
    """Enable server-side encryption on the S3 bucket."""
    try:
        print("🔒 Configuring bucket encryption...")
        
        encryption_config = {
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    }
                }
            ]
        }
        
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration=encryption_config
        )
        print("✅ Bucket encryption enabled (AES-256)")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to configure encryption: {e}")
        return False


def configure_bucket_cors(s3_client, bucket_name):
    """
    Configure CORS policy to allow web uploads from the PhotoShare frontend.
    
    This allows the React frontend to upload files directly to S3.
    """
    try:
        print("🌐 Configuring CORS policy...")
        
        cors_config = {
            'CORSRules': [
                {
                    'AllowedHeaders': ['*'],
                    'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                    'AllowedOrigins': [
                        'http://localhost:3000',  # Local development
                        'http://localhost:5173',  # Vite dev server
                        'https://your-domain.com'  # Production domain (update this)
                    ],
                    'ExposeHeaders': ['ETag'],
                    'MaxAgeSeconds': 3000
                }
            ]
        }
        
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_config
        )
        print("✅ CORS policy configured")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to configure CORS: {e}")
        return False


def configure_bucket_lifecycle(s3_client, bucket_name):
    """
    Configure lifecycle policy for cost optimization.
    
    - Transition to IA after 30 days
    - Transition to Glacier after 90 days
    - Delete incomplete multipart uploads after 7 days
    """
    try:
        print("♻️ Configuring lifecycle policy...")
        
        lifecycle_config = {
            'Rules': [
                {
                    'ID': 'PhotoShareLifecycle',
                    'Status': 'Enabled',
                    'Filter': {'Prefix': ''},
                    'Transitions': [
                        {
                            'Days': 30,
                            'StorageClass': 'STANDARD_IA'
                        },
                        {
                            'Days': 90,
                            'StorageClass': 'GLACIER'
                        }
                    ],
                    'AbortIncompleteMultipartUpload': {
                        'DaysAfterInitiation': 7
                    }
                }
            ]
        }
        
        s3_client.put_bucket_lifecycle_configuration(
            Bucket=bucket_name,
            LifecycleConfiguration=lifecycle_config
        )
        print("✅ Lifecycle policy configured")
        return True
        
    except ClientError as e:
        print(f"❌ Failed to configure lifecycle policy: {e}")
        return False


def setup_bucket_notification(s3_client, bucket_name):
    """
    Placeholder for setting up bucket notifications.
    
    This could be used to trigger Lambda functions when files are uploaded,
    for example to generate thumbnails or update database records.
    """
    print("📢 Bucket notifications can be configured later for:")
    print("   - Thumbnail generation on upload")
    print("   - Database updates on file changes")
    print("   - Image processing workflows")
    return True


def main():
    """Main function to set up the S3 bucket for PhotoShare."""
    print("🚀 Setting up S3 bucket for PhotoShare Church Media Platform")
    print("=" * 60)
    
    # Initialize S3 client
    s3_client = get_s3_client()
    if not s3_client:
        print("\n❌ Failed to initialize AWS S3 client")
        print("Please check your AWS credentials and try again")
        sys.exit(1)
    
    print(f"\n📋 Configuration:")
    print(f"   Bucket name: {BUCKET_NAME}")
    print(f"   Region: {AWS_REGION}")
    
    # Create the bucket
    print(f"\n1. Creating S3 bucket...")
    if not create_s3_bucket(s3_client, BUCKET_NAME, AWS_REGION):
        print("❌ Failed to create bucket. Exiting.")
        sys.exit(1)
    
    # Configure bucket settings
    print(f"\n2. Configuring bucket settings...")
    
    success_count = 0
    total_configs = 3  # Versioning disabled
    
    # Bucket versioning disabled per user request
    # if configure_bucket_versioning(s3_client, BUCKET_NAME):
    #     success_count += 1
    
    if configure_bucket_encryption(s3_client, BUCKET_NAME):
        success_count += 1
    
    if configure_bucket_cors(s3_client, BUCKET_NAME):
        success_count += 1
    
    if configure_bucket_lifecycle(s3_client, BUCKET_NAME):
        success_count += 1
    
    # Setup notifications info
    setup_bucket_notification(s3_client, BUCKET_NAME)
    
    # Summary
    print(f"\n📊 Setup Summary:")
    print(f"   Bucket created: ✅ {BUCKET_NAME}")
    print(f"   Configurations applied: {success_count}/{total_configs}")
    print(f"   Region: {AWS_REGION}")
    
    if success_count == total_configs:
        print(f"\n🎉 S3 bucket setup completed successfully!")
        print(f"\nNext steps:")
        print(f"   1. Update your Django settings with:")
        print(f"      AWS_STORAGE_BUCKET_NAME = '{BUCKET_NAME}'")
        print(f"      AWS_S3_REGION_NAME = '{AWS_REGION}'")
        print(f"   2. Configure django-storages for S3 integration")
        print(f"   3. Update CORS origins for your production domain")
        print(f"   4. Set up IAM policies for Django application access")
    else:
        print(f"\n⚠️ Bucket created but some configurations failed")
        print(f"   You may need to configure them manually in the AWS console")
    
    print(f"\n🔗 AWS Console: https://s3.console.aws.amazon.com/s3/buckets/{BUCKET_NAME}")


if __name__ == '__main__':
    main()