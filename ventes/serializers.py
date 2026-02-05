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
        items_data = validated_data.pop('items')


        # Créer la vente
        utilisateur = self.context['request'].user
        vente = Vente.objects.create(
            utilisateur=utilisateur
        )

        # Créer les détails de vente
        for item in items_data:
            produit, _ = Produit.objects.get_or_create(
                identifiant_produit=item['identifiant_produit'],
                defaults={
                    'nom_produit': item['nom_produit'],
                    'prix_unitaire': item['prix_unitaire_produit'],
                    'quantite_disponible': item['quantite_produit_disponible']
                }
            )

            # Décrémenter le stock
            produit.quantite_produit_disponible -= item['quantite_produit_disponible']
            produit.save()

            DetailVente.objects.create(
                vente=vente,
                produit=produit,
                quantite=item['quantite_produit_disponible'],
                prix_unitaire=item['prix_unitaire_produit'],
                sous_total=item['prix_unitaire_produit'] * item['quantite_produit_disponible']
            )

        # Calculer les totaux de la vente
        vente.calculer_totaux()
        return vente


# Serializer pour les détails de vente
class VoirDetailVenteSerializer(serializers.ModelSerializer):
    produit = serializers.StringRelatedField()  # Affiche le nom du produit

    class Meta:
        model = DetailVente
        fields = ['id', 'produit', 'quantite', 'prix_unitaire', 'sous_total']


# Serializer pour voir les ventes
class VoirVenteSerializer(serializers.ModelSerializer):
    details_ventes = VoirDetailVenteSerializer(many=True, read_only=True)
    utilisateur = UtilisateurSerializer()  
    # Affiche le nom de l'utilisateur

    class Meta:
        model = Vente
        fields = [
            'id',
            'identifiant_vente',
            'utilisateur',
            'date_vente',
            'total_ht',
            'tva',
            'total_ttc',
            'details_ventes',
        ]
