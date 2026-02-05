from django.shortcuts import render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from permissions import EstAdministrateur, EstClient
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Client
from .serializers import ClientSerializer

from rest_framework.pagination import LimitOffsetPagination

import re
from datetime import date

from django.core.cache import cache
from django.utils import timezone

# Create your views here.

# Fonction pour lister les Clients
@api_view(['GET'])
@permission_classes([AllowAny])
def list_client(request):
    try :
        today = timezone.now()
        clients = Client.objects.filter(date_creation__date=today).order_by('-date_creation')

        # Créer la clé du cache
        limit = request.GET.get("limit","10")
        offset = request.GET.get("offset","0")


        # Pagination
        pagination = LimitOffsetPagination()
        pagination.default_limit = 10
        clients_page = pagination.paginate_queryset(clients,request)

        serializer = ClientSerializer(clients_page, many=True)
        pagination_response = pagination.get_paginated_response(serializer.data)
        response_data = pagination_response.data

        return Response({
            "success":True,
            "data":response_data
        }, status=status.HTTP_200_OK)
    except Exception as e :
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fonction de creation d'un Client
@api_view(['POST'])
def create_client(request):
    nom = request.data.get('nom_client')
    numero = request.data.get('numero_telephone_client')

    # Verifier email, numero et nom
    if  not numero or not nom : 
        return Response({
            "success":False,
            "errors":"Tous les champs sont obligatoires"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if numero.isdigit():
        pattern = r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$'
        if not re.match(pattern,numero):
            return Response({
                "success":False,
                "errors":"Numero invalide (respecter le format des numeros ivoiriens)"
            }, status=status.HTTP_400_BAD_REQUEST)
        
    # Verifier que le Client n'existe pas
    if Client.objects.filter(numero_telephone_client=numero).exists():
        return Response({
            "success":False,
            "errors":"Cet client existe dejà"
        })
    
    # Création du client
    try :
        serializer = ClientSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success":True,
                "message":"Nouveau client ajouté"
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
    

# Voir et modifier les details du Client
@api_view(['GET','PUT'])
@permission_classes([EstAdministrateur])
def detail_client(request,identifiant):
    nom = request.data.get('nom_client')
    numero = request.data.get('numero_telephone_client')
    print(identifiant)

    # Verifier le numero
    try :
        client = Client.objects.get(identifiant_client=identifiant)
    except Client.DoesNotExist:
        return Response({
            "success":False,
            "errors":"Ce client n'existe pas"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Requette GET
    if request.method == 'GET':
        try :
            serializer = ClientSerializer(client)
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
            }, status=status.HTTP_404_NOT_FOUND)
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
        # Verifier numero et nom
        if  not numero or not nom : 
            return Response({
                "success":False,
                "errors":"Tous les champs sont obligatoires"
            }, status=status.HTTP_400_BAD_REQUEST)

        if numero.isdigit():
            pattern = r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$'
            if not re.match(pattern,numero):
                return Response({
                    "success":False,
                    "errors":"Numero invalide (respecter le format des numeros ivoiriens)"
                }, status=status.HTTP_400_BAD_REQUEST)

        try :
            serializer = ClientSerializer(client, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    "success":True,
                    "message":"Informations modifiées avec succès",
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
def delete_Client(request, identifiant):
    try :
        client = Client.objects.get(identifiant_client=identifiant)
    except Client.DoesNotExist:
        return Response({
            "success":False,
            "errors":"Ce client n'existe pas"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        client.delete()

        return Response({
            "success": True,
            "message": "Client supprimé avec succès"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    