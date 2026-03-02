from rest_framework import serializers
from django.db import transaction
from .models import Commande, DetailCommande, ZoneLivraison
from clients.models import Client
from produits.models import Produit
from utilisateurs.serializers import UtilisateurSerializer
from utilisateurs.models import Utilisateur
from decimal import Decimal
from produits.serializers import ProduitSerializer
from utils import calculer_distance_gps 

class ZoneLivraisonSerializer(serializers.ModelSerializer):
    class Meta:
        model = ZoneLivraison
        fields = '__all__'

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
    lieu_livraison = serializers.CharField()
    # Nouveaux champs pour la précision GPS
    latitude_client = serializers.FloatField(required=False, allow_null=True)
    longitude_client = serializers.FloatField(required=False, allow_null=True)
    identifiant_zone = serializers.UUIDField(required=False, allow_null=True)

    def create(self, validated_data):
        client_data = validated_data.pop('client')
        items_data = validated_data.pop('items')
        total_ht = validated_data.pop('total_ht')
        lieu_livraison = validated_data.pop('lieu_livraison')
        
        # Données GPS envoyées par React
        lat_c = validated_data.get('latitude_client')
        long_c = validated_data.get('longitude_client')
        identifiant_zone = validated_data.get('identifiant_zone')

        with transaction.atomic():
            # 1. Client
            client, _ = Client.objects.get_or_create(
                nom_client=client_data['nom_client'],
                numero_telephone_client=client_data['numero_telephone_client']
            )

            # 2. Rotation Vendeur
            vendeurs = Utilisateur.objects.filter(role="vendeur").order_by("id")
            last_commande = Commande.objects.order_by("-id").first()
            if last_commande and last_commande.utilisateur in vendeurs:
                v_list = list(vendeurs)
                next_index = (v_list.index(last_commande.utilisateur) + 1) % len(v_list)
                utilisateur = v_list[next_index]
            else:
                utilisateur = vendeurs.first()

            # 3. DÉTECTION INTELLIGENTE DE LA ZONE
            zone_obj = None
            frais_livraison = Decimal('0')

            # Priorité 1 : ID Zone direct (si l'utilisateur a choisi un point précis sur la carte)
            if identifiant_zone:
                zone_obj = ZoneLivraison.objects.filter(identifiant_zone=identifiant_zone).first()
            
            # Priorité 2 : Calcul GPS (si on a les coordonnées mais pas d'ID zone)
            if not zone_obj and lat_c and long_c:
                # Tri par rayon croissant pour trouver la zone la plus petite d'abord (Yakro)
                zones_candidates = ZoneLivraison.objects.all().order_by('rayon_metres')
                for z in zones_candidates:
                    dist = calculer_distance_gps(lat_c, long_c, z.latitude, z.longitude)
                    if dist <= z.rayon_metres:
                        zone_obj = z
                        break 

            # Priorité 3 : Recherche textuelle (Fallback)
            if not zone_obj:
                zone_obj = ZoneLivraison.objects.filter(nom_zone__iexact=lieu_livraison).first()

            # Application du tarif
            if zone_obj:
                frais_livraison = zone_obj.frais_livraison
            else:
                frais_livraison = Decimal('1000') if 'yamoussoukro' in lieu_livraison.lower() else Decimal('3000')

            # 4. Création Commande
            commande = Commande.objects.create(
                client=client,
                utilisateur=utilisateur,
                total_ht=total_ht, 
                total_ttc=total_ht + frais_livraison, 
                lieu_livraison=lieu_livraison,
                zone=zone_obj,
                frais_livraison_appliques=frais_livraison,
                latitude_client=lat_c,
                longitude_client=long_c
            )

            # 5. Articles & Stocks
            for item in items_data:
                produit = Produit.objects.get(identifiant_produit=item['identifiant_produit'])
                produit.quantite_produit_disponible -= item['quantite_produit']
                produit.save()

                DetailCommande.objects.create(
                    commande=commande,
                    produit=produit,
                    quantite=item['quantite_produit'],
                    prix_unitaire=Decimal(item['prix_unitaire_produit']),
                    sous_total=Decimal(item['prix_unitaire_produit']) * item['quantite_produit']
                )

        return commande

# ... (Garder tes classes VoirDetailCommandeSerializer et VoirCommandeSerializer inchangées)
class VoirDetailCommandeSerializer(serializers.ModelSerializer):
    produit = ProduitSerializer(read_only=True)
    class Meta:
        model = DetailCommande
        fields = ['id', 'produit', 'quantite', 'prix_unitaire', 'sous_total']

class VoirCommandeSerializer(serializers.ModelSerializer):
    client = ClientSerializer()
    details_commandes = VoirDetailCommandeSerializer(many=True, read_only=True)
    utilisateur = UtilisateurSerializer() 
    nom_zone = serializers.CharField(source='zone.nom_zone', read_only=True)

    class Meta:
        model = Commande
        fields = [
            'id', 'identifiant_commande', 'client', 'utilisateur', 
            'code_livraison', 'date_commande', 'etat_commande', 
            'total_ht', 'tva', 'frais_livraison_appliques', 'total_ttc', 
            'details_commandes', 'lieu_livraison', 'nom_zone', 'is_active'
        ]

class CommandeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commande
        fields = ['etat_commande']

    def validate_etat_commande(self, value):
        commande = self.instance
        if commande.etat_commande == 'livre':
            raise serializers.ValidationError("Une commande livrée ne peut plus être modifiée.")
        if commande.etat_commande == 'annule' and value != 'annule':
            raise serializers.ValidationError("Une commande annulée ne peut pas changer d’état.")
        if value == 'annule' and commande.etat_commande != 'annule':
            self._restore_stock(commande)
        return value

    def _restore_stock(self, commande):
        for detail in commande.details_commandes.all():
            detail.produit.quantite_produit_disponible += detail.quantite
            detail.produit.save()