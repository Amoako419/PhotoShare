"""
Church assignment service for multi-tenant user registration.

This service handles the critical process of assigning users to church tenants
using church codes. Church codes are used ONLY ONCE during signup to resolve
to a church_id and establish tenant boundaries.

Security Principles:
- Church codes are single-use validation tokens, not authentication
- Users can only be assigned to a church ONCE (unless admin override)
- Church IDs are never exposed directly to prevent tenant confusion
- Rate limiting prevents brute force church code attacks
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Tuple, Dict, Any
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from tenants.models import Church
from core.models import User

logger = logging.getLogger(__name__)


class ChurchAssignmentError(Exception):
    """Base exception for church assignment errors."""
    pass


class InvalidChurchCodeError(ChurchAssignmentError):
    """Church code is invalid, inactive, or doesn't exist."""
    pass


class UserAlreadyAssignedError(ChurchAssignmentError):
    """User is already assigned to a church."""
    pass


class RateLimitExceededError(ChurchAssignmentError):
    """Rate limit for church code attempts has been exceeded."""
    pass


class ChurchAssignmentService:
    """
    Service for handling church code validation and user assignment.
    
    This service ensures secure, one-time assignment of users to church
    tenants using church codes as validation tokens.
    """
    
    # Rate limiting configuration
    MAX_ATTEMPTS_PER_HOUR = 10
    MAX_ATTEMPTS_PER_DAY = 50
    RATE_LIMIT_CACHE_PREFIX = 'church_code_attempts'
    
    @classmethod
    def validate_church_code(cls, church_code: str) -> Church:
        """
        Validate a church code and return the associated church.
        
        Args:
            church_code: The church code to validate
            
        Returns:
            Church: The validated church object
            
        Raises:
            InvalidChurchCodeError: If church code is invalid or inactive
        """
        if not church_code or not church_code.strip():
            logger.warning("Empty church code validation attempted")
            raise InvalidChurchCodeError("Church code is required")
        
        # Normalize church code (consistent with Church.clean())
        normalized_code = church_code.lower().strip()
        
        try:
            church = Church.objects.get(
                church_code=normalized_code,
                is_active=True
            )
            logger.info(f"Church code '{normalized_code}' validated successfully for church: {church.name}")
            return church
            
        except Church.DoesNotExist:
            logger.warning(f"Invalid church code attempted: '{normalized_code}'")
            raise InvalidChurchCodeError("Invalid church code")
    
    @classmethod
    def check_rate_limits(cls, identifier: str) -> None:
        """
        Check if rate limits have been exceeded for church code attempts.
        
        Args:
            identifier: Unique identifier for rate limiting (IP, user_id, etc.)
            
        Raises:
            RateLimitExceededError: If rate limits are exceeded
        """
        now = timezone.now()
        
        # Check hourly limit
        hourly_key = f"{cls.RATE_LIMIT_CACHE_PREFIX}:hourly:{identifier}:{now.strftime('%Y%m%d%H')}"
        hourly_attempts = cache.get(hourly_key, 0)
        
        if hourly_attempts >= cls.MAX_ATTEMPTS_PER_HOUR:
            logger.warning(f"Hourly rate limit exceeded for identifier: {identifier}")
            raise RateLimitExceededError("Too many attempts. Please try again later.")
        
        # Check daily limit
        daily_key = f"{cls.RATE_LIMIT_CACHE_PREFIX}:daily:{identifier}:{now.strftime('%Y%m%d')}"
        daily_attempts = cache.get(daily_key, 0)
        
        if daily_attempts >= cls.MAX_ATTEMPTS_PER_DAY:
            logger.warning(f"Daily rate limit exceeded for identifier: {identifier}")
            raise RateLimitExceededError("Daily attempt limit exceeded. Please contact support.")
    
    @classmethod
    def increment_rate_limit_counter(cls, identifier: str) -> None:
        """
        Increment rate limit counters for an identifier.
        
        Args:
            identifier: Unique identifier for rate limiting
        """
        now = timezone.now()
        
        # Increment hourly counter
        hourly_key = f"{cls.RATE_LIMIT_CACHE_PREFIX}:hourly:{identifier}:{now.strftime('%Y%m%d%H')}"
        cache.set(hourly_key, cache.get(hourly_key, 0) + 1, timeout=3600)  # 1 hour
        
        # Increment daily counter  
        daily_key = f"{cls.RATE_LIMIT_CACHE_PREFIX}:daily:{identifier}:{now.strftime('%Y%m%d')}"
        cache.set(daily_key, cache.get(daily_key, 0) + 1, timeout=86400)  # 24 hours
    
    @classmethod
    def can_assign_church(cls, user: User) -> Tuple[bool, Optional[str]]:
        """
        Check if a user can be assigned to a church.
        
        Args:
            user: The user to check
            
        Returns:
            Tuple of (can_assign: bool, reason: Optional[str])
        """
        if not user.is_active:
            return False, "User account is inactive"
        
        if user.church_id:
            return False, "User is already assigned to a church"
        
        return True, None
    
    @classmethod
    @transaction.atomic
    def assign_church_to_user(
        cls, 
        user: User, 
        church_code: str, 
        identifier: str = None,
        admin_override: bool = False
    ) -> Dict[str, Any]:
        """
        Assign a church to a user using a church code.
        
        This is the main entry point for church assignment. It validates
        the church code, checks permissions, and performs the assignment.
        
        Args:
            user: The user to assign to a church
            church_code: The church code to validate and use for assignment
            identifier: Rate limiting identifier (IP, user_id, etc.)
            admin_override: Whether this is an admin override (bypasses some checks)
            
        Returns:
            Dict containing assignment result information
            
        Raises:
            InvalidChurchCodeError: Invalid or inactive church code
            UserAlreadyAssignedError: User already has a church assignment
            RateLimitExceededError: Rate limits exceeded
        """
        start_time = time.time()
        
        try:
            # Rate limiting (skip for admin overrides)
            if not admin_override and identifier:
                cls.check_rate_limits(identifier)
            
            # Validate church code
            church = cls.validate_church_code(church_code)
            
            # Check if user can be assigned
            can_assign, reason = cls.can_assign_church(user)
            
            if not can_assign:
                if admin_override and reason == "User is already assigned to a church":
                    # Admin override: allow reassignment
                    logger.info(f"Admin override: Reassigning user {user.email} from church {user.church} to {church.name}")
                else:
                    logger.warning(f"Church assignment failed for user {user.email}: {reason}")
                    if reason == "User is already assigned to a church":
                        raise UserAlreadyAssignedError(reason)
                    else:
                        raise ChurchAssignmentError(reason)
            
            # Perform the assignment
            old_church = user.church
            user.church = church
            user.save(update_fields=['church'])
            
            # Log the assignment
            if old_church:
                logger.info(f"User {user.email} reassigned from {old_church.name} to {church.name} (admin_override={admin_override})")
            else:
                logger.info(f"User {user.email} assigned to church {church.name}")
            
            # Increment rate limit counter (even for successful attempts)
            if not admin_override and identifier:
                cls.increment_rate_limit_counter(identifier)
            
            processing_time = time.time() - start_time
            
            return {
                'success': True,
                'church_name': church.name,
                'church_uuid': str(church.id),  # Safe to return for logging/admin purposes
                'previous_church': old_church.name if old_church else None,
                'admin_override': admin_override,
                'processing_time_ms': round(processing_time * 1000, 2)
            }
            
        except (InvalidChurchCodeError, UserAlreadyAssignedError, RateLimitExceededError):
            # Increment rate limit counter for failed attempts too
            if not admin_override and identifier:
                cls.increment_rate_limit_counter(identifier)
            raise
            
        except Exception as e:
            logger.error(f"Unexpected error during church assignment for user {user.email}: {str(e)}")
            if not admin_override and identifier:
                cls.increment_rate_limit_counter(identifier)
            raise ChurchAssignmentError("An unexpected error occurred during church assignment")
    
    @classmethod
    def get_rate_limit_status(cls, identifier: str) -> Dict[str, Any]:
        """
        Get current rate limit status for an identifier.
        
        Args:
            identifier: The identifier to check
            
        Returns:
            Dict with current attempt counts and limits
        """
        now = timezone.now()
        
        hourly_key = f"{cls.RATE_LIMIT_CACHE_PREFIX}:hourly:{identifier}:{now.strftime('%Y%m%d%H')}"
        daily_key = f"{cls.RATE_LIMIT_CACHE_PREFIX}:daily:{identifier}:{now.strftime('%Y%m%d')}"
        
        hourly_attempts = cache.get(hourly_key, 0)
        daily_attempts = cache.get(daily_key, 0)
        
        return {
            'hourly_attempts': hourly_attempts,
            'hourly_limit': cls.MAX_ATTEMPTS_PER_HOUR,
            'hourly_remaining': max(0, cls.MAX_ATTEMPTS_PER_HOUR - hourly_attempts),
            'daily_attempts': daily_attempts,
            'daily_limit': cls.MAX_ATTEMPTS_PER_DAY,
            'daily_remaining': max(0, cls.MAX_ATTEMPTS_PER_DAY - daily_attempts),
        }