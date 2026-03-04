from rest_framework import serializers
from .models import Utilisateur, DEFAULT_PROFILE_PHOTO, DEFAULT_PROFILE_THUMBNAIL

class UtilisateurSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    # On laisse DRF gérer ces champs pour permettre l'upload (écriture)
    photo_profil_utilisateur = serializers.ImageField(required=False, allow_null=True)
    thumbnail = serializers.URLField(read_only=True)

    class Meta:
        model = Utilisateur
        fields = [
            'identifiant_utilisateur', 'email_utilisateur', 'password', 
            'nom_utilisateur', 'numero_telephone_utilisateur', 
            'photo_profil_utilisateur', 'thumbnail', 'role', 
            'date_creation', 'date_modification', 'is_active', 
            'is_staff', 'is_superuser'
        ]
        read_only_fields = ['identifiant_utilisateur', 'date_creation', 'date_modification', 'is_active', 'thumbnail']

    def to_representation(self, instance):
        """Personnalise l'affichage des données envoyées au mobile (Lecture)"""
        representation = super().to_representation(instance)
        
        # Gestion de la photo de profil par défaut
        if not instance.photo_profil_utilisateur:
            representation['photo_profil_utilisateur'] = DEFAULT_PROFILE_PHOTO
        else:
            # S'assure de retourner l'URL Cloudinary
            representation['photo_profil_utilisateur'] = instance.photo_profil_utilisateur.url if hasattr(instance.photo_profil_utilisateur, 'url') else str(instance.photo_profil_utilisateur)

        # Gestion du thumbnail par défaut
        if not instance.thumbnail:
            representation['thumbnail'] = representation['photo_profil_utilisateur']
            
        return representation

    def update(self, instance, validated_data):
        """Gère la mise à jour, notamment le hachage du mot de passe"""
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)

    def create(self, validated_data):
        """Gère la création avec hachage du mot de passe"""
        password = validated_data.pop('password') 
        user = Utilisateur(**validated_data)
        user.set_password(password)
        user.save()
        return user