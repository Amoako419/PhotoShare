"""
Custom JWT Authentication Views and Serializers for Multi-Tenant System

Implements secure JWT authentication with:
- Custom token payload including church_id and role
- httpOnly cookie-based token storage
- Login, logout, and refresh endpoints
- Tenant-aware token claims
"""

from datetime import timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from rest_framework import serializers, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
import logging

from core.models import User

logger = logging.getLogger(__name__)

# Token lifetime constants
ACCESS_TOKEN_LIFETIME = timedelta(hours=1)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT serializer that includes church_id and role in token payload.
    
    Token payload will include:
    - user_id: Primary key of the user
    - church_id: UUID of the user's church (null if not assigned)
    - role: User's role in the church
    - email: User's email address
    """
    
    def validate(self, attrs):
        """Override validate to add church context to token."""
        data = super().validate(attrs)
        
        # Add custom claims to both access and refresh tokens
        refresh = self.get_token(self.user)
        
        # Add church and role information
        refresh['church_id'] = str(self.user.church.id) if self.user.church else None
        refresh['church_name'] = self.user.church.name if self.user.church else None
        refresh['role'] = self.user.role
        refresh['email'] = self.user.email
        
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)
        
        # Add user info for frontend (not in token)
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'role': self.user.role,
            'church': {
                'id': str(self.user.church.id) if self.user.church else None,
                'name': self.user.church.name if self.user.church else None,
                'church_code': self.user.church.church_code if self.user.church else None
            } if self.user.church else None
        }
        
        return data

    @classmethod
    def get_token(cls, user):
        """Get token with custom claims."""
        token = super().get_token(user)
        
        # Add custom claims
        token['church_id'] = str(user.church.id) if user.church else None
        token['church_name'] = user.church.name if user.church else None
        token['role'] = user.role
        token['email'] = user.email
        
        return token


class LoginSerializer(serializers.Serializer):
    """Serializer for login endpoint."""
    
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, attrs):
        """Validate login credentials."""
        email = attrs.get('email')
        password = attrs.get('password')
        
        if not email or not password:
            raise serializers.ValidationError('Email and password are required.')
        
        # Authenticate user
        user = authenticate(username=email, password=password)
        
        if not user:
            logger.warning(f"Failed login attempt for email: {email}")
            raise serializers.ValidationError('Invalid credentials.')
        
        if not user.is_active:
            logger.warning(f"Inactive user login attempt: {email}")
            raise serializers.ValidationError('Account is disabled.')
        
        attrs['user'] = user
        return attrs


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Login endpoint that returns JWT tokens via httpOnly cookies.
    
    POST /api/auth/login/
    {
        "email": "user@church.com",
        "password": "password123"
    }
    
    Returns:
    - Sets httpOnly cookies for access and refresh tokens
    - Returns user information and church context
    """
    serializer = LoginSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid credentials', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = serializer.validated_data['user']
    
    # Check if user's church is active (skip for superadmin)
    if user.church and not user.church.is_active:
        logger.warning(f"Login attempt from disabled church: {user.church.name} by {user.email}")
        return Response(
            {'error': 'Your church account has been disabled. Please contact support.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Generate tokens
    token_serializer = CustomTokenObtainPairSerializer()
    refresh = token_serializer.get_token(user)
    access_token = refresh.access_token
    
    # Prepare response data
    response_data = {
        'success': True,
        'message': 'Login successful',
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'church': {
                'id': str(user.church.id) if user.church else None,
                'name': user.church.name if user.church else None,
                'church_code': user.church.church_code if user.church else None
            } if user.church else None
        }
    }
    
    # Create response with httpOnly cookies
    response = Response(response_data, status=status.HTTP_200_OK)
    
    # Set httpOnly cookies for tokens
    response.set_cookie(
        key='access_token',
        value=str(access_token),
        max_age=3600,  # 1 hour
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax'
    )
    
    response.set_cookie(
        key='refresh_token',
        value=str(refresh),
        max_age=7 * 24 * 3600,  # 7 days
        httponly=True,
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax'
    )
    
    logger.info(f"User {user.email} logged in successfully. Church: {user.church}")
    return response


@api_view(['POST'])
@permission_classes([AllowAny])
def refresh_view(request):
    """
    Token refresh endpoint using httpOnly cookies.
    
    POST /api/auth/refresh/
    
    Returns:
    - New access token via httpOnly cookie
    - Optionally new refresh token if rotation is enabled
    """
    refresh_token = request.COOKIES.get('refresh_token')
    
    if not refresh_token:
        return Response(
            {'error': 'Refresh token not found'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token
        
        # Get user info from token
        user_id = refresh.payload.get('user_id')
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                
                response_data = {
                    'success': True,
                    'message': 'Token refreshed successfully',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'role': user.role,
                        'church': {
                            'id': str(user.church.id) if user.church else None,
                            'name': user.church.name if user.church else None,
                            'church_code': user.church.church_code if user.church else None
                        } if user.church else None
                    }
                }
            except User.DoesNotExist:
                return Response(
                    {'error': 'User not found'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            response_data = {
                'success': True,
                'message': 'Token refreshed successfully'
            }
        
        response = Response(response_data, status=status.HTTP_200_OK)
        
        # Set new access token cookie
        response.set_cookie(
            key='access_token',
            value=str(access_token),
            max_age=3600,  # 1 hour
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        
        # Set new refresh token if rotation is enabled
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            max_age=7 * 24 * 3600,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        
        logger.info(f"Token refreshed successfully for user_id: {user_id}")
        return response
        
    except TokenError as e:
        logger.warning(f"Invalid refresh token: {str(e)}")
        return Response(
            {'error': 'Invalid or expired refresh token'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint that clears httpOnly cookies and blacklists refresh token.
    
    POST /api/auth/logout/
    """
    try:
        # Get refresh token from cookies
        refresh_token = request.COOKIES.get('refresh_token')
        
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info(f"User {request.user.email} logged out - token blacklisted")
            except TokenError:
                # Token already invalid/blacklisted
                logger.info(f"User {request.user.email} logged out - token already invalid")
                pass
        
        response = Response(
            {'success': True, 'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
        
        # Clear cookies
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response
        
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        response = Response(
            {'success': True, 'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
        
        # Clear cookies even if blacklisting fails
        response.delete_cookie('access_token')
        response.delete_cookie('refresh_token')
        
        return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """
    Get current user information and church context.
    
    GET /api/auth/user/
    
    Returns user profile and church information from token.
    """
    user = request.user
    
    return Response({
        'success': True,
        'user': {
            'id': user.id,
            'email': user.email,
            'role': user.role,
            'church': {
                'id': str(user.church.id) if user.church else None,
                'name': user.church.name if user.church else None,
                'church_code': user.church.church_code if user.church else None
            } if user.church else None
        }
    })


# Signup and Church Assignment Views

class SignupSerializer(serializers.Serializer):
    """Serializer for user registration."""
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    
    def validate_email(self, value):
        """Check that the email is not already registered."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value


@api_view(['POST'])
@permission_classes([AllowAny])
def signup_view(request):
    """
    Create a new user account (step 1 of registration).
    
    The user is created but not assigned to a church yet.
    They must complete the church assignment in step 2.
    """
    serializer = SignupSerializer(data=request.data)
    
    if not serializer.is_valid():
        logger.warning(f"Signup attempt failed validation: {serializer.errors}")
        return Response({
            'error': 'Invalid signup data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Create user without church assignment
        user = User.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        
        logger.info(f"New user created: {user.email} (ID: {user.id})")
        
        return Response({
            'message': 'Account created successfully',
            'user_id': user.id,
            'email': user.email,
            'next_step': 'Please provide your church code to complete registration'
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating user account: {str(e)}")
        return Response({
            'error': 'Failed to create account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AdminSignupSerializer(serializers.Serializer):
    """Serializer for admin signup with church creation."""
    church_name = serializers.CharField(max_length=100, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    
    def validate_email(self, value):
        """Check if email already exists."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_church_name(self, value):
        """Validate church name is not empty."""
        if not value.strip():
            raise serializers.ValidationError("Church name cannot be empty.")
        return value.strip()


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_signup_view(request):
    """
    Admin signup endpoint - creates both church and admin user.
    
    POST /api/v1/auth/admin-signup/
    {
        "church_name": "Grace Community Church",
        "email": "admin@church.com",
        "password": "securepass123",
        "first_name": "John",  // optional
        "last_name": "Doe"     // optional
    }
    
    Returns:
    - User information
    - Church information
    - JWT tokens via httpOnly cookies
    - Church starts as inactive
    """
    serializer = AdminSignupSerializer(data=request.data)
    
    if not serializer.is_valid():
        logger.warning(f"Admin signup failed validation: {serializer.errors}")
        return Response({
            'error': 'Invalid signup data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from tenants.models import Church
        import secrets
        import string
        
        # Generate unique church code
        def generate_church_code():
            alphabet = string.ascii_uppercase + string.digits
            while True:
                code = ''.join(secrets.choice(alphabet) for _ in range(8))
                if not Church.objects.filter(church_code=code).exists():
                    return code
        
        # Create church (inactive by default)
        church = Church.objects.create(
            name=serializer.validated_data['church_name'],
            church_code=generate_church_code(),
            is_active=False  # Church starts inactive
        )
        
        # Create admin user
        user = User.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            church=church,
            role=User.Role.ADMIN
        )
        
        logger.info(
            f"Admin signup successful: {user.email} created church '{church.name}' "
            f"(Code: {church.church_code})"
        )
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add custom claims
        refresh['church_id'] = str(church.id)
        refresh['church_name'] = church.name
        refresh['role'] = user.role
        refresh['email'] = user.email
        
        access_token['church_id'] = str(church.id)
        access_token['church_name'] = church.name
        access_token['role'] = user.role
        access_token['email'] = user.email
        
        # Prepare response
        response_data = {
            'message': 'Admin account and church created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role
            },
            'church': {
                'id': str(church.id),
                'name': church.name,
                'church_code': church.church_code,
                'is_active': church.is_active
            },
            'next_step': 'Complete setup wizard to activate your church'
        }
        
        response = Response(response_data, status=status.HTTP_201_CREATED)
        
        # Set httpOnly cookies
        response.set_cookie(
            key='access_token',
            value=str(access_token),
            max_age=3600,  # 1 hour
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            max_age=7 * 24 * 3600,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error during admin signup: {str(e)}", exc_info=True)
        return Response({
            'error': 'Failed to create admin account and church'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChurchAssignmentSerializer(serializers.Serializer):
    """Serializer for church code assignment."""
    church_code = serializers.CharField(max_length=50)
    
    def validate_church_code(self, value):
        """Check that the church code exists."""
        from tenants.models import Church
        
        try:
            church = Church.objects.get(church_code=value.upper())
            return value.upper()
        except Church.DoesNotExist:
            raise serializers.ValidationError("Invalid church code.")


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_church_view(request):
    """
    Assign a church to the authenticated user (step 2 of registration).
    
    This endpoint expects the user to be authenticated but not yet assigned to a church.
    After successful assignment, it logs the user in with full JWT tokens.
    """
    user = request.user
    
    # Check if user already has a church assigned
    if user.church:
        logger.warning(f"User {user.email} attempted to assign church but already has one")
        return Response({
            'error': 'User already assigned to a church',
            'church': user.church.name
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ChurchAssignmentSerializer(data=request.data)
    
    if not serializer.is_valid():
        logger.warning(f"Church assignment failed validation: {serializer.errors}")
        return Response({
            'error': 'Invalid church code',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from tenants.models import Church
        
        # Get the church
        church = Church.objects.get(
            church_code=serializer.validated_data['church_code']
        )
        
        # Check if church is active
        if not church.is_active:
            logger.warning(f"User {user.email} attempted to join disabled church: {church.name}")
            return Response({
                'error': 'This church is currently disabled. Please contact your church administrator.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Assign church to user
        user.church = church
        user.save()
        
        logger.info(f"User {user.email} assigned to church {church.name} (Code: {church.church_code})")
        
        # Generate tokens for full authentication
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add church information to tokens
        refresh['church_id'] = str(user.church.id)
        refresh['church_name'] = user.church.name
        refresh['role'] = user.role
        refresh['email'] = user.email
        
        access_token['church_id'] = str(user.church.id)
        access_token['church_name'] = user.church.name
        access_token['role'] = user.role
        access_token['email'] = user.email
        
        # Create response
        response = Response({
            'message': 'Successfully assigned to church and logged in',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'church': {
                    'id': str(church.id),
                    'name': church.name,
                    'church_code': church.church_code
                }
            }
        }, status=status.HTTP_200_OK)
        
        # Set httpOnly cookies
        response.set_cookie(
            'access_token',
            str(access_token),
            max_age=ACCESS_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,  # Use secure cookies in production
            samesite='Lax'
        )
        
        response.set_cookie(
            'refresh_token', 
            str(refresh),
            max_age=REFRESH_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,  # Use secure cookies in production
            samesite='Lax'
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error assigning church to user {user.email}: {str(e)}")
        return Response({
            'error': 'Failed to assign church'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def anonymous_assign_church_view(request):
    """
    Alternative endpoint for church assignment when user is not authenticated.
    
    This is used when the signup flow needs to authenticate the user first,
    then assign the church. Expects email to identify the user.
    """
    email = request.data.get('email')
    church_code = request.data.get('church_code')
    
    if not email or not church_code:
        return Response({
            'error': 'Email and church_code are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        from tenants.models import Church
        
        # Find user by email
        user = User.objects.get(email=email)
        
        # Check if user already has a church
        if user.church:
            return Response({
                'error': 'User already assigned to a church'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Find church by code
        church = Church.objects.get(church_code=church_code.upper())
        
        # Assign church to user
        user.church = church
        user.save()
        
        logger.info(f"User {user.email} assigned to church {church.name} via anonymous endpoint")
        
        # Generate tokens for authentication
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add church information to tokens
        refresh['church_id'] = str(user.church.id)
        refresh['church_name'] = user.church.name
        refresh['role'] = user.role
        refresh['email'] = user.email
        
        access_token['church_id'] = str(user.church.id)
        access_token['church_name'] = user.church.name
        access_token['role'] = user.role
        access_token['email'] = user.email
        
        # Create response
        response = Response({
            'message': 'Successfully assigned to church and logged in',
            'user': {
                'id': user.id,
                'email': user.email,
                'role': user.role,
                'church': {
                    'id': str(church.id),
                    'name': church.name,
                    'church_code': church.church_code
                }
            }
        }, status=status.HTTP_200_OK)
        
        # Set httpOnly cookies
        response.set_cookie(
            'access_token',
            str(access_token),
            max_age=ACCESS_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax'
        )
        
        response.set_cookie(
            'refresh_token', 
            str(refresh),
            max_age=REFRESH_TOKEN_LIFETIME.total_seconds(),
            httponly=True,
            secure=not settings.DEBUG,
            samesite='Lax'
        )
        
        return response
        
    except User.DoesNotExist:
        return Response({
            'error': 'User not found'
        }, status=status.HTTP_404_NOT_FOUND)
    
    except Church.DoesNotExist:
        return Response({
            'error': 'Invalid church code'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error in anonymous church assignment: {str(e)}")
        return Response({
            'error': 'Failed to assign church'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MemberSignupSerializer(serializers.Serializer):
    """Serializer for member signup with church code validation."""
    church_code = serializers.CharField(max_length=50, required=True)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    first_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=30, required=False, allow_blank=True)
    
    def validate_email(self, value):
        """Check if email already exists."""
        if User.objects.filter(email=value.lower()).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()
    
    def validate_church_code(self, value):
        """Validate church code and check if church is active."""
        from tenants.models import Church
        
        try:
            church = Church.objects.get(church_code=value.upper())
            if not church.is_active:
                raise serializers.ValidationError(
                    "This church is not currently accepting new members. "
                    "Please contact your church administrator."
                )
            return value.upper()
        except Church.DoesNotExist:
            raise serializers.ValidationError("Invalid church code.")


@api_view(['POST'])
@permission_classes([AllowAny])
def member_signup_view(request):
    """
    Member signup endpoint - validates church code and creates member user.
    
    POST /api/v1/core/auth/member-signup/
    {
        "church_code": "ABC12345",
        "email": "member@church.com",
        "password": "securepass123",
        "first_name": "Jane",  // optional
        "last_name": "Smith"   // optional
    }
    
    Returns:
    - User information
    - Church information
    - JWT tokens via httpOnly cookies
    
    Rate limiting: Max 5 attempts per IP per 15 minutes
    """
    from django.core.cache import cache
    from tenants.models import Church
    
    # Rate limiting for church code attempts
    ip_address = request.META.get('REMOTE_ADDR', 'unknown')
    rate_limit_key = f'member_signup_attempts_{ip_address}'
    attempts = cache.get(rate_limit_key, 0)
    
    if attempts >= 5:
        logger.warning(f"Rate limit exceeded for member signup from IP: {ip_address}")
        return Response({
            'error': 'Too many signup attempts. Please try again in 15 minutes.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    serializer = MemberSignupSerializer(data=request.data)
    
    if not serializer.is_valid():
        # Increment attempts on validation failure (especially for invalid church code)
        cache.set(rate_limit_key, attempts + 1, 900)  # 15 minutes
        
        logger.warning(f"Member signup failed validation: {serializer.errors}")
        return Response({
            'error': 'Invalid signup data',
            'details': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Get the church (already validated in serializer)
        church = Church.objects.get(
            church_code=serializer.validated_data['church_code']
        )
        
        # Create member user
        user = User.objects.create_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data.get('first_name', ''),
            last_name=serializer.validated_data.get('last_name', ''),
            church=church,
            role=User.Role.MEMBER
        )
        
        logger.info(
            f"Member signup successful: {user.email} joined church '{church.name}' "
            f"(Code: {church.church_code})"
        )
        
        # Clear rate limit on successful signup
        cache.delete(rate_limit_key)
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add custom claims
        refresh['church_id'] = str(church.id)
        refresh['church_name'] = church.name
        refresh['role'] = user.role
        refresh['email'] = user.email
        
        access_token['church_id'] = str(church.id)
        access_token['church_name'] = church.name
        access_token['role'] = user.role
        access_token['email'] = user.email
        
        # Prepare response
        response_data = {
            'message': 'Member account created successfully',
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'role': user.role
            },
            'church': {
                'id': str(church.id),
                'name': church.name,
                'church_code': church.church_code
            }
        }
        
        response = Response(response_data, status=status.HTTP_201_CREATED)
        
        # Set httpOnly cookies
        response.set_cookie(
            key='access_token',
            value=str(access_token),
            max_age=3600,  # 1 hour
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            max_age=7 * 24 * 3600,  # 7 days
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax'
        )
        
        return response
        
    except Church.DoesNotExist:
        # This shouldn't happen due to serializer validation, but handle anyway
        cache.set(rate_limit_key, attempts + 1, 900)
        return Response({
            'error': 'Invalid church code'
        }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        logger.error(f"Error during member signup: {str(e)}", exc_info=True)
        return Response({
            'error': 'Failed to create member account'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_church_code_view(request):
    """
    Validate a church code without creating an account.
    
    POST /api/v1/core/auth/validate-church-code/
    {
        "church_code": "ABC12345"
    }
    
    Returns:
    - Church information if valid and active
    - Error if invalid or inactive
    
    Rate limiting: Max 10 attempts per IP per 15 minutes
    """
    from django.core.cache import cache
    from tenants.models import Church
    
    # Rate limiting for church code validation
    ip_address = request.META.get('REMOTE_ADDR', 'unknown')
    rate_limit_key = f'validate_church_code_{ip_address}'
    attempts = cache.get(rate_limit_key, 0)
    
    if attempts >= 10:
        logger.warning(f"Rate limit exceeded for church code validation from IP: {ip_address}")
        return Response({
            'error': 'Too many validation attempts. Please try again in 15 minutes.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    church_code = request.data.get('church_code', '').strip().upper()
    
    if not church_code:
        cache.set(rate_limit_key, attempts + 1, 900)  # 15 minutes
        return Response({
            'error': 'Church code is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        church = Church.objects.get(church_code=church_code)
        
        if not church.is_active:
            cache.set(rate_limit_key, attempts + 1, 900)
            logger.warning(f"Validation attempt for inactive church: {church.name} (Code: {church_code})")
            return Response({
                'error': 'This church is not currently accepting new members. Please contact your church administrator.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Clear rate limit on successful validation
        cache.delete(rate_limit_key)
        
        logger.info(f"Church code validated successfully: {church_code} -> {church.name}")
        return Response({
            'valid': True,
            'church': {
                'id': str(church.id),
                'name': church.name,
                'church_code': church.church_code
            }
        }, status=status.HTTP_200_OK)
        
    except Church.DoesNotExist:
        cache.set(rate_limit_key, attempts + 1, 900)
        logger.warning(f"Invalid church code validation attempt: {church_code}")
        return Response({
            'error': 'Invalid church code. Please check and try again.'
        }, status=status.HTTP_404_NOT_FOUND)