"""
Core models for multi-tenant church media platform.

This module contains shared models across all tenants, including
the custom User model for identity management.
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


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
    
    # Multi-tenant relationship (will be added later when Church model exists)
    # church = models.ForeignKey(
    #     'tenants.Church',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name='users',
    #     help_text='Church this user belongs to for tenant isolation'
    # )
    
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
            # models.Index(fields=['church', 'role']),  # Will be added when church field exists
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
