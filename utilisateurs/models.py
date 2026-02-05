from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.validators import RegexValidator
import uuid
from PIL import Image
import os
from io import BytesIO
from cloudinary.models import CloudinaryField
import requests
import cloudinary.uploader


# Create your models here.

# Définition de la photo de profil par defaut
def photo_profil_par_defaut():
    return 'https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png'

# Definition des roles de l'utilisateur
ROLE_CHOICES = (
    ('admin','admin'),
    ('gerant','gerant'),
    ('vendeur','vendeur'),
)

# Verification du numéro de l'utilisateur en conformité avec celui de la CI
verification_numero = RegexValidator(
    regex=r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$',
    message="Veuillez entrer un numéro ivoirien valide (ex: +2250102030405 ou 0102030405)."
)

class UtilisateurManager(BaseUserManager):
    def create_user(self, email_utilisateur=None, password=None, **extra_fields):
        if not email_utilisateur:
            raise ValueError("Email Obligatoire")
        
        extra_fields.setdefault('is_active',True)
        extra_fields.setdefault('is_staff',False)
        extra_fields.setdefault('is_superuser',False)

        # creation du compte
        email = self.normalize_email(email_utilisateur)
        user = self.model(email_utilisateur=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email_utilisateur, password=None, **extra_fields):
        extra_fields.setdefault('is_staff',True)
        extra_fields.setdefault('is_superuser',True)
        extra_fields.setdefault('is_active',True)
        extra_fields.setdefault('role','admin')

        if not password :
            raise ValueError("l'administrateur doit avoir un mot de passe")
        return self.create_user(email_utilisateur=email_utilisateur, password=password, **extra_fields)

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    identifiant_utilisateur = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    email_utilisateur = models.EmailField(max_length=50, unique=True, verbose_name="Email", blank=True, null=True)
    nom_utilisateur = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nom utilisateur")
    photo_profil_utilisateur = CloudinaryField(
        'photo_profil',
        folder='mes_projets/AfriCart/utilisateurs/photos_profil/',
        default=photo_profil_par_defaut,
        blank=True,
        null=True
    )
    thumbnail = models.URLField(blank=True, null=True, editable=False)

    numero_telephone_utilisateur = models.CharField(max_length=15, validators=[verification_numero], null=True, blank=True, verbose_name="Numero de téléphone")
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default="vendeur", verbose_name="role utilisateur")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UtilisateurManager()

    USERNAME_FIELD = "email_utilisateur"

    def make_thumbnail(self):
        if self.photo_profil_utilisateur:
            url = self.photo_profil_utilisateur.url
            response = requests.get(url)

            if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
                img = Image.open(BytesIO(response.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.thumbnail((200, 200))
                thumb_io = BytesIO()
                img.save(thumb_io, format="JPEG", quality=80)

                result = cloudinary.uploader.upload(
                    thumb_io.getvalue(),
                    folder="mes_projets/AfriCart/utilisateurs/thumbnails/",
                    public_id=f"thumb_{self.identifiant_utilisateur}"
                )
                # Stocker l’URL publique dans le champ thumbnail
                self.thumbnail = result["secure_url"]

    def save(self, *args, **kwargs):
        old_image_url = None
        if self.pk:
            try:
                old_instance = Utilisateur.objects.get(pk=self.pk)
                if old_instance.photo_profil_utilisateur:
                    old_image_url = old_instance.photo_profil_utilisateur.url
            except Utilisateur.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Génération automatique de la miniature si nécessaire
        if self.photo_profil_utilisateur:
            current_image_url = self.photo_profil_utilisateur.url
            if not self.thumbnail or old_image_url != current_image_url:
                self.make_thumbnail()
                super().save(update_fields=["thumbnail"])
