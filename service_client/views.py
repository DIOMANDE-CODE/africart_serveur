from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from decouple import config
from google import genai
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status
from .models import chatMessage
from produits.models import Produit
from commandes.models import Commande, ZoneLivraison



model_genai = "models/gemini-3.1-flash-lite-preview"


# Coordonnées du support à afficher quand le chatbot ne peut aider
CONTACT_PHONE = "07-11-39-88-54"
CONTACT_EMAIL = "support@africart.ci"
CONTACT_MESSAGE = f"Pour plus d'assistance, contactez le service client : {CONTACT_PHONE} ou {CONTACT_EMAIL}."

# Message standard utilisé quand la donnée locale est indisponible
MESSAGE_INDISPONIBLE = "Désolé, l'information demandée n'est pas encore disponible."



# 1. DÉFINITION DE LA CONSTITUTION DE L'IA (RESTRICTION DE CONTEXTE)
SYSTEM_INSTRUCTION = """
Tu es l’assistant officiel d’AfriCart, une plateforme e-commerce spécialisée dans la vente des produits du marché public en Afrique.

RÈGLES DE CONDUITE :
1. RÉPONSE EXCLUSIVE :
   - Ne réponds qu’aux questions liées à AfriCart : commandes, produits, livraisons, paiements, promotions, assistance technique sur le site ou l’application.
   - Tu peux aussi répondre aux questions sur les catégories de produits définies par AfriCart, les produits et les details de chaque produit.

2. REFUS DE HORS-SUJET :
   - Si l’utilisateur pose une question hors du cadre AfriCart (ex. cuisine, sport, devoirs, politique, santé, divertissement), réponds poliment :
     "Désolé, en tant qu’assistant AfriCart, je ne peux vous aider que pour vos achats et questions liés à notre plateforme."

3. TON :
   - Sois professionnel, chaleureux et accueillant.
   - Utilise des expressions conviviales adaptées au contexte ivoirien (ex. "Bienvenue chez AfriCart !", "Nous sommes ravis de vous accompagner dans vos achats").

4. CONTEXTE LOCAL :
   - Tu connais les spécificités des livraisons.
   - Tu connais différentes catégories, produits et leurs details
   - Tu prends en compte les réalités locales : délais de livraison, modes de paiement , disponibilité des produits.

5. LIMITES :
   - Ne donne jamais d’informations personnelles ou médicales.
   - Ne propose pas de services ou produits qui ne sont pas disponibles sur AfriCart.
   - Ne sors jamais du rôle d’assistant AfriCart.

6. OBJECTIF :
   - Ton rôle est d’accompagner l’utilisateur dans son expérience d’achat sur AfriCart, en facilitant la navigation, en répondant aux questions pratiques et en renforçant la confiance dans la plateforme.
"""


# Configuration du client Gemini
client_genai = genai.Client(api_key=config("GEMINI_API_KEY"))


def est_hors_sujet(message):
    """Retourne True si le message semble hors du scope AfriCart."""
    forbidden_topics = [
    # Loisirs et divertissement
    "recette", "cuisine", "gastronomie", "boisson", "restaurant",
    "football", "sport", "basketball", "tennis", "match", "résultats sportifs",
    "film", "cinéma", "série", "musique", "concert", "jeu vidéo", "gaming",

    # Actualité et société
    "politique", "élection", "gouvernement", "parti", "manifestation",
    "météo", "climat", "catastrophe naturelle", "actualité", "journal",

    # Éducation et apprentissage
    "cours de", "exercice", "devoir", "mathématiques", "physique", "chimie",
    "langue", "philosophie", "histoire", "géographie",

    # Santé et bien-être
    "médecine", "maladie", "symptôme", "diagnostic", "traitement",
    "psychologie", "thérapie", "nutrition", "régime", "fitness",

    # Finance et technologie hors AfriCart
    "bourse", "crypto", "banque", "investissement", "action", "trading",
    "programmation", "code", "développement logiciel", "IA", "robotique",

    # Divers hors contexte
    "voyage", "tourisme", "vacances", "astrologie", "religion",
    "philosophie", "culture générale", "quiz", "blague"
]

    return any(topic in message.lower() for topic in forbidden_topics)



