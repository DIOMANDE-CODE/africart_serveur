import logging
import re

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from decouple import config
from google import genai
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework import status

from difflib import SequenceMatcher

from .models import chatMessage
from produits.models import Produit, Categorie
from commandes.models import Commande, DetailCommande, ZoneLivraison
from recommandations.models import Recommandation, VueProduit

logger = logging.getLogger(__name__)

# --- CONFIGURATION -----------------------------------------------------------
MAX_MESSAGE_LENGTH = 1000
MAX_HISTORY_GENAI = 20
MODEL_GENAI = "models/gemini-3.1-flash-lite-preview"

CONTACT_PHONE = "07-11-39-88-54"
CONTACT_EMAIL = "support@africart.ci"
CONTACT_MESSAGE = (
    f"Pour plus d'assistance, contactez le service client : "
    f"{CONTACT_PHONE} ou {CONTACT_EMAIL}."
)
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
   - Tu connais différentes catégories, produits et leurs details.
   - Tu prends en compte les réalités locales : délais de livraison, modes de paiement, disponibilité des produits.
   - AfriCart livre actuellement uniquement à Yamoussoukro. Les frais de livraison varient selon la distance.

5. CAPACITÉS :
   - Tu peux chercher des produits par nom, catégorie ou mots-clés.
   - Tu peux recommander des produits similaires ou populaires.
   - Tu peux afficher les promotions en cours avec les économies réalisées.
   - Tu peux consulter le détail d'une commande (articles, prix, état).
   - Tu peux donner le profil de l'utilisateur connecté.
   - Tu tolères les fautes de frappe grâce à la recherche floue.
   - Quand un utilisateur demande un produit, propose aussi de voir les promotions ou la catégorie associée.

6. LIMITES :
   - Ne donne jamais d’informations personnelles ou médicales.
   - Ne propose pas de services ou produits qui ne sont pas disponibles sur AfriCart.
   - Ne sors jamais du rôle d’assistant AfriCart.

7. OBJECTIF :
   - Ton rôle est d’accompagner l’utilisateur dans son expérience d’achat sur AfriCart, en facilitant la navigation, en répondant aux questions pratiques et en renforçant la confiance dans la plateforme.
