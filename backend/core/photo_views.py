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
from .s3_service import s3_service, S3MediaService
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
        Upload photo(s) to S3 and create database records.
        
        Supports both single and batch uploads.
        
        Expected form data:
        Single upload:
        - image: Image file
        - title: Photo title
        - description: Optional description
        - album_id: Optional album ID
        - is_public: Boolean for public visibility
        
        Batch upload:
        - photos: Multiple image files
        - album_title: Title for new album
        - event_date: Optional event date for album
        """
        try:
            # Get user's church for tenant isolation
            church = request.user.church
            if not church:
                return Response(
                    {'error': 'User must belong to a church'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            # Check if this is a batch upload (multiple photos)
            if 'photos' in request.FILES:
                return self._handle_batch_upload(request, church)
            
            # Single file upload
            if 'image' not in request.FILES:
                return Response(
                    {'error': 'Image file is required (use "image" for single upload or "photos" for batch upload)'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            image_file = request.FILES['image']
            title = request.data.get('title', '').strip()
            description = request.data.get('description', '').strip()
            album_id = request.data.get('album_id')
            is_public = request.data.get('is_public', 'false').lower() == 'true'
            
            if not title:
                title = image_file.name  # Use filename as title if none provided
            
            # Validate album if specified
            album = None
            if album_id:
                try:
                    album = Album.objects.filter(church=church).get(id=album_id)
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
                'message': 'Photo uploaded successfully'
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
    
    def _handle_batch_upload(self, request, church):
        """Handle batch upload of multiple photos to a new or existing album."""
        photos_files = request.FILES.getlist('photos')
        
        if not photos_files:
            return Response(
                {'error': 'No photos provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        album_title = request.data.get('album_title', '').strip()
        if not album_title:
            return Response(
                {'error': 'Album title is required for batch upload'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        event_date = request.data.get('event_date')
        
        # Try to get existing album or create new one with unique title
        try:
            # Check if album already exists
            album = Album.objects.filter(
                church=church,
                title=album_title
            ).first()
            
            if album:
                logger.info(f"Using existing album '{album_title}' for church {church.id}")
            else:
                # Create new album
                album = Album.objects.create(
                    church=church,
                    title=album_title,
                    created_by=request.user,
                    event_date=event_date if event_date else None,
                    is_public=True  # Default to public for batch uploads
                )
                logger.info(f"Created new album '{album_title}' for church {church.id}")
        except Exception as e:
            logger.error(f"Failed to get/create album: {e}")
            return Response(
                {'error': f'Failed to create album: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Upload all photos
        uploaded_photos = []
        failed_uploads = []
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/gif', 'image/webp']
        
        for photo_file in photos_files:
            try:
                # Validate file type
                if photo_file.content_type not in allowed_types:
                    failed_uploads.append({
                        'filename': photo_file.name,
                        'error': f'Unsupported file type: {photo_file.content_type}'
                    })
                    continue
                
                # Upload to S3
                s3_key, metadata = s3_service.upload_photo(
                    church=church,
                    file_obj=photo_file,
                    filename=photo_file.name,
                    content_type=photo_file.content_type
                )
                
                # Create Photo record
                photo = Photo.objects.create(
                    church=church,
                    album=album,
                    title=photo_file.name,  # Use filename as title
                    filename=photo_file.name,
                    s3_key=s3_key,
                    file_size=photo_file.size,
                    content_type=photo_file.content_type,
                    uploaded_by=request.user,
                    is_public=True
                )
                
                uploaded_photos.append({
                    'id': photo.id,
                    'title': photo.title,
                    'filename': photo.filename
                })
                
                logger.info(f"Uploaded photo {photo.id} to album {album.id}")
                
            except Exception as e:
                logger.error(f"Failed to upload {photo_file.name}: {e}")
                failed_uploads.append({
                    'filename': photo_file.name,
                    'error': str(e)
                })
        
        # Return results
        response_data = {
            'message': f'Uploaded {len(uploaded_photos)} of {len(photos_files)} photos',
            'album_id': album.id,
            'album_title': album.title,
            'uploaded_count': len(uploaded_photos),
            'failed_count': len(failed_uploads),
            'uploaded_photos': uploaded_photos
        }
        
        if failed_uploads:
            response_data['failed_uploads'] = failed_uploads
        
        status_code = status.HTTP_201_CREATED if uploaded_photos else status.HTTP_400_BAD_REQUEST
        
        return Response(response_data, status=status_code)


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
                Photo.objects.filter(church=church),
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
        
        return Photo.objects.filter(church=church).select_related(
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


class AlbumViewSet(TenantModelViewSet):
    """
    Album management API with tenant isolation.
    
    Provides CRUD operations for albums with automatic tenant scoping
    and photo count information.
    """
    
    model = Album
    tenant_field = 'church'
    authentication_classes = [CookieJWTAuthentication]
    permission_classes = [TenantIsolationPermission]
    
    def get_queryset(self):
        """Get tenant-scoped album queryset."""
        church = getattr(self.request.user, 'church', None)
        if not church:
            return Album.objects.none()
        
        return Album.objects.filter(church=church).select_related(
            'church', 'created_by'
        ).order_by('-created_at')
    
    def list(self, request, *args, **kwargs):
        """List albums with photo counts."""
        try:
            queryset = self.get_queryset()
            
            # Simple pagination
            limit = min(int(request.GET.get('limit', 50)), 100)
            offset = int(request.GET.get('offset', 0))
            
            total_count = queryset.count()
            albums = queryset[offset:offset + limit]
            
            album_data = []
            for album in albums:
                try:
                    data = {
                        'id': album.id,
                        'title': album.title,
                        'description': album.description,
                        'photo_count': album.photo_count,
                        'is_public': album.is_public,
                        'is_featured': album.is_featured,
                        'event_date': album.event_date,
                        'created_by': album.created_by.email if album.created_by else 'Unknown',
                        'created_at': album.created_at,
                        'updated_at': album.updated_at
                    }
                    
                    # Add latest photo info if available
                    latest_photo = album.latest_photo
                    if latest_photo and latest_photo.has_file:
                        try:
                            data['cover_image_url'] = latest_photo.get_secure_url(expiry_minutes=10)
                        except Exception as e:
                            logger.warning(f"Failed to generate cover image URL for album {album.id}: {e}")
                            data['cover_image_url'] = None
                    else:
                        data['cover_image_url'] = None
                    
                    album_data.append(data)
                except Exception as e:
                    logger.error(f"Failed to serialize album {album.id}: {e}")
                    continue
            
            return Response({
                'albums': album_data,
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'has_next': offset + limit < total_count
            })
        except Exception as e:
            logger.error(f"Failed to list albums: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to load albums', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        Delete an album and all its photos from S3.
        Only admins can delete albums.
        """
        # Check if user is admin
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only administrators can delete albums'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            album = self.get_object()
            album_title = album.title
            church = album.church
            
            # Get all photos in the album
            photos = Photo.objects.filter(album=album, church=church)
            photo_count = photos.count()
            
            # Delete photos from S3
            s3_service = S3MediaService()
            deleted_count = 0
            failed_count = 0
            
            logger.info(f"Starting deletion of album '{album_title}' (ID: {album.id}) with {photo_count} photos")
            
            for photo in photos:
                try:
                    # Delete from S3
                    if photo.s3_key:
                        s3_service.delete_file(photo.s3_key, church)
                        deleted_count += 1
                        logger.debug(f"Deleted photo {photo.id} from S3: {photo.s3_key}")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to delete photo {photo.id} from S3: {e}")
            
            # Delete the album (cascade will delete photo records)
            album.delete()
            
            logger.info(
                f"Album '{album_title}' deleted successfully. "
                f"Photos deleted from S3: {deleted_count}/{photo_count}, Failed: {failed_count}"
            )
            
            return Response({
                'message': f'Album "{album_title}" deleted successfully',
                'photos_deleted': deleted_count,
                'photos_failed': failed_count,
                'total_photos': photo_count
            }, status=status.HTTP_200_OK)
            
        except Album.DoesNotExist:
            return Response(
                {'error': 'Album not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Failed to delete album: {e}", exc_info=True)
            return Response(
                {'error': 'Failed to delete album', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )