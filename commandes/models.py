from django.db import models
from clients.models import Client
from utilisateurs.models import Utilisateur
from django.utils import timezone
from decimal import Decimal
import uuid
from produits.models import Produit

# Create your models here.

ETAT_COMMANDE = (
    ('en_cours','en_cours'),
    ('valide','valide'),
    ('livre','livre'),
    ('annule','annule')
)

# Modèle Commande
class Commande(models.Model):
    identifiant_commande = models.CharField(max_length=50, editable=False, unique=True)
    etat_commande = models.CharField(max_length=10, choices=ETAT_COMMANDE,default="en_cours")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=True, blank=True, related_name='commandes_clients')
    utilisateur=models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True, related_name="commandes_utilisateurs")
    date_commande = models.DateTimeField(default=timezone.now)
    code_livraison = models.CharField(max_length=20, editable=False, default="MARCHEPRO-")
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="commande active")

    def save(self, *args, **kwargs):
        if not self.identifiant_commande:
            today_str = timezone.now().strftime("%Y%m%d")
            count_today = Commande.objects.filter(date_commande__date=timezone.now().date()).count() + 1
            self.identifiant_commande = f"AfriCart-C-{today_str}-{count_today:03d}"
        if self.code_livraison :
            code = str(uuid.uuid4())[:6].upper()
            self.code_livraison = f"M-{code}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Commande {self.identifiant_commande} - Code de livraison {self.code_livraison}"
    
    def calculer_totaux(self):
        """
        Calcule le total HT, la TVA et le total TTC à partir des détails de la commande.
        """
        details = self.details_commandes.all()
        total_ht = sum(detail.sous_total for detail in details)
        tva = total_ht * Decimal('0.0') 
        total_ttc = total_ht + tva

        self.total_ht = total_ht
        self.tva = tva
        self.total_ttc = total_ttc
        self.save()


# Modèle Detail de la commande
class DetailCommande(models.Model):
    identifiant_detail_commande = models.UUIDField(default=uuid.uuid4, editable=False,unique=True)
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='details_commandes')
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT,related_name='details_commandes')
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    sous_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.produit.nom_produit} - Qte: {self.quantite}"
    

class AttributionCommande(models.Model):
    dernier_index = models.IntegerField(default=0)