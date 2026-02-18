from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

Utilisateur = get_user_model()


class CustomAuthenticationBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = Utilisateur.objects.get(email_utilisateur=username)
      
        except Utilisateur.DoesNotExist:
            return None
    
        return None