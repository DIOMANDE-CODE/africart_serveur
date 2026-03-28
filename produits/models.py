import uuid
from io import BytesIO
import requests
from PIL import Image
import cloudinary.uploader

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

from cloudinary.models import CloudinaryField
from utilisateurs.models import Utilisateur


def image_produit_par_defaut():
    return "https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png"


class Categorie(models.Model):
    identifiant_categorie = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    nom_categorie = models.CharField(max_length=50, unique=True)
    description_categorie = models.TextField(null=True, blank=True)

    pourcentage_promo_categorie = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        blank=True,
        null=True,
    )

    prix_promo_categorie = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        blank=True,
        null=True,
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["nom_categorie", "date_creation"]),
            models.Index(fields=["date_creation"]),
        ]

    def __str__(self):
        return self.nom_categorie


class Produit(models.Model):
    identifiant_produit = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    nom_produit = models.CharField(max_length=50, unique=True)

    image_produit = CloudinaryField(
        "image_produit",
        folder="mes_projets/AfriCart/produits/images/",
        default=image_produit_par_defaut,
        blank=True,
        null=True,
        max_length=500,
    )
    thumbnail = models.URLField(blank=True, null=True, editable=False)

    image_produit_2 = CloudinaryField(
        "image_produit_2",
        folder="mes_projets/AfriCart/produits/images/",
        default=image_produit_par_defaut,
        blank=True,
        null=True,
        max_length=500,
    )
    thumbnail_2 = models.URLField(blank=True, null=True, editable=False)

    image_produit_3 = CloudinaryField(
        "image_produit_3",
        folder="mes_projets/AfriCart/produits/images/",
        default=image_produit_par_defaut,
        blank=True,
        null=True,
        max_length=500,
    )
    thumbnail_3 = models.URLField(blank=True, null=True, editable=False)

    categorie_produit = models.ForeignKey(
        Categorie, on_delete=models.CASCADE, related_name="produits"
    )

    description_produit = models.TextField(blank=True, null=True)
    caracteristiques_produit = models.TextField(blank=True, null=True)

    prix_unitaire_produit = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    prix_promo_produit = models.DecimalField(
        max_digits=10, decimal_places=2, blank=True, null=True
    )

    quantite_produit_disponible = models.IntegerField(validators=[MinValueValidator(0)])
    seuil_alerte_produit = models.IntegerField(validators=[MinValueValidator(0)])

    pourcentage_promo = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
        blank=True,
        null=True,
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["categorie_produit"]),
            models.Index(fields=["nom_produit"]),
            models.Index(fields=["quantite_produit_disponible"]),
            models.Index(fields=["date_creation"]),
        ]

    def __str__(self):
        return self.nom_produit

    # ---------- Compression image ----------
    def compress_and_upload(self, image_url, public_id):
        try:
            if isinstance(image_url, str) and image_url.startswith("http"):
                response = requests.get(image_url)
                img = Image.open(BytesIO(response.content))
            else:
                img = Image.open(image_url)

            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            img.thumbnail((1000, 1000))
            thumb_io = BytesIO()
            img.save(thumb_io, format="JPEG", quality=70)

            result = cloudinary.uploader.upload(
                thumb_io.getvalue(),
                folder="mes_projets/AfriCart/produits/compressed/",
                public_id=public_id,
            )
            return result.get("secure_url")
        except Exception:
            return None

    # ---------- Save principal ----------
    def save(self, *args, **kwargs):
        old_instance = None
        if self.pk:
            # Utiliser filter().first() pour éviter un try/except silencieux
            old_instance = Produit.objects.filter(pk=self.pk).first()

        # calcul promo SAFE (sans save interne)
        if self.pourcentage_promo and self.pourcentage_promo > 0:
            self.prix_promo_produit = self.prix_unitaire_produit * (
                1 - self.pourcentage_promo / 100
            )
        else:
            self.prix_promo_produit = None

        super().save(*args, **kwargs)

        # ---------- thumbnails ----------
        for field, thumb, prefix in [
            ("image_produit", "thumbnail", "thumb_"),
            ("image_produit_2", "thumbnail_2", "thumb2_"),
            ("image_produit_3", "thumbnail_3", "thumb3_"),
        ]:
            image = getattr(self, field)
            image_url = image if isinstance(image, str) else getattr(image, "url", None)

            old_url = (
                getattr(old_instance, field).url
                if old_instance and getattr(old_instance, field)
                else None
            )

            if image_url and (not getattr(self, thumb) or image_url != old_url):
                setattr(
                    self,
                    thumb,
                    self.compress_and_upload(
                        image_url, f"{prefix}{self.identifiant_produit}"
                    ),
                )

        super().save(
            update_fields=[
                "thumbnail",
                "thumbnail_2",
                "thumbnail_3",
                "prix_promo_produit",
            ]
        )

        # ---------- Alert logic: create or update AlertProduit ----------
        try:
            # If stock is at or below threshold, ensure an active alert exists
            if self.quantite_produit_disponible <= self.seuil_alerte_produit:
                alert = AlertProduit.objects.filter(produit=self).first()
                if alert:
                    if not alert.statut_alerte:
                        alert.statut_alerte = True
                        if not alert.message_alerte:
                            alert.message_alerte = f"Stock faible: {self.quantite_produit_disponible} <= {self.seuil_alerte_produit}"
                        alert.save(update_fields=["statut_alerte", "message_alerte"])
                else:
                    AlertProduit.objects.create(
                        produit=self,
                        statut_alerte=True,
                        message_alerte=f"Stock faible: {self.quantite_produit_disponible} <= {self.seuil_alerte_produit}",
                    )
            else:
                # If stock has been replenished above threshold, deactivate any active alerts
                AlertProduit.objects.filter(produit=self, statut_alerte=True).update(
                    statut_alerte=False
                )
        except Exception:
            # Do not break saving on alert errors; log could be added later
            pass


class AlertProduit(models.Model):
    identifiant_alerte = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    message_alerte = models.CharField(max_length=50, null=True, blank=True)
    statut_alerte = models.BooleanField(default=True)
    date_alerte = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["produit"]),
            models.Index(fields=["statut_alerte", "date_alerte"]),
        ]

    def __str__(self):
        return f"Alerte pour {self.produit.nom_produit}"


class NotationProduit(models.Model):
    identifiant_notation = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.CASCADE, related_name="notations_produit"
    )
    utilisateur = models.ForeignKey(
        Utilisateur, on_delete=models.CASCADE, related_name="notations_utilisateur"
    )

    note_produit = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    date_notation = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("produit", "utilisateur")
        indexes = [
            models.Index(fields=["produit", "date_notation"]),
            models.Index(fields=["utilisateur", "date_notation"]),
        ]

    def __str__(self):
        return f"Notation {self.note_produit} pour {self.produit.nom_produit}"
