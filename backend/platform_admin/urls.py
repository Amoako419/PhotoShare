"""
Platform management URL configuration.

Superadmin-only endpoints for platform operations.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Church management
    path('churches/', views.church_management, name='church_management'),
    path('churches/<uuid:church_id>/stats/', views.church_stats, name='church_stats'),
    path('churches/<uuid:church_id>/status/', views.toggle_church_status, name='toggle_church_status'),
]
