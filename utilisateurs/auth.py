from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from rest_framework.authtoken.models import Token

class CookieTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token_key = request.COOKIES.get('auth_token')
        if not token_key:
            return None
        try:
            token = Token.objects.get(key=token_key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')
        return (token.user, token)
