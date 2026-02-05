from django.db import models
import uuid
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from PIL import Image
import os
from io import BytesIO
from django.core.files.base import ContentFile
from cloudinary.models import CloudinaryField
import requests
import cloudinary.uploader

def image_produit_par_defaut():
    return 'https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png'

class Categorie(models.Model):
    identifiant_categorie = models.UUIDField(default=uuid.uuid4, editable=False, unique=True )
    nom_categorie = models.CharField(max_length=50, verbose_name="nom catégorie", unique=True)
    description_categorie = models.TextField(null=True, blank=True, verbose_name="description produit")

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nom_categorie


class Produit(models.Model):
    identifiant_produit = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom_produit = models.CharField(max_length=50, unique=True)

    image_produit = CloudinaryField(
        'image_produit',
        folder='mes_projets/AfriCart/produits/images/',
        default=image_produit_par_defaut,
        blank=True,
        null=True,
    )

    thumbnail = models.URLField(blank=True, null=True, editable=False)

    description_produit = models.TextField(blank=True, null=True)
    prix_unitaire_produit = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    quantite_produit_disponible = models.IntegerField(validators=[MinValueValidator(0)])
    seuil_alerte_produit = models.IntegerField(validators=[MinValueValidator(0)])
    categorie_produit = models.ForeignKey(Categorie, on_delete=models.CASCADE, related_name="categories")

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def make_thumbnail(self):
        if self.image_produit:
            response = requests.get(self.image_produit.url)
            if response.status_code == 200 and "image" in response.headers.get("Content-Type", ""):
                img = Image.open(BytesIO(response.content))
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                img.thumbnail((200, 200))
                thumb_io = BytesIO()
                img.save(thumb_io, format="JPEG", quality=80)

                result = cloudinary.uploader.upload(
                    thumb_io.getvalue(),
                    folder="mes_projets/AfriCart/produits/thumbnails/",
                    public_id=f"thumb_{self.identifiant_produit}"
                )

                # Stocker l’URL publique dans le champ thumbnail
                self.thumbnail = result["secure_url"]

    def save(self, *args, **kwargs):
        old_image_url = None
        if self.pk:
            try:
                old_instance = Produit.objects.get(pk=self.pk)
                if old_instance.image_produit:
                    old_image_url = old_instance.image_produit.url
            except Produit.DoesNotExist:
                pass

        self.clean()
        super().save(*args, **kwargs)

        if self.image_produit:
            current_image_url = self.image_produit.url
            if not self.thumbnail or old_image_url != current_image_url:
                self.make_thumbnail()
                super().save(update_fields=["thumbnail"])

        # Vérification automatique du stock faible
        if self.quantite_produit_disponible <= self.seuil_alerte_produit:
            alerte_existante = AlertProduit.objects.filter(produit=self, statut_alerte=True).first()
            if not alerte_existante:
                AlertProduit.objects.create(
                    produit=self,
                    message_alerte=f"Le stock du produit '{self.nom_produit}' est faible ({self.quantite_produit_disponible} restants)."
                )
        else:
            AlertProduit.objects.filter(produit=self, statut_alerte=True).update(statut_alerte=False)

    def __str__(self):
        return self.nom_produit


class AlertProduit(models.Model):
    identifiant_alerte = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, verbose_name="alert_produit")
    message_alerte = models.CharField(max_length=50, null=True, blank=True)
    statut_alerte = models.BooleanField(default=True)
    date_alerte = models.DateTimeField(auto_now_add=True)
