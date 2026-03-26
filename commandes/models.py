from django.db import models
from clients.models import Client
from utilisateurs.models import Utilisateur
from django.utils import timezone
from decimal import Decimal
import uuid
from produits.models import Produit
from utils import calculer_distance_gps

# Choix pour l'état de la commande
ETAT_COMMANDE = (
    ("en_cours", "en_cours"),
    ("valide", "valide"),
    ("livre", "livre"),
    ("annule", "annule"),
)


# 1. Zone de Livraison (Configuration des tarifs par zone géographique)
class ZoneLivraison(models.Model):
    identifiant_zone = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    # Ex: "Yamoussoukro" ou "Intérieur"
    nom_zone = models.CharField(max_length=50, unique=True)
    frais_livraison = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    latitude = models.FloatField()
    longitude = models.FloatField()
    rayon_metres = models.PositiveIntegerField()
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.nom_zone} ({self.frais_livraison} FCFA)"


# 2. Modèle Commande (Cœur de la transaction)


class Commande(models.Model):
    identifiant_commande = models.CharField(max_length=50, editable=False, unique=True)
    etat_commande = models.CharField(
        max_length=10, choices=ETAT_COMMANDE, default="en_cours"
    )
    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="commandes_clients",
    )
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="commandes_utilisateurs",
    )

    # Géolocalisation et Zone
    zone = models.ForeignKey(
        ZoneLivraison,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="commandes",
    )
    lieu_livraison = models.CharField(max_length=250, default="yamoussoukro")
    frais_livraison_appliques = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )

    # --- AJOUT DES CHAMPS GPS POUR LA COMPARAISON ---
    latitude_client = models.FloatField(null=True, blank=True)
    longitude_client = models.FloatField(null=True, blank=True)

    # Dates et Sécurité
    date_commande = models.DateTimeField(default=timezone.now)
    code_livraison = models.CharField(
        max_length=20, editable=False, default="MARCHEPRO-"
    )

    # Montants financiers
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="commande active")

    class Meta:
        indexes = [
            models.Index(fields=["utilisateur", "date_commande"]),
            models.Index(fields=["client", "date_commande"]),
            models.Index(fields=["etat_commande", "date_commande"]),
            models.Index(fields=["zone"]),
            models.Index(fields=["lieu_livraison"]),
        ]

    def save(self, *args, **kwargs):
        # Génération de l'identifiant unique AfriCart
        if not self.identifiant_commande:
            today_str = timezone.now().strftime("%Y%m%d")
            count_today = (
                Commande.objects.filter(
                    date_commande__date=timezone.now().date()
                ).count()
                + 1
            )
            self.identifiant_commande = f"AfriCart-C-{today_str}-{count_today:03d}"

        # Génération du code de livraison sécurisé (M-XXXXXX)
        if self.code_livraison == "MARCHEPRO-":
            code = str(uuid.uuid4())[:6].upper()
            self.code_livraison = f"M-{code}"

        super().save(*args, **kwargs)

    def determiner_zone_automatique(self):
        """Trouve la zone la plus petite couvrant la position du client"""
        if self.latitude_client and self.longitude_client:
            # (pour privilégier la précision : ville avant pays)
            zones = ZoneLivraison.objects.all().order_by("rayon_metres")

            for z in zones:
                distance = calculer_distance_gps(
                    self.latitude_client, self.longitude_client, z.latitude, z.longitude
                )
                if distance <= z.rayon_metres:
                    self.zone = z
                    return z
        return None

    def calculer_totaux(self):
        """Calcule les totaux HT, TVA et TTC incluant les frais de zone"""
        details = self.details_commandes.all()
        self.total_ht = sum((detail.sous_total for detail in details), Decimal("0"))

        # TVA à 0% par défaut
        self.tva = self.total_ht * Decimal("0")

        # Application des frais de livraison (Priorité à la zone liée, sinon fallback manuel)
        if self.zone:
            self.frais_livraison_appliques = self.zone.frais_livraison
        else:
            # Fallback basé sur le texte (Yakro=300, Reste=3000)
            if self.lieu_livraison.lower() == "yamoussoukro":
                self.frais_livraison_appliques = Decimal("300")
            else:
                self.frais_livraison_appliques = Decimal("3000")

        self.total_ttc = self.total_ht + self.tva + self.frais_livraison_appliques

        # Sauvegarde uniquement des champs calculés pour éviter la récursion
        self.save(
            update_fields=["total_ht", "tva", "total_ttc", "frais_livraison_appliques"]
        )

    def __str__(self):
        return f"Commande {self.identifiant_commande} - {self.etat_commande}"


# 3. Détails de la commande (Articles individuels)


class DetailCommande(models.Model):
    identifiant_detail_commande = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True
    )
    commande = models.ForeignKey(
        Commande, on_delete=models.CASCADE, related_name="details_commandes"
    )
    produit = models.ForeignKey(
        Produit, on_delete=models.PROTECT, related_name="details_commandes"
    )
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    sous_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["commande", "produit"]),
            models.Index(fields=["produit", "date_creation"]),
            models.Index(fields=["date_creation"]),
        ]

    def save(self, *args, **kwargs):
        # 1. Calcul du sous-total de la ligne
        self.sous_total = Decimal(str(self.quantite)) * self.prix_unitaire

        # 2. Mise à jour du stock produit (uniquement à la création du détail)
        if not self.pk:
            produit = self.produit
            produit.quantite_produit_disponible -= self.quantite
            produit.save()

            # Vérification du seuil d'alerte
            if produit.quantite_produit_disponible < produit.seuil_alerte_produit:
                from produits.models import AlertProduit

                AlertProduit.objects.get_or_create(
                    produit=produit,
                    statut_alerte=True,
                    defaults={
                        "message_alerte": f"Stock critique pour {produit.nom_produit}"
                    },
                )

        super().save(*args, **kwargs)

        # 3. Mise à jour automatique des totaux de la commande parente
        self.commande.calculer_totaux()

    def __str__(self):
        return f"{self.produit.nom_produit} (x{self.quantite})"


# 4. Table de gestion de la rotation des vendeurs


class AttributionCommande(models.Model):
    dernier_index = models.IntegerField(default=0)
    date_mise_a_jour = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Index de rotation actuel : {self.dernier_index}"
