from django.urls import path
from .views import (
    login_utilisateur,
    logout_utilisateur,
    check_session,
    changer_mot_de_passe,
    mobile_check_session,
    logout_mobile,
    login_token,
)

urlpatterns = [
    path("login/", login_utilisateur, name="login_utilisateur"),
    path("login_token/", login_token, name="login_token"),
    path("logout/", logout_utilisateur, name="logout_utilisateur"),
    path("logout_mobile/", logout_mobile, name="logout_mobile"),
    path("check_session/", check_session, name="check_session"),
    path("mobile_check_session/", mobile_check_session, name="mobile_check_session"),
    path("changer_mot_de_passe/", changer_mot_de_passe, name="changer_mot_de_passe"),
]
