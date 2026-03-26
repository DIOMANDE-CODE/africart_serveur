from django.urls import path
from .views import (
    create_utilisateur,
    detail_utilisateur,
    delete_utilisateur,
    list_utilisateur,
    info_utilisateur,
)

urlpatterns = [
    path("list/", list_utilisateur, name="list-utilisateur"),
    path("create/", create_utilisateur, name="create-utilisateur"),
    path("detail/", detail_utilisateur, name="detail-utilisateur"),
    path("info_utilisateur/", info_utilisateur, name="info-utilisateur"),
    path("delete/<str:id>/", delete_utilisateur, name="delete-utilisateur"),
]
