"""FastAPI dependencies para autenticacao."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

import jwt as pyjwt

from .auth import decode_token
from .db import get_user_by_id

security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Extrai e valida JWT do header Authorization."""
    settings = request.app.state.settings
    token = credentials.credentials

    try:
        payload = decode_token(token, settings.jwt_secret)
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido ou expirado.",
        )

    if payload.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido (tipo incorreto).",
        )

    conn = request.app.state.auth_db
    user = await get_user_by_id(conn, payload.sub)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado.",
        )

    return user


async def get_current_active_user(
    user: dict = Depends(get_current_user),
) -> dict:
    """Valida que o usuario esta ativo."""
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desativado.",
        )
    return user


async def get_admin_user(
    user: dict = Depends(get_current_active_user),
) -> dict:
    """Valida que o usuario e admin."""
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores.",
        )
    return user
