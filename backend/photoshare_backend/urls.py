"""
URL configuration for photoshare_backend project.

Multi-tenant SaaS application for private church media platform.
Configured for API-first architecture with custom JWT authentication using httpOnly cookies.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Custom JWT Authentication endpoints (using httpOnly cookies)
    # Legacy SimpleJWT endpoints are replaced by our custom auth system
    
    # API versioning - v1
    path('api/v1/core/', include('core.urls')),
    path('api/v1/tenants/', include('tenants.urls')),
    
    # API root - DRF browsable API
    path('api/', include('rest_framework.urls', namespace='rest_framework')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
