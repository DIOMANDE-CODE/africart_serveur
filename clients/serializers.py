from rest_framework import serializers
from .models import Client
from django.contrib.auth.hashers import make_password


# Creation des serializers
class ClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = ['identifiant_client','nom_client','role','numero_telephone_client','is_active','date_creation','date_modification']
        read_only_fields = ['identifiant_client','date_creation','date_modification']