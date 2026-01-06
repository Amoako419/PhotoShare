"""
Church settings views for admin branding customization.
"""

import logging
from django.core.files.uploadedfile import UploadedFile
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework import status
from tenants.models import Church
from .s3_service import S3MediaService
from .authentication import CookieJWTAuthentication

logger = logging.getLogger(__name__)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def church_settings_view(request):
    """
    Get or update church settings (admin only).
    
    GET: Returns current church settings with signed URLs
    PUT: Updates church settings including image uploads
    """
    # Check if user has a church
    if not request.user.church:
        return Response({
            'error': 'User not assigned to a church'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user is admin
    if request.user.role != 'admin':
        return Response({
            'error': 'Only administrators can access church settings'
        }, status=status.HTTP_403_FORBIDDEN)
    
    church = request.user.church
    
    if request.method == 'GET':
        return _get_church_settings(church)
    elif request.method == 'PUT':
        return _update_church_settings(request, church)


def _get_church_settings(church: Church) -> Response:
    """Get current church settings with signed URLs for images."""
    s3_service = S3MediaService()
    
    settings_data = {
        'church_id': str(church.id),
        'church_name': church.name,
        'church_code': church.church_code,
        'logo_url': None,
        'login_cover_image': None,
    }
    
    # Generate signed URLs for existing images
    try:
        if church.logo_url:
            settings_data['logo_url'] = s3_service.generate_signed_url(
                s3_key=church.logo_url,
                church=church,
                expiry_minutes=60
            )
        
        if church.login_cover_image:
            settings_data['login_cover_image'] = s3_service.generate_signed_url(
                s3_key=church.login_cover_image,
                church=church,
                expiry_minutes=60
            )
    except Exception as e:
        logger.error(f"Error generating signed URLs for church {church.id}: {e}")
    
    return Response(settings_data)


def _update_church_settings(request, church: Church) -> Response:
    """Update church settings including image uploads."""
    try:
        s3_service = S3MediaService()
        updated_fields = []
        
        # Update church name if provided
        church_name = request.data.get('church_name')
        if church_name and church_name.strip():
            church.name = church_name.strip()
            updated_fields.append('name')
        
        # Handle logo upload
        logo_file = request.FILES.get('logo')
        if logo_file:
            # Delete old logo if exists
            if church.logo_url:
                try:
                    s3_service.delete_file(church.logo_url, church)
                except Exception as e:
                    logger.warning(f"Failed to delete old logo: {e}")
            
            # Upload new logo
            try:
                s3_key, metadata = s3_service.upload_photo(
                    church=church,
                    file_obj=logo_file.file,
                    filename=f"logo_{logo_file.name}",
                    content_type=logo_file.content_type or 'image/png'
                )
                church.logo_url = s3_key
                updated_fields.append('logo')
            except Exception as e:
                logger.error(f"Failed to upload logo: {e}")
                return Response({
                    'error': 'Failed to upload logo',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Handle cover image upload
        cover_file = request.FILES.get('login_cover_image')
        if cover_file:
            # Delete old cover if exists
            if church.login_cover_image:
                try:
                    s3_service.delete_file(church.login_cover_image, church)
                except Exception as e:
                    logger.warning(f"Failed to delete old cover image: {e}")
            
            # Upload new cover
            try:
                s3_key, metadata = s3_service.upload_photo(
                    church=church,
                    file_obj=cover_file.file,
                    filename=f"cover_{cover_file.name}",
                    content_type=cover_file.content_type or 'image/jpeg'
                )
                church.login_cover_image = s3_key
                updated_fields.append('cover_image')
            except Exception as e:
                logger.error(f"Failed to upload cover image: {e}")
                return Response({
                    'error': 'Failed to upload cover image',
                    'detail': str(e)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Save church
        church.save()
        
        logger.info(f"Church settings updated for {church.name}: {updated_fields}")
        
        # Return updated settings
        return _get_church_settings(church)
        
    except Exception as e:
        logger.error(f"Failed to update church settings: {e}", exc_info=True)
        return Response({
            'error': 'Failed to update church settings',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def activate_church_view(request):
    """
    Activate a church after setup wizard completion (admin only).
    
    POST /api/v1/core/church/activate/
    
    Request (multipart/form-data):
    - logo: File (optional)
    - cover_image: File (optional)
    - confirmation: Boolean (required, must be true)
    
    Response:
    - Activates the church (sets is_active=True)
    - Returns updated church information
    """
    # Check if user has a church
    if not request.user.church:
        return Response({
            'error': 'User not assigned to a church'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user is admin
    if request.user.role != 'admin':
        return Response({
            'error': 'Only administrators can activate the church'
        }, status=status.HTTP_403_FORBIDDEN)
    
    church = request.user.church
    
    # Check if church is already active
    if church.is_active:
        return Response({
            'error': 'Church is already active'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Require confirmation
    confirmation = request.data.get('confirmation')
    if confirmation != 'true' and confirmation is not True:
        return Response({
            'error': 'Confirmation is required to activate the church'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        s3_service = S3MediaService()
        updated = False
        
        # Upload logo if provided
        logo_file = request.FILES.get('logo')
        if logo_file:
            try:
                # Upload to S3
                s3_path = s3_service.upload_file(
                    file=logo_file,
                    church=church,
                    folder='branding/logo'
                )
                church.logo_url = s3_path
                updated = True
                logger.info(f"Uploaded logo for church {church.name}: {s3_path}")
            except Exception as e:
                logger.error(f"Failed to upload logo during activation: {e}")
                # Don't fail activation if logo upload fails
        
        # Upload cover image if provided
        cover_file = request.FILES.get('cover_image')
        if cover_file:
            try:
                # Upload to S3
                s3_path = s3_service.upload_file(
                    file=cover_file,
                    church=church,
                    folder='branding/cover'
                )
                church.login_cover_image = s3_path
                updated = True
                logger.info(f"Uploaded cover image for church {church.name}: {s3_path}")
            except Exception as e:
                logger.error(f"Failed to upload cover image during activation: {e}")
                # Don't fail activation if cover upload fails
        
        # Activate the church
        church.is_active = True
        church.save()
        
        logger.info(
            f"Church '{church.name}' (Code: {church.church_code}) activated by "
            f"admin {request.user.email}"
        )
        
        # Get signed URLs for images
        logo_signed_url = None
        cover_signed_url = None
        
        if church.logo_url:
            try:
                logo_signed_url = s3_service.generate_signed_url(
                    church=church,
                    s3_path=church.logo_url,
                    expiry_minutes=60
                )
            except Exception as e:
                logger.error(f"Failed to generate logo signed URL: {e}")
        
        if church.login_cover_image:
            try:
                cover_signed_url = s3_service.generate_signed_url(
                    church=church,
                    s3_path=church.login_cover_image,
                    expiry_minutes=60
                )
            except Exception as e:
                logger.error(f"Failed to generate cover signed URL: {e}")
        
        return Response({
            'message': 'Church activated successfully',
            'church': {
                'id': str(church.church_id),
                'name': church.name,
                'church_code': church.church_code,
                'is_active': church.is_active,
                'logo_url': logo_signed_url,
                'cover_image_url': cover_signed_url,
                'created_at': church.created_at.isoformat(),
                'updated_at': church.updated_at.isoformat()
            }
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Failed to activate church: {e}", exc_info=True)
        return Response({
            'error': 'Failed to activate church',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
