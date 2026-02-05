from django.db import models
import uuid
from django.core.validators import RegexValidator
from utilisateurs.models import Utilisateur

# Create your models here.

# Définition de la photo de profil par defaut
def photo_profil_par_defaut():
    return 'https://res.cloudinary.com/darkqhocp/image/upload/v1770326117/Logo_moderne_d_AfriCart_en_couleurs_vives_kydtpd.png'

# Verification du numéro de l'utilisateur en conformité avec celui de la CI
verification_numero = RegexValidator(
    regex=r'^(?:\+225|00225)?(01|05|07|25|27)\d{8}$',
    message="Veuillez entrer un numéro ivoirien valide (ex: +2250102030405 ou 0102030405)."
)

# Creation du modèle client
class Client(models.Model):
    identifiant_client = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nom_client = models.CharField(max_length=150, blank=True, null=True, verbose_name="Nom client")
    numero_telephone_client = models.CharField(max_length=15, validators=[verification_numero],null=True, blank=True, verbose_name="Numero de téléphone")
    role = models.CharField(max_length=10, default="client", verbose_name="role client", editable=False, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now = True)

    def __str__(self):
        return self.nom_client
    