def verifier_stock_et_prix(nom_produit: str):
    """Recherche des produits par nom et retourne prix, description et stock.

    Utilise les champs du modèle `Produit` présents dans `produits/models.py`.
    """
    produits = Produit.objects.filter(nom_produit__icontains=nom_produit)[:3]
    if not produits:
        return f"Désolé, je n'ai pas trouvé de produit nommé '{nom_produit}'."

    # Construire données structurées
    produits_data = []
    for p in produits:
        produits_data.append({
            "nom_produit": p.nom_produit,
            "prix": float(p.prix_promo_produit if p.prix_promo_produit else p.prix_unitaire_produit),
            "quantite_disponible": p.quantite_produit_disponible,
            "description": p.description_produit,
        })

    # Générer un texte lisible pour l'utilisateur
    premier = produits[0]
    dispo = "En stock" if premier.quantite_produit_disponible > 0 else "Rupture de stock"
    prix_texte = int(premier.prix_promo_produit) if premier.prix_promo_produit else int(premier.prix_unitaire_produit)
    reponse_texte = f"J'ai trouvé {len(produits)} produit(s). Exemple: {premier.nom_produit} — {prix_texte} FCFA — {dispo}."

    return {"reply": reponse_texte, "data": {"produits": produits_data}}


def detecter_intention(message: str):
    """Détecte l'intention principale du message utilisateur.

    Retourne une des intentions:
    - 'recherche_produit'
    - 'statut_commande'
    - 'infos_livraison'
    - 'infos_paiement'
    - 'promotion'
    - 'salutation'
    - 'aide'
    - 'inconnu'
    """
    texte = message.lower()

    # Recherche produit
    if any(k in texte for k in ["prix", "combien", "coûte", "trouver", "cher", "produit", "nom", "recherche", "disponible", "stock"]):
        return 'recherche_produit'

    # Questions sur ce que nous vendons / nos offres / catalogue / services
    if any(k in texte for k in [
        "que vendez", "qu'est ce que vous vendez", "qu'est-ce que vous vendez", "ce que vous vendez",
        "nos produits", "nos offres", "que proposez", "quelles sont vos offres", "catalogue", "catalogue africart",
        "services", "proposition", "propositions", "offres", "vente", "vendre", "nos services"
    ]):
        return 'presentation_offres'

    # Demande sur MES COMMANDES (préférence pour les demandes personnelles)
    if any(k in texte for k in ["mes commandes", "mes achats", "historique", "mes commandes en cours", "mes commandes récentes"]):
        return 'mes_commandes'

    # Frais de livraison (mot-clés dédiés) -> retourner tarifs depuis la BDD
    if any(k in texte for k in ["frais de livraison", "frais", "tarif", "tarifs", "coût livraison", "prix livraison", "prix de livraison"]):
        return 'frais_livraison'

    # Lieux / zones / localités de livraison -> retourner zones depuis la BDD
    if any(k in texte for k in ["lieu", "lieux", "localité", "localités", "ville", "villes", "adresse", "adresses", "point de retrait", "point de livraison", "dépôt"]):
        return 'zones_livraison'

    # Questions génériques sur la livraison (fallback vers infos_livraison via BDD)
    if any(k in texte for k in ["livraison", "livrer", "livrés", "délai", "délais"]):
        return 'infos_livraison'

    # Statut de commande (référence ou suivi)
    if any(k in texte for k in ["statut", "suivi", "retard", "annulée", "annule", "id commande", "référence", "référence commande", "suivre ma commande", "commande"]):
        return 'statut_commande'

    # Paiement
    if any(k in texte for k in ["paiement", "payer", "carte", "mobile money", "momo", "télépaiement", "transaction"]):
        return 'infos_paiement'

    # Parcours de commande / comment commander
    if any(k in texte for k in ["comment commander", "comment passer une commande", "passer commande", "comment acheter", "parcours", "procédure de commande", "comment ça marche pour commander"]):
        return 'parcours_commande'

    # Promotions
    if any(k in texte for k in ["promo", "promotion", "réduction", "soldes", "offre"]):
        return 'promotion'

    # Salutations / aide
    if any(k in texte for k in ["bonjour", "salut", "bonsoir", "hello", "aide", "s'il vous plaît", "svp"]):
        return 'salutation'

    return 'inconnu'


