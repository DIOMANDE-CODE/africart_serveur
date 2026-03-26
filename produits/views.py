from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from permissions import EstAdministrateur

from .models import Categorie, Produit, AlertProduit, NotationProduit
from .serializers import (
    CategorieSerializer,
    ProduitSerializer,
    AlertProduitSerializer,
    NotationProduitSerializer,
)
from decimal import Decimal
import os

from rest_framework.pagination import LimitOffsetPagination
from django.db.models import Q
from django.db.models import Case, When, Value, IntegerField, F
from permissions import EstClient
from django.db.models import Avg
from permissions import EstGerant

# Create your views here.

# """ Fonctiionnalités du modèle Categorie """"

# Lister les categories


@api_view(["GET"])
@permission_classes([AllowAny])
def list_categorie(request):
    try:
        categories = Categorie.objects.all()

        serializer = CategorieSerializer(categories, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Ajouter une catégorie
@api_view(["POST"])
@permission_classes([EstAdministrateur | EstGerant])
def create_categorie(request):
    print(request.data)
    nom = request.data.get("nom_categorie")

    # Verifier le champs nom
    if not nom:
        return Response(
            {"success": False, "errors": "Le champs nom est obligatoire"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verifier que la categorie n'existe pas
    if Categorie.objects.filter(nom_categorie=nom).exists():
        return Response({"success": False, "errors": "Cette catégorie existe dejà"})

    # Création de la catégorie
    try:
        serializer = CategorieSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"success": True, "message": "Nouvelle catégorie ajoutée"},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(Exception)
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Voir et modifier les details categorie
@api_view(["GET", "PUT"])
@permission_classes([EstAdministrateur | EstGerant])
def detail_categorie(request, identifiant):
    nom = request.data.get("nom_categorie")

    # Verifier la categorie
    try:
        categorie = Categorie.objects.get(identifiant_categorie=identifiant)
    except Categorie.DoesNotExist:
        return Response(
            {"success": False, "errors": "Cette catégorie n'existe pas"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Requette GET
    if request.method == "GET":

        try:
            serializer = CategorieSerializer(categorie)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(Exception)
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne du serveur",
                    "message": str(e),
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(Exception)
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne du serveur",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Requette PUT
    if request.method == "PUT":

        # Verifier le champs nom
        if not nom:
            return Response(
                {"success": False, "errors": "Le champs nom est obligatoire"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            serializer = CategorieSerializer(categorie, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "success": True,
                        "message": "Informations modifiées avec succès",
                        "data": serializer.data,
                    },
                    status=status.HTTP_200_OK,
                )
            else:
                return Response(
                    {"success": False, "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne du serveur",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Requette DELETE


@api_view(["DELETE"])
@permission_classes([EstAdministrateur | EstGerant])
def delete_Categorie(request, identifiant):
    try:
        categorie = Categorie.objects.get(identifiant_client=identifiant)
    except Categorie.DoesNotExist:
        return Response(
            {"success": False, "errors": "Cette catégorie n'existe pas"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        categorie.delete()

        return Response(
            {"success": True, "message": "Categorie supprimé avec succès"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# """ Fonctiionnalités du modèle Produit """"
# Lister les produits
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_produit_pour_personnel(request):
    try:
        search = request.GET.get("search")

        # Base queryset
        produits = Produit.objects.annotate(
            critique=Case(
                When(
                    quantite_produit_disponible__lte=F("seuil_alerte_produit"),
                    then=Value(1),
                ),
                default=Value(0),
                output_field=IntegerField(),
            )
        ).order_by("-critique", "quantite_produit_disponible", "nom_produit")

        # Recherche
        if search:
            produits = produits.filter(Q(nom_produit__icontains=search))

        # Pagination
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        produits_page = paginator.paginate_queryset(produits, request)

        serializer = ProduitSerializer(produits_page, many=True)
        paginator_response = paginator.get_paginated_response(serializer.data)
        response_data = paginator_response.data

        return Response(
            {"success": True, "data": response_data}, status=status.HTTP_200_OK
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Lister les produits ( Personnel )


# Lister les produits
@api_view(["GET"])
@permission_classes([AllowAny])
def list_produit(request):
    try:
        search = request.GET.get("search")
        tri_categorie = request.GET.get("categorie")  # filtre par catégorie
        sortBy = request.GET.get("tri_par")  # tri par prix/date

        # Base queryset
        produits = Produit.objects.filter(
            quantite_produit_disponible__gt=5, is_active=False
        )

        # Recherche
        if search:
            produits = produits.filter(Q(nom_produit__icontains=search))

        # Filtre par catégorie
        if tri_categorie:
            produits = produits.filter(categorie_produit__nom_categorie=tri_categorie)

        # Tri
        if sortBy:
            if sortBy == "prix_croissant":
                produits = produits.order_by("prix_unitaire_produit")
            elif sortBy == "prix_decroissant":
                produits = produits.order_by("-prix_unitaire_produit")
            elif sortBy == "nouveaute":
                produits = produits.order_by("-date_creation")
        else:
            # tri par défaut
            produits = produits.order_by("-date_creation")

        # Pagination
        paginator = LimitOffsetPagination()
        paginator.default_limit = 10
        produits_page = paginator.paginate_queryset(produits, request)

        serializer = ProduitSerializer(produits_page, many=True)
        paginator_response = paginator.get_paginated_response(serializer.data)
        response_data = paginator_response.data

        return Response(
            {"success": True, "data": response_data}, status=status.HTTP_200_OK
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Ajouter un produit
@api_view(["POST"])
@permission_classes([EstAdministrateur | EstGerant])
def create_produit(request):
    nom = request.data.get("nom_produit")
    prix_unitaire = Decimal(request.data.get("prix_unitaire_produit"))
    quantite_produit = int(request.data.get("quantite_produit_disponible"))
    seuil_produit = int(request.data.get("seuil_alerte_produit"))
    categorie_uuid = request.data.get("categorie_produit")
    categorie = Categorie.objects.get(identifiant_categorie=categorie_uuid)
    image = request.FILES.get("image_produit")

    # Charger une image par defauut
    if not image:
        image_path = os.path.join("media", "logo_marchePro.png")
    else:
        image_path = image

    # Verifier les champs
    if (
        not nom
        and not prix_unitaire
        or not quantite_produit
        or not seuil_produit
        or not categorie_uuid
    ):
        return Response(
            {"success": False, "errors": "Le champs nom est obligatoire"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verifier que le produit n'existe pas
    if Produit.objects.filter(nom_produit=nom).exists():
        return Response(
            {"success": False, "errors": "Ce produit existe dejà"},
            status=status.HTTP_409_CONFLICT,
        )

    # Verifier que le seuil est inferieur à la quantité du produit
    if seuil_produit >= quantite_produit:
        return Response(
            {"success": False, "errors": "Le seuil doit être inférieure à la quantité"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Création du produit

    try:
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
            return Response(
                {"success": True, "message": "Nouveau produit ajouté"},
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(Exception)
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["GET", "PUT"])
@permission_classes([AllowAny])
def detail_produit(request, identifiant):
    # GET : récupérer un produit
    if request.method == "GET":
        try:
            produit = Produit.objects.get(identifiant_produit=identifiant)
            serializer = ProduitSerializer(produit)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Produit.DoesNotExist:
            return Response(
                {"success": False, "errors": "Produit introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne du serveur",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # PUT : modifier un produit (admin uniquement)
    if request.method == "PUT" and getattr(request.user, "role", None) == "admin":
        try:
            produit = Produit.objects.get(identifiant_produit=identifiant)
        except Produit.DoesNotExist:
            return Response(
                {"success": False, "errors": "Produit introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        nom = request.data.get("nom_produit")
        prix_unitaire = request.data.get("prix_unitaire_produit")
        quantite_produit = request.data.get("quantite_produit_disponible")
        seuil_produit = request.data.get("seuil_alerte_produit")
        categorie_uuid = request.data.get("categorie_produit")

        # Vérification des champs obligatoires
        if (
            nom is None
            or prix_unitaire is None
            or quantite_produit is None
            or seuil_produit is None
            or categorie_uuid is None
        ):
            return Response(
                {"success": False, "errors": "Tous les champs sont obligatoires."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Conversion des valeurs
        try:
            prix_unitaire = Decimal(prix_unitaire)
            quantite_produit = int(quantite_produit)
            seuil_produit = int(seuil_produit)
        except Exception:
            return Response(
                {"success": False, "errors": "Valeurs numériques invalides."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Vérification de la catégorie
        try:
            categorie = Categorie.objects.get(identifiant_categorie=categorie_uuid)
        except Categorie.DoesNotExist:
            return Response(
                {"success": False, "errors": "Catégorie introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Vérifier que le seuil est inférieur à la quantité
        if seuil_produit >= quantite_produit:
            return Response(
                {
                    "success": False,
                    "errors": "Le seuil doit être inférieur à la quantité.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Mise à jour du produit
        serializer = ProduitSerializer(produit, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(categorie_produit=categorie)
            return Response(
                {
                    "success": True,
                    "message": "Informations modifiées avec succès",
                    "data": serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        else:
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return Response(
        {"success": False, "errors": "Méthode non autorisée ou accès refusé."},
        status=status.HTTP_403_FORBIDDEN,
    )


# Requette DELETE


@api_view(["DELETE"])
@permission_classes([EstAdministrateur | EstGerant])
def delete_produit(request, identifiant):
    try:
        produit = Produit.objects.get(identifiant_produit=identifiant)
    except Categorie.DoesNotExist:
        return Response(
            {"success": False, "errors": "Cette catégorie n'existe pas"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        produit.delete()

        return Response(
            {"success": True, "message": "Categorie supprimé avec succès"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Fonction sur les alertes de stock faible
@api_view(["GET"])
def alertes_actives(request):
    try:
        alertes = AlertProduit.objects.filter(statut_alerte=True).order_by(
            "-date_alerte"
        )
        serializer = AlertProduitSerializer(alertes, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        print(Exception)
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

# Fonction pour la notation des produits

# Fonction pour noter un produit
@api_view(["POST"])
@permission_classes([EstClient])
def noter_produit(request, identifiant):
    try:
        produit = Produit.objects.get(identifiant_produit=identifiant)
    except Produit.DoesNotExist:
        return Response(
            {"success": False, "errors": "Produit introuvable."},
            status=status.HTTP_404_NOT_FOUND,
        )

    note = request.data.get("note_produit")
    if note is None:
        return Response(
            {"success": False, "errors": "La note est obligatoire."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        note_found = NotationProduit.objects.get(
            produit=produit, utilisateur=request.user
        )
        if note_found:
            return Response(
                {"success": False, "errors": "Vous avez déjà noté ce produit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

    except NotationProduit.DoesNotExist:
        pass

    if type(note) is str:
        return Response(
            {"success": False, "errors": "La note doit être un entier entre 1 et 5."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        note = int(note)
        if note < 1 or note > 5:
            raise ValueError
    except ValueError:
        return Response(
            {"success": False, "errors": "La note doit être un entier entre 1 et 5."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    serializer = NotationProduitSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(produit=produit, utilisateur=request.user)
        return Response(
            {
                "success": True,
                "message": "Merci pour votre note !",
                "data": serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )
    else:
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )


# Fonction pour calculer la note moyenne d'un produit


@api_view(["GET"])
@permission_classes([AllowAny])
def note_moyenne_produit(request, identifiant_produit):
    try:
        produit = Produit.objects.get(identifiant_produit=identifiant_produit)
    except Produit.DoesNotExist:
        return Response(
            {"success": False, "errors": "Produit introuvable."},
            status=status.HTTP_404_NOT_FOUND,
        )

    notations = NotationProduit.objects.filter(produit=produit)
    if not notations.exists():
        return Response(
            {"success": True, "data": {"note_moyenne": None, "nombre_notations": 0}},
            status=status.HTTP_200_OK,
        )

    note_moyenne = notations.aggregate(moyenne=Avg("note_produit"))["moyenne"]
    nombre_notations = notations.count()

    return Response(
        {
            "success": True,
            "data": {
                "note_moyenne": round(note_moyenne, 2),
                "nombre_notations": nombre_notations,
            },
        },
        status=status.HTTP_200_OK,
    )
