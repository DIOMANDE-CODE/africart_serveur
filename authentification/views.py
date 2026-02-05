from django.shortcuts import render
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
import re

from clients.models import Client
from clients.serializers import ClientSerializer
from utils.jwt_client import generate_clients_token, decode_token
from permissions import EstClient
from django.contrib.auth.hashers import check_password,make_password
from rest_framework.authentication import get_authorization_header



# Create your views here.


# Fonction de connexion
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

    # Connexion (session)
    try :
        user = authenticate(request, username=email, password=password)
        if user is not None:
            token, _ = Token.objects.get_or_create(user=user)
            info_user = UtilisateurSerializer(user).data
            return Response({
            "success": True,
            "message": "Connexion établie",
            "token": token.key,
            "user":info_user,
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "errors": "Identifiant invalide"
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e :
        import traceback
        traceback.print_exc()
        print(Exception)
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
@api_view(['POST'])
def logout_utilisateur(request):
    try :
        token_key = request.auth.key
        print(token_key)
        Token.objects.filter(key=token_key).delete()
    except Exception as e :
        import traceback
        traceback.print_exc()
        print(Exception)
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response({
                "success":True,
                "message":"Compte déconnecté"
            }, status=status.HTTP_200_OK)

@api_view(['POST'])
@permission_classes([AllowAny])
def check_session(request):
    token_key = request.data.get('token_key')

    if not token_key:
        return Response({
            "success": False,
            "authenticated": False,
            "message": "Token manquant"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Vérifie si le token existe dans la table Token
        token = Token.objects.filter(key=token_key).first()

        if token:
            return Response({
                "success": True,
                "authenticated": True,
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "authenticated": False,
                "message": "Token invalide ou expiré"
            }, status=status.HTTP_401_UNAUTHORIZED)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# Authentification du Client

@api_view(['POST'])
@permission_classes([AllowAny])
def login_client(request):
    numero = request.data.get('numero_telephone_client')
    password = request.data.get('password_client')

    # Vérification des champs requis
    if not numero or not password:
        return Response({
            "success": False,
            "errors": "Tous les champs sont obligatoires"
        }, status=status.HTTP_400_BAD_REQUEST)
    

    # Validation du numéro 
    pattern = r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$' 
    if not re.match(pattern, numero): 
        return Response({ 
            "success": False, 
            "errors": "Numéro invalide (respecter le format des numéros ivoiriens)" }, 
            status=status.HTTP_400_BAD_REQUEST)


    # Vérification de l'existence de l'utilisateur
    try:
        client = Client.objects.get(numero_telephone_client=numero, is_active=True)
    except Client.DoesNotExist:
        return Response({
            "success": False,
            "errors": "Aucun client associé à ce numéro"
        }, status=status.HTTP_404_NOT_FOUND)

    # Vérification du mot de passe
    password_is_valid = check_password(password, client.password_client)
    if not password_is_valid:
        return Response({
            "success": False,
            "errors": "Mot de passe incorrect"
        }, status=status.HTTP_401_UNAUTHORIZED)

    # Connexion (session)
    try :
        if client is not None:
            access, refresh = generate_clients_token(client)
            info_client = ClientSerializer(client).data
            return Response({
            "success": True,
            "message": "Connexion établie",
            "access_token":access,
            "refresh_token":refresh,
            "client":info_client,
            }, status=status.HTTP_200_OK)
        return Response({
            "success": False,
            "errors": "Identifiant invalide"
        }, status=status.HTTP_401_UNAUTHORIZED)
    except Exception as e :
        import traceback
        traceback.print_exc()
        print(Exception)
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

@api_view(['POST'])
@permission_classes([EstClient])
def logout_client(request):
    return Response({"success": True, "message": "Déconnexion réussie"}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def verifier_session_client(request): 
    token_key = request.data.get('token_key')
    print(token_key)
    
    payload = decode_token(token_key) 
    if not payload or payload.get("type") != "access": 
        return Response({"success": False, "errors": "Token invalide ou expiré"}, status=status.HTTP_401_UNAUTHORIZED) 
    
    try: 
        client = Client.objects.get(identifiant_client=payload["client_id"], is_active=True) 
        
    except Client.DoesNotExist: 
        return Response({"success": False, "errors": "Client introuvable"}, status=status.HTTP_404_NOT_FOUND)
     
    return Response({ "success": True, "message": "Session valide", "client": ClientSerializer(client).data }, status=status.HTTP_200_OK)



@api_view(['POST']) 
@permission_classes([AllowAny]) 
def refresh_client_access_token(request): 
    refresh_token = request.data.get("refresh") 
    
    if not refresh_token: 
        return Response({"success": False, "errors": "Refresh token manquant"}, status=status.HTTP_400_BAD_REQUEST) 
    
    payload = decode_token(refresh_token) 
    if not payload or payload.get("type") != "refresh": 
        return Response({"success": False, "errors": "Refresh token invalide ou expiré"}, status=status.HTTP_401_UNAUTHORIZED) 
    
    try: 
        client = Client.objects.get(identifiant_client=payload["client_id"], is_active=True) 
        
    except Client.DoesNotExist: 
        return Response({"success": False, "errors": "Client introuvable"}, status=status.HTTP_404_NOT_FOUND) 
    
    # Générer un nouveau access token (on garde le refresh existant) 
    access, _ = generate_clients_token(client) 
    return Response({ "success": True, "message": "Nouveau access token généré", "access": access }, status=status.HTTP_200_OK)