# Petites réponses FAQ/PRÉCONFIGURÉES pour éviter les appels externes
FAQ_LOCAL = {
    'horaires': "Nous sommes disponibles 7j/7 de 6h à 22h pour la prise de commandes.",
    'retours': "Vous pouvez retourner un produit dans les 7 jours suivant la réception si l'article est défectueux. Contactez le support via le numéro 07 11 39 95 67.",
    'moyens_de_paiement': "Nous acceptons les paiements à la livraison pour le moment. Les frais de livraison varient selon les zones.",
    'livraison_zones': "Les frais et délais de livraison dépendent de votre zone. Indiquez votre localité pour obtenir une estimation.",
}


def repondre_selon_intention(utilisateur, intention, message):
    """Route la requête vers un outil local selon l'intention détectée.

    Si l'intention n'est pas traitable localement, retourne None pour laisser
    l'IA générative répondre (toujours avec restriction de contexte).
    """
    if intention == 'recherche_produit':
        # extraire un mot-clé simple (le premier mot significatif)
        return verifier_stock_et_prix(message)

    if intention == 'details_produit':
        return obtenir_details_produit(message)

    if intention == 'liste_produits':
        return lister_produits(message)

    if intention == 'presentation_offres':
        # Présentation des offres : lister les produits disponibles (catalogue)
        return lister_produits(None, limite=20)

    if intention == 'statut_commande':
        # Pour un utilisateur non-authentifié, demander référence
        if not utilisateur or not getattr(utilisateur, 'is_authenticated', False):
            return {"reply": "Pour consulter le statut d'une commande, veuillez vous connecter ou fournir la référence de commande (ex: AfriCart-C-20260307-001).", "data": None}

        # Essayer d'extraire une référence simple
        import re
        m = re.search(r"afr?icart[-_]?[cC]?[- ]?\w+", message, re.IGNORECASE)
        if m:
            ref = m.group(0)
            try:
                commande = Commande.objects.filter(identifiant_commande__icontains=ref).first()
                if commande:
                    data = {
                        "identifiant": commande.identifiant_commande,
                        "etat": commande.etat_commande,
                        "total_ttc": float(commande.total_ttc) if getattr(commande, 'total_ttc', None) is not None else None,
                        "date": str(commande.date_commande) if getattr(commande, 'date_commande', None) else None,
                    }
                    reply = f"Commande {commande.identifiant_commande} : état = {commande.etat_commande}, total = {data.get('total_ttc')} FCFA."
                    return {"reply": reply, "data": {"commande": data}, "audience": "auth"}
                else:
                    return {"reply": "Référence non trouvée. Vérifiez la référence de commande ou contactez le support.", "data": None}
            except Exception:
                return {"reply": "Erreur lors de la recherche de la commande. Réessayez plus tard.", "data": None}
        else:
            return {"reply": "Merci de fournir la référence de commande (ex: AfriCart-C-20260307-001) pour que je puisse vérifier le statut.", "data": None, "audience": "auth"}

    if intention == 'mes_commandes':
        # Fournit un résumé des commandes personnelles pour l'utilisateur authentifié
        if not utilisateur or not getattr(utilisateur, 'is_authenticated', False):
            return {"reply": "Pour consulter vos commandes, veuillez vous connecter à votre compte AfriCart.", "data": None}

        try:
            commandes = Commande.objects.filter(utilisateur=utilisateur).order_by('-date_commande')[:5]
            if not commandes:
                return {"reply": "Vous n'avez pas de commandes récentes.", "data": {"commandes": []}}

            items = []
            for c in commandes:
                items.append({
                    "identifiant": c.identifiant_commande,
                    "etat": c.etat_commande,
                    "total_ttc": float(c.total_ttc) if getattr(c, 'total_ttc', None) is not None else None,
                    "date": str(c.date_commande) if getattr(c, 'date_commande', None) else None,
                })

            reponse = f"Voici vos {len(items)} dernières commande(s)."
            return {"reply": reponse, "data": {"commandes": items}, "audience": "auth"}
        except Exception:
            return {"reply": "Erreur lors de la récupération de vos commandes. Réessayez plus tard.", "data": None}

    if intention == 'infos_livraison':
        # Retourner les informations de livraison détaillées issues de la base de données
        return obtenir_zones_livraison()

    if intention == 'zones_livraison':
        return obtenir_zones_livraison()

    if intention == 'frais_livraison':
        return obtenir_frais_livraison_par_ville(message)

    if intention == 'infos_paiement':
        return {"reply": FAQ_LOCAL['moyens_de_paiement'], "data": {"faq": "moyens_de_paiement"}}

    if intention == 'promotion':
        return {"reply": "Les 'Promotions' ne sont pas encore disponibles.", "data": None}

    if intention == 'salutation':
        return {"reply": "Bonjour ! Je suis l'assistant AfriCart — comment puis-je vous aider pour vos achats aujourd'hui ?", "data": None}

    if intention == 'parcours_commande':
        # Explication claire et étape par étape du parcours de commande
        reponse = (
            "Pour passer une commande :1) Se connecter; 2) Ajouter des produits au panier; "
            "3) Passer à la caisse; 4) Sélectionner le lieu de livraison; 5) Choisir le paiement; 6) Confirmer la commande."
        )
        return {"reply": reponse}

    return None


