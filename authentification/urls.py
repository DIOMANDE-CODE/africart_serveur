from django.urls import path
from .views import login_utilisateur,logout_utilisateur, check_session,changer_mot_de_passe,mobile_check_session

urlpatterns = [
    path('login/', login_utilisateur,name='login_utilisateur'),
    path('logout/', logout_utilisateur,name='logout_utilisateur'),
    path('check_session/', check_session,name='check_session'),
    path('mobile_check_session/', mobile_check_session,name='mobile_check_session'),
    path('changer_mot_de_passe/', changer_mot_de_passe,name='changer_mot_de_passe'),
]
