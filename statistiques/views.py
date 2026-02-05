from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from datetime import date, timedelta
from decimal import Decimal

from ventes.models import Vente
from produits.models import Produit, AlertProduit
from clients.models import Client
from ventes.models import DetailVente
from django.db.models import Sum, Count, Q, F, DecimalField
from django.db.models.functions import Coalesce
import calendar
from permissions import EstAdministrateur
from commandes.models import Commande, DetailCommande
from rest_framework.permissions import AllowAny

# Create your views here.

# FONCTIONS UTILITAIRES POUR LES STATISTIQUES
def obtenir_plage_dates(period='jour'):
    """Retourne le début et la fin de la période demandée"""
    today = date.today()
    
    if period == 'jour':
        return today, today
    elif period == 'semaine':
        debut = today - timedelta(days=today.weekday())
        fin = debut + timedelta(days=6)
        return debut, fin
    elif period == 'mois':
        debut = today.replace(day=1)
        dernier_jour = calendar.monthrange(today.year, today.month)[1]
        fin = today.replace(day=dernier_jour)
        return debut, fin
    return today, today

def obtenir_plage_dates_precedente(period='jour'):
    """Retourne le début et la fin de la période précédente pour comparaison"""
    today = date.today()
    
    if period == 'jour':
        prev_day = today - timedelta(days=1)
        return prev_day, prev_day
    elif period == 'semaine':
        debut = today - timedelta(days=today.weekday())
        prev_debut = debut - timedelta(days=7)
        prev_fin = prev_debut + timedelta(days=6)
        return prev_debut, prev_fin
    elif period == 'mois':
        debut = today.replace(day=1)
        prev_fin = debut - timedelta(days=1)
        prev_debut = prev_fin.replace(day=1)
        return prev_debut, prev_fin
    return today, today

def calculer_apercu_ventes(debut, fin):
    """Calcule la vue d'ensemble des ventes pour une période"""
    ventes = Vente.objects.filter(date_vente__date__range=[debut, fin])
    commandes_livrees = Commande.objects.filter(
        date_commande__date__range=[debut, fin],
        etat_commande='livre'
    )
    
    total_ventes = sum(v.total_ttc for v in ventes)
    total_commandes = sum(c.total_ttc for c in commandes_livrees)
    total_ca = total_ventes + total_commandes
    
    # Nombre de ventes réalisées
    nb_ventes = ventes.count() + commandes_livrees.count()
    
    # Produits les plus vendus
    top_products = DetailVente.objects.filter(
        vente__date_vente__date__range=[debut, fin]
    ).values('produit__nom_produit', 'produit__identifiant_produit').annotate(
        total_qty=Sum('quantite'),
        total_amount=Sum(F('quantite') * F('prix_unitaire'), output_field=DecimalField())
    ).order_by('-total_qty')[:5]
    
    # Ajouter les produits des commandes livrées
    commande_products = DetailCommande.objects.filter(
        commande__date_commande__date__range=[debut, fin],
        commande__etat_commande='livre'
    ).values('produit__nom_produit', 'produit__identifiant_produit').annotate(
        total_qty=Sum('quantite'),
        total_amount=Sum(F('quantite') * F('prix_unitaire'), output_field=DecimalField())
    ).order_by('-total_qty')
    
    # Combiner et trier
    all_products = {}
    for p in list(top_products) + list(commande_products):
        key = p['produit__identifiant_produit']
        if key not in all_products:
            all_products[key] = p
        else:
            all_products[key]['total_qty'] += p['total_qty']
            all_products[key]['total_amount'] += p['total_amount']
    
    top_products_sorted = sorted(all_products.values(), key=lambda x: x['total_qty'], reverse=True)[:5]

    
    return {
        'total_ca': float(total_ca),
        'total_ventes': float(total_ventes),
        'total_commandes': float(total_commandes),
        'nombre_ventes': nb_ventes,
        'top_produits': top_products_sorted
    }

