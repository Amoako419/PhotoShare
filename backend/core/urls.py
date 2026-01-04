"""
Core app URLs for shared functionality across tenants.
"""

from django.urls import path
from rest_framework.routers import DefaultRouter

# Create a router for ViewSets (will be used when models/views are implemented)
router = DefaultRouter()

urlpatterns = [
    # Core API endpoints will be added here when models/views are implemented
    # Example: health check, system status, etc.
]

# Include router URLs
urlpatterns += router.urls