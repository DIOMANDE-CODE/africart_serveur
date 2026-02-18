from rest_framework import serializers
from .models import Categorie, Produit, AlertProduit
from cloudinary.utils import cloudinary_url

# Serializer de la classe Categorie
class CategorieSerializer(serializers.ModelSerializer):
    produits = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Categorie
        fields = ['identifiant_categorie','nom_categorie','description_categorie','date_creation','date_modification','produits']
        read_only_fields = ['identifiant_categorie','date_creation','date_modification']

    def get_produits(self, obj):
        produits = Produit.objects.filter(categorie_produit=obj)
        return [
            { 
                "identifiant_produit": p.identifiant_produit, 
                "nom_produit": p.nom_produit, 
                "prix_unitaire_produit": str(p.prix_unitaire_produit), 
                "quantite_produit_disponible": p.quantite_produit_disponible, 
                "seuil_alerte_produit": p.seuil_alerte_produit, 
                "thumbnail": p.thumbnail, 
                "image_produit": cloudinary_url(p.image_produit.public_id, secure=True)[0] if p.image_produit else None
            } 
            for p in produits
        ]

# Serializer de Produit
class ProduitSerializer(serializers.ModelSerializer):
    categorie_produit = CategorieSerializer(required=False, read_only=True)
    image_produit = serializers.SerializerMethodField()
    class Meta:
        model = Produit
        fields = ['identifiant_produit','nom_produit','image_produit','thumbnail','image_produit_2','thumbnail_2','image_produit_3','thumbnail_3','description_produit','caracteristiques_produit','prix_unitaire_produit','quantite_produit_disponible','seuil_alerte_produit','categorie_produit','date_creation','date_modification']
        read_only_fields = ['identifiant_produit','categorie_produit','date_creation','date_modification']

    def get_image_produit(self, obj):
        if obj.image_produit:
            url, options = cloudinary_url(obj.image_produit.public_id, secure=True)
            return url
        return None

# Serializer de Alert Produit
class AlertProduitSerializer(serializers.ModelSerializer):
    produit = ProduitSerializer(required=False, read_only=True)
    class Meta:
        model = AlertProduit
        fields = '__all__'
        read_only_fields = ['identifiant_alerte','produit','date_creation']