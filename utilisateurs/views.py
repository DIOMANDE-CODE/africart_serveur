from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

from .models import Utilisateur
from .serializers import UtilisateurSerializer
from django.views.decorators.csrf import csrf_exempt
from clients.models import Client
from rest_framework.permissions import IsAuthenticated
from permissions import EstAdministrateur, EstGerant
import re


# Create your views here.
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def info_utilisateur(request):
    if not request.user.is_authenticated:
        return Response(
            {"success": False, "errors": "Utilisateur non authentifié"},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    serializer = UtilisateurSerializer(request.user)
    return Response(
        {
            "success": True,
            "message": "Utilisateur authentifié",
            "data": serializer.data,
        },
        status=status.HTTP_200_OK,
    )


# Fonction pour lister les utilisateurs


@api_view(["GET"])
@permission_classes([EstAdministrateur | EstGerant])
def list_utilisateur(request):
    try:
        user = Utilisateur.objects.all().filter(is_active=True)
        serializer = UtilisateurSerializer(user, many=True)
        return Response(
            {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


# Fonction de creation d'un utilisateur


@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def create_utilisateur(request):
    nom = request.data.get("nom_utilisateur")
    email = request.data.get("email_utilisateur")
    numero = request.data.get("numero_telephone_utilisateur")
    password = request.data.get("password")
    role = request.data.get("role")

    # Verifier le mot de passe respecte les critères de sécurité
    if len(password) < 6:
        return Response(
            {
                "success": False,
                "errors": "Le mot de passe doit contenir au moins 6 caractères.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not re.search(r"[A-Z]", password):
        return Response(
            {
                "success": False,
                "errors": "Le mot de passe doit contenir au moins une lettre majuscule.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not re.search(r"[a-z]", password):
        return Response(
            {
                "success": False,
                "errors": "Le mot de passe doit contenir au moins une lettre minuscule.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if not re.search(r"\d", password):
        return Response(
            {
                "success": False,
                "errors": "Le mot de passe doit contenir au moins un chiffre.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Verification liée à la création d'un compte client
    if role == "client":
        if not email or not nom or not password or not numero:
            return Response(
                {"success": False, "errors": "Tous les champs sont obligatoires"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verifier que l'email n'existe pas
        if Utilisateur.objects.filter(email_utilisateur=email).exists():
            return Response(
                {"success": False, "errors": "Cet compte existe dejà"},
                status=status.HTTP_409_CONFLICT,
            )

        # Verifier l'email
        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"success": False, "errors": "Email invalide"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verifier la validité du numéro
        if numero.isdigit():
            pattern = r"^(?:\+225|00225)?(01|05|07)\d{8}$"
            if not re.match(pattern, numero):
                return Response(
                    {
                        "success": False,
                        "errors": "Numéro invalide (respecter le format des numeros ivoiriens).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "success": False,
                    "errors": "Numéro invalide (respecter le format des numeros ivoiriens).",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Création du compte client
        try:
            serializer = UtilisateurSerializer(data=request.data)
            if serializer.is_valid():
                utilisateur = serializer.save()
                Client.objects.create(
                    utilisateur=utilisateur,
                    nom_client=nom,
                    email_client=email,
                    numero_telephone_client=numero,
                    role="client",
                )
                return Response(
                    {"success": True, "message": "Compte crée avec succès"},
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(Exception)
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne du serveur",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # Verification liée à la création d'un compte utilisateur (vendeur, gerant ou admin)
    else:
        if not request.user.is_authenticated:
            return Response(
                {
                    "success": False,
                    "errors": "Vous devez être connecté pour créer un compte utilisateur.",
                },
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Vérifier si l'utilisateur a le rôle requis (admin ou vendeur)
        if not (request.user.role == "admin" or request.user.role == "vendeur"):
            return Response(
                {
                    "success": False,
                    "errors": "Vous n'avez pas la permission de créer un compte utilisateur.",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Verifier email, numero et nom
        if not email or not numero or not nom or not password:
            return Response(
                {"success": False, "errors": "Tous les champs sont obligatoires"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {"success": False, "errors": "Email invalide"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verfier que l'utilisateur n'existe pas
        if Utilisateur.objects.filter(email_utilisateur=email).exists():
            return Response(
                {"success": False, "errors": "Cet utilisateur existe dejà"},
                status=status.HTTP_409_CONFLICT,
            )

        # Verifier que le numero n'existe pas
        if Utilisateur.objects.filter(numero_telephone_utilisateur=numero).exists():
            return Response(
                {"success": False, "errors": "Cet Numéro existe dejà"},
                status=status.HTTP_409_CONFLICT,
            )

        if numero.isdigit():
            pattern = r"^(?:\+225|00225)?(01|05|07)\d{8}$"
            if not re.match(pattern, numero):
                return Response(
                    {
                        "success": False,
                        "errors": "Numéro invalide (respecter le format des numeros ivoiriens).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {
                    "success": False,
                    "errors": "Numéro invalide (respecter le format des numeros ivoiriens).",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Création du compte utilisateur (vendeur, gerant ou admin)
        try:
            serializer = UtilisateurSerializer(data=request.data)
            if serializer.is_valid():
                utilisateur = serializer.save()
                return Response(
                    {"success": True, "message": "Compte crée avec succès"},
                    status=status.HTTP_201_CREATED,
                )
            return Response(
                {"success": False, "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            import traceback

            traceback.print_exc()
            print(Exception)
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne du serveur",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@api_view(["GET", "PUT"])
@permission_classes([IsAuthenticated])
def detail_utilisateur(request):
    user = request.user

    # 1. Sécurité : Vérification du compte actif
    if not user.is_active:
        return Response(
            {"success": False, "errors": "Ce compte est désactivé."},
            status=status.HTTP_403_FORBIDDEN,
        )

    # --- LOGIQUE : RÉCUPÉRATION (GET) ---
    if request.method == "GET":
        try:
            serializer = UtilisateurSerializer(user)
            return Response(
                {"success": True, "data": serializer.data}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {
                    "success": False,
                    "errors": "Erreur lors de la récupération des données.",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # --- LOGIQUE : MODIFICATION (PUT) ---
    if request.method == "PUT":
        nom = request.data.get("nom_utilisateur")
        email = request.data.get("email_utilisateur")
        numero = request.data.get("numero_telephone_utilisateur")
        role_data = request.data.get("role")
        ancien_code = request.data.get("ancien_code")
        nouveau_mdp = request.data.get("nouveau_code")

        # A. Validations préalables (Email & Téléphone)
        if email:
            try:
                validate_email(email)
            except ValidationError:
                return Response(
                    {"success": False, "errors": "Format d'email invalide"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if numero:
            # Format Côte d'Ivoire (10 chiffres)
            pattern = r"^(?:\+225|00225)?(01|05|07)\d{8}$"
            if not re.match(pattern, str(numero)):
                return Response(
                    {
                        "success": False,
                        "errors": "Numéro invalide (format ivoirien 10 chiffres requis).",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # B. BLOC SÉCURITÉ MOT DE PASSE (Protection contre le NoneType)
        # On n'exécute ces tests QUE si l'utilisateur a envoyé un nouveau code
        if nouveau_mdp:
            # 1. L'ancien code est obligatoire pour changer le mot de passe
            if not ancien_code:
                return Response(
                    {
                        "success": False,
                        "errors": "Veuillez saisir votre mot de passe actuel pour le modifier.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 2. Vérification de l'ancien mot de passe
            if not user.check_password(ancien_code):
                return Response(
                    {"success": False, "errors": "Mot de passe actuel incorrect"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 3. Comparaison nouveau/ancien
            if ancien_code == nouveau_mdp:
                return Response(
                    {
                        "success": False,
                        "errors": "Le nouveau mot de passe doit être différent du mot de passe actuel",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # 4. Critères de sécurité (re.search est maintenant sécurisé car nouveau_mdp != None)
            if len(nouveau_mdp) < 6:
                return Response(
                    {
                        "success": False,
                        "errors": "Le mot de passe doit contenir au moins 6 caractères.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not re.search(r"[A-Z]", nouveau_mdp):
                return Response(
                    {
                        "success": False,
                        "errors": "Le mot de passe doit contenir au moins une lettre majuscule.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not re.search(r"[a-z]", nouveau_mdp):
                return Response(
                    {
                        "success": False,
                        "errors": "Le mot de passe doit contenir au moins une lettre minuscule.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not re.search(r"\d", nouveau_mdp):
                return Response(
                    {
                        "success": False,
                        "errors": "Le mot de passe doit contenir au moins un chiffre.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # C. Mise à jour via le Serializer
        try:
            # On utilise request.user directement pour plus de sécurité
            serializer = UtilisateurSerializer(user, data=request.data, partial=True)
            if not serializer.is_valid():
                return Response(
                    {"success": False, "errors": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            utilisateur = serializer.save()

            # Enregistrement du nouveau mot de passe hashé si validé
            if nouveau_mdp:
                utilisateur.set_password(nouveau_mdp)
                utilisateur.save()

            # D. Logique spécifique selon le rôle
            if role_data == "client":
                from .models import (
                    Client,
                )  # Import local pour éviter les imports circulaires

                Client.objects.filter(utilisateur=utilisateur).update(
                    nom_client=nom or utilisateur.nom_utilisateur,
                    email_client=email or utilisateur.email_utilisateur,
                    numero_telephone_client=numero
                    or utilisateur.numero_telephone_utilisateur,
                )
                message_succes = "Profil client mis à jour avec succès"
            else:
                if user.role not in ["admin", "vendeur", "gerant"]:
                    return Response(
                        {"success": False, "errors": "Permissions insuffisantes."},
                        status=status.HTTP_403_FORBIDDEN,
                    )
                message_succes = "Profil personnel mis à jour avec succès"

            return Response(
                {"success": True, "data": serializer.data, "message": message_succes},
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {
                    "success": False,
                    "errors": "Erreur interne lors de la mise à jour",
                    "message": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    return Response(
        {"success": False, "errors": "Méthode non autorisée"},
        status=status.HTTP_405_METHOD_NOT_ALLOWED,
    )


# Requette DELETE
@api_view(["DELETE"])
@permission_classes([EstAdministrateur | EstGerant])
def delete_utilisateur(request, id):
    try:
        # Vérifier l'existence de l'utilisateur
        user = Utilisateur.objects.get(identifiant=id, is_active=True)
    except Utilisateur.DoesNotExist:
        return Response(
            {"success": False, "errors": "Cet utilisateur n'existe pas"},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        user.is_active = False
        user.save()

        return Response(
            {"success": True, "message": "Utilisateur supprimé avec succès"},
            status=status.HTTP_200_OK,
        )

    except Exception as e:
        return Response(
            {
                "success": False,
                "errors": "Erreur interne du serveur",
                "message": str(e),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
