from django.urls import path
from .views import login_utilisateur,logout_utilisateur, check_session

urlpatterns = [
    path('login/', login_utilisateur,name='login_utilisateur'),
    path('logout/', logout_utilisateur,name='logout_utilisateur'),
    path('check_session/', check_session,name='check_session'),
]
