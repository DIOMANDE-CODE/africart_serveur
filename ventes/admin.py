from django.contrib import admin
from .models import Vente, DetailVente

@admin.register(Vente)
class VenteAdmin(admin.ModelAdmin):
    list_display = (
        'identifiant_vente',
        'utilisateur',
        'date_vente',
        'total_ht',
        'tva',
        'total_ttc',
        'date_creation',
    )
    search_fields = ('utilisateur__username', 'identifiant_vente')
    list_filter = ('date_vente',)
    readonly_fields = ('date_creation', 'date_modification')

@admin.register(DetailVente)
class DetailVenteAdmin(admin.ModelAdmin):
    list_display = (
        'identifiant_detail_vente',
        'vente',
        'produit',
        'quantite',
        'prix_unitaire',
        'sous_total',
        'date_creation',
    )
    search_fields = ('vente__identifiant_vente', 'produit__nom_produit')
    list_filter = ('produit',)
    readonly_fields = ('sous_total', 'date_creation', 'date_modification')