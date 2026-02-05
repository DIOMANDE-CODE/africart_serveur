from django.db import models
from utilisateurs.models import Utilisateur
from clients.models import Client
from produits.models import Produit
from django.utils import timezone
import uuid
from decimal import Decimal
# Create your models here.

# Modèle de Vente
class Vente(models.Model):
    identifiant_vente = models.CharField(max_length=50, editable=False, unique=True)
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True, blank=True, related_name='ventes_utilisateurs')
    date_vente = models.DateTimeField(default=timezone.now)
    total_ht = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_ttc = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.identifiant_vente:
            # Exemple: MarchePro-V-20251016-001
            today_str = timezone.now().strftime("%Y%m%d")
            count_today = Vente.objects.filter(date_vente__date=timezone.now().date()).count() + 1
            self.identifiant_vente = f"AfriCart-V-{today_str}-{count_today:03d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Vente {self.identifiant_vente}"
    
    def calculer_totaux(self):
        """
        Calcule le total HT, la TVA et le total TTC à partir des détails de la vente.
        """
        details = self.details_ventes.all()
        total_ht = sum(detail.sous_total for detail in details)
        tva = total_ht * Decimal('0.00') 
        total_ttc = total_ht + tva

        self.total_ht = total_ht
        self.tva = tva
        self.total_ttc = total_ttc
        self.save()
    


# Modele de DetailVente
class DetailVente(models.Model):
    identifiant_detail_vente = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name='details_ventes')
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, related_name='details_ventes')
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    sous_total = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.produit.nom_produit} - Qte: {self.quantite}"
