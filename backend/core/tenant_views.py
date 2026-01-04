"""
Tenant-Aware Base Views and Mixins

Provides secure base classes for views that handle tenant-scoped data.
All views automatically enforce tenant isolation and filter data by church.

SECURITY GUARANTEE: Views using these base classes cannot accidentally
expose cross-tenant data or allow unauthorized tenant access.
"""

from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models
import logging

from .tenant_isolation import (
    TenantIsolationPermission,
    SuperuserBypassDenied,
    TenantScopedQuerySetMixin,
    get_tenant_object_or_404
)

logger = logging.getLogger(__name__)


class TenantViewMixin:
    """
    Mixin that enforces tenant isolation for all view operations.
    
    SECURITY FEATURES:
    - Automatically applies tenant isolation permissions
    - Filters all querysets by request.church
    - Prevents cross-tenant object access
    - Logs all tenant-scoped operations for audit
    
    Usage:
        class MyViewSet(TenantViewMixin, viewsets.ModelViewSet):
            model = MyModel
            serializer_class = MySerializer
    """
    
    # Enforce tenant isolation permissions
    permission_classes = [TenantIsolationPermission, SuperuserBypassDenied]
    
    def get_queryset(self):
        """Return queryset filtered by user's church."""
        
        # Ensure we have a model defined
        if not hasattr(self, 'model'):
            raise NotImplementedError(
                "TenantViewMixin requires 'model' attribute to be defined"
            )
        
        # Verify model has church field for tenant isolation
        if not hasattr(self.model, '_meta') or not any(
            field.name == 'church' for field in self.model._meta.fields
        ):
            raise ValueError(
                f"Model {self.model.__name__} must have 'church' field for tenant isolation"
            )
        
        # Get tenant-scoped queryset
        queryset = self.model.objects.filter(church=self.request.church)
        
        # Log queryset access for audit
        logger.info(
            f"Tenant queryset access: {self.model.__name__} by {self.request.user.email} "
            f"in church {self.request.church.name} (action: {self.action})"
        )
        
        return queryset
    
    def get_object(self):
        """Get object ensuring it belongs to user's church."""
        
        # Use standard DRF get_object but with tenant-filtered queryset
        obj = super().get_object()
        
        # Double-check tenant isolation (defense in depth)
        if hasattr(obj, 'church') and obj.church != self.request.church:
            logger.error(
                f"SECURITY: Cross-tenant object access blocked - "
                f"user {self.request.user.email} (church: {self.request.church.name}) "
                f"attempted access to {type(obj).__name__} from {obj.church.name}"
            )
            # This should never happen if queryset filtering works correctly
            # But we fail securely just in case
            from rest_framework.exceptions import NotFound
            raise NotFound("Object not found")
        
        return obj
    
    def perform_create(self, serializer):
        """Create object with automatic church assignment."""
        
        # Automatically assign church to new objects
        serializer.save(church=self.request.church)
        
        logger.info(
            f"Tenant object created: {serializer.instance.__class__.__name__} "
            f"by {self.request.user.email} in church {self.request.church.name}"
        )
    
    def perform_update(self, serializer):
        """Update object ensuring tenant isolation."""
        
        # Ensure church cannot be changed via update
        if 'church' in serializer.validated_data:
            if serializer.validated_data['church'] != self.request.church:
                logger.warning(
                    f"SECURITY: Attempted church reassignment by {self.request.user.email} "
                    f"blocked - objects cannot change tenant boundaries"
                )
                # Remove church from update data to prevent reassignment
                del serializer.validated_data['church']
        
        serializer.save()
        
        logger.info(
            f"Tenant object updated: {serializer.instance.__class__.__name__} "
            f"by {self.request.user.email} in church {self.request.church.name}"
        )


class TenantModelViewSet(TenantViewMixin, viewsets.ModelViewSet):
    """
    Complete ModelViewSet with tenant isolation enforcement.
    
    Provides full CRUD operations scoped to user's church.
    
    Usage:
        class PhotoViewSet(TenantModelViewSet):
            model = Photo
            serializer_class = PhotoSerializer
            
            # Additional customizations...
    """
    pass


class TenantReadOnlyViewSet(TenantViewMixin, viewsets.ReadOnlyModelViewSet):
    """
    Read-only ViewSet with tenant isolation.
    
    Usage:
        class ReportsViewSet(TenantReadOnlyViewSet):
            model = Report
            serializer_class = ReportSerializer
    """
    pass


class TenantListCreateView(TenantViewMixin, generics.ListCreateAPIView):
    """
    List and create view with tenant isolation.
    
    Usage:
        class EventListCreateView(TenantListCreateView):
            model = Event
            serializer_class = EventSerializer
    """
    pass


class TenantDetailView(TenantViewMixin, generics.RetrieveUpdateDestroyAPIView):
    """
    Detail view with tenant isolation.
    
    Usage:
        class EventDetailView(TenantDetailView):
            model = Event
            serializer_class = EventSerializer
    """
    pass


# Usage Examples with Real Models

def example_album_viewset():
    """
    Example of how to create a ViewSet for Album model.
    
    This demonstrates the minimal code needed to create a secure,
    tenant-isolated ViewSet using the Album model we created.
    """
    from .models import Album
    
    class AlbumViewSet(TenantModelViewSet):
        model = Album
        # serializer_class = AlbumSerializer  # Would be defined separately
        
        # Additional customizations can be added here
        # All tenant isolation is handled automatically
    
    return AlbumViewSet


def example_photo_viewset():
    """
    Example of how to create a ViewSet for Photo model.
    
    This demonstrates the minimal code needed to create a secure,
    tenant-isolated ViewSet using the Photo model we created.
    """
    from .models import Photo
    
    class PhotoViewSet(TenantModelViewSet):
        model = Photo
        # serializer_class = PhotoSerializer  # Would be defined separately
        
        @action(detail=False, methods=['get'])
        def my_uploads(self, request):
            """Get photos uploaded by current user in their church."""
            
            # Queryset is automatically filtered by church via TenantViewMixin
            photos = self.get_queryset().filter(uploaded_by=request.user)
            
            return Response({
                'count': photos.count(),
                'message': f'Photos uploaded by {request.user.email} in {request.church.name}'
            })
    
    return PhotoViewSet


def example_function_based_view(request, photo_id):
    """
    Example function-based view with tenant isolation.
    
    Demonstrates how to use tenant isolation utilities in function views
    with the real Photo model.
    """
    from .tenant_isolation import enforce_tenant_isolation, get_tenant_object_or_404
    from .models import Photo
    
    # Apply tenant isolation decorator
    @enforce_tenant_isolation
    def _inner_view(request, photo_id):
        # Get tenant-scoped object
        photo = get_tenant_object_or_404(Photo, request, id=photo_id)
        
        # Process photo (guaranteed to belong to user's church)
        return {
            'photo': photo.title,
            'church': photo.church.name,
            'user_church': request.church.name,
            'tenant_isolated': True,
            'file_info': {
                'filename': photo.filename,
                'size_mb': photo.file_size_mb,
                'dimensions': f'{photo.width}×{photo.height}' if photo.width else None
            }
        }
    
    return _inner_view(request, photo_id)