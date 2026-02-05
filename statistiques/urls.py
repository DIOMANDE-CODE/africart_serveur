from django.urls import path
from .views import statistiques_du_jour, statistiques_de_la_semaine, statistiques_du_mois, statistiques_quotidiennes_vendeur

urlpatterns = [
    path('du_jour/', statistiques_du_jour,name='statistiques_du_jour'),
    path('du_jour/vendeur/', statistiques_quotidiennes_vendeur,name='statistiques_quotidiennes_vendeur'),
    path('de_semaine/', statistiques_de_la_semaine,name='statistiques_de_la_semaine'),
    path('de_mois/', statistiques_du_mois,name='statistiques_du_mois'),

    
]
