from django.shortcuts import render
from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from commandes.models import DetailCommande
from produits.models import Produit
from .models import Recommandation, VueProduit, TYPES_DE_RECOMMANDATION

# Create your views here.

# Enregistrement d'une vue produit
@api_view(['POST'])
@permission_classes([AllowAny])
def enregistrer_vue_produit(request):
    produit_id = request.data.get('produit_id')

    if not produit_id:
        return Response({"error":"produit_id requis"}, status=status.HTTP_400_BAD_REQUEST)
    
    produit = Produit.objects.filter(identifiant_produit=produit_id).first()
    if not produit:
        return Response({"error": "Produit non trouvé."}, status=status.HTTP_404_NOT_FOUND)

    utilisateur = request.user if getattr(request.user,'is_authenticated',False) else None
    session_key = request.session.session_key if hasattr(request, 'session') else None

    VueProduit.objects.create(produit=produit, utilisateur=utilisateur, session_key=session_key)
    return Response({"message": "Vue enregistrée."}, status=status.HTTP_201_CREATED)


# Obtenir les recommandations
@api_view(['GET'])
@permission_classes([AllowAny])
def obtenir_recommandations(request):

    type_reco = request.query_params.get('type','best_sellers')
    produit_id = request.query_params.get('produit_id')
    limite = min(int(request.query_params.get('limite', 10)), 50)

    types_valides = [t[0] for t in TYPES_DE_RECOMMANDATION]
    if type_reco not in types_valides:
        return Response({"error": f"type de recommandation invalide. Choisissez parmi : {', '.join(types_valides)}."}, status=status.HTTP_400_BAD_REQUEST)
    
    # Type personnalisé
    if type_reco == 'personnalise':
        if not getattr(request.user, 'is_authenticated', False):
            produits = _best_sellers(limite)
            return Response({
                "type": "best_sellers",
                "note": "Connectez-vous pour des recommandations personnalisées.",
                "data": {"produits": produits},
            })
        return Response({"type": "personnalise", "data": {"produits": _personnalise(request.user, limite)}})
    
    #  Best sellers globaux
    if type_reco == 'best_sellers':
        return Response({"type": "best_sellers", "data": {"produits": _best_sellers(limite)}})
    
    # Type necessistant un produit_id
    if not produit_id:
        return Response({"error": "produit_id requis pour ce type de recommandation."}, status=status.HTTP_400_BAD_REQUEST)
    
    produit_src = Produit.objects.filter(identifiant_produit=produit_id).first()
    if not produit_src:
        return Response({"error": "Produit non trouvé."}, status=status.HTTP_404_NOT_FOUND)

    recos = (
        Recommandation.objects
        .filter(produit_source=produit_src, type_recommandation=type_reco)
        .select_related('produit_recommande__categorie_produit')
        .order_by('-score')[:limite]
    )
    produits = [_ser(r.produit_recommande, r.score) for r in recos]

    # Fallback → best-sellers si table vide
    if not produits:
        produits = _best_sellers(limite)

    return Response({"type": type_reco, "data": {"produits": produits}})


    # ─── Helpers internes ─────────────────────────────────────────────────────────
def _best_sellers(limite):
    recos = (
        Recommandation.objects
        .filter(produit_source__isnull=True, type_recommandation='best_sellers')
        .select_related('produit_recommande__categorie_produit')
        .order_by('-score')[:limite]
    )
    if recos:
        return [_ser(r.produit_recommande, r.score) for r in recos]
    # Fallback calcul à la volée
    ventes = (
        DetailCommande.objects
        .values('produit_id')
        .annotate(total=Sum('quantite'))
        .order_by('-total')[:limite]
    )
    ids     = [v['produit_id'] for v in ventes]
    cache   = {p.pk: p for p in Produit.objects.filter(pk__in=ids).select_related('categorie_produit')}
    return [_ser(cache[v['produit_id']], v['total']) for v in ventes if v['produit_id'] in cache]


def _personnalise(utilisateur, limite):
    deja_achetes = set(
        DetailCommande.objects
        .filter(commande__utilisateur=utilisateur)
        .values_list('produit_id', flat=True)
    )
    recos_co = list(
        Recommandation.objects
        .filter(produit_source__in=deja_achetes, type_recommandation='co_achat')
        .exclude(produit_recommande__in=deja_achetes)
        .select_related('produit_recommande__categorie_produit')
        .order_by('-score')[:limite]
    )
    vus = set(
        VueProduit.objects
        .filter(utilisateur=utilisateur, timestamp__gte=timezone.now() - timedelta(days=30))
        .values_list('produit_id', flat=True).distinct()
    )
    recos_sim = list(
        Recommandation.objects
        .filter(produit_source__in=vus, type_recommandation='similaire_categorie')
        .exclude(produit_recommande__in=deja_achetes)
        .select_related('produit_recommande__categorie_produit')
        .order_by('-score')[:limite]
    )
    vus_ids, fusionnes = set(), []
    for r in recos_co + recos_sim:
        if r.produit_recommande_id not in vus_ids:
            vus_ids.add(r.produit_recommande_id)
            fusionnes.append(r)
        if len(fusionnes) >= limite:
            break
    return [_ser(r.produit_recommande, r.score) for r in fusionnes] if fusionnes else _best_sellers(limite)


def _ser(produit, score=None):
    return {
        "identifiant_produit":  str(produit.identifiant_produit),
        "nom_produit":          produit.nom_produit,
        "prix":                 float(produit.prix_promo_produit or produit.prix_unitaire_produit),
        "prix_promo":           float(produit.prix_promo_produit) if produit.prix_promo_produit else None,
        "thumbnail":            produit.thumbnail,
        "categorie":            produit.categorie_produit.nom_categorie if produit.categorie_produit else None,
        "quantite_disponible":  produit.quantite_produit_disponible,
        "score_reco":           round(score, 4) if score is not None else None,
    }