def calculer_statut_commandes(debut, fin):
    """Calcule l'état des commandes"""
    commandes_en_cours = Commande.objects.filter(
        date_creation__date__range=[debut, fin],
        etat_commande='en_cours'
    )
    commandes_validees = Commande.objects.filter(
        date_creation__date__range=[debut, fin],
        etat_commande='valide'
    )
    commandes_livrees = Commande.objects.filter(
        date_creation__date__range=[debut, fin],
        etat_commande='livre'
    )
    commandes_annulees = Commande.objects.filter(
        date_creation__date__range=[debut, fin],
        etat_commande='annule'
    )

    total_commande = commandes_en_cours.count() + commandes_validees.count() + commandes_livrees.count() + commandes_annulees.count()
    
    valeur_commande_en_cours = sum(c.total_ttc for c in commandes_en_cours)
    valeur_commande_en_livraison = sum(c.total_ttc for c in commandes_validees)
    valeur_commande_livre = sum(c.total_ttc for c in commandes_livrees)
    valeur_commande_annulees = sum(c.total_ttc for c in commandes_annulees)
    
    return {
        'en_cours': commandes_en_cours.count(),
        'en_livraison': commandes_validees.count(),
        'livrees': commandes_livrees.count(),
        'annulees': commandes_annulees.count(),
        'valeur_commande_en_cours': float(valeur_commande_en_cours),
        'valeur_commande_en_livraison': float(valeur_commande_en_livraison),
        'total_commande': total_commande,
        'valeur_commande_livre':valeur_commande_livre,
        'valeur_commande_annulees':valeur_commande_annulees,
    }

def calculer_statut_stock():
    """Calcule l'état du stock"""
    total_stock = Produit.objects.count()
    rupture_stock = Produit.objects.filter(quantite_produit_disponible=0)
    alertes_stock = AlertProduit.objects.filter(statut_alerte=True)
    
    produits_invendus = DetailVente.objects.exclude(
        produit__in=DetailVente.objects.filter(
            vente__date_vente__date__gte=date.today() - timedelta(days=30)
        ).values_list('produit')
    ).values_list('produit', flat=True).distinct()
    
    return {
        'total_stock':total_stock,
        'rupture_stock': rupture_stock.count(),
        'produits_rupture': [{'nom': p.nom_produit, 'id': str(p.identifiant_produit)} for p in rupture_stock],
        'alerte_faible_stock': alertes_stock.count(),
        'produits_alerte': [
            {
                'nom': a.produit.nom_produit,
                'id': str(a.produit.identifiant_produit),
                'quantite': a.produit.quantite_produit_disponible,
                'seuil': a.produit.seuil_alerte_produit
            }
            for a in alertes_stock
        ],
        'produits_invendus': produits_invendus.count(),
    }

def calculer_stats_clients(debut, fin):
    """Calcule les statistiques clients"""
    nouveaux_clients = Client.objects.filter(date_creation__date__range=[debut, fin]).count()
    
    # Clients réguliers (3+ commandes en 30 jours)
    clients_reguliers = Client.objects.annotate(
        commande_count=Count('commandes_clients')
    ).filter(commande_count__gte=3)
    
    # Top clients par nombre de commandes
    top_clients = Client.objects.annotate(
        commande_count=Count('commandes_clients'),
        total_depense=Coalesce(Sum('commandes_clients__total_ttc'), Decimal('0'))
    ).order_by('-total_depense')[:10]
    
    return {
        'nouveaux_clients': nouveaux_clients,
        'clients_reguliers': clients_reguliers.count(),
        'top_clients': [
            {
                'nom': c.nom_client,
                'id': str(c.identifiant_client),
                'commandes': c.commande_count,
                'total_depense': float(c.total_depense)
            }
            for c in top_clients
        ]
    }

def calculer_comparaison(period='jour'):
    """Calcule la comparaison avec la période précédente"""
    debut, fin = obtenir_plage_dates(period)
    prev_debut, prev_fin = obtenir_plage_dates_precedente(period)
    
    # CA actuel vs précédent
    ca_actuel = calculer_apercu_ventes(debut, fin)['total_ca']
    ca_precedent = calculer_apercu_ventes(prev_debut, prev_fin)['total_ca']
    
    evolution_ca = ((ca_actuel - ca_precedent) / ca_precedent * 100) if ca_precedent > 0 else 0
    
    # Nombre de ventes
    ventes_actuelles = Vente.objects.filter(date_vente__date__range=[debut, fin]).count()
    ventes_precedentes = Vente.objects.filter(date_vente__date__range=[prev_debut, prev_fin]).count()
    evolution_ventes = ((ventes_actuelles - ventes_precedentes) / ventes_precedentes * 100) if ventes_precedentes > 0 else 0
    
    return {
        'ca_evolution': round(evolution_ca, 2),
        'ventes_evolution': round(evolution_ventes, 2),
        'ca_periode_actuelle': float(ca_actuel),
        'ca_periode_precedente': float(ca_precedent),
    }

