from rest_framework import serializers
from .models import Commande, DetailCommande
from clients.models import Client
from produits.models import Produit
from utilisateurs.serializers import UtilisateurSerializer
from utilisateurs.models import Utilisateur
from decimal import Decimal
from produits.serializers import ProduitSerializer


class ItemSerializer(serializers.Serializer):
    identifiant_produit = serializers.CharField()
    nom_produit = serializers.CharField()
    prix_unitaire_produit = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantite_produit_disponible = serializers.IntegerField()
    quantite_produit = serializers.IntegerField()


class ClientSerializer(serializers.Serializer):
    nom_client = serializers.CharField()
    numero_telephone_client = serializers.CharField()

class CommandeCreateSerializer(serializers.Serializer):
    client = ClientSerializer()
    items = ItemSerializer(many=True)
    total_ht = serializers.DecimalField(max_digits=10, decimal_places=2) 
    total_ttc = serializers.DecimalField(max_digits=10, decimal_places=2) 
    lieu_livraison = serializers.CharField()

    def create(self, validated_data):
        client_data = validated_data.pop('client')
        items_data = validated_data.pop('items')
        total_ht = validated_data.pop('total_ht') 
        total_ttc = validated_data.pop('total_ttc') 
        lieu_livraison = validated_data.pop('lieu_livraison')
     

        # Créer ou récupérer le client
        client, _ = Client.objects.get_or_create(
            nom_client=client_data['nom_client'],
            numero_telephone_client=client_data['numero_telephone_client']
        )

        # Rotation des vendeurs
        vendeurs = Utilisateur.objects.filter(role="vendeur").order_by("id")
        last_commande = Commande.objects.order_by("-identifiant_commande").first()
        if last_commande and last_commande.utilisateur in vendeurs:
            last_index = list(vendeurs).index(last_commande.utilisateur)
            next_index = (last_index + 1) % vendeurs.count()
            utilisateur = vendeurs[next_index]
        else:
            utilisateur = vendeurs.first()


      # Frais de livraison 
        if lieu_livraison.lower() != 'yamoussoukro' :
            frais_livraison = Decimal('2000')  
        else :
            frais_livraison = Decimal('0') 
        # Recalculer le total TTC 
        total_ttc = total_ht + frais_livraison

        # Créer la commande
        commande = Commande.objects.create(
            client=client,
            utilisateur=utilisateur,
            total_ht=total_ht, 
            total_ttc=total_ttc, 
            lieu_livraison=lieu_livraison
        )

        # Créer les détails de commande
        for item in items_data:
            produit, _ = Produit.objects.get_or_create(
                identifiant_produit=item['identifiant_produit'],
                defaults={
                    'nom_produit': item['nom_produit'],
                    'prix_unitaire': Decimal(item['prix_unitaire_produit']),
                    'quantite_disponible': item['quantite_produit_disponible'],
                    'seuil_alerte': item.get('seuil_alerte_produit', 0),
                    'image_produit': item.get('image_produit'),
                    'thumbnail': item.get('thumbnail')
                }
            )

            # Décrémenter le stock avec la quantité commandée
            quantite_commandee = item['quantite_produit']
            produit.quantite_produit_disponible -= quantite_commandee
            produit.save()

            DetailCommande.objects.create(
                commande=commande,
                produit=produit,
                quantite=quantite_commandee,
                prix_unitaire=Decimal(item['prix_unitaire_produit']),
                sous_total=Decimal(item['prix_unitaire_produit']) * quantite_commandee
            )

        return commande

# Serializer pour les details de commande
class VoirDetailCommandeSerializer(serializers.ModelSerializer):
    produit = ProduitSerializer(read_only=True)

    class Meta:
        model = DetailCommande
        fields = ['id', 'produit', 'quantite', 'prix_unitaire', 'sous_total']

# Serializer pour voir les commandes
class VoirCommandeSerializer(serializers.ModelSerializer):
    client = ClientSerializer()  # Client imbriqué
    details_commandes = VoirDetailCommandeSerializer(many=True, read_only=True)
    utilisateur = UtilisateurSerializer() 

    class Meta:
        model = Commande
        fields = [
            'id',
            'identifiant_commande',
            'client',
            'utilisateur',
            'code_livraison',
            'date_commande',
            'etat_commande',
            'total_ht',
            'tva',
            'total_ttc',
            'details_commandes',
            'lieu_livraison',
            'is_active',
        ]
 

#  Serializer pour changer l'etat de la commande
class CommandeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = ['etat_commande']

    def validate_etat_commande(self,value):
        commande = self.instance

        if commande.etat_commande == 'livre':
            raise serializers.ValidationError(
                "Une commande livrée ne peut plus être modifiée."
            )
        if commande.etat_commande == 'annule' and value != 'annule':
            raise serializers.ValidationError(
                "Une commande annulée ne peut pas changer d’état."
            )
        if  value == 'annule' and commande.etat_commande != 'annule':
            self._restore_stock(commande)

        
        return value
    

    
    def _restore_stock(self, commande):
        """
        Restaure le stock des produits commandés à leur quantité initiale
        """
        details = commande.details_commandes.all()
        for detail in details:
            # Augmenter le stock du produit de la quantité commandée
            detail.produit.quantite_produit_disponible += detail.quantite
            detail.produit.save()