def _normaliser_reponse_locale(resp):
    """Normalise la réponse d'un outil local.

    Si l'outil indique une erreur ou ne renvoie pas de données utiles,
    retourne un message poli pour indiquer l'indisponibilité.

    Retour: tuple (reply_text, data_or_None)
    """
    message_indisponible = MESSAGE_INDISPONIBLE

    if resp is None:
        return (message_indisponible, None)

    if isinstance(resp, dict):
        # si l'outil signale une erreur explicite
        if 'error' in resp:
            return (message_indisponible, None)

        data = resp.get('data')
        reply = resp.get('reply') or ''

        # aucune donnée significative
        if data is None:
            return (reply or message_indisponible, None)

        # si data est dict et toutes les valeurs sont vides/listes vides
        if isinstance(data, dict):
            any_non_empty = False
            for v in data.values():
                if v:
                    any_non_empty = True
                    break
            if not any_non_empty:
                return (message_indisponible, None)

        # si data est liste vide
        if isinstance(data, list) and len(data) == 0:
            return (message_indisponible, None)

        return (reply, data)

    # chaîne simple
    return (str(resp), None)


# Intents qui doivent STRICTEMENT se baser sur la base de données (pas de fallback GenAI)
INTENTS_LOCAUX_SEULS = {
    'recherche_produit', 'details_produit', 'liste_produits', 'presentation_offres',
    'zones_livraison', 'frais_livraison', 'mes_commandes', 'statut_commande', 'profil_utilisateur'
}


