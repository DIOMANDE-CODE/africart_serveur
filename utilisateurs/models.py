from django.db import models
from django.contrib.auth.models import (
    BaseUserManager,
    AbstractBaseUser,
    PermissionsMixin,
)
from django.core.validators import RegexValidator
import uuid
from cloudinary.models import CloudinaryField

# Définition de la photo de profil par défaut (stockée sur Cloudinary)
DEFAULT_PROFILE_PHOTO = "https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png"
DEFAULT_PROFILE_THUMBNAIL = "https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png"


def photo_profil_par_defaut():
    return DEFAULT_PROFILE_PHOTO


ROLE_CHOICES = (
    ("admin", "admin"),
    ("gerant", "gerant"),
    ("vendeur", "vendeur"),
    ("client", "client"),
)

verification_numero = RegexValidator(
    regex=r"^(?:\+225|00225)?(01|05|07|25|27)\d{8}$",
    message="Veuillez entrer un numéro ivoirien valide (ex: +2250102030405 ou 0102030405).",
)


class UtilisateurManager(BaseUserManager):
    def create_user(self, email_utilisateur=None, password=None, **extra_fields):
        if not email_utilisateur:
            raise ValueError("Email Obligatoire")

        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        email = self.normalize_email(email_utilisateur)
        user = self.model(email_utilisateur=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email_utilisateur, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")

        if not password:
            raise ValueError("l'administrateur doit avoir un mot de passe")
        return self.create_user(
            email_utilisateur=email_utilisateur, password=password, **extra_fields
        )


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    identifiant_utilisateur = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    email_utilisateur = models.EmailField(
        max_length=50, unique=True, verbose_name="Email", blank=True, null=True
    )
    nom_utilisateur = models.CharField(
        max_length=150, blank=True, null=True, verbose_name="Nom utilisateur"
    )

    photo_profil_utilisateur = CloudinaryField(
        "photo_profil",
        folder="mes_projets/AfriCart/utilisateurs/photos_profil/",
        blank=True,
        null=True,
        max_length=500,
    )
    thumbnail = models.URLField(blank=True, null=True, editable=False)

    numero_telephone_utilisateur = models.CharField(
        max_length=15,
        validators=[verification_numero],
        null=True,
        blank=True,
        verbose_name="Numéro de téléphone",
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default="vendeur",
        verbose_name="Rôle utilisateur",
    )
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UtilisateurManager()

    USERNAME_FIELD = "email_utilisateur"

    class Meta:
        indexes = [
            models.Index(fields=["numero_telephone_utilisateur"]),
            models.Index(fields=["role", "date_creation"]),
            models.Index(fields=["is_active", "date_creation"]),
            models.Index(fields=["date_creation"]),
        ]

    def __str__(self):
        return (
            self.nom_utilisateur
            if self.nom_utilisateur
            else f"Utilisateur {self.identifiant_utilisateur}"
        )

    def make_thumbnail(self):
        """Génère une miniature en utilisant les transformations Cloudinary (plus rapide)."""
        if self.photo_profil_utilisateur and hasattr(
            self.photo_profil_utilisateur, "url"
        ):
            url = self.photo_profil_utilisateur.url
            # Cloudinary permet de créer une miniature juste en modifiant l'URL
            # On insère 'c_fill,h_200,w_200' dans l'URL
            if "upload/" in url:
                self.thumbnail = url.replace("upload/", "upload/c_fill,h_200,w_200/")

    def save(self, *args, **kwargs):
        old_image_url = None
        if self.pk:
            # Récupération sans try/except silencieux
            old_instance = Utilisateur.objects.filter(pk=self.pk).first()
            if (
                old_instance
                and old_instance.photo_profil_utilisateur
                and hasattr(old_instance.photo_profil_utilisateur, "url")
            ):
                old_image_url = old_instance.photo_profil_utilisateur.url

        super().save(*args, **kwargs)

        # Si pas de photo, charger la photo par défaut
        if not self.photo_profil_utilisateur:
            self.photo_profil_utilisateur = DEFAULT_PROFILE_PHOTO
            self.thumbnail = DEFAULT_PROFILE_THUMBNAIL
            super().save(update_fields=["photo_profil_utilisateur", "thumbnail"])
        elif self.photo_profil_utilisateur and hasattr(
            self.photo_profil_utilisateur, "url"
        ):
            current_image_url = self.photo_profil_utilisateur.url
            if not self.thumbnail or old_image_url != current_image_url:
                self.make_thumbnail()
                super().save(update_fields=["thumbnail"])
