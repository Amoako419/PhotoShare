"""
Custom permission classes for role-based access control.
"""

from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission class to check if user is a superadmin.
    Superadmins have full platform access with no tenant restrictions.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and
            request.user.role == 'superadmin'
        )


class IsAdmin(permissions.BasePermission):
    """
    Permission class to check if user is an admin (church admin).
    Admins have full access to their church tenant's data.
    """
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            hasattr(request.user, 'role') and
            request.user.role == 'admin'
        )


class IsAdminOrReadOnly(permissions.BasePermission):
    """
    Permission class to allow admins full access, members read-only.
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Admins have full access
        if hasattr(request.user, 'role') and request.user.role == 'admin':
            return True
        
        # Members have read-only access
        if request.method in permissions.SAFE_METHODS:
            return True
        
        return False
