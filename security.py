from jose import jwt, JWTError
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
import hashlib

SECRET_KEY = "troque_isto_por_uma_chave_grande_com_32+_chars_1234567890"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def _normalize_password(password: str) -> str:
    # bcrypt limita 72 bytes. Se exceder, reduz via SHA-256 (hex = 64 chars).
    pw_bytes = password.encode("utf-8")
    if len(pw_bytes) > 72:
        return hashlib.sha256(pw_bytes).hexdigest()
    return password

def hash_password(password: str) -> str:
    return pwd_context.hash(_normalize_password(password))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(_normalize_password(plain_password), hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


    

def decode_access_token(token: str) -> dict:
    """
    Retorna o payload do JWT se for válido.
    Lança ValueError se for inválido/expirado.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError("Token inválido ou expirado") from e