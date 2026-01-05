"""
Tenants app URLs for multi-tenant functionality.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter
from . import views

# Create a router for ViewSets (will be used when models/views are implemented)
router = DefaultRouter()

urlpatterns = [
    # Authenticated tenant branding (requires login)
    path('branding/', views.tenant_branding_view, name='tenant-branding'),
    
    # Public tenant branding (for login page, requires church_code param)
    path('branding/public/', views.public_tenant_branding_view, name='public-tenant-branding'),
]

# Include router URLs
urlpatterns += router.urls