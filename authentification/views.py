from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from rest_framework.authtoken.models import Token

from utilisateurs.models import Utilisateur
from utilisateurs.serializers import UtilisateurSerializer
from django.views.decorators.csrf import csrf_exempt
import traceback
from rest_framework.permissions import IsAuthenticated


# Connexion utilisateur
@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_utilisateur(request):
    email = request.data.get('email_utilisateur')
    password = request.data.get('password')

    try:
        # Vérification des champs requis
        if not email or not password:
            return Response({
                "success": False,
                "errors": "Tous les champs sont obligatoires"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validation du format d'email
        try:
            validate_email(email)
        except ValidationError:
            return Response({
                "success": False,
                "errors": "Adresse e-mail invalide"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Vérification de l'existence de l'utilisateur
        try:
            user = Utilisateur.objects.get(email_utilisateur=email, is_active=True)
        except Utilisateur.DoesNotExist:
            return Response({
                "success": False,
                "errors": "Aucun compte associé à cet e-mail"
            }, status=status.HTTP_404_NOT_FOUND)

        # Vérification du mot de passe
        if not user.check_password(password):
            return Response({
                "success": False,
                "errors": "Mot de passe incorrect"
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Authentification
        user = authenticate(request, username=email, password=password)
        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            info_user = UtilisateurSerializer(user).data

            response = Response({
                "success": True,
                "message": "Connexion établie",
                "token": token.key,
                "user": info_user
            }, status=status.HTTP_200_OK)

            # Cookie sécurisé
            response.set_cookie(
                key='auth_token',
                value=token.key,
                httponly=True,
                secure=False,
                samesite="Strict",
                max_age=43200
            )
            return response

        return Response({
            "success": False,
            "errors": "Identifiant invalide"
        }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        # Log complet de la stack trace pour le debug
        traceback.print_exc()
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def login_token(request):
    email = request.data.get('email_utilisateur')
    password = request.data.get('password')

    if not Utilisateur.objects.filter(email_utilisateur=email, is_active=True).exists():
        return Response({
            "success": False,
            "errors": "Aucun compte associé à cet e-mail"
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        user = authenticate(username=email, password=password)

        if user:
            token, _ = Token.objects.get_or_create(user=user)
            info_user = UtilisateurSerializer(user).data

            return Response({
                "token": token.key,
                "user_id": user.id,
                "user": info_user
            }, status=status.HTTP_200_OK)

        return Response({"error": "Identifiants invalides"}, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        traceback.print_exc()
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Déconnexion utilisateur
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def logout_utilisateur(request):
    try:
        # Supprime le token en base
        if request.user.is_authenticated:
            request.user.auth_token.delete()

        response = Response({
            "success": True,
            "message": "Compte déconnecté"
        }, status=status.HTTP_200_OK)

        # Supprime le cookie côté navigateur
        response.delete_cookie('auth_token')
        return response

    except Exception as e:
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_mobile(request):
    try:
        # On utilise .auth_token car DRF lie automatiquement le token à l'user
        if hasattr(request.user, 'auth_token'):
            request.user.auth_token.delete()

        response = Response({
            "success": True,
            "message": "Déconnexion réussie"
        }, status=status.HTTP_200_OK)

        # 2. Supprime le cookie côté client (important pour votre CookieTokenAuthentication)
        response.delete_cookie(
            'auth_token', 
            path='/',      # Assurez-vous que le path correspond à celui du login
            samesite='Lax' # Ou 'None' selon votre config CORS
        )
        
        return response

    except Exception as e:
        return Response({
            "success": False,
            "message": "Erreur lors de la déconnexion",
            "errors": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Vérification de session utilisateur
    
@api_view(['GET'])
def check_session(request):
    # lire le token dans les cookies
    token_key = request.COOKIES.get("auth_token")

    if not token_key:
        return Response(
            {"success": False, "authenticated": False},
            status=401
        )

    try:
        token = Token.objects.get(key=token_key)
        user = token.user

        return Response({
            "success": True,
            "authenticated": True,
            "user": UtilisateurSerializer(user).data
        }, status=200)

    except Token.DoesNotExist:
        return Response(
            {"success": False, "authenticated": False},
            status=401
        )

@api_view(['POST'])
def mobile_check_session(request):
    token_key = request.data.get("token_key")

    if not token_key:
        return Response(
            {"success": False, "authenticated": False},
            status=401
        )

    if "Token " in token_key:
        token_key = token_key.replace("Token ", "").strip()

    try:
        token = Token.objects.get(key=token_key)
        user = token.user

        return Response({
            "success": True,
            "authenticated": True,
            "user": UtilisateurSerializer(user).data
        }, status=200)

    except Token.DoesNotExist:
        return Response(
            {"success": False, "authenticated": False},
            status=401
        )




# Changez de mot de passe
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def changer_mot_de_passe(request):
    user = request.user
    ancien_mdp = request.data.get('ancien_mot_de_passe')
    nouveau_mdp = request.data.get('nouveau_mot_de_passe')
    print(user.email_utilisateur)

    # Vérification de l'existence de l'utilisateur
    try:
        user = Utilisateur.objects.get(email_utilisateur=user.email_utilisateur, is_active=True)
    except Utilisateur.DoesNotExist:
        return Response({
            "success": False,
            "errors": "Aucun compte associé à cet e-mail"
        }, status=status.HTTP_404_NOT_FOUND)
    
    # Verifier que l'ancien mot de passe est différent du nouveau
    if ancien_mdp == nouveau_mdp :
        return Response({
            "success":False,
            "errors":"Le nouveau mot de passe doit être différent du mot de passe actuel"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Vérification du mot de passe
    if not user.check_password(ancien_mdp):
        return Response({
            "success": False,
            "errors": "Mot de passe actuel incorrect"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try :
        user.set_password(nouveau_mdp)
        user.save()
        return Response({
            "success":True,
            "message":"Mot de passe changé avec succès"
        }, status=status.HTTP_200_OK)
    
    except Exception as e :
            import traceback
            traceback.print_exc()
            print(Exception)
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
