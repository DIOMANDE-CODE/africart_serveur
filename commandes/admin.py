from django.contrib import admin
from .models import Commande, DetailCommande

# Register your models here.

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        'identifiant_commande',
        'client',
        'utilisateur',
        'code_livraison',
        'date_commande',
        'etat_commande',
        'is_active',
        'total_ht',
        'tva',
        'total_ttc',
        'date_creation',
    )
    search_fields = ('client__nom_client', 'utilisateur__username', 'identifiant_commande')
    list_filter = ('date_commande',)
    readonly_fields = ('date_creation', 'date_modification')


@admin.register(DetailCommande)
class DetailCommandeAdmin(admin.ModelAdmin):
    list_display = (
        'identifiant_detail_commande',
        'commande',
        'produit',
        'quantite',
        'prix_unitaire',
        'sous_total',
        'date_creation',
    )
    search_fields = ('commande__identifiant_commande', 'produit__nom_produit')
    list_filter = ('produit',)
    readonly_fields = ('sous_total', 'date_creation', 'date_modification')
