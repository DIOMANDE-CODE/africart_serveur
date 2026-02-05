from django.urls import path
from .views import creer_vente,liste_ventes,detail_ventes,liste_ventes_par_vendeur

urlpatterns = [
    path('creer/', creer_vente,name='creer-vente'),
    path('list/', liste_ventes,name='liste_ventes'),
    path('list/vendeur/', liste_ventes_par_vendeur,name='liste_ventes_par_vendeur'),
    path('detail/<str:vente_id>/', detail_ventes,name='detail_ventes'),
]
