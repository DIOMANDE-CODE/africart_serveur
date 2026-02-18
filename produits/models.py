from django.db import models
import uuid
from django.core.validators import MinValueValidator
from PIL import Image
import requests
from io import BytesIO
from cloudinary.models import CloudinaryField
import cloudinary.uploader

def image_produit_par_defaut():
    return 'https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png'


class Categorie(models.Model):
    identifiant_categorie = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom_categorie = models.CharField(max_length=50, verbose_name="nom catégorie", unique=True)
    description_categorie = models.TextField(null=True, blank=True, verbose_name="description produit")

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom_categorie


class Produit(models.Model):
    identifiant_produit = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom_produit = models.CharField(max_length=50, unique=True)

    # Images principales et secondaires
    image_produit = CloudinaryField(
        'image_produit',
        folder='mes_projets/AfriCart/produits/images/',
        default=image_produit_par_defaut,
        blank=True,
        null=True,
    )
    thumbnail = models.URLField(blank=True, null=True, editable=False)

    image_produit_2 = CloudinaryField(
        'image_produit_2',
        folder='mes_projets/AfriCart/produits/images/',
        default=image_produit_par_defaut,
        blank=True,
        null=True,
    )
    thumbnail_2 = models.URLField(blank=True, null=True, editable=False)

    image_produit_3 = CloudinaryField(
        'image_produit_3',
        folder='mes_projets/AfriCart/produits/images/',
        default=image_produit_par_defaut,
        blank=True,
        null=True,
    )
    thumbnail_3 = models.URLField(blank=True, null=True, editable=False)

    description_produit = models.TextField(blank=True, null=True)
    caracteristiques_produit = models.TextField(
        blank=True,
        null=True,
        verbose_name="caractéristiques du produit (Ex: Écran, Clavier, Souris)"
    )
    prix_unitaire_produit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantite_produit_disponible = models.IntegerField(validators=[MinValueValidator(0)])
    seuil_alerte_produit = models.IntegerField(validators=[MinValueValidator(0)])
    categorie_produit = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name="produits")

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom_produit

    # Fonction générique de compression
    def compress_and_upload(self, image_url, public_id):
        response = requests.get(image_url)
        if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
            img = Image.open(BytesIO(response.content))
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail((800, 800))  # taille max
            thumb_io = BytesIO()
            img.save(thumb_io, format="JPEG", quality=70)

            result = cloudinary.uploader.upload(
                thumb_io.getvalue(),
                folder="mes_projets/AfriCart/produits/compressed/",
                public_id=public_id
            )
            return result["secure_url"]
        return None

    # Méthodes séparées pour chaque thumbnail
    def update_thumbnail(self, old_instance=None):
        if self.image_produit:
            if not self.thumbnail or (old_instance and old_instance.image_produit.url != self.image_produit.url):
                self.thumbnail = self.compress_and_upload(
                    self.image_produit.url,
                    f"thumb_{self.identifiant_produit}"
                )
                super().save(update_fields=["thumbnail"])

    def update_thumbnail_2(self, old_instance=None):
        if self.image_produit_2:
            if not self.thumbnail_2 or (old_instance and old_instance.image_produit_2.url != self.image_produit_2.url):
                self.thumbnail_2 = self.compress_and_upload(
                    self.image_produit_2.url,
                    f"thumb2_{self.identifiant_produit}"
                )
                super().save(update_fields=["thumbnail_2"])

    def update_thumbnail_3(self, old_instance=None):
        if self.image_produit_3:
            if not self.thumbnail_3 or (old_instance and old_instance.image_produit_3.url != self.image_produit_3.url):
                self.thumbnail_3 = self.compress_and_upload(
                    self.image_produit_3.url,
                    f"thumb3_{self.identifiant_produit}"
                )
                super().save(update_fields=["thumbnail_3"])

    def save(self, *args, **kwargs):
        old_instance = None
        if self.pk:
            try:
                old_instance = Produit.objects.get(pk=self.pk)
            except Produit.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Mise à jour séparée des thumbnails
        self.update_thumbnail(old_instance)
        self.update_thumbnail_2(old_instance)
        self.update_thumbnail_3(old_instance)

        # Vérification automatique du stock faible
        if self.quantite_produit_disponible <= self.seuil_alerte_produit:
            alerte_existante = AlertProduit.objects.filter(produit=self, statut_alerte=True).first()
            if not alerte_existante:
                AlertProduit.objects.create(
                    produit=self,
                    message_alerte=f"Le stock du produit '{self.nom_produit}' est faible "
                                   f"({self.quantite_produit_disponible} restants)."
                )
        else:
            AlertProduit.objects.filter(produit=self, statut_alerte=True).update(statut_alerte=False)


class AlertProduit(models.Model):
    identifiant_alerte = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, verbose_name="alert_produit")
    message_alerte = models.CharField(max_length=50, null=True, blank=True)
    statut_alerte = models.BooleanField(default=True)
    date_alerte = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Alerte pour {self.produit.nom_produit}"
