from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from .models import Commande, DetailCommande, AttributionCommande
from datetime import date
from rest_framework.pagination import LimitOffsetPagination
from .serializers import CommandeCreateSerializer, VoirCommandeSerializer, CommandeUpdateSerializer
from utilisateurs.models import Utilisateur


# Create your views here.

# Fonction de création de nouvelle commande
@api_view(['POST'])
@permission_classes([AllowAny])
def creer_commande(request):
    """
    Recoit un JSON et creer la commande avec les details des produits commandés et du client
    """

    # Recuperation de la commande
    data = request.data

    # Creation de la commande
    try :
        serializer = CommandeCreateSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            commande = serializer.save()
            return Response({"message": "Commande créée avec succès", 
            "reference_commande": commande.identifiant_commande}, status=status.HTTP_201_CREATED)
        return Response({
            "success":False,
            "errors":serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(Exception)
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# iste des commandes
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liste_commande(request):
    try:
        commandes = Commande.objects.filter(date_creation__date=date.today()).order_by('-date_creation')
        
        limit = request.GET.get("limit","10")
        offset = request.GET.get("offset","0")

        # Pagination
        pagination = LimitOffsetPagination()
        pagination.default_limit = 10
        commandes_page = pagination.paginate_queryset(commandes,request)
        serializer = VoirCommandeSerializer(commandes_page, many=True)
        pagination_response = pagination.get_paginated_response(serializer.data)
        response_data = pagination_response.data
        return Response({
            "success":True,
            "data":response_data,
        }, status=status.HTTP_200_OK)
    except Exception as e :
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

# Fonction pour lister les commandes par vendeur
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def liste_commande_par_vendeur(request):
    user = request.user

    if user.role != "vendeur":
        return Response({
            "success":False,
            "errors":"Accès refusé. Cette vue est réservée aux vendeurs."
        }, status=403)
    else:
        try:
            commandes = Commande.objects.filter(utilisateur=user,date_commande__date=date.today()).order_by('-date_commande')

            limit = request.GET.get("limit","10")
            offset = request.GET.get("offset","0")

            # Pagination
            pagination = LimitOffsetPagination()
            pagination.default_limit = 10
            commandes_page = pagination.paginate_queryset(commandes,request)
            serializer = VoirCommandeSerializer(commandes_page, many=True)
            pagination_response = pagination.get_paginated_response(serializer.data)
            response_data = pagination_response.data
            return Response({
                "success":True,
                "data":response_data,
            }, status=status.HTTP_200_OK)
        except Exception as e :
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

# Fonction pour voir les details d'une commande
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detail_commande(request, commande_id):
    try:
        commande = Commande.objects.get(identifiant_commande = commande_id)
    except Commande.DoesNotExist:  
        return Response({'success': False, 'message': 'Commande non trouvée'}, status=status.HTTP_404_NOT_FOUND)
    
    try:
        serializer = VoirCommandeSerializer(commande)
        return Response({'success': True, 'data': serializer.data}, status=status.HTTP_200_OK)
    except Exception as e :
        return Response({
            "success":False,
            "errors":"Erreur interne du serveur",
            "message":str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
# Fonction pour valider la commande
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def valider_commande(request, commande_id):
    user = request.user
    if user.role != "vendeur":
        return Response({
            "success": False,
            "errors": "Accès refusé. Cette vue est réservée aux vendeurs."
        }, status=403)
    
    try:
        commande = Commande.objects.get(identifiant_commande=commande_id)
    except Commande.DoesNotExist:
        return Response({
            "success": False,
            "errors": "Commande non trouvée."
        }, status=404)
    
    try:
        serializer = CommandeUpdateSerializer(
            commande,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success":True,
                "data":serializer.data
            }, status=200)
        return Response({
            "success":False,
            "errors":serializer.errors
        }, status=400)
    except Exception as e :
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    


# Fonction pour valider livraison de la commande
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def livrer_commande(request, commande_id):
    user = request.user
    if user.role != "vendeur":
        return Response({
            "success": False,
            "errors": "Accès refusé. Cette vue est réservée aux vendeurs."
        }, status=403)
    
    try:
        commande = Commande.objects.get(identifiant_commande=commande_id)
    except Commande.DoesNotExist:
        return Response({
            "success": False,
            "errors": "Commande non trouvée."
        }, status=404)
    
    try:
        serializer = CommandeUpdateSerializer(
            commande,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success":True,
                "data":serializer.data
            }, status=200)
        return Response({
            "success":False,
            "errors":serializer.errors
        }, status=400)
    except Exception as e :
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def annuler_commande(request,commande_id):
    user = request.user
    if user.role != "vendeur":
        return Response({
            "success": False,
            "errors": "Accès refusé. Cette vue est réservée aux vendeurs."
        }, status=403)
    
    try:
        commande = Commande.objects.get(identifiant_commande=commande_id)
        commande.is_active = False
    except Commande.DoesNotExist:
        return Response({
            "success": False,
            "errors": "Commande non trouvée."
        }, status=404)
    
    try:
        serializer = CommandeUpdateSerializer(
            commande,
            data=request.data,
            partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success":True,
                "data":serializer.data
            }, status=200)
        return Response({
            "success":False,
            "errors":serializer.errors
        }, status=400)
    except Exception as e :
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