# Vue des statistiqes quotidiennes par vendeurs
@api_view(['GET'])
def statistiques_quotidiennes_vendeur(request):
    user = request.user
    if user.role != 'vendeur':
        return Response({
            "success": False,
            "errors": "Accès refusé. Cette vue est réservée aux vendeurs."
        }, status=403)
    else :
        aujourd_hui = date.today()
        try :
            # Somme total des ventes du jour effectuée par le vendeur connecté
            ventes_du_aujourdhui = Vente.objects.filter(utilisateur=user, date_vente__date=aujourd_hui)
            total_ventes_aujourd_hui = sum(vente.total_ttc for vente in ventes_du_aujourdhui)

            # Somme total des commandes du jour effectuée et livré par le vendeur connecté
            commandes_du_aujourdhui = Commande.objects.filter(utilisateur=user, date_commande__date=aujourd_hui, etat_commande="livre")
            total_ventes_commandes_aujourd_hui = sum(vente.total_ttc for vente in commandes_du_aujourdhui)

            nb_ventes = ventes_du_aujourdhui.count() + commandes_du_aujourdhui.count()

            # Caisse du jour du vendeur connecté
            total_caisse_jour = total_ventes_aujourd_hui + total_ventes_commandes_aujourd_hui

            # Total Commande du jour
            total_commande_aujourd_hui = Commande.objects.filter(date_creation__date=aujourd_hui,utilisateur=user).count()

            # Total Commande Attente du jour
            total_commande_attente_aujourd_hui = Commande.objects.filter(date_creation__date=aujourd_hui,etat_commande='en_cours',utilisateur=user).count()

            # Total Commande Attente du jour
            total_commande_valide_aujourd_hui = Commande.objects.filter(date_creation__date=aujourd_hui,etat_commande='valide',utilisateur=user).count()

            # Total Commande Livre du jour
            total_commande_livre_aujourd_hui = Commande.objects.filter(date_creation__date=aujourd_hui,etat_commande='livre',utilisateur=user).count()

            # Total Commande Annulée du jour
            total_commande_annulee_aujourd_hui = Commande.objects.filter(date_creation__date=aujourd_hui,etat_commande='annule',utilisateur=user).count()

            return Response({
            "success":True,
            "data":{
                "total_caisse_jour": total_caisse_jour,
                "total_commande_aujourd_hui":total_commande_aujourd_hui,
                "total_commande_valide_aujourd_hui":total_commande_valide_aujourd_hui,
                "total_commande_livre_aujourd_hui":total_commande_livre_aujourd_hui,
                "total_commande_attente_aujourd_hui":total_commande_attente_aujourd_hui,
                "total_ventes_aujourd_hui":total_ventes_aujourd_hui,
                "total_ventes_commandes_aujourd_hui":total_ventes_commandes_aujourd_hui,
                "total_commande_annulee_aujourd_hui":total_commande_annulee_aujourd_hui,
                "nombre_total_vente_aujourd_hui":nb_ventes,
            }
        }, status=200)
        except Exception as e :
            import traceback
            traceback.print_exc()
            return Response({
                "success":False,
                "errors":"Erreur interne du serveur",
                "message":str(e)
            }, status=500)



