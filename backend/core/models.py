"""
Core models for multi-tenant church media platform.

This module contains shared models across all tenants, including
the custom User model for identity management and media metadata models.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .tenant_isolation import TenantScopedQuerySetMixin


class CustomUserManager(BaseUserManager):
    """
    Custom user manager for email-based authentication.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and return a regular user with an email and password."""
        if not email:
            raise ValueError('The Email field must be set')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and return a superuser with an email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for multi-tenant church media platform.
    
    Uses email as the unique identifier instead of username.
    Every user belongs to exactly one church for tenant isolation.
    """
    
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        MEMBER = 'member', 'Member'
    
    # Core identity fields
    email = models.EmailField(
        unique=True,
        max_length=255,
        help_text='Email address used for authentication'
    )
    first_name = models.CharField(
        max_length=150,
        blank=True,
        help_text='User\'s first name'
    )
    last_name = models.CharField(
        max_length=150,
        blank=True,
        help_text='User\'s last name'
    )
    
    # Multi-tenant relationship
    church = models.ForeignKey(
        'tenants.Church',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        help_text='Church this user belongs to for tenant isolation'
    )
    
    # Role within the church
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.MEMBER,
        help_text='User\'s role within their church'
    )
    
    # Account status
    is_active = models.BooleanField(
        default=True,
        help_text='Designates whether this user should be treated as active'
    )
    is_staff = models.BooleanField(
        default=False,
        help_text='Designates whether the user can log into the admin site'
    )
    
    # Timestamps
    date_joined = models.DateTimeField(
        default=timezone.now,
        help_text='When the user account was created'
    )
    last_login = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When the user last logged in'
    )
    
    # Custom manager
    objects = CustomUserManager()
    
    # Configuration
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email is already the USERNAME_FIELD
    
    class Meta:
        db_table = 'core_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['church', 'role']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.email
    
    @property
    def full_name(self):
        """Return the user's full name."""
        return f'{self.first_name} {self.last_name}'.strip() or self.email
    
    def get_short_name(self):
        """Return the user's first name."""
        return self.first_name or self.email
    
    @property
    def is_church_admin(self):
        """Check if user has admin role in their church."""
        return self.role == self.Role.ADMIN
    
    def clean(self):
        """Validate the user instance."""
        super().clean()
        # Normalize email
        self.email = self.__class__.objects.normalize_email(self.email)


class Album(TenantScopedQuerySetMixin, models.Model):
    """
    Album model for organizing photos within a church (tenant).
    
    Albums are tenant-scoped collections that group related photos
    for events, ministries, or other organizational purposes.
    
    TENANT ISOLATION: All albums are scoped to a specific church.
    Cross-tenant access is prevented by design.
    """
    
    # CRITICAL: Church field for tenant isolation
    church = models.ForeignKey(
        'tenants.Church',
        on_delete=models.CASCADE,
        related_name='albums',
        help_text="Church that owns this album"
    )
    
    # Album metadata
    title = models.CharField(
        max_length=200,
        help_text="Album title (e.g., 'Easter Service 2026')"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional description of the album contents"
    )
    
    # Organization fields
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_albums',
        help_text="User who created this album"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Album settings
    is_public = models.BooleanField(
        default=False,
        help_text="Whether album is visible to all church members"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether to feature this album prominently"
    )
    
    # Event association (optional)
    event_date = models.DateField(
        null=True, blank=True,
        help_text="Date of the event this album represents"
    )
    
    class Meta:
        verbose_name = 'Album'
        verbose_name_plural = 'Albums'
        # CRITICAL: Indexes for efficient tenant-scoped queries
        indexes = [
            models.Index(fields=['church', 'created_at']),
            models.Index(fields=['church', 'is_public']),
            models.Index(fields=['church', 'is_featured']),
            models.Index(fields=['church', 'event_date']),
            models.Index(fields=['created_by']),
        ]
        # Prevent duplicate album titles within same church
        unique_together = [['church', 'title']]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.church.name})"
    
    def clean(self):
        """Validate album instance."""
        super().clean()
        
        # Ensure created_by user belongs to same church
        if self.created_by and self.church and self.created_by.church != self.church:
            raise ValidationError(
                "Album creator must belong to the same church as the album"
            )
    
    @property
    def photo_count(self):
        """Get number of photos in this album."""
        return self.photos.count()
    
    @property
    def latest_photo(self):
        """Get the most recently added photo in this album."""
        return self.photos.order_by('-created_at').first()