"""


# Configuration du client Gemini
client_genai = genai.Client(api_key=config("GEMINI_API_KEY"))


# --- STOPWORDS FRANÇAIS (extraction de mots-clés produit) ---------------------
_STOPWORDS_FR = frozenset(
    {
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "du",
        "de",
        "d",
        "l",
        "je",
        "tu",
        "il",
        "elle",
        "nous",
        "vous",
        "ils",
        "elles",
        "on",
        "mon",
        "ton",
        "son",
        "ma",
        "ta",
        "sa",
        "mes",
        "tes",
        "ses",
        "ce",
        "cette",
        "ces",
        "quel",
        "quelle",
        "quels",
        "quelles",
        "qui",
        "que",
        "quoi",
        "dont",
        "où",
        "est",
        "sont",
        "a",
        "ai",
        "as",
        "avez",
        "avons",
        "ont",
        "être",
        "avoir",
        "et",
        "ou",
        "mais",
        "donc",
        "car",
        "ni",
        "or",
        "en",
        "au",
        "aux",
        "par",
        "pour",
        "avec",
        "sans",
        "sur",
        "sous",
        "dans",
        "ne",
        "pas",
        "plus",
        "jamais",
        "rien",
        "très",
        "trop",
        "assez",
        "bien",
        "mal",
        "combien",
        "comment",
        "pourquoi",
        "quand",
        "prix",
        "coûte",
        "coute",
        "cher",
        "cherche",
        "trouver",
        "recherche",
        "disponible",
        "stock",
        "produit",
        "produits",
        "acheter",
        "veux",
        "voudrais",
        "besoin",
        "svp",
        "merci",
        "bonjour",
        "salut",
        "bonsoir",
        "y",
        "s",
        "c",
        "n",
        "j",
        "m",
        "t",
        "se",
        "me",
        "te",
        "est-ce",
        "qu",
        "là",
        "ça",
        "ca",
    }
)


# --- TOPICS INTERDITS (filtrage hors-sujet) -----------------------------------
_FORBIDDEN_TOPICS = (
    "recette",
    "cuisine",
    "gastronomie",
    "boisson",
    "restaurant",
    "football",
    "sport",
    "basketball",
    "tennis",
    "match",
    "résultats sportifs",
    "film",
    "cinéma",
    "série",
    "musique",
    "concert",
    "jeu vidéo",
    "gaming",
    "politique",
    "élection",
    "gouvernement",
    "parti",
    "manifestation",
    "météo",
    "climat",
    "catastrophe naturelle",
    "actualité",
    "journal",
    "cours de",
    "exercice",
    "devoir",
    "mathématiques",
    "physique",
    "chimie",
    "langue",
    "philosophie",
    "histoire",
    "géographie",
    "médecine",
    "maladie",
    "symptôme",
    "diagnostic",
    "traitement",
    "psychologie",
    "thérapie",
    "nutrition",
    "régime",
    "fitness",
    "bourse",
    "crypto",
    "banque",
    "investissement",
    "action",
    "trading",
    "programmation",
    "code",
    "développement logiciel",
    "IA",
    "robotique",
    "voyage",
    "tourisme",
    "vacances",
    "astrologie",
    "religion",
    "philosophie",
    "culture générale",
    "quiz",
    "blague",
)


# Intentions qui doivent STRICTEMENT se baser sur la BDD (pas de fallback GenAI)
_INTENTS_DB_ONLY = frozenset(
    {
        "recherche_produit",
        "details_produit",
        "liste_produits",
        "presentation_offres",
        "zones_livraison",
        "frais_livraison",
        "mes_commandes",
        "statut_commande",
        "profil_utilisateur",
        "recherche_categorie",
        "recommandations",
        "promotions_en_cours",
        "details_commande",
    }
)

# Seuil de similarité pour la recherche floue (0.0 à 1.0)
_FUZZY_THRESHOLD = 0.55


# =============================================================================
#  UTILITAIRES
# =============================================================================


def _extraire_mot_cle_produit(message: str) -> str:
    """Extrait les mots significatifs d'un message pour la recherche produit.

    Retire les stopwords français pour ne garder que les termes
    susceptibles de désigner un produit.
    """
    texte = re.sub(r"[^\w\s'-]", " ", message.lower())
    mots = [m for m in texte.split() if m not in _STOPWORDS_FR and len(m) > 1]
    return " ".join(mots) if mots else message.strip()


def _tronquer_historique(historique: list) -> list:
    """Garde uniquement les N derniers messages pour respecter les limites GenAI."""
    if len(historique) > MAX_HISTORY_GENAI:
        return historique[-MAX_HISTORY_GENAI:]
    return list(historique)


def _valider_message(message) -> tuple:
    """Valide et nettoie le message utilisateur.

    Returns (message_nettoyé, erreur_Response_ou_None).
    """
    if not message or not isinstance(message, str) or not message.strip():
        return None, Response(
            {"error": "Message vide."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    message = message.strip()
    if len(message) > MAX_MESSAGE_LENGTH:
        return None, Response(
            {"error": f"Message trop long (max {MAX_MESSAGE_LENGTH} caractères)."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return message, None


def _valider_historique(historique) -> list:
    """Valide et nettoie l'historique envoyé par le client.

    Filtre les entrées malformées et limite la taille.
    """
    if not isinstance(historique, list):
        return []
    propre = []
    for entry in historique[-MAX_HISTORY_GENAI:]:
        if (
            isinstance(entry, dict)
            and entry.get("role") in ("user", "model")
            and isinstance(entry.get("parts"), list)
        ):
            propre.append(entry)
    return propre


def _recherche_floue_produit(terme: str, seuil: float = _FUZZY_THRESHOLD):
    """Recherche les produits dont le nom est proche du terme (tolérant aux fautes).

    Utilise SequenceMatcher pour calculer la similarité entre le terme cherché
    et chaque nom de produit actif en base.
    """
    terme_lower = terme.lower()
    produits = Produit.objects.filter(is_active=True).only(
        "nom_produit", "identifiant_produit"
    )
    correspondances = []
    for p in produits:
        nom = p.nom_produit.lower()
        # Similarité sur le nom complet
        ratio = SequenceMatcher(None, terme_lower, nom).ratio()
        if ratio >= seuil:
            correspondances.append((p, ratio))
            continue
        # Similarité sur chaque mot du nom
        for mot in nom.split():
            if SequenceMatcher(None, terme_lower, mot).ratio() >= seuil:
                correspondances.append((p, ratio))
                break
    correspondances.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in correspondances[:5]]


def est_hors_sujet(message: str) -> bool:
    """Retourne True si le message semble hors du scope AfriCart."""
    texte = message.lower()
    return any(topic in texte for topic in _FORBIDDEN_TOPICS)


def verifier_stock_et_prix(nom_produit: str):
    """Recherche par mot-clé extrait et retourne prix, description et stock."""
    mot_cle = _extraire_mot_cle_produit(nom_produit)
    produits = Produit.objects.filter(nom_produit__icontains=mot_cle, is_active=True)[
        :5
    ]

    # Si rien trouvé avec la phrase complète, essayer mot par mot
    if not produits and " " in mot_cle:
        for mot in mot_cle.split():
            produits = Produit.objects.filter(
                nom_produit__icontains=mot, is_active=True
            )[:5]
            if produits:
                break

    # Fallback : recherche floue (tolérant aux fautes de frappe)
    if not produits:
        produits_flous = _recherche_floue_produit(mot_cle)
        if produits_flous:
            produits = produits_flous

    if not produits:
        return {
            "reply": f"Aucun produit trouvé pour '{mot_cle}'. Essayez avec un autre terme.",
            "data": None,
        }

    produits_data = []
    for p in produits:
        prix = float(
            p.prix_promo_produit if p.prix_promo_produit else p.prix_unitaire_produit
        )
        produits_data.append(
            {
                "nom_produit": p.nom_produit,
                "prix": prix,
                "quantite_disponible": p.quantite_produit_disponible,
                "description": p.description_produit,
            }
        )

    premier = produits[0]
    dispo = (
        "En stock" if premier.quantite_produit_disponible > 0 else "Rupture de stock"
    )
    prix_texte = int(
        premier.prix_promo_produit
        if premier.prix_promo_produit
        else premier.prix_unitaire_produit
    )
    reponse = (
        f"J'ai trouvé {len(produits_data)} produit(s). "
        f"Exemple : {premier.nom_produit} — {prix_texte} FCFA — {dispo}."
    )
    return {"reply": reponse, "data": {"produits": produits_data}}


def detecter_intention(message: str) -> str:
    """Détecte l'intention principale du message utilisateur."""
    texte = message.lower()

    # Recherche produit
    if any(
        k in texte
        for k in [
            "prix",
            "combien",
            "coûte",
            "coute",
            "trouver",
            "cher",
            "produit",
            "recherche",
            "disponible",
            "stock",
        ]
    ):
        return "recherche_produit"

    # Détail d'un produit spécifique
    if any(
        k in texte
        for k in [
            "détail",
            "detail",
            "description",
            "caractéristique",
            "fiche produit",
            "info produit",
            "informations sur",
        ]
    ):
        return "details_produit"

    # Recherche par catégorie
    if any(
        k in texte
        for k in [
            "catégorie",
            "categorie",
            "rayon",
            "type de produit",
            "produits de type",
            "dans la catégorie",
            "dans la categorie",
        ]
    ):
        return "recherche_categorie"

    # Recommandations
    if any(
        k in texte
        for k in [
            "recommand",
            "suggér",
            "sugger",
            "similaire",
            "comme ça",
            "comparable",
            "propose-moi",
            "proposez-moi",
            "idée",
            "quoi acheter",
            "meilleur",
            "populaire",
            "tendance",
        ]
    ):
        return "recommandations"

    # Promotions en cours
    if any(
        k in texte
        for k in [
            "promo",
            "promotion",
            "réduction",
            "soldes",
            "offre spéciale",
            "remise",
            "en promo",
            "prix réduit",
            "bonnes affaires",
        ]
    ):
        return "promotions_en_cours"

    # Lister les produits / catalogue
    if any(
        k in texte
        for k in [
            "liste",
            "lister",
            "tous les produits",
            "voir les produits",
            "afficher les produits",
        ]
    ):
        return "liste_produits"

    # Catalogue / offres
    if any(
        k in texte
        for k in [
            "que vendez",
            "qu'est ce que vous vendez",
            "qu'est-ce que vous vendez",
            "ce que vous vendez",
            "nos produits",
            "nos offres",
            "que proposez",
            "quelles sont vos offres",
            "catalogue",
            "services",
            "propositions",
            "offres",
        ]
    ):
        return "presentation_offres"

    # Mes commandes
    if any(
        k in texte
        for k in [
            "mes commandes",
            "mes achats",
            "historique",
            "mes commandes en cours",
            "mes commandes récentes",
        ]
    ):
        return "mes_commandes"

    # Profil utilisateur
    if any(
        k in texte
        for k in [
            "mon profil",
            "mon compte",
            "mes informations",
            "mes coordonnées",
            "modifier profil",
        ]
    ):
        return "profil_utilisateur"

    # Frais de livraison
    if any(
        k in texte
        for k in [
            "frais de livraison",
            "frais",
            "tarif",
            "tarifs",
            "coût livraison",
            "prix livraison",
            "prix de livraison",
        ]
    ):
        return "frais_livraison"

    # Zones de livraison
    if any(
        k in texte
        for k in [
            "lieu",
            "lieux",
            "localité",
            "localités",
            "ville",
            "villes",
            "adresse",
            "adresses",
            "point de retrait",
            "point de livraison",
            "dépôt",
        ]
    ):
        return "zones_livraison"

    # Livraison (générique)
    if any(
        k in texte
        for k in [
            "livraison",
            "livrer",
            "livrés",
            "délai",
            "délais",
        ]
    ):
        return "infos_livraison"

    # Statut de commande
    if any(
        k in texte
        for k in [
            "statut",
            "suivi",
            "retard",
            "annulée",
            "annule",
            "id commande",
            "référence",
            "référence commande",
            "suivre ma commande",
            "commande",
        ]
    ):
        # Si l'utilisateur demande les détails (articles) d'une commande
        if any(
            k in texte for k in ["détail", "detail", "article", "contenu", "quoi dans"]
        ):
            return "details_commande"
        return "statut_commande"

    # Paiement
    if any(
        k in texte
        for k in [
            "paiement",
            "payer",
            "carte",
            "mobile money",
            "momo",
            "télépaiement",
            "transaction",
        ]
    ):
        return "infos_paiement"

    # Comment commander
    if any(
        k in texte
        for k in [
            "comment commander",
            "comment passer une commande",
            "passer commande",
            "comment acheter",
            "parcours",
            "procédure de commande",
            "comment ça marche",
        ]
    ):
        return "parcours_commande"

    # Salutations / aide
    if any(
        k in texte
        for k in [
            "bonjour",
            "salut",
            "bonsoir",
            "hello",
            "aide",
            "s'il vous plaît",
            "svp",
        ]
    ):
        return "salutation"

    return "inconnu"


