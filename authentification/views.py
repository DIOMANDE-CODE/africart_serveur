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


# Connexion utilisateur
@api_view(['POST'])
@permission_classes([AllowAny])
def login_utilisateur(request):
    email = request.data.get('email_utilisateur')
    password = request.data.get('password')

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
            "user": info_user
        }, status=status.HTTP_200_OK)

        # Cookie sécurisé
        response.set_cookie(
            key='auth_token',
            value=token.key,
            httponly=True,
            secure=False,      
            samesite="Lax", 
            max_age=43200
        )
        return response

    return Response({
        "success": False,
        "errors": "Identifiant invalide"
    }, status=status.HTTP_401_UNAUTHORIZED)


# Déconnexion utilisateur
@api_view(['POST'])
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


# Vérification de session via cookie HttpOnly
@api_view(['GET'])
def check_session(request):
    if request.user.is_authenticated:
        return Response({
            "success": True,
            "authenticated": True,
            "user": UtilisateurSerializer(request.user).data
        }, status=200)
    return Response({
        "success": False,
        "authenticated": False
    }, status=401)


# Changez de mot de passe
@api_view(['POST'])
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
