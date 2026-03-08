from django.contrib import admin
from .models import VueProduit, Recommandation


@admin.register(VueProduit)
class VueProduitAdmin(admin.ModelAdmin):
    list_display  = ('produit', 'utilisateur', 'timestamp')
    list_filter   = ('timestamp',)
    date_hierarchy = 'timestamp'
    ordering      = ('-timestamp',)


@admin.register(Recommandation)
class RecommandationAdmin(admin.ModelAdmin):
    list_display  = ('type_recommandation', 'produit_source', 'produit_recommande', 'score', 'date_calcul')
    list_filter   = ('type_recommandation',)
    search_fields = ('produit_source__nom_produit', 'produit_recommande__nom_produit')
    ordering      = ('-score',)