# FAQ locale
_FAQ_LOCAL = {
    "horaires": "Nous sommes disponibles 7j/7 de 6h à 22h pour la prise de commandes.",
    "retours": (
        "Vous pouvez retourner un produit dans les 7 jours suivant la réception "
        "si l'article est défectueux. Contactez le support via le numéro 07 11 39 95 67."
    ),
    "moyens_de_paiement": (
        "Nous acceptons les paiements à la livraison pour le moment. "
        "Les frais de livraison varient selon les zones."
    ),
}


def repondre_selon_intention(utilisateur, intention, message):
    """Route la requête vers un outil local selon l'intention détectée.

    Retourne None si l'intention n'est pas traitable localement.
    """
    if intention == "recherche_produit":
        return verifier_stock_et_prix(message)

    if intention == "details_produit":
        return obtenir_details_produit(message)

    if intention == "liste_produits":
        return lister_produits(message)

    if intention == "presentation_offres":
        return lister_produits(None, limite=20)

    if intention == "statut_commande":
        if not utilisateur or not getattr(utilisateur, "is_authenticated", False):
            return {
                "reply": (
                    "Pour consulter le statut d'une commande, veuillez vous "
                    "connecter ou fournir la référence (ex: AfriCart-C-20260307-001)."
                ),
                "data": None,
            }
        m = re.search(r"afr?icart[-_]?[cC]?[- ]?\w+", message, re.IGNORECASE)
        if m:
            ref = m.group(0)
            try:
                commande = Commande.objects.filter(
                    identifiant_commande__icontains=ref
                ).first()
                if commande:
                    data = {
                        "identifiant": commande.identifiant_commande,
                        "etat": commande.etat_commande,
                        "total_ttc": (
                            float(commande.total_ttc)
                            if commande.total_ttc is not None
                            else None
                        ),
                        "date": (
                            str(commande.date_commande)
                            if commande.date_commande
                            else None
                        ),
                    }
                    reply = (
                        f"Commande {commande.identifiant_commande} : "
                        f"état = {commande.etat_commande}, "
                        f"total = {data.get('total_ttc')} FCFA."
                    )
                    return {
                        "reply": reply,
                        "data": {"commande": data},
                        "audience": "auth",
                    }
                return {
                    "reply": "Référence non trouvée. Vérifiez la référence ou contactez le support.",
                    "data": None,
                }
            except Exception:
                logger.exception("Erreur recherche commande ref=%s", ref)
                return {
                    "reply": "Erreur lors de la recherche de la commande. Réessayez plus tard.",
                    "data": None,
                }
        return {
            "reply": (
                "Merci de fournir la référence de commande "
                "(ex: AfriCart-C-20260307-001) pour vérifier le statut."
            ),
            "data": None,
            "audience": "auth",
        }

    if intention == "mes_commandes":
        if not utilisateur or not getattr(utilisateur, "is_authenticated", False):
            return {
                "reply": "Pour consulter vos commandes, veuillez vous connecter.",
                "data": None,
            }
        try:
            commandes = Commande.objects.filter(utilisateur=utilisateur).order_by(
                "-date_commande"
            )[:5]
            if not commandes:
                return {
                    "reply": "Vous n'avez pas de commandes récentes.",
                    "data": {"commandes": []},
                }
            items = [
                {
                    "identifiant": c.identifiant_commande,
                    "etat": c.etat_commande,
                    "total_ttc": (
                        float(c.total_ttc) if c.total_ttc is not None else None
                    ),
                    "date": str(c.date_commande) if c.date_commande else None,
                }
                for c in commandes
            ]
            return {
                "reply": f"Voici vos {len(items)} dernière(s) commande(s).",
                "data": {"commandes": items},
                "audience": "auth",
            }
        except Exception:
            logger.exception("Erreur récupération commandes pour %s", utilisateur)
            return {
                "reply": "Erreur lors de la récupération de vos commandes. Réessayez plus tard.",
                "data": None,
            }

    if intention == "infos_livraison":
        return obtenir_zones_livraison()

    if intention == "zones_livraison":
        return obtenir_zones_livraison()

    if intention == "frais_livraison":
        return obtenir_frais_livraison_par_ville(message)

    if intention == "recherche_categorie":
        return rechercher_par_categorie(message)

    if intention == "recommandations":
        return obtenir_recommandations(utilisateur, message)

    if intention == "promotions_en_cours":
        return obtenir_promotions_en_cours()

    if intention == "details_commande":
        return obtenir_details_commande(utilisateur, message)

    if intention == "infos_paiement":
        return {
            "reply": _FAQ_LOCAL["moyens_de_paiement"],
            "data": {"faq": "moyens_de_paiement"},
        }

    if intention == "salutation":
        return {
            "reply": (
                "Bonjour ! Je suis l'assistant AfriCart — "
                "comment puis-je vous aider pour vos achats aujourd'hui ?"
            ),
            "data": None,
        }

    if intention == "parcours_commande":
        return {
            "reply": (
                "Pour passer une commande :\n"
                "1) Connectez-vous à votre compte\n"
                "2) Ajoutez des produits au panier\n"
                "3) Passez à la caisse\n"
                "4) Sélectionnez le lieu de livraison\n"
                "5) Choisissez le mode de paiement\n"
                "6) Confirmez la commande"
            ),
        }

    if intention == "profil_utilisateur":
        return obtenir_profil_utilisateur(utilisateur)

    return None


