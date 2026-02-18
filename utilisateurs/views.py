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
from clients.models import Client
from rest_framework.permissions import IsAuthenticated

import re

# Create your views here.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def info_utilisateur(request):
    if not request.user.is_authenticated:
        return Response({
            "success": False,
            "errors": "Utilisateur non authentifié"
        }, status=status.HTTP_401_UNAUTHORIZED)

    serializer = UtilisateurSerializer(request.user)
    return Response({
        "success": True,
        "message": "Utilisateur authentifié",
        "data": serializer.data
    }, status=status.HTTP_200_OK)

   

# Fonction pour lister les utilisateurs
@api_view(['GET'])
@permission_classes([AllowAny])
def list_utilisateur(request):
    try :
        user = Utilisateur.objects.all().filter(is_active=True)
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
@permission_classes([AllowAny])
def create_utilisateur(request):
    nom = request.data.get('nom_utilisateur')
    email = request.data.get('email_utilisateur')
    numero = request.data.get('numero_telephone_utilisateur')
    password = request.data.get('password')
    role = request.data.get('role')

    
    # Verification liée à la création d'un compte client
    if role == 'client':
        if not email or not nom or not password or not numero :
            return Response({
                "success":False,
                "errors":"Tous les champs sont obligatoires"
            }, status=status.HTTP_400_BAD_REQUEST)
        

         # Verifier que l'email n'existe pas
        if Utilisateur.objects.filter(email_utilisateur=email).exists():
            return Response({
                "success":False,
                "errors":"Cet compte existe dejà"
            }, status=status.HTTP_409_CONFLICT)        

        # Verifier l'email
        try :
            validate_email(email)
        except ValidationError:
            return Response({
                "success":False,
                "errors":"Email invalide"
            }, status=status.HTTP_400_BAD_REQUEST)
        

        # Verifier la validité du numéro
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
        
        # Création du compte client
        try :
            serializer = UtilisateurSerializer(data=request.data)
            if serializer.is_valid():
                utilisateur = serializer.save()
                Client.objects.create(
                    utilisateur=utilisateur,
                    nom_client=nom,
                    email_client=email,
                    numero_telephone_client=numero,
                    role='client'
                )
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


    # Verification liée à la création d'un compte utilisateur (vendeur, gerant ou admin)
    else :
        if not request.user.is_authenticated :
            return Response({
                "success": False,
                "errors": "Vous devez être connecté pour créer un compte utilisateur."
            }, status=status.HTTP_401_UNAUTHORIZED) 
        
        # Vérifier si l'utilisateur a le rôle requis (admin ou vendeur)
        if not (request.user.role == 'admin' or request.user.role == 'vendeur'):
            return Response({
                "success": False,
                "errors": "Vous n'avez pas la permission de créer un compte utilisateur."
            }, status=status.HTTP_403_FORBIDDEN)
        
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
        
        # Création du compte utilisateur (vendeur, gerant ou admin)
        try :
            serializer = UtilisateurSerializer(data=request.data)
            if serializer.is_valid():
                utilisateur = serializer.save()
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
    role = request.data.get('role')

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

        # Verifier que l'utilisateur connecté est un client
        if role == 'client':
            # Verifier l'email
            if email:
                try :
                    validate_email(email)
                except ValidationError:
                    return Response({
                        "success":False,
                        "errors":"Email invalide"
                    }, status=status.HTTP_400_BAD_REQUEST)
                

            # Verifier la validité du numéro
            if numero:
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
                
            # Création du compte client
            try :
                serializer = UtilisateurSerializer(user, data=request.data, partial=True)
                if serializer.is_valid():
                    utilisateur = serializer.save()

                    # Mise à jour du client lié de l'utilisateur
                    Client.objects.filter(utilisateur=utilisateur).update(
                        nom_client=nom,
                        email_client=email,
                        numero_telephone_client=numero,
                        role='client'
                    )
                    return Response({
                        "success":True,
                        "data":serializer.data,
                        "message":"Informations mises à jour avec succès"
                    }, status=status.HTTP_200_OK)
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

    # Verification liée à la création d'un compte utilisateur (vendeur, gerant ou admin)
    else :
        if not request.user.is_authenticated :
            return Response({
                "success": False,
                "errors": "Vous devez être connecté pour créer un compte utilisateur."
            }, status=status.HTTP_401_UNAUTHORIZED) 
        
        # Vérifier si l'utilisateur a le rôle requis (admin ou vendeur)
        if not (request.user.role == 'admin' or request.user.role == 'vendeur'):
            return Response({
                "success": False,
                "errors": "Vous n'avez pas la permission de créer un compte utilisateur."
            }, status=status.HTTP_403_FORBIDDEN)
    
        if email:
            try :
                validate_email(email)
            except ValidationError:
                return Response({
                    "success":False,
                    "errors":"Email invalide"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if numero:        
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
            
        # Création du compte utilisateur (vendeur, gerant ou admin)
        try :
            serializer = UtilisateurSerializer(user,data=request.data,partial=True)
            if serializer.is_valid():
                utilisateur = serializer.save()
                return Response({
                    "success":True,
                    "data":serializer.data,
                    "message":"Information modifiée avec succès"
                }, status=status.HTTP_200_OK)
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