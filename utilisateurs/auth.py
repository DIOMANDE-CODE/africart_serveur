from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework import exceptions
from rest_framework.authtoken.models import Token


class CookieTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token_key = None

        # 1. ESSAI MOBILE : Header Authorization
        auth = get_authorization_header(request).split()
        if auth and len(auth) == 2:
            # On accepte 'Token' ou 'Bearer' pour plus de souplesse
            if auth[0].lower() in [b"token", b"bearer"]:
                token_key = auth[1].decode("utf-8")

        # 2. ESSAI WEB : Cookie (si le header est vide)
        if not token_key:
            token_key = request.COOKIES.get("auth_token")

        if not token_key:
            return None

        try:
            # Utilisation de la clé pour trouver le token
            token = Token.objects.select_related("user").get(key=token_key)
        except (Token.DoesNotExist, UnicodeError):
            # C'est ici que l'erreur "Clé invalide" est levée
            raise exceptions.AuthenticationFailed("Clé invalide ou session expirée")

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed("Compte utilisateur désactivé")

        return (token.user, token)