def _normaliser_reponse_locale(resp):
    """Normalise la réponse d'un outil local.

    Retour: tuple (reply_text, data_or_None)
    """
    if resp is None:
        return (MESSAGE_INDISPONIBLE, None)

    if isinstance(resp, dict):
        if "error" in resp:
            return (MESSAGE_INDISPONIBLE, None)

        data = resp.get("data")
        reply = resp.get("reply", "")

        if data is None:
            return (reply or MESSAGE_INDISPONIBLE, None)

        if isinstance(data, dict) and not any(data.values()):
            return (MESSAGE_INDISPONIBLE, None)

        if isinstance(data, list) and len(data) == 0:
            return (MESSAGE_INDISPONIBLE, None)

        return (reply, data)

    return (str(resp), None)


def obtenir_details_produit(nom_produit: str):
    """Retourne des informations détaillées sur les produits correspondants."""
    mot_cle = _extraire_mot_cle_produit(nom_produit)
    produits_qs = Produit.objects.filter(
        nom_produit__icontains=mot_cle, is_active=True
    )[:10]

    # Fallback mot par mot
    if not produits_qs and " " in mot_cle:
        for mot in mot_cle.split():
            produits_qs = Produit.objects.filter(
                nom_produit__icontains=mot, is_active=True
            )[:10]
            if produits_qs:
                break

    if not produits_qs:
        return {"error": f"Aucun produit trouvé pour '{mot_cle}'."}

    produits = []
    for p in produits_qs:
        produits.append(
            {
                "nom_produit": p.nom_produit,
                "identifiant": str(p.identifiant_produit),
                "prix_unitaire": float(p.prix_unitaire_produit),
                "prix_promo": (
                    float(p.prix_promo_produit) if p.prix_promo_produit else None
                ),
                "quantite_disponible": p.quantite_produit_disponible,
                "seuil_alerte": p.seuil_alerte_produit,
                "description": p.description_produit,
                "categorie": (
                    p.categorie_produit.nom_categorie if p.categorie_produit else None
                ),
                "thumbnail": p.thumbnail,
            }
        )

    reponse_texte = (
        f"J'ai trouvé {len(produits)} produit(s) correspondant à '{mot_cle}'."
    )
    return {"reply": reponse_texte, "data": {"produits": produits}}


