from django.urls import path
from .views import create_categorie, create_produit, list_categorie, list_produit, detail_categorie, delete_Categorie,detail_produit, delete_produit, alertes_actives

urlpatterns = [
    # Categories
    path('list/categorie/', list_categorie,name='list_categorie'),
    path('create/categorie/', create_categorie,name='create_categorie'),
    path('detail/categorie/<str:identifiant>/', detail_categorie,name='detail_categorie'),
    path('delete/categorie/<str:identifiant>/', delete_Categorie,name='delete_categorie'),

    # Produits
    path('list/', list_produit,name='list_produit'),
    path('create/', create_produit,name='create_produit'),
    path('detail/<str:identifiant>/', detail_produit,name='detail_produit'),
    path('delete/<str:identifiant>/', delete_produit,name='delete_produit'),

    # Alertes de stock faible
    path('alerte/stock_faible/', alertes_actives,name='alertes_actives'),
]
    