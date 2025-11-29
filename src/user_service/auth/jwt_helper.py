import base64
from datetime import datetime, timedelta, timezone
import os
from authlib.jose import jwt, JoseError
from dotenv import load_dotenv

DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 

load_dotenv()

def get_private_key():
    try:
        b64_key = os.getenv("JWT_PRIVATE_KEY")
        if not b64_key:
            raise ValueError("JWT_PRIVATE_KEY is missing from environment")
        private_key_bytes = base64.b64decode(b64_key)
        return private_key_bytes

    except Exception as e:
        print(f"Error loading private key: {e}")
        raise

PRIVATE_KEY = get_private_key()

with open('./keys/public.pem', "rb") as f:
    PUBLIC_KEY = f.read()

def create_access_token(user_id: int, expiry: datetime) -> str:
    now_utc = datetime.now(timezone.utc)
    max_expiry_time_utc = now_utc + timedelta(minutes=DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES)

    if expiry < max_expiry_time_utc:
        final_expiry_time = expiry
    else:
        final_expiry_time = max_expiry_time_utc

    header = {'alg': 'RS256'}

    payload = {
        "sub": str(user_id), 
        "exp": int(final_expiry_time.timestamp()),
    }

    s = jwt.encode(header, payload, PRIVATE_KEY)

    if isinstance(s, bytes):
        s = s.decode("utf-8")
        
    return s

def validate_jwt(token: str):
    try:
        payload = jwt.decode(token, PUBLIC_KEY)
        payload.validate()
        return payload
    except JoseError:
        raise ValueError("Invalid or expired JWT")