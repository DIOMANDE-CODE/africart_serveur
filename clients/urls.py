from django.urls import path
from .views import create_client, delete_Client,detail_client,list_client

urlpatterns = [
    path('list/', list_client,name='list_client'),
    path('create/', create_client,name='create_client'),
    path('detail/<str:identifiant>/', detail_client,name='detail_client'),
    path('delete/<str:identifiant>/', delete_Client,name='delete_Client'),
]
