"""
Tenants app URLs for multi-tenant functionality.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

# Create a router for ViewSets (will be used when models/views are implemented)
router = DefaultRouter()

urlpatterns = [
    # Tenant management endpoints will be added here when models/views are implemented
    # Example: tenant creation, domain management, etc.
]

# Include router URLs
urlpatterns += router.urls