class Photo(TenantScopedQuerySetMixin, models.Model):
    """
    Photo model for storing media metadata within a church (tenant).
    
    Photos are tenant-scoped media objects that contain metadata
    about uploaded images. The actual file storage is handled separately.
    
    TENANT ISOLATION: All photos are scoped to a specific church.
    Cross-tenant access is prevented by design.
    """
    
    # CRITICAL: Church field for tenant isolation
    church = models.ForeignKey(
        'tenants.Church',
        on_delete=models.CASCADE,
        related_name='photos',
        help_text="Church that owns this photo"
    )
    
    # Album association (optional)
    album = models.ForeignKey(
        Album,
        on_delete=models.CASCADE,
        related_name='photos',
        null=True, blank=True,
        help_text="Album this photo belongs to"
    )
    
    # Photo metadata
    title = models.CharField(
        max_length=200,
        help_text="Photo title or caption"
    )
    
    description = models.TextField(
        blank=True,
        help_text="Optional photo description"
    )
    
    # File metadata and S3 storage
    filename = models.CharField(
        max_length=255,
        help_text="Original filename"
    )
    
    # S3 storage key for private file access
    s3_key = models.CharField(
        max_length=500,
        blank=True,
        help_text="S3 object key for secure file access"
    )
    
    file_size = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="File size in bytes"
    )
    
    content_type = models.CharField(
        max_length=100,
        default='image/jpeg',
        help_text="MIME type of the photo"
    )
    
    # Image dimensions
    width = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Image width in pixels"
    )
    
    height = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Image height in pixels"
    )
    
    # Organization fields
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_photos',
        help_text="User who uploaded this photo"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Photo settings
    is_public = models.BooleanField(
        default=False,
        help_text="Whether photo is visible to all church members"
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text="Whether to feature this photo prominently"
    )
    
    # EXIF and technical metadata
    taken_at = models.DateTimeField(
        null=True, blank=True,
        help_text="When the photo was taken (from EXIF data)"
    )
    
    camera_model = models.CharField(
        max_length=100, blank=True,
        help_text="Camera model (from EXIF data)"
    )
    
    location = models.CharField(
        max_length=200, blank=True,
        help_text="Location where photo was taken"
    )
    
    class Meta:
        verbose_name = 'Photo'
        verbose_name_plural = 'Photos'
        # CRITICAL: Indexes for efficient tenant-scoped queries
        indexes = [
            models.Index(fields=['church', 'created_at']),
            models.Index(fields=['church', 'album']),
            models.Index(fields=['church', 'is_public']),
            models.Index(fields=['church', 'is_featured']),
            models.Index(fields=['church', 'taken_at']),
            models.Index(fields=['album', 'created_at']),
            models.Index(fields=['uploaded_by']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} ({self.church.name})"
    
    def clean(self):
        """Validate photo instance."""
        super().clean()
        
        # Ensure uploaded_by user belongs to same church
        if self.uploaded_by and self.church and self.uploaded_by.church != self.church:
            raise ValidationError(
                "Photo uploader must belong to the same church as the photo"
            )
        
        # Ensure album belongs to same church (if specified)
        if self.album and self.church and self.album.church != self.church:
            raise ValidationError(
                "Photo album must belong to the same church as the photo"
            )
    
    @property
    def aspect_ratio(self):
        """Calculate aspect ratio of the image."""
        if self.width and self.height:
            return self.width / self.height
        return None
    
    @property
    def is_landscape(self):
        """Check if image is landscape orientation."""
        ratio = self.aspect_ratio
        return ratio and ratio > 1.0
    
    @property
    def is_portrait(self):
        """Check if image is portrait orientation."""  
        ratio = self.aspect_ratio
        return ratio and ratio < 1.0
    
    @property
    def file_size_mb(self):
        """Get file size in megabytes."""
        if self.file_size:
            return round(self.file_size / (1024 * 1024), 2)
        return None
    
    def get_secure_url(self, expiry_minutes: int = 10) -> str:
        """
        Generate a signed URL for secure access to this photo.
        
        Args:
            expiry_minutes: URL expiration time (5-10 minutes max)
            
        Returns:
            str: Pre-signed URL for secure access
            
        Raises:
            ValidationError: If S3 key is missing or URL generation fails
        """
        if not self.s3_key:
            raise ValidationError("Cannot generate URL: Photo has no S3 key")
        
        from .s3_service import s3_service
        return s3_service.generate_signed_url(
            self.s3_key, 
            self.church, 
            expiry_minutes
        )
    
    def delete_from_s3(self) -> bool:
        """
        Delete the photo file from S3 storage.
        
        Returns:
            bool: True if deletion successful
        """
        if not self.s3_key:
            return True  # Nothing to delete
        
        from .s3_service import s3_service
        return s3_service.delete_file(self.s3_key, self.church)
    
    @property
    def has_file(self) -> bool:
        """Check if photo has an associated S3 file."""
        return bool(self.s3_key)