def obtenir_details_produit(nom_produit: str):
    """Retourne des informations détaillées sur les produits correspondants.

    Renvoie un dictionnaire sérialisable contenant une liste `produits`.
    """
    produits_qs = Produit.objects.filter(nom_produit__icontains=nom_produit)[:10]
    if not produits_qs:
        return {"error": f"Aucun produit trouvé pour '{nom_produit}'."}

    produits = []
    for p in produits_qs:
        produits.append({
            "nom_produit": p.nom_produit,
            "identifiant": str(p.identifiant_produit),
            "prix_unitaire": float(p.prix_unitaire_produit),
            "prix_promo": float(p.prix_promo_produit) if p.prix_promo_produit else None,
            "quantite_disponible": p.quantite_produit_disponible,
            "seuil_alerte": p.seuil_alerte_produit,
            "description": p.description_produit,
            "categorie": p.categorie_produit.nom_categorie if p.categorie_produit else None,
            "thumbnail": p.thumbnail,
        })

    # Texte de synthèse
    reponse_texte = f"J'ai trouvé {len(produits)} produit(s) correspondant à '{nom_produit}'."
    return {"reply": reponse_texte, "data": {"produits": produits}}


def lister_produits(texte_filtre: str = None, limite: int = 20):
    """Retourne une liste sommaire de produits (optionnellement filtrée)."""
    qs = Produit.objects.all()
    if texte_filtre:
        qs = qs.filter(nom_produit__icontains=texte_filtre)
    qs = qs[:limite]

    resultat = [{
        "nom_produit": p.nom_produit,
        "prix": float(p.prix_promo_produit if p.prix_promo_produit else p.prix_unitaire_produit),
        "quantite_disponible": p.quantite_produit_disponible,
    } for p in qs]

    reponse_texte = f"Liste de {len(resultat)} produit(s)."
    return {"reply": reponse_texte, "data": {"produits": resultat}}


def obtenir_zones_livraison():
    """Retourne les zones de livraison actives pour AfriCart.

    Règle stricte : AfriCart livre actuellement uniquement à Yamoussoukro.
    Cette fonction ne renvoie que les zones stockées dans la table `ZoneLivraison`
    correspondant à Yamoussoukro. Aucun calcul heuristique ou fallback n'est utilisé.
    """
    # Ne considérer que les zones explicitement liées à Yamoussoukro
    zones_y = ZoneLivraison.objects.filter(nom_zone__icontains='yamoussoukro')
    # Si aucune zone détaillée n'existe en base, renvoyer Yamoussoukro comme lieu
    # de livraison par défaut (sans inventer de frais).
    if not zones_y:
        data = [{
            "nom_zone": "Yamoussoukro",
            "frais_livraison": None,
        }]
        reponse_texte = "AfriCart livre actuellement uniquement à Yamoussoukro. Les frais de livraison commencent à partir de 500 FCFA."
        return {"reply": reponse_texte}

    data = [{
        "nom_zone": z.nom_zone,
        "frais_livraison": float(z.frais_livraison),
        "rayon_metres": z.rayon_metres,
        "latitude": z.latitude,
        "longitude": z.longitude,
    } for z in zones_y]

    # Préciser que les frais varient selon la distance dans Yamoussoukro
    reponse_texte = f"AfriCart livre à Yamoussoukro : {len(data)} zone(s) configurée(s). Les frais de livraison varient uniquement en fonction de la distance dans Yamoussoukro."
    return {"reply": reponse_texte, "data": {"zones": data}}


