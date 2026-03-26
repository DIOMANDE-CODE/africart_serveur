from django.urls import path
from .views import enregistrer_vue_produit, obtenir_recommandations

urlpatterns = [
    path("", obtenir_recommandations, name="obtenir_recommandations"),
    path("vue/", enregistrer_vue_produit, name="enregistrer_vue_produit"),
]
