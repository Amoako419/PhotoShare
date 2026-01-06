"""
Platform management views for superadmin operations.

This module handles superadmin-only operations for platform management,
including church tenant creation and administration.
"""

import logging
import secrets
import string
from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from tenants.models import Church
from core.models import User
from core.permissions import IsSuperAdmin

logger = logging.getLogger(__name__)


def generate_church_code():
    """
    Generate a secure, unique church code.
    Format: 8 uppercase alphanumeric characters (e.g., 'ABC12XYZ')
    """
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(secrets.choice(alphabet) for _ in range(8))
        # Ensure uniqueness
        if not Church.objects.filter(church_code=code).exists():
            return code


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsSuperAdmin])
def church_management(request):
    """
    Church management endpoint. Superadmin only.
    
    GET: List all churches
    POST: Create a new church
    """
    if request.method == 'POST':
        return create_church(request)
    else:
        return list_churches(request)


def create_church(request):
    """
    Create a new church tenant. Superadmin only.
    
    POST /api/v1/platform/churches/
    Request body:
    {
        "name": "First Baptist Church"
    }
    
    Response:
    {
        "church_id": "uuid-string",
        "church_code": "ABC12XYZ",
        "name": "First Baptist Church",
        "created_at": "2026-01-06T12:00:00Z"
    }
    """
    try:
        church_name = request.data.get('name', '').strip()
        
        if not church_name:
            return Response(
                {'error': 'Church name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(church_name) > 255:
            return Response(
                {'error': 'Church name must be 255 characters or less'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate unique church code
        church_code = generate_church_code()
        
        # Create church tenant
        church = Church.objects.create(
            name=church_name,
            church_code=church_code,
            is_active=True  # Active by default
        )
        
        logger.info(
            f"Superadmin {request.user.email} created church: {church.name} ({church_code})"
        )
        
        return Response({
            'church_id': str(church.id),
            'church_code': church.church_code,
            'name': church.name,
            'created_at': church.created_at.isoformat(),
            'is_active': church.is_active
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating church: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to create church. Please try again.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def list_churches(request):
    """
    List all church tenants. Superadmin only.
    
    GET /api/v1/platform/churches/
    
    Response:
    {
        "churches": [
            {
                "church_id": "uuid",
                "church_code": "ABC12XYZ",
                "name": "First Baptist Church",
                "is_active": true,
                "total_users": 5,
                "admin_count": 2,
                "member_count": 3,
                "created_at": "2026-01-06T12:00:00Z"
            }
        ],
        "total_count": 1,
        "summary": {
            "total_churches": 1,
            "active_churches": 1,
            "total_users": 5
        }
    }
    """
    try:
        churches = Church.objects.all().order_by('-created_at')
        
        total_users_count = 0
        active_churches_count = 0
        
        churches_data = []
        for church in churches:
            admin_count = church.users.filter(role='admin').count()
            member_count = church.users.filter(role='member').count()
            total_users = church.total_users
            
            total_users_count += total_users
            if church.is_active:
                active_churches_count += 1
            
            churches_data.append({
                'church_id': str(church.id),
                'church_code': church.church_code,
                'name': church.name,
                'is_active': church.is_active,
                'total_users': total_users,
                'admin_count': admin_count,
                'member_count': member_count,
                'created_at': church.created_at.isoformat()
            })
        
        return Response({
            'churches': churches_data,
            'total_count': len(churches_data),
            'summary': {
                'total_churches': len(churches_data),
                'active_churches': active_churches_count,
                'total_users': total_users_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing churches: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to fetch churches'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated, IsSuperAdmin])
def church_stats(request, church_id):
    """
    Get detailed analytics for a specific church. Superadmin only.
    
    GET /api/v1/platform/churches/{church_id}/stats/
    
    Response:
    {
        "church": {
            "church_id": "uuid",
            "church_code": "ABC12XYZ",
            "name": "First Baptist Church",
            "is_active": true,
            "created_at": "2026-01-06T12:00:00Z"
        },
        "users": {
            "total": 10,
            "admins": 2,
            "members": 8,
            "active": 9,
            "inactive": 1
        },
        "recent_signups": [
            {
                "user_id": "uuid",
                "email": "user@example.com",
                "role": "member",
                "date_joined": "2026-01-06T12:00:00Z"
            }
        ],
        "activity": {
            "last_signup": "2026-01-06T12:00:00Z",
            "signups_last_7_days": 3,
            "signups_last_30_days": 10
        }
    }
    """
    try:
        # Get church
        church = Church.objects.get(id=church_id)
        
        # Get all users for this church
        users = User.objects.filter(church=church)
        
        # Calculate user stats
        total_users = users.count()
        admin_count = users.filter(role=User.Role.ADMIN).count()
        member_count = users.filter(role=User.Role.MEMBER).count()
        active_users = users.filter(is_active=True).count()
        inactive_users = users.filter(is_active=False).count()
        
        # Get recent signups (last 10)
        recent_users = users.order_by('-date_joined')[:10]
        recent_signups_data = [{
            'user_id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'is_active': user.is_active,
            'date_joined': user.date_joined.isoformat()
        } for user in recent_users]
        
        # Calculate activity metrics
        now = timezone.now()
        seven_days_ago = now - timedelta(days=7)
        thirty_days_ago = now - timedelta(days=30)
        
        signups_last_7_days = users.filter(date_joined__gte=seven_days_ago).count()
        signups_last_30_days = users.filter(date_joined__gte=thirty_days_ago).count()
        
        # Get last signup date
        last_user = users.order_by('-date_joined').first()
        last_signup = last_user.date_joined.isoformat() if last_user else None
        
        # Get last login activity
        last_login_user = users.filter(last_login__isnull=False).order_by('-last_login').first()
        last_activity = last_login_user.last_login.isoformat() if last_login_user else None
        
        return Response({
            'church': {
                'church_id': str(church.id),
                'church_code': church.church_code,
                'name': church.name,
                'is_active': church.is_active,
                'created_at': church.created_at.isoformat()
            },
            'users': {
                'total': total_users,
                'admins': admin_count,
                'members': member_count,
                'active': active_users,
                'inactive': inactive_users
            },
            'recent_signups': recent_signups_data,
            'activity': {
                'last_signup': last_signup,
                'last_activity': last_activity,
                'signups_last_7_days': signups_last_7_days,
                'signups_last_30_days': signups_last_30_days
            }
        })
        
    except Church.DoesNotExist:
        return Response(
            {'error': 'Church not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching church stats for {church_id}: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to fetch church statistics'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsSuperAdmin])
def toggle_church_status(request, church_id):
    """
    Toggle church active status. Superadmin only.
    
    PATCH /api/v1/platform/churches/{church_id}/status/
    
    Request Body:
    {
        "is_active": true/false
    }
    
    Response:
    {
        "church_id": "uuid",
        "church_code": "CODE",
        "name": "Church Name",
        "is_active": true/false,
        "updated_at": "2026-01-06T12:00:00Z"
    }
    """
    try:
        church = Church.objects.get(id=church_id)
        
        # Get the new status from request
        is_active = request.data.get('is_active')
        
        if is_active is None:
            return Response(
                {'error': 'is_active field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate boolean
        if not isinstance(is_active, bool):
            return Response(
                {'error': 'is_active must be a boolean'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update church status
        church.is_active = is_active
        church.save(update_fields=['is_active', 'updated_at'])
        
        logger.info(
            f"Superadmin {request.user.email} {'enabled' if is_active else 'disabled'} "
            f"church {church.name} ({church.church_code})"
        )
        
        return Response({
            'church_id': str(church.id),
            'church_code': church.church_code,
            'name': church.name,
            'is_active': church.is_active,
            'updated_at': church.updated_at.isoformat()
        })
        
    except Church.DoesNotExist:
        return Response(
            {'error': 'Church not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error toggling church status for {church_id}: {e}", exc_info=True)
        return Response(
            {'error': 'Failed to update church status'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )