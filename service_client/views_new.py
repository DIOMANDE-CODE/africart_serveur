import logging

from decouple import config
from google import genai

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
MESSAGE_INDISPONIBLE = (
    "D\u00e9sol\u00e9, l'information demand\u00e9e n'est pas encore disponible."
)

client_genai = genai.Client(api_key=config("GEMINI_API_KEY"))
