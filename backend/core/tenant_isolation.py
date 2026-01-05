"""
Tenant Isolation Middleware and Permissions

Implements strict tenant isolation for multi-tenant SaaS application.
Ensures users can only access data from their assigned church (tenant).

THREAT MODEL:
1. Malicious authenticated users attempting cross-tenant access
2. Accidental data leakage through missing tenant filters
3. API endpoints that forget to enforce tenant boundaries
4. Privilege escalation attempts through tenant manipulation

SECURITY PRINCIPLES:
- Fail securely (reject unknown/missing tenant context)
- No silent failures (explicit errors for violations)
- No superuser bypass (consistent enforcement)
- Default deny (require explicit tenant access)
"""

from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from rest_framework import permissions, status
from rest_framework.exceptions import PermissionDenied
import logging

logger = logging.getLogger(__name__)


class JWTCookieAuthenticationMiddleware:
    """
    Middleware to authenticate users from JWT cookies early in the request cycle.
    
    This allows the tenant isolation middleware to work properly with JWT authentication
    by setting request.user before process_view runs.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
    def __call__(self, request):
        # Try to authenticate from JWT cookie for API requests
        if request.path.startswith('/api/'):
            access_token = request.COOKIES.get('access_token')
            
            if access_token and not request.user.is_authenticated:
                # Import here to avoid circular imports
                from .authentication import CookieJWTAuthentication
                
                auth = CookieJWTAuthentication()
                try:
                    user_auth = auth.authenticate(request)
                    if user_auth is not None:
                        request.user = user_auth[0]
                        logger.debug(f"JWT cookie authenticated: {request.user.email}")
                except Exception as e:
                    logger.debug(f"JWT cookie authentication failed: {e}")
                    pass
        
        response = self.get_response(request)
        return response


class TenantContextMiddleware(MiddlewareMixin):
    """
    Middleware that injects tenant context into all authenticated requests.
    
    For authenticated users:
    - Sets request.church to the user's assigned church
    - Sets request.is_tenant_isolated = True
    - Logs tenant context for audit trail
    
    For unauthenticated requests:
    - Sets request.church = None  
    - Sets request.is_tenant_isolated = False
    - Allows through (authentication will be handled by auth system)
    
    SECURITY: This middleware must run AFTER authentication middleware
    to ensure user.church is available.
    
    For DRF views with token authentication, use process_view to run after
    DRF's authentication is complete.
    """
    
    def process_request(self, request):
        """Add tenant context to request for session-based auth."""
        
        # Initialize tenant context
        request.church = None
        request.is_tenant_isolated = False
        
        # Skip non-API requests (admin, static files, etc.)
        if not request.path.startswith('/api/'):
            return None
            
        # For session-authenticated users (Django admin, browsable API)
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'church') and request.user.church:
                request.church = request.user.church
                request.is_tenant_isolated = True
                
                logger.info(
                    f"Tenant access: user={request.user.email}, "
                    f"church={request.church.name}, "
                    f"path={request.path}, "
                    f"method={request.method}"
                )
        
        return None
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        """Add tenant context after DRF authentication for API views."""
        
        # Skip non-API requests
        if not request.path.startswith('/api/'):
            return None
            
        # If already processed (from session auth in process_request), skip
        if request.is_tenant_isolated:
            return None
            
        # After DRF authentication runs, user should be properly set
        # This handles JWT cookie authentication and other DRF auth methods
        if hasattr(request, 'user') and request.user.is_authenticated:
            if hasattr(request.user, 'church') and request.user.church:
                request.church = request.user.church
                request.is_tenant_isolated = True
                
                # Audit log for tenant access
                logger.info(
                    f"Tenant access (DRF): user={request.user.email}, "
                    f"church={request.church.name}, "
                    f"path={request.path}, "
                    f"method={request.method}"
                )
            else:
                # User is authenticated but has no church assignment
                logger.warning(
                    f"User {request.user.email} authenticated but no church assigned "
                    f"for {request.path}"
                )
        
        # Don't block at middleware level for DRF views
        # Let view-level authentication and permissions handle tenant isolation
        return None


class TenantIsolationPermission(permissions.BasePermission):
    """
    Permission class that enforces strict tenant isolation.
    
    SECURITY RULES:
    1. Only authenticated users with church assignment can access tenant data
    2. Users can only access data from their assigned church
    3. No cross-tenant access allowed (even for staff/superusers)
    4. Explicit failure for any tenant boundary violation
    
    This permission should be applied to ALL views that handle tenant data.
    """
    
    message = "Access denied: Tenant isolation violation"
    
    def has_permission(self, request, view):
        """Check if user has permission to access tenant-scoped resources."""
        
        # Must be authenticated
        if not request.user.is_authenticated:
            return False
            
        # Must have tenant context injected by middleware
        if not hasattr(request, 'is_tenant_isolated') or not request.is_tenant_isolated:
            logger.error(
                f"SECURITY: Missing tenant context for {request.user.email} "
                f"on {request.path} - middleware may not be configured"
            )
            return False
            
        # Must have church assignment
        if not request.church:
            logger.warning(
                f"SECURITY: User {request.user.email} lacks church assignment "
                f"for tenant-scoped access to {request.path}"
            )
            return False
            
        # Audit successful tenant permission check
        logger.debug(
            f"Tenant permission granted: user={request.user.email}, "
            f"church={request.church.name}, path={request.path}"
        )
        
        return True
    
    def has_object_permission(self, request, view, obj):
        """Check if user can access specific tenant-scoped object."""
        
        # First check basic tenant permission
        if not self.has_permission(request, view):
            return False
            
        # Object must have church attribute for tenant isolation
        if not hasattr(obj, 'church'):
            logger.error(
                f"SECURITY: Object {type(obj).__name__} lacks church attribute "
                f"for tenant isolation check by {request.user.email}"
            )
            return False
            
        # Object must belong to user's church
        if obj.church != request.church:
            logger.warning(
                f"SECURITY: Cross-tenant access attempt by {request.user.email} "
                f"(church: {request.church.name}) to {type(obj).__name__} "
                f"belonging to {obj.church.name if obj.church else 'None'}"
            )
            return False
            
        return True


class SuperuserBypassDenied(permissions.BasePermission):
    """
    Permission that explicitly denies superuser bypass of tenant isolation.
    
    This permission should be combined with TenantIsolationPermission
    to ensure even superusers cannot bypass tenant boundaries.
    
    RATIONALE: In a multi-tenant system, even superusers should operate
    within tenant boundaries to prevent accidental cross-tenant operations.
    """
    
    message = "Superuser tenant bypass denied - explicit tenant scoping required"
    
    def has_permission(self, request, view):
        """Deny superuser bypass attempts."""
        
        # If user is superuser but trying to access without tenant context
        if (request.user.is_authenticated and 
            request.user.is_superuser and 
            (not hasattr(request, 'is_tenant_isolated') or not request.is_tenant_isolated)):
            
            logger.warning(
                f"SECURITY: Superuser {request.user.email} attempted tenant bypass "
                f"on {request.path} - denied per security policy"
            )
            return False
            
        return True


class TenantScopedQuerySetMixin:
    """
    Mixin for Django models to provide tenant-scoped querysets.
    
    Automatically filters querysets by church context from request.
    Prevents accidental cross-tenant data access in views.
    
    Usage:
        class MyModel(TenantScopedQuerySetMixin, models.Model):
            church = models.ForeignKey(Church, on_delete=models.CASCADE)
            # other fields...
            
        # In views:
        queryset = MyModel.objects.tenant_scoped(request)
    """
    
    class Meta:
        abstract = True
    
    @classmethod
    def get_tenant_scoped_queryset(cls, request):
        """
        Get queryset filtered by request's tenant context.
        
        Args:
            request: Django request with tenant context
            
        Returns:
            QuerySet: Filtered by request.church
            
        Raises:
            PermissionDenied: If tenant context is missing or invalid
        """
        
        # Verify tenant context
        if not hasattr(request, 'is_tenant_isolated') or not request.is_tenant_isolated:
            logger.error(
                f"SECURITY: Attempt to get tenant queryset without tenant context "
                f"by {getattr(request.user, 'email', 'anonymous')} on {cls.__name__}"
            )
            raise PermissionDenied("Tenant context required for data access")
            
        if not request.church:
            logger.error(
                f"SECURITY: Attempt to get tenant queryset without church assignment "
                f"by {request.user.email} on {cls.__name__}"
            )
            raise PermissionDenied("Church assignment required for data access")
            
        # Return church-filtered queryset
        logger.debug(
            f"Tenant queryset: {cls.__name__} filtered for church {request.church.name} "
            f"by user {request.user.email}"
        )
        
        return cls.objects.filter(church=request.church)


def enforce_tenant_isolation(view_func):
    """
    Decorator to enforce tenant isolation on function-based views.
    
    Usage:
        @enforce_tenant_isolation
        def my_view(request):
            # request.church is guaranteed to be valid
            # Only tenant-scoped data accessible
            pass
    """
    def wrapper(request, *args, **kwargs):
        # Check tenant isolation
        permission = TenantIsolationPermission()
        if not permission.has_permission(request, None):
            logger.warning(
                f"SECURITY: Tenant isolation violation in view {view_func.__name__} "
                f"by {getattr(request.user, 'email', 'anonymous')}"
            )
            raise PermissionDenied("Tenant access denied")
            
        return view_func(request, *args, **kwargs)
    
    return wrapper


# Utility functions for tenant-aware operations

def get_tenant_object_or_404(model_class, request, **kwargs):
    """
    Get object filtered by tenant scope or raise 404.
    
    Prevents cross-tenant access by always filtering by request.church.
    
    Args:
        model_class: Django model class
        request: Request with tenant context
        **kwargs: Filter parameters
        
    Returns:
        Model instance from user's church
        
    Raises:
        Http404: If object not found in user's church
        PermissionDenied: If tenant context invalid
    """
    from django.shortcuts import get_object_or_404
    
    # Verify tenant context
    if not hasattr(request, 'is_tenant_isolated') or not request.is_tenant_isolated:
        raise PermissionDenied("Tenant context required")
        
    if not request.church:
        raise PermissionDenied("Church assignment required")
    
    # Always add church filter
    kwargs['church'] = request.church
    
    obj = get_object_or_404(model_class, **kwargs)
    
    logger.debug(
        f"Tenant object access: {model_class.__name__}({kwargs}) "
        f"by {request.user.email} in church {request.church.name}"
    )
    
    return obj