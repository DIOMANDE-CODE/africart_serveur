import jwt
from datetime import datetime, timedelta
from django.conf import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"

def generate_clients_token(client):
    payload_access = {
        "client_id":str(client.identifiant_client),
        "role":client.role,
        "exp":datetime.now() + timedelta(minutes=2),
        "type":"access"
    }

    payload_refresh = {
        "client_id":str(client.identifiant_client),
        "role":client.role,
        "exp":datetime.now() + timedelta(days=7),
        "type":"refresh"
    }

    access = jwt.encode(payload_access, SECRET_KEY, algorithm=ALGORITHM)
    refresh = jwt.encode(payload_refresh, SECRET_KEY, algorithm=ALGORITHM)
    
    return access, refresh

def decode_token(token):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None