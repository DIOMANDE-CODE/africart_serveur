from django.shortcuts import render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from permissions import EstAdministrateur, EstGerant

from .models import Utilisateur
from .serializers import UtilisateurSerializer
from django.views.decorators.csrf import csrf_exempt

import re

# Create your views here.

# Fonction pour lister les utilisateurs
@api_view(['GET'])
@permission_classes([EstAdministrateur])
def list_utilisateur(request):
    try :
        user = Utilisateur.objects.all().filter(role='vendeur')
        serializer = UtilisateurSerializer(user, many=True)
        return Response({
            "success":True,
            "data":serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e :
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fonction de creation d'un utilisateur
@csrf_exempt
@api_view(['POST'])
def create_utilisateur(request):
    print(request.data)
    nom = request.data.get('nom_utilisateur')
    email = request.data.get('email_utilisateur')
    numero = request.data.get('numero_telephone_utilisateur')
    password = request.data.get('password')

    # Verifier email, numero et nom
    if not email or not numero or not nom or not password : 
        return Response({
            "success":False,
            "errors":"Tous les champs sont obligatoires"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try :
        validate_email(email)
    except ValidationError:
        return Response({
            "success":False,
            "errors":"Email invalide"
        }, status=status.HTTP_400_BAD_REQUEST)
    if numero.isdigit():
        pattern = r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$'
        if not re.match(pattern,numero):
            return Response({
                "success":False,
                "errors":"Numéro invalide (respecter le format des numeros ivoiriens)."
            }, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({
                "success":False,
                "errors":"Numéro invalide (respecter le format des numeros ivoiriens)."
            }, status=status.HTTP_400_BAD_REQUEST)
        
    # Verfier que l'utilisateur n'existe pas
    if Utilisateur.objects.filter(email_utilisateur=email).exists():
        return Response({
            "success":False,
            "errors":"Cet utilisateur existe dejà"
        }, status=status.HTTP_409_CONFLICT)
    
    # Verifier que le numero n'existe pas
    if Utilisateur.objects.filter(numero_telephone_utilisateur=numero).exists():
        return Response({
            "success":False,
            "errors":"Cet Numéro existe dejà"
        }, status=status.HTTP_409_CONFLICT)
    
    # Création du compte
    try :
        serializer = UtilisateurSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success":True,
                "message":"Compte crée avec succès"
            }, status=status.HTTP_201_CREATED)
        return Response({
            "success":False,
            "errors":serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e :
        import traceback
        traceback.print_exc()
        print(Exception)
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# Voir et modifier les details de l'utilisateur connecté
@api_view(['GET','PUT'])
def detail_utilisateur(request):

    user = request.user
    nom = request.data.get('nom_utilisateur')
    email = request.data.get('email_utilisateur')
    numero = request.data.get('numero_telephone_utilisateur')


    if not user.is_active:
        return Response({
            "success": False,
            "errors": "Ce compte est désactivé."
        }, status=status.HTTP_403_FORBIDDEN)
    
    # Requette GET
    if request.method == 'GET':
        try :
            serializer = UtilisateurSerializer(user)
            return Response({
                    "success":True,
                    "data":serializer.data
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
    
    # Requette PUT
    if request.method == 'PUT':

        # Verifier email, numero et nom
        if not email or not numero or not nom : 
            return Response({
                "success":False,
                "errors":"Les champs nom,numero et email sont obligatoires"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try :
            validate_email(email)
        except ValidationError:
            return Response({
                "success":False,
                "errors":"Email invalide"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Verifier le numero
        if numero.isdigit():
            pattern = r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$'
            if not re.match(pattern,numero):
                return Response({
                    "success":False,
                    "errors":"Numero invalide (respecter le format des numeros ivoiriens)"
                }, status=status.HTTP_400_BAD_REQUEST)

        try :
            serializer = UtilisateurSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                user = serializer.save()
                nouveau_mot_de_passe = request.data.get('nouveau_code',None)
                if nouveau_mot_de_passe:
                    user.set_password(nouveau_mot_de_passe)
                    user.save()
                return Response({
                    "success":True,
                    "message":"Compte modifié avec succès",
                    "data":serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "success":False,
                    "errors":serializer.errors
                }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e :
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
# Requette DELETE
@api_view(['DELETE'])
@permission_classes([EstAdministrateur])
def delete_utilisateur(request, id):
    try:
        # Vérifier l'existence de l'utilisateur
        user = Utilisateur.objects.get(identifiant=id, is_active=True)
    except Utilisateur.DoesNotExist:
        return Response({
            "success": False,
            "errors": "Cet utilisateur n'existe pas"
        }, status=status.HTTP_404_NOT_FOUND)

    try:
        user.is_active = False
        user.save()

        return Response({
            "success": True,
            "message": "Utilisateur supprimé avec succès"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)