def lister_produits(texte_filtre: str = None, limite: int = 20):
    """Retourne une liste sommaire de produits (optionnellement filtrée)."""
    qs = Produit.objects.filter(is_active=True)
    if texte_filtre:
        mot_cle = _extraire_mot_cle_produit(texte_filtre)
        qs = qs.filter(nom_produit__icontains=mot_cle)
    qs = qs[:limite]

    resultat = [
        {
            "nom_produit": p.nom_produit,
            "prix": float(
                p.prix_promo_produit
                if p.prix_promo_produit
                else p.prix_unitaire_produit
            ),
            "quantite_disponible": p.quantite_produit_disponible,
        }
        for p in qs
    ]

    return {
        "reply": f"Liste de {len(resultat)} produit(s).",
        "data": {"produits": resultat},
    }


def obtenir_zones_livraison():
    """Retourne les zones de livraison actives pour AfriCart.

    Règle stricte : AfriCart livre actuellement uniquement à Yamoussoukro.
    Cette fonction ne renvoie que les zones stockées dans la table `ZoneLivraison`
    correspondant à Yamoussoukro. Aucun calcul heuristique ou fallback n'est utilisé.
    """
    # Ne considérer que les zones explicitement liées à Yamoussoukro
    zones_y = ZoneLivraison.objects.filter(nom_zone__icontains="yamoussoukro")
    # Si aucune zone détaillée n'existe en base, renvoyer Yamoussoukro comme lieu
    # de livraison par défaut (sans inventer de frais).
    if not zones_y:
        data = [
            {
                "nom_zone": "Yamoussoukro",
                "frais_livraison": None,
            }
        ]
        reponse_texte = "AfriCart livre actuellement uniquement à Yamoussoukro. Les frais de livraison commencent à partir de 500 FCFA."
        return {"reply": reponse_texte}

    data = [
        {
            "nom_zone": z.nom_zone,
            "frais_livraison": float(z.frais_livraison),
            "rayon_metres": z.rayon_metres,
            "latitude": z.latitude,
            "longitude": z.longitude,
        }
        for z in zones_y
    ]

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
        return {
            "error": "Précisez la localité (ex: Yamoussoukro) pour obtenir les frais."
        }

    texte = ville.strip().lower()

    # Si l'utilisateur ne mentionne pas Yamoussoukro, indiquer clairement la limitation
    if "yamoussoukro" not in texte:
        return {
            "reply": "AfriCart livre actuellement uniquement à Yamoussoukro. Les frais de livraison commencent à partir de 500 FCFA.",
        }

    # Rechercher les zones Yamoussoukro en base
    zone = ZoneLivraison.objects.filter(nom_zone__icontains="yamoussoukro").first()
    if not zone:
        # Si aucune zone détaillée n'est configurée, indiquer Yamoussoukro comme lieu
        # de livraison par défaut, sans fournir de montant estimé.
        return {
            "reply": "AfriCart livre à Yamoussoukro. Les frais de livraison commencent à partir de 500 FCFA.",
            "data": {
                "nom_zone": "Yamoussoukro",
                "frais_livraison": None,
                "frais_min": 500,
            },
        }

    reponse_texte = f"Zone '{zone.nom_zone}' — frais de livraison : {float(zone.frais_livraison)} FCFA."
    return {
        "reply": reponse_texte,
        "data": {
            "nom_zone": zone.nom_zone,
            "frais_livraison": float(zone.frais_livraison),
        },
    }


