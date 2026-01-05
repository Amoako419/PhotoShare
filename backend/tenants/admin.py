"""
Django admin configuration for tenant models.

Provides administrative interfaces for managing churches (tenants)
and related tenant-specific functionality.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import Church


@admin.register(Church)
class ChurchAdmin(admin.ModelAdmin):
    """
    Admin interface for Church (tenant) management.
    
    Provides comprehensive management of church tenants with
    filtering, searching, and bulk operations.
    """
    
    list_display = [
        'name',
        'church_code',
        'total_users_display',
        'active_users_display',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'is_active',
        'created_at',
    ]
    
    search_fields = [
        'name',
        'church_code',
    ]
    
    readonly_fields = [
        'id',
        'created_at',
        'updated_at',
        'total_users_display',
        'active_users_display',
    ]
    
    fieldsets = [
        ('Church Information', {
            'fields': ['name', 'church_code']
        }),
        ('Status', {
            'fields': ['is_active']
        }),
        ('Statistics', {
            'fields': ['total_users_display', 'active_users_display'],
            'classes': ['collapse']
        }),
        ('System Information', {
            'fields': ['id', 'created_at', 'updated_at'],
            'classes': ['collapse']
        }),
    ]
    
    ordering = ['name']
    
    def total_users_display(self, obj):
        """Display total number of users in the church."""
        count = obj.total_users
        return format_html('<strong>{}</strong>', count)
    total_users_display.short_description = 'Total Users'
    
    def active_users_display(self, obj):
        """Display number of active users in the church."""
        count = obj.active_users
        return format_html('<span style="color: green;">{}</span>', count)
    active_users_display.short_description = 'Active Users'
    
    def get_queryset(self, request):
        """Optimize queryset with prefetch for user counts."""
        return super().get_queryset(request).prefetch_related('users')
