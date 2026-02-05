from django.contrib import admin
from .models import Categorie, Produit, AlertProduit

# Register your models here.

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display=('id','identifiant_categorie','nom_categorie','description_categorie','date_creation','date_modification',)
    search_fields=('nom_categorie',)
    ordering = ['nom_categorie']


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display=('id','identifiant_produit','nom_produit','image_produit','thumbnail','description_produit','prix_unitaire_produit','quantite_produit_disponible','seuil_alerte_produit','categorie_produit','date_creation','date_modification',)
    search_fields=('nom_produit',)
    ordering = ['nom_produit']

@admin.register(AlertProduit)
class AlertProduitAdmin(admin.ModelAdmin):
    list_display=('id','identifiant_alerte','produit','message_alerte','statut_alerte','date_alerte',)
    search_fields=('message_alertet',)
    ordering = ['message_alerte']
