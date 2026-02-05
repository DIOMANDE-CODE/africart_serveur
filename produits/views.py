from django.shortcuts import render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from permissions import EstAdministrateur, EstGerant

from .models import Categorie, Produit, AlertProduit
from .serializers import CategorieSerializer, ProduitSerializer, AlertProduitSerializer
from decimal import Decimal
from django.shortcuts import get_object_or_404
import os

from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q
from django.core.cache import cache
# Create your views here.
     
# """ Fonctiionnalités du modèle Categorie """"

# Lister les categories
@api_view(['GET'])
# @permission_classes([EstAdministrateur])
@permission_classes([EstAdministrateur])
def list_categorie(request):
    try :
        categories = Categorie.objects.all()
        serializer = CategorieSerializer(categories, many=True)
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
    

# Ajouter une catégorie
@api_view(['POST'])
@permission_classes([EstAdministrateur])
def create_categorie(request):
    print(request.data)
    nom = request.data.get('nom_categorie')

    # Verifier le champs nom
    if  not nom : 
        return Response({
            "success":False,
            "errors":"Le champs nom est obligatoire"
        }, status=status.HTTP_400_BAD_REQUEST)
    
        
    # Verifier que la categorie n'existe pas
    if Categorie.objects.filter(nom_categorie=nom).exists():
        return Response({
            "success":False,
            "errors":"Cette catégorie existe dejà"
        })
    
    # Création de la catégorie
    try :
        serializer = CategorieSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "success":True,
                "message":"Nouvelle catégorie ajoutée"
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

    
# Voir et modifier les details categorie
@api_view(['GET','PUT'])
@permission_classes([EstAdministrateur])
def detail_categorie(request,identifiant):
    nom = request.data.get('nom_categorie')


    # Verifier la categorie
    try :
        categorie = Categorie.objects.get(identifiant_categorie=identifiant)
    except Categorie.DoesNotExist:
        return Response({
            "success":False,
            "errors":"Cette catégorie n'existe pas"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Requette GET
    if request.method == 'GET':
        try :
            serializer = CategorieSerializer(categorie)
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

        # Verifier le champs nom
        if  not nom : 
            return Response({
                "success":False,
                "errors":"Le champs nom est obligatoire"
            }, status=status.HTTP_400_BAD_REQUEST)

        try :
            serializer = CategorieSerializer(categorie, data=request.data, partial=True)
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
def delete_Categorie(request, identifiant):
    try :
        categorie = Categorie.objects.get(identifiant_client=identifiant)
    except Categorie.DoesNotExist:
        return Response({
            "success":False,
            "errors":"Cette catégorie n'existe pas"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        categorie.delete()

        return Response({
            "success": True,
            "message": "Categorie supprimé avec succès"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



# """ Fonctiionnalités du modèle Produit """"

# Lister les produits
@api_view(['GET'])
# @permission_classes([EstAdministrateur,EstGerant])
@permission_classes([AllowAny])
def list_produit(request):
    try :

        search = request.GET.get('search','')

        produits = Produit.objects.all().order_by('-date_creation')

        if search :
            produits = produits.filter(
                Q(nom_produit__icontains=search) | Q(prix_unitaire_produit__icontains=search)
            )

        # Creation d'une clé de cache
        limit = request.GET.get('limit','10')
        offset = request.GET.get('offset','0')

        # Pagination
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        produits_page = paginator.paginate_queryset(produits, request)


        serializer = ProduitSerializer(produits_page, many=True)
        paginator_response = paginator.get_paginated_response(serializer.data)
        response_data = paginator_response.data


        return Response({
            "success":True,
            "data": response_data
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
    

# Ajouter un produit
@api_view(['POST'])
@permission_classes([EstAdministrateur])
def create_produit(request):
    nom = request.data.get('nom_produit')
    prix_unitaire = Decimal(request.data.get('prix_unitaire_produit'))
    quantite_produit = int(request.data.get('quantite_produit_disponible'))
    seuil_produit = int(request.data.get('seuil_alerte_produit'))
    categorie_uuid = request.data.get('categorie_produit')
    categorie = Categorie.objects.get(identifiant_categorie=categorie_uuid)
    image = request.FILES.get('image_produit')

    # Charger une image par defauut
    if not image:
        image_path = os.path.join('media', 'logo_marchePro.png')
    else:
        image_path = image


    # Verifier les champs
    if  not nom and not prix_unitaire or not quantite_produit or not seuil_produit or not categorie_uuid : 
        return Response({
            "success":False,
            "errors":"Le champs nom est obligatoire"
        }, status=status.HTTP_400_BAD_REQUEST)
    
        
    # Verifier que le produit n'existe pas
    if Produit.objects.filter(nom_produit=nom).exists():
        return Response({
            "success":False,
            "errors":"Ce produit existe dejà"
        }, status=status.HTTP_409_CONFLICT)
    
    # Verifier que le seuil est inferieur à la quantité du produit
    if seuil_produit >= quantite_produit:
        return Response({
            "success":False,
            "errors":"Le seuil doit être inférieure à la quantité"
        },status=status.HTTP_400_BAD_REQUEST)
    
    # Création du produit
    
    try :
        serializer = ProduitSerializer(data=request.data)
        if serializer.is_valid():
            produit = Produit(
            nom_produit=nom,
            prix_unitaire_produit=prix_unitaire,
            quantite_produit_disponible=quantite_produit,
            seuil_alerte_produit=seuil_produit,
            categorie_produit=categorie,
            image_produit=image_path,
)
            produit.save()
            return Response({
                "success":True,
                "message":"Nouveau produit ajouté"
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
def detail_produit(request,identifiant):
    nom = request.data.get('nom_categorie')

    # Requette GET
    if request.method == 'GET':
        # Verifier la categorie
        try :
            produit = Produit.objects.get(identifiant_produit=identifiant)
        except Categorie.DoesNotExist:
                return Response({
                    "success":False,
                    "errors":"Cette catégorie n'existe pas"
                }, status=status.HTTP_400_BAD_REQUEST)
        
        try :
            serializer = ProduitSerializer(produit)
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

        try:
            produit = Produit.objects.get(identifiant_produit=identifiant)
        except Produit.DoesNotExist:
            return Response({
                "success": False,
                "errors": "Produit introuvable."
            }, status=status.HTTP_404_NOT_FOUND)

        nom = request.data.get('nom_produit')
        prix_unitaire = Decimal(request.data.get('prix_unitaire_produit'))
        quantite_produit = int(request.data.get('quantite_produit_disponible'))
        seuil_produit = int(request.data.get('seuil_alerte_produit'))
        categorie_uuid = request.data.get('categorie_produit')

        # Vérification de la catégorie
        try:
            categorie = Categorie.objects.get(identifiant_categorie=categorie_uuid)
        except Categorie.DoesNotExist:
            return Response({
                "success": False,
                "errors": "Catégorie introuvable."
            }, status=status.HTTP_404_NOT_FOUND)

        # Verifier les champs
        if  not nom or not prix_unitaire or not quantite_produit or not seuil_produit or not categorie : 
            return Response({
                "success":False,
                "errors":"Le champs nom est obligatoire"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verifier que le seuil est inferieur à la quantité du produit
        if seuil_produit >= quantite_produit:
            return Response({
                "success":False,
                "errors":"Le seuil doit être inférieure à la quantité"
            },status=status.HTTP_400_BAD_REQUEST)

        try :
            serializer = ProduitSerializer(produit, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save(categorie_produit=categorie)
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
def delete_produit(request, identifiant):
    try :
        produit = Produit.objects.get(identifiant_produit=identifiant)
    except Categorie.DoesNotExist:
        return Response({
            "success":False,
            "errors":"Cette catégorie n'existe pas"
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        produit.delete()

        return Response({
            "success": True,
            "message": "Categorie supprimé avec succès"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Fonction sur les alertes de stock faible
@api_view(["GET"])
def alertes_actives(request):
    try:
        alertes = AlertProduit.objects.filter(statut_alerte=True).order_by('-date_alerte')
        serializer = AlertProduitSerializer(alertes, many=True)
        return Response({
            "success": True,
            "data": serializer.data
        }, status=status.HTTP_200_OK)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(Exception)
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)