# Vue pour obtenir des statistiques du jour
@api_view(['GET'])
@permission_classes([AllowAny])
def statistiques_du_jour(request):
    try:
        debut, fin = obtenir_plage_dates('jour')
        
        # 1. VUE D'ENSEMBLE DES VENTES
        sales_overview = calculer_apercu_ventes(debut, fin)
        
        # Calcul de la marge bénéficiaire estimée
        # Note: Vous devez ajouter un champ 'prix_cout' au modèle Produit pour une marge réelle
        total_ca = sales_overview['total_ca']
        marge_estimee = Decimal(total_ca) * Decimal('0.30')  # 30% de marge estimée
        
        # 2. COMMANDES EN COURS
        orders_status = calculer_statut_commandes(debut, fin)
        
        # 3. PRODUITS ET STOCK
        stock_status = calculer_statut_stock()
        
        # 4. CLIENTS
        clients_stats = calculer_stats_clients(debut, fin)
        
        # 5. COMPARAISON AVEC PÉRIODE PRÉCÉDENTE
        comparison = calculer_comparaison('jour')
        
        return Response({
            "success": True,
            "data": {
                "periode": "jour",
                "date": str(debut),
                "vue_ensemble_ventes": {
                    "chiffre_affaires": sales_overview['total_ca'],
                    "nombre_ventes": sales_overview['nombre_ventes'],
                    "produits_plus_vendus": sales_overview['top_produits'],
                    "marge_beneficiaire_estimee": float(marge_estimee),
                },
                "comparaison_periode_precedente": comparison,
                "commandes_en_cours": orders_status,
                "produits_stock": stock_status,
                "clients": clients_stats,
            }
        }, status=200)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def statistiques_de_la_semaine(request):
    try:
        debut, fin = obtenir_plage_dates('semaine')
        
        # 1. VUE D'ENSEMBLE DES VENTES
        sales_overview = calculer_apercu_ventes(debut, fin)
        
        # Calcul de la marge bénéficiaire estimée
        total_ca = sales_overview['total_ca']
        marge_estimee = Decimal(total_ca) * Decimal('0.30')  # 30% de marge estimée
        
        # 2. COMMANDES EN COURS
        orders_status = calculer_statut_commandes(debut, fin)
        
        # 3. PRODUITS ET STOCK
        stock_status = calculer_statut_stock()
        
        # 4. CLIENTS
        clients_stats = calculer_stats_clients(debut, fin)
        
        # 5. COMPARAISON AVEC PÉRIODE PRÉCÉDENTE
        comparison = calculer_comparaison('semaine')
        
        return Response({
            "success": True,
            "data": {
                "periode": "semaine",
                "date_debut": str(debut),
                "date_fin": str(fin),
                "vue_ensemble_ventes": {
                    "chiffre_affaires": sales_overview['total_ca'],
                    "nombre_ventes": sales_overview['nombre_ventes'],
                    "produits_plus_vendus": sales_overview['top_produits'],
                    "marge_beneficiaire_estimee": float(marge_estimee),
                },
                "comparaison_periode_precedente": comparison,
                "commandes_en_cours": orders_status,
                "produits_stock": stock_status,
                "clients": clients_stats,
            }
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=500)


# Rapports mois
@api_view(['GET'])
@permission_classes([AllowAny])
def statistiques_du_mois(request):
    try:
        debut, fin = obtenir_plage_dates('mois')
        
        # 1. VUE D'ENSEMBLE DES VENTES
        sales_overview = calculer_apercu_ventes(debut, fin)
        
        # Calcul de la marge bénéficiaire estimée
        total_ca = sales_overview['total_ca']
        marge_estimee = Decimal(total_ca) * Decimal('0.30')  # 30% de marge estimée
        
        # 2. COMMANDES EN COURS
        orders_status = calculer_statut_commandes(debut, fin)
        
        # 3. PRODUITS ET STOCK
        stock_status = calculer_statut_stock()
        
        # 4. CLIENTS
        clients_stats = calculer_stats_clients(debut, fin)
        
        # 5. COMPARAISON AVEC PÉRIODE PRÉCÉDENTE
        comparison = calculer_comparaison('mois')
        
        return Response({
            "success": True,
            "data": {
                "periode": "mois",
                "date_debut": str(debut),
                "date_fin": str(fin),
                "vue_ensemble_ventes": {
                    "chiffre_affaires": sales_overview['total_ca'],
                    "nombre_ventes": sales_overview['nombre_ventes'],
                    "produits_plus_vendus": sales_overview['top_produits'],
                    "marge_beneficiaire_estimee": float(marge_estimee),
                },
                "comparaison_periode_precedente": comparison,
                "commandes_en_cours": orders_status,
                "produits_stock": stock_status,
                "clients": clients_stats,
            }
        }, status=200)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return Response({
            "success": False,
            "errors": "Erreur interne du serveur",
            "message": str(e)
        }, status=500)