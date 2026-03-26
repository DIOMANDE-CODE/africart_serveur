from rest_framework import serializers
from .models import Vente, DetailVente
from produits.models import Produit
from utilisateurs.serializers import UtilisateurSerializer


class ItemSerializer(serializers.Serializer):
    identifiant_produit = serializers.CharField()
    nom_produit = serializers.CharField()
    prix_unitaire_produit = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantite_produit_disponible = serializers.IntegerField()


class VenteCreateSerializer(serializers.Serializer):
    items = ItemSerializer(many=True)

    def create(self, validated_data):
        items_data = validated_data.pop("items")
        # Créer la vente
        utilisateur = self.context["request"].user
        vente = Vente.objects.create(utilisateur=utilisateur)

        # Précharger les produits pour éviter un N+1 et empêcher les créations implicites
        identifiants = [item["identifiant_produit"] for item in items_data]
        produits_map = {
            str(p.identifiant_produit): p
            for p in Produit.objects.filter(identifiant_produit__in=identifiants)
        }

        manquants = [pid for pid in identifiants if str(pid) not in produits_map]
        if manquants:
            raise serializers.ValidationError(
                {
                    "items": [
                        f"Produit introuvable pour l'identifiant {m}."
                        for m in manquants
                    ]
                }
            )

        # Créer les détails de vente et mettre à jour le stock
        for item in items_data:
            produit = produits_map[str(item["identifiant_produit"])]

            produit.quantite_produit_disponible -= item["quantite_produit_disponible"]
            produit.save()

            DetailVente.objects.create(
                vente=vente,
                produit=produit,
                quantite=item["quantite_produit_disponible"],
                prix_unitaire=item["prix_unitaire_produit"],
                sous_total=item["prix_unitaire_produit"]
                * item["quantite_produit_disponible"],
            )

        # Calculer les totaux de la vente
        vente.calculer_totaux()
        return vente


# Serializer pour les détails de vente
class VoirDetailVenteSerializer(serializers.ModelSerializer):
    produit = serializers.StringRelatedField()  # Affiche le nom du produit

    class Meta:
        model = DetailVente
        fields = ["id", "produit", "quantite", "prix_unitaire", "sous_total"]


# Serializer pour voir les ventes
class VoirVenteSerializer(serializers.ModelSerializer):
    details_ventes = VoirDetailVenteSerializer(many=True, read_only=True)
    utilisateur = UtilisateurSerializer()
    # Affiche le nom de l'utilisateur

    class Meta:
        model = Vente
        fields = [
            "id",
            "identifiant_vente",
            "utilisateur",
            "date_vente",
            "total_ht",
            "tva",
            "total_ttc",
            "details_ventes",
        ]
