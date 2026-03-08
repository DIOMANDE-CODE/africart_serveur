from django.urls import path
from .views import chatbot, chatbot_user_connected

urlpatterns = [
    path('chatbot/', chatbot, name='chatbot'),
    path('chatbot_user_connected/', chatbot_user_connected, name='chatbot_user_connected'),
]
