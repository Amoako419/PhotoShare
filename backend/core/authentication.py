"""
Custom JWT Authentication for httpOnly Cookies

Extends SimpleJWT authentication to work with httpOnly cookies
instead of Authorization headers for enhanced security.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.settings import api_settings
from django.contrib.auth.models import AnonymousUser
import logging

logger = logging.getLogger(__name__)


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from httpOnly cookies.
    
    This provides enhanced security by preventing XSS attacks since
    tokens are not accessible to JavaScript.
    """
    
    def authenticate(self, request):
        """
        Authenticate using JWT token from httpOnly cookie.
        
        Returns:
            tuple: (user, token) if authentication successful, None otherwise
        """
        # Get access token from cookie
        raw_token = request.COOKIES.get('access_token')
        
        if raw_token is None:
            return None
            
        # Validate token and get user
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        
        return user, validated_token
    
    def get_validated_token(self, raw_token):
        """
        Validate the JWT token.
        
        Args:
            raw_token (str): Raw JWT token string
            
        Returns:
            UntypedToken: Validated token
            
        Raises:
            InvalidToken: If token is invalid or expired
        """
        messages = []
        
        # Get JWT settings from api_settings
        auth_token_classes = api_settings.AUTH_TOKEN_CLASSES or (api_settings.ACCESS_TOKEN_CLASS,)
        
        for AuthToken in auth_token_classes:
            try:
                return AuthToken(raw_token)
            except TokenError as e:
                messages.append({
                    'token_class': AuthToken.__name__,
                    'token_type': getattr(AuthToken, 'token_type', 'access'),
                    'message': e.args[0],
                })

        raise InvalidToken({
            'detail': 'Given token not valid for any token type',
            'messages': messages,
        })
    
    def get_user(self, validated_token):
        """
        Get user from validated token.
        
        Args:
            validated_token: Validated JWT token
            
        Returns:
            User: User instance
            
        Raises:
            InvalidToken: If user not found or inactive
        """
        try:
            user_id = validated_token[api_settings.USER_ID_CLAIM]
        except KeyError:
            raise InvalidToken('Token contained no recognizable user identification')

        try:
            user = self.user_model.objects.get(**{api_settings.USER_ID_FIELD: user_id})
        except self.user_model.DoesNotExist:
            raise InvalidToken('User not found')

        if not user.is_active:
            raise InvalidToken('User is inactive')

        return user