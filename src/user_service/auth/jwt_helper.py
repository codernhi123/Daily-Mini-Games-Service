from datetime import datetime, timedelta, timezone
from authlib.jose import jwt, JoseError

DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 
with open('./keys/private.pem', "rb") as f:
    PRIVATE_KEY = f.read()

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