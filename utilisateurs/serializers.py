from .models import Utilisateur
from rest_framework import serializers

class UtilisateurSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False)
    is_superuser = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)
    password = serializers.CharField(write_only=True)

    class Meta :
        model = Utilisateur
        fields = ['identifiant_utilisateur','email_utilisateur','password','nom_utilisateur','numero_telephone_utilisateur','photo_profil_utilisateur','thumbnail','role','date_creation','date_modification','is_active','is_staff','is_superuser']
        read_only_fields = ['identifiant_utilisateur','date_creation','date_modification','is_active']

    def create(self, validated_data):
        password = validated_data.pop('password') 
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user