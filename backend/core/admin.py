"""
Django admin configuration for core models.

Provides administrative interfaces for user management, albums, and photos with
tenant-aware filtering and church assignment capabilities.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Count
from .models import User, Album, Photo


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Custom admin interface for the User model.
    
    Extends Django's built-in UserAdmin to work with email-based
    authentication and church (tenant) relationships.
    """
    
    # Display configuration
    list_display = [
        'email',
        'full_name',
        'church_display',
        'role',
        'is_active',
        'is_staff',
        'date_joined',
    ]
    
    list_filter = [
        'is_active',
        'is_staff',
        'is_superuser',
        'role',
        'church',
        'date_joined',
    ]
    
    search_fields = [
        'email',
        'first_name',
        'last_name',
        'church__name',
        'church__church_code',
    ]
    
    readonly_fields = [
        'date_joined',
        'last_login',
    ]
    
    # Fieldsets for editing
    fieldsets = [
        ('Authentication', {
            'fields': ['email', 'password']
        }),
        ('Personal Information', {
            'fields': ['first_name', 'last_name']
        }),
        ('Church Assignment', {
            'fields': ['church', 'role']
        }),
        ('Permissions', {
            'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'],
            'classes': ['collapse']
        }),
        ('Timestamps', {
            'fields': ['date_joined', 'last_login'],
            'classes': ['collapse']
        }),
    ]
    
    # Fieldsets for adding new users
    add_fieldsets = [
        ('Required Information', {
            'classes': ['wide'],
            'fields': ['email', 'password1', 'password2']
        }),
        ('Optional Information', {
            'classes': ['wide'],
            'fields': ['first_name', 'last_name', 'church', 'role']
        }),
        ('Permissions', {
            'classes': ['wide', 'collapse'],
            'fields': ['is_active', 'is_staff', 'is_superuser']
        }),
    ]
    
    ordering = ['email']
    
    # Override the username field since we use email
    username_field = 'email'
    
    def church_display(self, obj):
        """Display church information with formatting."""
        if obj.church:
            return format_html(
                '<span title="{}">{}</span>',
                obj.church.name,
                obj.church.church_code
            )
        return format_html('<em style="color: #999;">No church assigned</em>')
    church_display.short_description = 'Church'
    
    def get_queryset(self, request):
        """Optimize queryset with church information."""
        return super().get_queryset(request).select_related('church')


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    """
    Admin interface for Album model with tenant-aware features.
    
    Provides church-scoped album management with photo count tracking
    and efficient filtering for large datasets.
    """
    
    # Display configuration
    list_display = [
        'title',
        'church_display',
        'photo_count_display',
        'created_by',
        'is_public',
        'is_featured',
        'event_date',
        'created_at',
    ]
    
    list_filter = [
        'church',
        'is_public',
        'is_featured',
        'created_at',
        'event_date',
        'created_by',
    ]
    
    search_fields = [
        'title',
        'description',
        'church__name',
        'church__church_code',
        'created_by__email',
    ]
    
    # Form configuration
    fieldsets = [
        ('Album Information', {
            'fields': ['title', 'description', 'church']
        }),
        ('Organization', {
            'fields': ['created_by', 'event_date']
        }),
        ('Visibility Settings', {
            'fields': ['is_public', 'is_featured']
        }),
    ]
    
    # Filtering and optimization
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    # Read-only fields
    readonly_fields = ['created_at', 'updated_at']
    
    def church_display(self, obj):
        """Display church information with formatting."""
        if obj.church:
            return format_html(
                '<span title="{}">{}</span>',
                obj.church.name,
                obj.church.church_code
            )
        return format_html('<em style="color: #999;">No church</em>')
    church_display.short_description = 'Church'
    church_display.admin_order_field = 'church__name'
    
    def photo_count_display(self, obj):
        """Display photo count with link to photos."""
        count = obj.photo_count
        if count > 0:
            return format_html(
                '<a href="/admin/core/photo/?album__id__exact={}" title="View photos in this album">{} photos</a>',
                obj.id,
                count
            )
        return format_html('<em style="color: #999;">0 photos</em>')
    photo_count_display.short_description = 'Photos'
    
    def get_queryset(self, request):
        """Optimize queryset with related data and photo counts."""
        return super().get_queryset(request).select_related(
            'church', 'created_by'
        ).annotate(
            photo_count=Count('photos')
        )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter foreign key choices by tenant context where applicable."""
        if db_field.name == "created_by":
            # Only show users from the same church as the album
            if hasattr(request, '_obj_') and request._obj_ and request._obj_.church:
                kwargs["queryset"] = User.objects.filter(church=request._obj_.church)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    """
    Admin interface for Photo model with tenant-aware features.
    
    Provides church-scoped photo management with metadata display,
    thumbnail previews (when implemented), and efficient filtering.
    """
    
    # Display configuration
    list_display = [
        'title',
        'church_display',
        'album_display',
        'uploaded_by',
        'file_info_display',
        'dimensions_display',
        'is_public',
        'is_featured',
        'created_at',
    ]
    
    list_filter = [
        'church',
        'album',
        'is_public',
        'is_featured',
        'content_type',
        'created_at',
        'taken_at',
        'uploaded_by',
    ]
    
    search_fields = [
        'title',
        'description',
        'filename',
        'church__name',
        'church__church_code',
        'album__title',
        'uploaded_by__email',
        'location',
    ]
    
    # Form configuration
    fieldsets = [
        ('Photo Information', {
            'fields': ['title', 'description', 'church', 'album']
        }),
        ('File Metadata', {
            'fields': ['filename', 'content_type', 'file_size', 'width', 'height'],
            'classes': ['collapse']
        }),
        ('Organization', {
            'fields': ['uploaded_by', 'taken_at', 'location']
        }),
        ('Technical Metadata', {
            'fields': ['camera_model'],
            'classes': ['collapse']
        }),
        ('Visibility Settings', {
            'fields': ['is_public', 'is_featured']
        }),
    ]
    
    # Filtering and optimization
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    # Read-only fields (file metadata should not be manually edited)
    readonly_fields = [
        'created_at', 'updated_at', 'file_size', 'width', 'height', 
        'content_type', 'camera_model'
    ]
    
    def church_display(self, obj):
        """Display church information with formatting."""
        if obj.church:
            return format_html(
                '<span title="{}">{}</span>',
                obj.church.name,
                obj.church.church_code
            )
        return format_html('<em style="color: #999;">No church</em>')
    church_display.short_description = 'Church'
    church_display.admin_order_field = 'church__name'
    
    def album_display(self, obj):
        """Display album information with link."""
        if obj.album:
            return format_html(
                '<a href="/admin/core/album/{}/change/" title="Edit album">{}</a>',
                obj.album.id,
                obj.album.title
            )
        return format_html('<em style="color: #999;">No album</em>')
    album_display.short_description = 'Album'
    album_display.admin_order_field = 'album__title'
    
    def file_info_display(self, obj):
        """Display file size and type information."""
        info_parts = []
        
        if obj.file_size_mb:
            info_parts.append(f"{obj.file_size_mb} MB")
        
        if obj.content_type:
            # Extract just the image type (e.g., "jpeg" from "image/jpeg")
            image_type = obj.content_type.split('/')[-1].upper()
            info_parts.append(image_type)
        
        if info_parts:
            return format_html(
                '<span title="File: {}">{}</span>',
                obj.filename,
                ' • '.join(info_parts)
            )
        
        return format_html('<em style="color: #999;">Unknown</em>')
    file_info_display.short_description = 'File Info'
    
    def dimensions_display(self, obj):
        """Display image dimensions and orientation."""
        if obj.width and obj.height:
            orientation = ""
            if obj.is_landscape:
                orientation = "📐"  # Landscape icon
            elif obj.is_portrait:
                orientation = "📱"  # Portrait icon
            else:
                orientation = "⬜"  # Square icon
            
            return format_html(
                '<span title="Aspect ratio: {:.2f}">{} {}×{}</span>',
                obj.aspect_ratio or 0,
                orientation,
                obj.width,
                obj.height
            )
        
        return format_html('<em style="color: #999;">Unknown</em>')
    dimensions_display.short_description = 'Dimensions'
    
    def get_queryset(self, request):
        """Optimize queryset with related data."""
        return super().get_queryset(request).select_related(
            'church', 'album', 'uploaded_by'
        )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Filter foreign key choices by tenant context."""
        if db_field.name == "album":
            # Only show albums from the same church as the photo
            if hasattr(request, '_obj_') and request._obj_ and request._obj_.church:
                kwargs["queryset"] = Album.objects.filter(church=request._obj_.church)
        elif db_field.name == "uploaded_by":
            # Only show users from the same church as the photo
            if hasattr(request, '_obj_') and request._obj_ and request._obj_.church:
                kwargs["queryset"] = User.objects.filter(church=request._obj_.church)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
