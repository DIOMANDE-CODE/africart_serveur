from rest_framework import serializers
from .models import Client


# Creation des serializers
class ClientSerializer(serializers.ModelSerializer):

    class Meta:
        model = Client
        fields = ['identifiant_client','nom_client','email_client','role','numero_telephone_client','date_creation','date_modification']
        read_only_fields = ['identifiant_client','date_creation','date_modification']