def obtenir_frais_livraison_par_ville(ville: str):
    """Retourne les frais de livraison pour une localité en se basant STRICTEMENT
    sur les enregistrements de `ZoneLivraison`.

    Comportement :
    - Si la `ville` correspond à une zone en base (nom_zone), renvoyer ses frais.
    - AfriCart livre uniquement à Yamoussoukro : si la ville n'est pas Yamoussoukro
      ou qu'aucune zone Yamoussoukro n'est trouvée, renvoyer un message indiquant
      que la livraison n'est pas disponible pour cette localité.
    - Aucun fallback, estimation ou valeur par défaut n'est renvoyée.
    """
    if not ville:
        return {"error": "Précisez la localité (ex: Yamoussoukro) pour obtenir les frais."}

    texte = ville.strip().lower()

    # Si l'utilisateur ne mentionne pas Yamoussoukro, indiquer clairement la limitation
    if 'yamoussoukro' not in texte:
        return {
            "reply": "AfriCart livre actuellement uniquement à Yamoussoukro. Les frais de livraison commencent à partir de 500 FCFA.",
        }

    # Rechercher les zones Yamoussoukro en base
    zone = ZoneLivraison.objects.filter(nom_zone__icontains='yamoussoukro').first()
    if not zone:
        # Si aucune zone détaillée n'est configurée, indiquer Yamoussoukro comme lieu
        # de livraison par défaut, sans fournir de montant estimé.
        return {
            "reply": "AfriCart livre à Yamoussoukro. Les frais de livraison commencent à partir de 500 FCFA.",
            "data": {"nom_zone": "Yamoussoukro", "frais_livraison": None, "frais_min": 500}
        }

    reponse_texte = f"Zone '{zone.nom_zone}' — frais de livraison : {float(zone.frais_livraison)} FCFA."
    return {"reply": reponse_texte, "data": {"nom_zone": zone.nom_zone, "frais_livraison": float(zone.frais_livraison)}}


def obtenir_profil_utilisateur(utilisateur):
    """Retourne les informations publiques du profil utilisateur connecté."""
    if not utilisateur or not getattr(utilisateur, 'is_authenticated', False):
        return {"error": "Utilisateur non authentifié."}

    try:
        profil = {
            "identifiant_utilisateur": str(getattr(utilisateur, 'identifiant_utilisateur', '')),
            "nom_utilisateur": getattr(utilisateur, 'nom_utilisateur', None),
            "email_utilisateur": getattr(utilisateur, 'email_utilisateur', None),
            "numero_telephone": getattr(utilisateur, 'numero_telephone_utilisateur', None),
            "role": getattr(utilisateur, 'role', None),
            "photo_profil": getattr(utilisateur, 'thumbnail', None) or getattr(utilisateur, 'photo_profil_utilisateur', None),
            "date_creation": getattr(utilisateur, 'date_creation', None),
        }
        reponse_texte = f"Profil de {profil.get('nom_utilisateur') or 'utilisateur'} : rôle={profil.get('role')}" 
        return {"reply": reponse_texte, "data": {"profil": profil}}
    except Exception:
        return {"error": "Impossible de récupérer le profil."}