def obtenir_profil_utilisateur(utilisateur):
    """Retourne les informations publiques du profil utilisateur connecté."""
    if not utilisateur or not getattr(utilisateur, "is_authenticated", False):
        return {"error": "Utilisateur non authentifié."}

    try:
        profil = {
            "identifiant_utilisateur": str(
                getattr(utilisateur, "identifiant_utilisateur", "")
            ),
            "nom_utilisateur": getattr(utilisateur, "nom_utilisateur", None),
            "email_utilisateur": getattr(utilisateur, "email_utilisateur", None),
            "numero_telephone": getattr(
                utilisateur, "numero_telephone_utilisateur", None
            ),
            "role": getattr(utilisateur, "role", None),
            "photo_profil": getattr(utilisateur, "thumbnail", None)
            or getattr(utilisateur, "photo_profil_utilisateur", None),
            "date_creation": getattr(utilisateur, "date_creation", None),
        }
        reponse_texte = f"Profil de {profil.get('nom_utilisateur') or 'utilisateur'} : rôle={profil.get('role')}"
        return {"reply": reponse_texte, "data": {"profil": profil}}
    except Exception:
        logger.exception("Erreur récupération profil pour %s", utilisateur)
        return {"error": "Impossible de récupérer le profil."}


def rechercher_par_categorie(message: str):
    """Recherche les produits d'une catégorie donnée."""
    mot_cle = _extraire_mot_cle_produit(message)

    # Trouver la catégorie correspondante
    categorie = Categorie.objects.filter(nom_categorie__icontains=mot_cle).first()
    if not categorie and " " in mot_cle:
        for mot in mot_cle.split():
            categorie = Categorie.objects.filter(nom_categorie__icontains=mot).first()
            if categorie:
                break

    # Si toujours pas trouvé, lister les catégories disponibles
    if not categorie:
        categories = list(
            Categorie.objects.values_list("nom_categorie", flat=True)[:20]
        )
        if categories:
            noms = ", ".join(categories)
            return {
                "reply": f"Catégorie introuvable. Catégories disponibles : {noms}.",
                "data": {"categories_disponibles": categories},
            }
        return {"reply": "Aucune catégorie disponible pour le moment.", "data": None}

    produits = Produit.objects.filter(categorie_produit=categorie, is_active=True)[:15]
    if not produits:
        return {
            "reply": f"Aucun produit actif dans la catégorie '{categorie.nom_categorie}'.",
            "data": None,
        }

    items = [
        {
            "nom_produit": p.nom_produit,
            "prix": float(
                p.prix_promo_produit
                if p.prix_promo_produit
                else p.prix_unitaire_produit
            ),
            "quantite_disponible": p.quantite_produit_disponible,
            "thumbnail": p.thumbnail,
        }
        for p in produits
    ]

    return {
        "reply": f"{len(items)} produit(s) dans la catégorie '{categorie.nom_categorie}'.",
        "data": {"categorie": categorie.nom_categorie, "produits": items},
    }


def obtenir_recommandations(utilisateur, message: str):
    """Renvoie des recommandations de produits.

    Stratégie :
    1. Si l'utilisateur est connecté → recommandations basées sur ses vues récentes
    2. Sinon → meilleures ventes (best_sellers) globales
    3. Si un nom de produit est mentionné → produits similaires par catégorie
    """
    mot_cle = _extraire_mot_cle_produit(message)

    # Recommandations liées à un produit mentionné
    produit_mentionne = Produit.objects.filter(
        nom_produit__icontains=mot_cle, is_active=True
    ).first()

    if produit_mentionne:
        # Recommandations stockées en BDD pour ce produit
        recos = (
            Recommandation.objects.filter(
                produit_source=produit_mentionne,
                produit_recommande__is_active=True,
            )
            .select_related("produit_recommande")
            .order_by("-score")[:5]
        )

        if recos:
            items = [
                {
                    "nom_produit": r.produit_recommande.nom_produit,
                    "prix": float(
                        r.produit_recommande.prix_promo_produit
                        if r.produit_recommande.prix_promo_produit
                        else r.produit_recommande.prix_unitaire_produit
                    ),
                    "type_recommandation": r.type_recommandation,
                    "score": r.score,
                }
                for r in recos
            ]
            return {
                "reply": f"Voici {len(items)} produit(s) recommandé(s) en rapport avec '{produit_mentionne.nom_produit}'.",
                "data": {"recommandations": items},
            }

        # Fallback : produits de la même catégorie
        meme_cat = Produit.objects.filter(
            categorie_produit=produit_mentionne.categorie_produit,
            is_active=True,
        ).exclude(pk=produit_mentionne.pk)[:5]
        if meme_cat:
            items = [
                {
                    "nom_produit": p.nom_produit,
                    "prix": float(
                        p.prix_promo_produit
                        if p.prix_promo_produit
                        else p.prix_unitaire_produit
                    ),
                }
                for p in meme_cat
            ]
            return {
                "reply": f"Produits similaires dans la catégorie '{produit_mentionne.categorie_produit}'.",
                "data": {"recommandations": items},
            }

    # Recommandations personnalisées basées sur les vues récentes
    if utilisateur and getattr(utilisateur, "is_authenticated", False):
        vues_recentes = (
            VueProduit.objects.filter(
                utilisateur=utilisateur,
            )
            .select_related("produit__categorie_produit")
            .order_by("-timestamp")[:10]
        )

        categories_vues = set()
        for v in vues_recentes:
            if v.produit and v.produit.categorie_produit:
                categories_vues.add(v.produit.categorie_produit_id)

        if categories_vues:
            produits_perso = Produit.objects.filter(
                categorie_produit_id__in=categories_vues,
                is_active=True,
            ).order_by("-date_creation")[:5]
            if produits_perso:
                items = [
                    {
                        "nom_produit": p.nom_produit,
                        "prix": float(
                            p.prix_promo_produit
                            if p.prix_promo_produit
                            else p.prix_unitaire_produit
                        ),
                        "categorie": (
                            p.categorie_produit.nom_categorie
                            if p.categorie_produit
                            else None
                        ),
                    }
                    for p in produits_perso
                ]
                return {
                    "reply": f"Voici {len(items)} suggestion(s) basées sur vos consultations récentes.",
                    "data": {"recommandations": items},
                }

    # Fallback global : best_sellers
    best = (
        Recommandation.objects.filter(
            type_recommandation="best_sellers",
            produit_recommande__is_active=True,
        )
        .select_related("produit_recommande")
        .order_by("-score")[:5]
    )
    if best:
        items = [
            {
                "nom_produit": r.produit_recommande.nom_produit,
                "prix": float(
                    r.produit_recommande.prix_promo_produit
                    if r.produit_recommande.prix_promo_produit
                    else r.produit_recommande.prix_unitaire_produit
                ),
            }
            for r in best
        ]
        return {
            "reply": f"Voici les {len(items)} produit(s) les plus populaires.",
            "data": {"recommandations": items},
        }

    return {"reply": "Aucune recommandation disponible pour le moment.", "data": None}


