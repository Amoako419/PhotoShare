"""
Tenant views for branding and church information.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from .models import Church
from core.s3_service import S3MediaService
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tenant_branding_view(request):
    """
    Get tenant branding information for authenticated user's church.
    Returns church name, logo, and login cover image with signed URLs.
    """
    if not request.user.church:
        return Response({
            'error': 'User not assigned to a church'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    church = request.user.church
    s3_service = S3MediaService()
    
    branding_data = {
        'church_name': church.name,
        'church_id': str(church.id),
        'logo_url': None,
        'login_cover_image': None
    }
    
    # Generate signed URLs for branding images if they exist
    try:
        if church.logo_url:
            branding_data['logo_url'] = s3_service.generate_presigned_url(
                s3_key=church.logo_url,
                expiration=3600  # 1 hour expiry for branding
            )
        
        if church.login_cover_image:
            branding_data['login_cover_image'] = s3_service.generate_presigned_url(
                s3_key=church.login_cover_image,
                expiration=3600
            )
    except Exception as e:
        logger.error(f"Error generating signed URLs for church {church.id}: {e}")
    
    return Response(branding_data)


@api_view(['GET'])
@permission_classes([AllowAny])
def public_tenant_branding_view(request):
    """
    Get public tenant branding by church code (for login page).
    Only returns login_cover_image, not the full branding.
    """
    church_code = request.query_params.get('church_code')
    
    if not church_code:
        return Response({
            'error': 'church_code query parameter is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        church = Church.objects.get(church_code=church_code.lower().strip(), is_active=True)
        s3_service = S3MediaService()
        
        branding_data = {
            'church_name': church.name,
            'login_cover_image': None
        }
        
        if church.login_cover_image:
            branding_data['login_cover_image'] = s3_service.generate_presigned_url(
                s3_key=church.login_cover_image,
                expiration=3600
            )
        
        return Response(branding_data)
        
    except Church.DoesNotExist:
        return Response({
            'error': 'Church not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error fetching public branding for {church_code}: {e}")
        return Response({
            'error': 'Failed to fetch branding'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