# --- CHATBOT POUR UTILISATEURS NON CONNECTÉS ---
@api_view(['POST'])
@permission_classes([AllowAny])
def chatbot(request):
    """Point d'entrée public pour le chatbot AfriCart.

    Attends dans `request.data` : `message` (str) et optionnellement `history` (liste).
    """
    message_utilisateur = request.data.get("message")
    historique = request.data.get("history", [])
    outils = [verifier_stock_et_prix]

    # liste_models_ia = client_genai.models.list()
    # print("MODELS DISPONIBLES:", [m.name for m in liste_models_ia])

    if not message_utilisateur:
        return Response({"error": "Message vide."}, status=status.HTTP_400_BAD_REQUEST)

    # Filtrage préventif des sujets hors-sujet
    if est_hors_sujet(message_utilisateur):
        reply_text = "Désolé, je ne peux répondre qu'aux questions concernant AfriCart. " + CONTACT_MESSAGE
        return Response({"reply": reply_text, "history": historique}, status=status.HTTP_200_OK)

    # Détection d'intention et réponse locale prioritaire
    intention = detecter_intention(message_utilisateur)
    reponse_locale = repondre_selon_intention(None, intention, message_utilisateur)
    if reponse_locale:
        # respecter l'audience indiquée par l'outil local (auth / anon / all)
        audience = reponse_locale.get('audience', 'all')
        if audience == 'auth':
            # information réservée aux utilisateurs connectés
            reply_text = "Cette information est réservée aux utilisateurs connectés. Veuillez vous connecter pour y accéder."
            nouvel_historique = historique + [
                {"role": "user", "parts": [{"text": message_utilisateur}]},
                {"role": "model", "parts": [{"text": reply_text}]}
            ]
            return Response({"reply": reply_text, "history": nouvel_historique}, status=status.HTTP_200_OK)
        # Normaliser la réponse locale et vérifier disponibilité des données
        reply_text, data = _normaliser_reponse_locale(reponse_locale)

        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message_utilisateur}]},
            {"role": "model", "parts": [{"text": reply_text}]}
        ]

        response_payload = {"reply": reply_text, "history": nouvel_historique}
        if data is not None:
            response_payload["data"] = data

        return Response(response_payload, status=status.HTTP_200_OK)

    # Si aucune réponse locale, mais l'intention exige DE TRAVAILLER SEULEMENT AVEC LA BDD,
    # on refuse poliment au lieu d'appeler GenAI.
    if intention in INTENTS_LOCAUX_SEULS:
        reply_text = "Désolé, l'information demandée n'est pas encore disponible."
        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message_utilisateur}]},
            {"role": "model", "parts": [{"text": reply_text}]}
        ]
        return Response({"reply": reply_text, "history": nouvel_historique}, status=status.HTTP_200_OK)

    # Si aucune réponse locale, appeler le modèle générique mais en conservant la restriction système
    try:
        chat = client_genai.chats.create(
            model=model_genai,
            history=historique,
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "temperature": 0.2,
                "tools": outils,
            }
        )

        message_reponse = chat.send_message(message_utilisateur)

        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message_utilisateur}]},
            {"role": "model", "parts": [{"text": message_reponse.text}]}
        ]

        return Response({"reply": message_reponse.text, "history": nouvel_historique}, status=status.HTTP_200_OK)

    except Exception as e:
        err_str = str(e)
        # Gestion spécifique pour les conflits (409)
        if getattr(e, 'status_code', None) == 409 or '409' in err_str:
            return Response({"reply": "Conflit : votre demande ne peut être traitée (409). " + CONTACT_MESSAGE}, status=status.HTTP_409_CONFLICT)
        # Pour d'autres erreurs, proposer le contact support
        return Response({"reply": f"Une erreur est survenue. {CONTACT_MESSAGE}", "error": err_str}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- CHATBOT POUR UTILISATEURS CONNECTÉS (AVEC PERSISTENCE) ---
@api_view(['POST', 'GET'])
@permission_classes([IsAuthenticated])
def chatbot_user_connected(request):
    """Point d'entrée pour utilisateurs authentifiés avec stockage des messages en base.

    GET : retourne l'historique récent (20 derniers messages).
    POST : enregistre le message utilisateur et la réponse du modèle en base.
    """
    utilisateur = request.user

 

    # RÉCUPÉRATION DE L'HISTORIQUE EN BASE DE DONNÉES
    if request.method == "GET":
        messages = chatMessage.objects.filter(utilisateur=utilisateur).order_by('timestamp')[:20]
        historique = [{"role": m.role, "parts": [{"text": m.message}]} for m in messages]
        return Response({"history": historique}, status=status.HTTP_200_OK)

    # TRAITEMENT DU NOUVEAU MESSAGE (POST)
    if request.method == "POST":
        message_utilisateur = request.data.get("message")
        historique = request.data.get("history", [])

        # liste_models_ia = client_genai.models.list()
        # print("MODELS DISPONIBLES:", [m.name for m in liste_models_ia])

        if not message_utilisateur:
            return Response({"error": "Message vide."}, status=status.HTTP_400_BAD_REQUEST)

        if est_hors_sujet(message_utilisateur):
            reply_text = "En tant qu'assistant AfriCart, je me limite aux sujets liés à la boutique. " + CONTACT_MESSAGE
            return Response({"reply": reply_text}, status=200)

        # Détection d'intention et tentative de réponse locale (authentifiée)
        intention = detecter_intention(message_utilisateur)
        reponse_locale = repondre_selon_intention(utilisateur, intention, message_utilisateur)
        if reponse_locale:
            # respecter l'audience indiquée par l'outil local (auth / anon / all)
            audience = reponse_locale.get('audience', 'all')
            # pour l'utilisateur connecté, on permet toutes les audiences
            # (si une réponse était explicitement réservée aux non-connectés, on l'affiche quand même)
            # Normaliser la réponse locale et vérifier disponibilité des données
            reply_text, data = _normaliser_reponse_locale(reponse_locale)

            # Sauvegarde en base : stocker le message utilisateur et le résumé
            chatMessage.objects.create(utilisateur=utilisateur, role="user", message=message_utilisateur)
            chatMessage.objects.create(utilisateur=utilisateur, role="model", message=reply_text)

            nouvel_historique = historique + [
                {"role": "user", "parts": [{"text": message_utilisateur}]},
                {"role": "model", "parts": [{"text": reply_text}]}
            ]

            payload = {"reply": reply_text, "history": nouvel_historique}
            if data is not None:
                payload["data"] = data

            return Response(payload, status=status.HTTP_200_OK)

        # Intention locale sans données : refuser poliment (pas de fallback GenAI)
        if intention in INTENTS_LOCAUX_SEULS:
            reply_text = MESSAGE_INDISPONIBLE + " " + CONTACT_MESSAGE
            chatMessage.objects.create(utilisateur=utilisateur, role="user", message=message_utilisateur)
            chatMessage.objects.create(utilisateur=utilisateur, role="model", message=reply_text)

            nouvel_historique = historique + [
                {"role": "user", "parts": [{"text": message_utilisateur}]},
                {"role": "model", "parts": [{"text": reply_text}]}
            ]

            return Response({"reply": reply_text, "history": nouvel_historique}, status=status.HTTP_200_OK)

        # Sinon, appel contrôlé au modèle générique (avec instruction système stricte)
        try:
            chat = client_genai.chats.create(
                model=model_genai,
                history=historique,
                config={"system_instruction": SYSTEM_INSTRUCTION}
            )

            message_reponse = chat.send_message(message_utilisateur)

            # SAUVEGARDE PERSISTANTE EN BASE DE DONNÉES
            chatMessage.objects.create(utilisateur=utilisateur, role="user", message=message_utilisateur)
            chatMessage.objects.create(utilisateur=utilisateur, role="model", message=message_reponse.text)

            nouvel_historique = historique + [
                {"role": "user", "parts": [{"text": message_utilisateur}]},
                {"role": "model", "parts": [{"text": message_reponse.text}]}
            ]

            return Response({"reply": message_reponse.text, "history": nouvel_historique}, status=status.HTTP_200_OK)

        except Exception as e:
            err_str = str(e)
            if getattr(e, 'status_code', None) == 409 or '409' in err_str:
                # sauvegarde des messages
                chatMessage.objects.create(utilisateur=utilisateur, role="user", message=message_utilisateur)
                chatMessage.objects.create(utilisateur=utilisateur, role="model", message="Conflit (409) : demande non traitée")
                return Response({"reply": "Conflit : votre demande ne peut être traitée (409). " + CONTACT_MESSAGE}, status=status.HTTP_409_CONFLICT)

            # sauvegarde des messages et invitation à contacter le support
            chatMessage.objects.create(utilisateur=utilisateur, role="user", message=message_utilisateur)
            chatMessage.objects.create(utilisateur=utilisateur, role="model", message=f"Une erreur est survenue. {CONTACT_MESSAGE}")
            return Response({"reply": f"Une erreur est survenue. {CONTACT_MESSAGE}", "error": err_str}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)