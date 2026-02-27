"""Hashing de senhas e geracao/validacao de JWT."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

ALGORITHM = "HS256"


@dataclass(frozen=True)
class TokenPayload:
    sub: int
    role: str
    exp: datetime
    type: str  # "access" ou "refresh"


def hash_password(plain: str) -> str:
    """Gera hash bcrypt da senha."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifica senha contra hash bcrypt."""
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(
    user_id: int,
    role: str,
    secret: str,
    expiry_minutes: int = 30,
) -> str:
    """Gera JWT de acesso."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": now + timedelta(minutes=expiry_minutes),
        "type": "access",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_refresh_token(
    user_id: int,
    role: str,
    secret: str,
    expiry_days: int = 7,
) -> str:
    """Gera JWT de refresh."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": now + timedelta(days=expiry_days),
        "type": "refresh",
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> TokenPayload:
    """Decodifica e valida JWT. Levanta jwt.InvalidTokenError se invalido."""
    data = jwt.decode(token, secret, algorithms=[ALGORITHM])
    return TokenPayload(
        sub=int(data["sub"]),
        role=data["role"],
        exp=datetime.fromtimestamp(data["exp"], tz=timezone.utc),
        type=data["type"],
    )
