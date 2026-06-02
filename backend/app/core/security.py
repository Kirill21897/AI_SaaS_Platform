from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from app.core.config import settings
import logging
import hashlib
import os

# Custom simple hashing for mock/MVP to avoid bcrypt native extension issues on Windows
def _hash_password(password: str, salt: str = None) -> str:
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode('utf-8')).hexdigest()
    return f"{salt}${hashed}"


def _get_secret_key() -> str:
    if settings.SECRET_KEY is None or not settings.SECRET_KEY.get_secret_value():
        raise RuntimeError("SECRET_KEY is not set")
    return settings.SECRET_KEY.get_secret_value()

def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode,
        _get_secret_key(),
        algorithm=settings.ALGORITHM,
    )
    return encoded_jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        # Check if it's our custom hash format
        if "$" in hashed_password:
            salt, _ = hashed_password.split("$", 1)
            return _hash_password(plain_password, salt) == hashed_password
            
        # Fallback for old bcrypt hashes if any (though we won't create them anymore)
        return False
    except Exception as e:
        logging.error(f"Error verifying password: {e}")
        return False

def get_password_hash(password: str) -> str:
    return _hash_password(password)
