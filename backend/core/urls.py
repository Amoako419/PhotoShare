"""
Core app URLs for shared functionality across tenants.
Includes authentication and photo management endpoints.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter
from . import auth_views
from .photo_views import (
    PhotoUploadView,
    PhotoAccessView,
    PhotoViewSet
)

# Create a router for ViewSets
router = DefaultRouter()
router.register(r'photos', PhotoViewSet, basename='photo')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', auth_views.login_view, name='login'),
    path('auth/logout/', auth_views.logout_view, name='logout'),
    path('auth/refresh/', auth_views.refresh_view, name='refresh'),
    path('auth/user/', auth_views.user_info_view, name='user_info'),
    
    # Photo management endpoints
    path('photos/upload/', PhotoUploadView.as_view(), name='photo_upload'),
    path('photos/<int:photo_id>/access/', PhotoAccessView.as_view(), name='photo_access'),
    
    # Core API endpoints
]

# Include router URLs
urlpatterns += router.urls