from .models import Utilisateur, DEFAULT_PROFILE_PHOTO, DEFAULT_PROFILE_THUMBNAIL
from rest_framework import serializers

class UtilisateurSerializer(serializers.ModelSerializer):
    is_staff = serializers.BooleanField(default=False)
    is_superuser = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)
    password = serializers.CharField(write_only=True)
    photo_profil_utilisateur = serializers.SerializerMethodField()
    thumbnail = serializers.SerializerMethodField()

    class Meta :
        model = Utilisateur
        fields = ['identifiant_utilisateur','email_utilisateur','password','nom_utilisateur','numero_telephone_utilisateur','photo_profil_utilisateur','thumbnail','role','date_creation','date_modification','is_active','is_staff','is_superuser']
        read_only_fields = ['identifiant_utilisateur','date_creation','date_modification','is_active']

    def get_photo_profil_utilisateur(self, obj):
        """Retourner la photo de profil ou la photo par défaut"""
        if obj.photo_profil_utilisateur:
            if hasattr(obj.photo_profil_utilisateur, 'url'):
                return obj.photo_profil_utilisateur.url
            return str(obj.photo_profil_utilisateur)
        return DEFAULT_PROFILE_PHOTO

    def get_thumbnail(self, obj):
        """Retourner la miniature ou la photo par défaut"""
        if obj.thumbnail:
            return obj.thumbnail
        if obj.photo_profil_utilisateur:
            if hasattr(obj.photo_profil_utilisateur, 'url'):
                return obj.photo_profil_utilisateur.url
            return str(obj.photo_profil_utilisateur)
        return DEFAULT_PROFILE_THUMBNAIL

    def create(self, validated_data):
        password = validated_data.pop('password') 
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user