def obtenir_promotions_en_cours():
    """Renvoie les produits actuellement en promotion."""
    from django.db.models import Q

    promos = Produit.objects.filter(
        Q(prix_promo_produit__isnull=False, prix_promo_produit__gt=0)
        | Q(pourcentage_promo__gt=0),
        is_active=True,
    ).select_related("categorie_produit")[:15]

    if not promos:
        return {"reply": "Aucune promotion en cours pour le moment.", "data": None}

    items = []
    for p in promos:
        prix_normal = float(p.prix_unitaire_produit)
        prix_promo = float(p.prix_promo_produit) if p.prix_promo_produit else None
        pourcentage = float(p.pourcentage_promo) if p.pourcentage_promo else None
        economie = None
        if prix_promo and prix_normal > prix_promo:
            economie = round(prix_normal - prix_promo)

        items.append(
            {
                "nom_produit": p.nom_produit,
                "prix_normal": prix_normal,
                "prix_promo": prix_promo,
                "pourcentage_promo": pourcentage,
                "economie_fcfa": economie,
                "categorie": (
                    p.categorie_produit.nom_categorie if p.categorie_produit else None
                ),
                "thumbnail": p.thumbnail,
            }
        )

    return {
        "reply": f"🎉 {len(items)} produit(s) en promotion actuellement !",
        "data": {"promotions": items},
    }


def obtenir_details_commande(utilisateur, message: str):
    """Retourne les articles d'une commande spécifique."""
    if not utilisateur or not getattr(utilisateur, "is_authenticated", False):
        return {
            "reply": "Connectez-vous pour consulter le détail de vos commandes.",
            "data": None,
        }

    # Essayer d'extraire la référence
    m = re.search(r"afr?icart[-_]?[cC]?[- ]?\w+", message, re.IGNORECASE)
    if m:
        ref = m.group(0)
        commande = Commande.objects.filter(
            identifiant_commande__icontains=ref,
            utilisateur=utilisateur,
        ).first()
    else:
        # Prendre la dernière commande par défaut
        commande = (
            Commande.objects.filter(utilisateur=utilisateur)
            .order_by("-date_commande")
            .first()
        )

    if not commande:
        return {"reply": "Aucune commande trouvée.", "data": None}

    details = DetailCommande.objects.filter(commande=commande).select_related("produit")

    articles = [
        {
            "produit": d.produit.nom_produit,
            "quantite": d.quantite,
            "prix_unitaire": float(d.prix_unitaire),
            "sous_total": float(d.sous_total),
        }
        for d in details
    ]

    data = {
        "identifiant": commande.identifiant_commande,
        "etat": commande.etat_commande,
        "date": str(commande.date_commande) if commande.date_commande else None,
        "total_ht": float(commande.total_ht) if commande.total_ht else None,
        "frais_livraison": (
            float(commande.frais_livraison_appliques)
            if commande.frais_livraison_appliques
            else None
        ),
        "total_ttc": float(commande.total_ttc) if commande.total_ttc else None,
        "articles": articles,
    }

    reply = (
        f"Commande {commande.identifiant_commande} — {len(articles)} article(s), "
        f"état : {commande.etat_commande}, total : {data['total_ttc']} FCFA."
    )
    return {"reply": reply, "data": {"commande_details": data}, "audience": "auth"}


# =============================================================================
#  LOGIQUE COMMUNE (supprime la duplication chatbot / chatbot_user_connected)
# =============================================================================


