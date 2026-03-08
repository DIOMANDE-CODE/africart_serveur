from django.db import models
import uuid
from produits.models import Produit
from utilisateurs.models import Utilisateur

# Create your models here.

TYPES_DE_RECOMMANDATION = (
    ('best_sellers', 'Meilleures ventes'),
    ('similar_categorie', 'Similaire par catégorie'),
    ('co_achat','Co-achat (complémentaire)'),
    ('personnalise','Personnalisé')
)


class VueProduit(models.Model):
    # Alimente chaque vue d'un produit pour alimenté le moteur de recherche
    identifiant_vue = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="vues_produit")
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name="vues_utilisateur")
    session_key = models.CharField(max_length=100, null=True, blank=True)  # Pour les utilisateurs non connectés
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['produit', 'timestamp']),
            models.Index(fields=['utilisateur', 'timestamp']),
        ]
        ordering = ['-timestamp']  # Les vues les plus récentes en premier

    def __str__(self):
        return f"Vue de {self.produit.nom_produit} par {self.utilisateur.email_utilisateur} à {self.timestamp}"
    


class Recommandation(models.Model):
    # Stocke les recommandations générées pour chaque produit
    identifiant_recommandation = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    produit_source = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="recommandations_source", blank=True, null=True)
    produit_recommande = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name="recommandations_recommande")
    type_recommandation = models.CharField(max_length=20, choices=TYPES_DE_RECOMMANDATION)
    score = models.FloatField(default=0.0)  # Score de pertinence de la recommandation
    date_calcul = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('produit_source', 'produit_recommande', 'type_recommandation')
        indexes = [
            models.Index(fields=['produit_source','type_recommandation','-score']),
            models.Index(fields=['type_recommandation','-score'])
        ]
        ordering = ['-score']

    def __str__(self):
        src = self.produit_source.nom_produit if self.produit_source else 'Global'
        return f"{self.type_recommandation}: {src} → {self.produit_recommande.nom_produit} ({self.score:.2f})"