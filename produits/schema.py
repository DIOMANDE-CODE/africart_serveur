import graphene
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field
from cloudinary.models import CloudinaryField
from .models import Categorie, Produit
from django.db.models import DecimalField
from graphql import GraphQLError

# Converter global pour DecimalField → Float


@convert_django_field.register(DecimalField)
def convert_decimal_to_float(field, registry=None):
    return graphene.Float()


# Converter global pour CloudinaryField → String


@convert_django_field.register(CloudinaryField)
def convert_cloudinary_field(field, registry=None):
    return graphene.String()


class CategorieType(DjangoObjectType):
    class Meta:
        model = Categorie
        fields = (
            "identifiant_categorie",
            "nom_categorie",
            "description_categorie",
            "date_creation",
            "date_modification",
            "produits",
        )


class ProduitType(DjangoObjectType):
    class Meta:
        model = Produit
        interfaces = (graphene.relay.Node,)
        fields = (
            "identifiant_produit",
            "nom_produit",
            "image_produit",  # exposé comme String (URL)
            "thumbnail",
            "image_produit_2",
            "thumbnail_2",
            "image_produit_3",
            "thumbnail_3",
            "description_produit",
            "caracteristiques_produit",
            "prix_unitaire_produit",
            "quantite_produit_disponible",
            "seuil_alerte_produit",
            "categorie_produit",
            "date_creation",
            "date_modification",
        )


class ProduitConnection(graphene.relay.Connection):
    class Meta:
        node = ProduitType


# Classe pour créer un produit
class CreateProduit(graphene.Mutation):

    class Arguments:
        nom_produit = graphene.String(required=True)
        categorie_produit = graphene.UUID(required=True)
        prix_unitaire_produit = graphene.Float(required=True)
        quantite_produit_disponible = graphene.Int(required=True)
        seuil_alerte_produit = graphene.Int(required=True)

    produit = graphene.Field(ProduitType)

    def mutate(
        root,
        info,
        nom_produit,
        categorie_produit,
        prix_unitaire_produit,
        quantite_produit_disponible,
        seuil_alerte_produit,
    ):
        # Vérifier les champs
        if (
            not nom_produit
            or prix_unitaire_produit is None
            or quantite_produit_disponible is None
            or seuil_alerte_produit is None
            or not categorie_produit
        ):
            raise GraphQLError("Tous les champs sont obligatoires.")

        # Verifier que le produit n'existe pas
        if Produit.objects.filter(nom_produit=nom_produit).exists():
            raise GraphQLError("Ce produit existe déjà.")

        # Verifier que le seuil est inferieur à la quantité du produit
        if seuil_alerte_produit >= quantite_produit_disponible:
            raise GraphQLError("Le seuil doit être inférieur à la quantité disponible.")

        try:
            categorie = Categorie.objects.get(identifiant_categorie=categorie_produit)
        except Categorie.DoesNotExist:
            raise GraphQLError("La catégorie spécifiée n'existe pas.")

        produit = Produit(
            nom_produit=nom_produit,
            categorie_produit=categorie,
            prix_unitaire_produit=prix_unitaire_produit,
            quantite_produit_disponible=quantite_produit_disponible,
            seuil_alerte_produit=seuil_alerte_produit,
        )
        produit.save()
        return CreateProduit(produit=produit)


# Classe pour mettre à jour un produit
class UpdateProduit(graphene.Mutation):

    class Arguments:
        identifiant_produit = graphene.UUID(required=True)
        nom_produit = graphene.String()
        categorie_produit = graphene.UUID()
        prix_unitaire_produit = graphene.Float()
        quantite_produit_disponible = graphene.Int()
        seuil_alerte_produit = graphene.Int()
        categorie_produit = graphene.UUID()

    produit = graphene.Field(ProduitType)

    def mutate(
        root,
        info,
        identifiant_produit,
        nom_produit=None,
        categorie_produit=None,
        prix_unitaire_produit=None,
        quantite_produit_disponible=None,
        seuil_alerte_produit=None,
    ):
        try:
            produit = Produit.objects.get(identifiant_produit=identifiant_produit)
        except Produit.DoesNotExist:
            raise Exception("Produit non trouvé")

        if nom_produit is not None:
            produit.nom_produit = nom_produit
        if categorie_produit is not None:
            try:
                categorie = Categorie.objects.get(
                    identifiant_categorie=categorie_produit
                )
                produit.categorie_produit = categorie
            except Categorie.DoesNotExist:
                raise Exception("Catégorie non trouvée")

        if prix_unitaire_produit is not None:
            produit.prix_unitaire_produit = prix_unitaire_produit
        if quantite_produit_disponible is not None:
            produit.quantite_produit_disponible = quantite_produit_disponible
        if seuil_alerte_produit is not None:
            produit.seuil_alerte_produit = seuil_alerte_produit

        produit.save()
        return UpdateProduit(produit=produit)


# Classe pour les requêtes
class Query(graphene.ObjectType):
    # Lister tous les produits
    products = graphene.relay.ConnectionField(ProduitConnection)
    categories = graphene.List(CategorieType)

    # Avoir les details d'un produit par son identifiant
    product = graphene.Field(
        ProduitType, identifiant_produit=graphene.UUID(required=True)
    )

    def resolve_products(root, info, **kwargs):
        return Produit.objects.all().order_by("-date_creation")

    def resolve_product(root, info, identifiant_produit):
        try:
            return Produit.objects.get(identifiant_produit=identifiant_produit)
        except Produit.DoesNotExist:
            return None

    def resolve_categories(root, info):
        return Categorie.objects.all()


class Mutation(graphene.ObjectType):
    update_produit = UpdateProduit.Field()
    create_produit = CreateProduit.Field()


# Déclaration du schéma
schema = graphene.Schema(query=Query, mutation=Mutation)