def _traiter_message(utilisateur, message, historique, est_authentifie=False):
    """Traite un message chatbot et retourne (payload_dict, http_status).

    Centralise la logique partagée entre les endpoints public et authentifié.
    """
    # 1. Filtrage hors-sujet
    if est_hors_sujet(message):
        reply = (
            "Désolé, je ne peux répondre qu'aux questions concernant AfriCart. "
            + CONTACT_MESSAGE
        )
        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message}]},
            {"role": "model", "parts": [{"text": reply}]},
        ]
        return {"reply": reply, "history": nouvel_historique}, status.HTTP_200_OK

    # 2. Détection d'intention + réponse locale prioritaire
    intention = detecter_intention(message)
    reponse_locale = repondre_selon_intention(
        utilisateur if est_authentifie else None,
        intention,
        message,
    )

    if reponse_locale is not None:
        audience = (
            reponse_locale.get("audience", "all")
            if isinstance(reponse_locale, dict)
            else "all"
        )

        # Bloquer les réponses "auth" pour les non-connectés
        if audience == "auth" and not est_authentifie:
            reply = (
                "Cette information est réservée aux utilisateurs connectés. "
                "Veuillez vous connecter pour y accéder."
            )
            nouvel_historique = historique + [
                {"role": "user", "parts": [{"text": message}]},
                {"role": "model", "parts": [{"text": reply}]},
            ]
            return {"reply": reply, "history": nouvel_historique}, status.HTTP_200_OK

        reply_text, data = _normaliser_reponse_locale(reponse_locale)
        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message}]},
            {"role": "model", "parts": [{"text": reply_text}]},
        ]
        payload = {"reply": reply_text, "history": nouvel_historique}
        if data is not None:
            payload["data"] = data
        return payload, status.HTTP_200_OK

    # 3. Intentions DB-only sans résultat : refuser poliment
    if intention in _INTENTS_DB_ONLY:
        reply = MESSAGE_INDISPONIBLE
        if est_authentifie:
            reply += " " + CONTACT_MESSAGE
        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message}]},
            {"role": "model", "parts": [{"text": reply}]},
        ]
        return {"reply": reply, "history": nouvel_historique}, status.HTTP_200_OK

    # 4. Fallback GenAI (avec instruction système stricte et config unifiée)
    try:
        historique_tronque = _tronquer_historique(historique)
        chat = client_genai.chats.create(
            model=MODEL_GENAI,
            history=historique_tronque,
            config={
                "system_instruction": SYSTEM_INSTRUCTION,
                "temperature": 0.2,
                "tools": [verifier_stock_et_prix],
            },
        )
        message_reponse = chat.send_message(message)
        reply = message_reponse.text

        nouvel_historique = historique + [
            {"role": "user", "parts": [{"text": message}]},
            {"role": "model", "parts": [{"text": reply}]},
        ]
        return {"reply": reply, "history": nouvel_historique}, status.HTTP_200_OK

    except Exception:
        logger.exception("Erreur GenAI pour message='%s'", message[:100])
        reply = f"Une erreur est survenue. {CONTACT_MESSAGE}"
        return {"reply": reply}, status.HTTP_500_INTERNAL_SERVER_ERROR


# =============================================================================
#  ENDPOINTS
# =============================================================================


@api_view(["POST"])
@permission_classes([AllowAny])
def chatbot(request):
    """Point d'entrée public pour le chatbot AfriCart."""
    message, err = _valider_message(request.data.get("message"))
    if err:
        return err

    historique = _valider_historique(request.data.get("history", []))

    payload, http_status = _traiter_message(
        utilisateur=None,
        message=message,
        historique=historique,
        est_authentifie=False,
    )
    return Response(payload, status=http_status)


@api_view(["POST", "GET", "DELETE"])
@permission_classes([IsAuthenticated])
def chatbot_user_connected(request):
    """Point d'entrée authentifié avec persistance en BDD."""
    utilisateur = request.user

    # GET : retourner l'historique récent depuis la BDD
    if request.method == "GET":
        messages = chatMessage.objects.filter(utilisateur=utilisateur).order_by(
            "timestamp"
        )[:50]
        historique = [
            {"role": m.role, "parts": [{"text": m.message}]} for m in messages
        ]
        return Response({"history": historique}, status=status.HTTP_200_OK)

    # DELETE : effacer l'historique de conversation
    if request.method == "DELETE":
        count, _ = chatMessage.objects.filter(utilisateur=utilisateur).delete()
        return Response(
            {"message": f"{count} message(s) supprimé(s)."},
            status=status.HTTP_200_OK,
        )

    # POST : traiter le nouveau message
    message, err = _valider_message(request.data.get("message"))
    if err:
        return err

    # Reconstruire l'historique depuis la BDD (plus fiable que celui du client)
    messages_db = list(
        chatMessage.objects.filter(utilisateur=utilisateur).order_by("-timestamp")[
            :MAX_HISTORY_GENAI
        ]
    )
    messages_db.reverse()
    historique = [{"role": m.role, "parts": [{"text": m.message}]} for m in messages_db]

    payload, http_status = _traiter_message(
        utilisateur=utilisateur,
        message=message,
        historique=historique,
        est_authentifie=True,
    )

    # Sauvegarder l'échange en BDD
    reply_text = payload.get("reply", "")
    chatMessage.objects.create(utilisateur=utilisateur, role="user", message=message)
    chatMessage.objects.create(
        utilisateur=utilisateur, role="model", message=reply_text
    )

    return Response(payload, status=http_status)
