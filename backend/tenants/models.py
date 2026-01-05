"""
Tenant models for multi-tenant church media platform.

This module contains models that define tenant boundaries and isolation.
Each church operates as an independent tenant with isolated data.
"""

import uuid
from django.db import models
from django.utils import timezone


class Church(models.Model):
    """
    Church model representing a tenant in the multi-tenant system.
    
    Each church is an independent tenant with its own isolated data,
    users, and media content. The church code provides a human-readable
    identifier that can be rotated for security purposes.
    """
    
    # UUID primary key for security and scalability
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique identifier for the church tenant'
    )
    
    # Church identification
    name = models.CharField(
        max_length=255,
        help_text='Full name of the church'
    )
    
    # Human-readable, rotatable church code
    church_code = models.CharField(
        max_length=50,
        unique=True,
        help_text='Unique human-readable code for the church (can be rotated)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        default=timezone.now,
        help_text='When this church was created in the system'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='When this church record was last updated'
    )
    
    # Status fields for tenant management
    is_active = models.BooleanField(
        default=True,
        help_text='Whether this church tenant is active'
    )
    
    # Branding fields
    logo_url = models.CharField(
        max_length=500,
        blank=True,
        help_text='S3 path to church logo (e.g., tenants/{church_id}/branding/logo.png)'
    )
    
    login_cover_image = models.CharField(
        max_length=500,
        blank=True,
        help_text='S3 path to login page cover image (e.g., tenants/{church_id}/branding/cover.jpg)'
    )
    
    class Meta:
        db_table = 'tenants_church'
        verbose_name = 'Church'
        verbose_name_plural = 'Churches'
        ordering = ['name']
        indexes = [
            models.Index(fields=['church_code']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.name} ({self.church_code})'
    
    @property
    def total_users(self):
        """Get the total number of users in this church."""
        return self.users.count()
    
    @property
    def active_users(self):
        """Get the number of active users in this church."""
        return self.users.filter(is_active=True).count()
    
    def clean(self):
        """Validate the church instance."""
        super().clean()
        # Normalize church code to lowercase for consistency
        if self.church_code:
            self.church_code = self.church_code.lower().strip()
