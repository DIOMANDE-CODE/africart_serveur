from django.contrib import admin
from .models import Categorie, Produit, AlertProduit, NotationProduit

# Register your models here.


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifiant_categorie",
        "nom_categorie",
        "description_categorie",
        "pourcentage_promo_categorie",
        "prix_promo_categorie",
        "date_creation",
        "date_modification",
    )
    search_fields = ("nom_categorie",)
    ordering = ["nom_categorie"]


@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifiant_produit",
        "nom_produit",
        "image_produit",
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
        "pourcentage_promo",
        "prix_promo_produit",
        "date_creation",
        "date_modification",
        "is_active",
    )
    search_fields = ("nom_produit",)
    ordering = ["nom_produit"]


@admin.register(AlertProduit)
class AlertProduitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifiant_alerte",
        "produit",
        "message_alerte",
        "statut_alerte",
        "date_alerte",
    )
    search_fields = ("message_alertet",)
    ordering = ["message_alerte"]


@admin.register(NotationProduit)
class NotationProduitAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "identifiant_notation",
        "produit",
        "utilisateur",
        "note_produit",
        "date_notation",
    )
    search_fields = ("note_produit",)
    ordering = ["date_notation"]
