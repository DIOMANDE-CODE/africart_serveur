from django.urls import path
from .views import creer_commande,liste_commande_par_vendeur, detail_commande,valider_commande, liste_commande, livrer_commande, annuler_commande

urlpatterns = [
    path('creer/', creer_commande,name='creer-commande'),
    path('list/', liste_commande,name='liste-commande'),
    path('list/vendeur/', liste_commande_par_vendeur,name='liste-commande'),
    path('detail/<str:commande_id>/', detail_commande,name='detail-commande'),
    path('valider/<str:commande_id>/', valider_commande,name='valider-commande'),
    path('livrer/<str:commande_id>/', livrer_commande,name='valider-commande'),
    path('annuler/<str:commande_id>/', annuler_commande,name='annuler_commande')
]