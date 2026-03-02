from django.contrib import admin
from .models import Commande, DetailCommande,ZoneLivraison

# Register your models here.

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = (
        'identifiant_commande',
        'client',
        'utilisateur',
        'code_livraison',
        'lieu_livraison',
        'date_commande',
        'etat_commande',
        'frais_livraison_appliques',
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

@admin.register(ZoneLivraison)
class ZoneLivraisonAdmin(admin.ModelAdmin):
    list_display = ('identifiant_zone','nom_zone','frais_livraison','latitude','longitude','rayon_metres','date_creation','date_modification',)
    search_fields = ('nom_zone',)
    list_filter = ('nom_zone',)

 