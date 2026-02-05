from rest_framework import serializers
from .models import Categorie, Produit, AlertProduit

# Serializer de la classe Categorie
class CategorieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categorie
        fields = ['identifiant_categorie','nom_categorie','description_categorie','date_creation','date_modification']
        read_only_fields = ['identifiant_categorie','date_creation','date_modification']

# Serializer de Produit
class ProduitSerializer(serializers.ModelSerializer):
    categorie_produit = CategorieSerializer(required=False, read_only=True)
    class Meta:
        model = Produit
        fields = ['identifiant_produit','nom_produit','image_produit','thumbnail','description_produit','prix_unitaire_produit','quantite_produit_disponible','seuil_alerte_produit','categorie_produit','date_creation','date_modification']
        read_only_fields = ['identifiant_produit','categorie_produit','date_creation','date_modification']

# Serializer de Alert Produit
class AlertProduitSerializer(serializers.ModelSerializer):
    produit = ProduitSerializer(required=False, read_only=True)
    class Meta:
        model = AlertProduit
        fields = '__all__'
        read_only_fields = ['identifiant_alerte','produit','date_creation']