"""Testes para o modulo auth (hashing e JWT)."""

from datetime import datetime, timedelta, timezone

import jwt as pyjwt
import pytest

from jarvis.auth import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

SECRET = "test-secret"


class TestPasswordHashing:
    def test_hash_and_verify(self):
        plain = "minha-senha-123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert verify_password(plain, hashed)

    def test_wrong_password_fails(self):
        hashed = hash_password("correta")
        assert not verify_password("errada", hashed)

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("mesma")
        h2 = hash_password("mesma")
        assert h1 != h2  # bcrypt salt diferente


class TestAccessToken:
    def test_create_and_decode(self):
        token = create_access_token(1, "admin", SECRET, expiry_minutes=5)
        payload = decode_token(token, SECRET)

        assert payload.sub == 1
        assert payload.role == "admin"
        assert payload.type == "access"
        assert payload.exp > datetime.now(timezone.utc)

    def test_expired_token_raises(self):
        token = create_access_token(1, "user", SECRET, expiry_minutes=0)
        # Token com expiry 0 minutos — pode expirar imediatamente
        # Criamos manualmente um token ja expirado
        expired_payload = {
            "sub": 1,
            "role": "user",
            "exp": datetime.now(timezone.utc) - timedelta(seconds=10),
            "type": "access",
        }
        expired_token = pyjwt.encode(expired_payload, SECRET, algorithm=ALGORITHM)

        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_token(expired_token, SECRET)

    def test_wrong_secret_raises(self):
        token = create_access_token(1, "user", SECRET)
        with pytest.raises(pyjwt.InvalidSignatureError):
            decode_token(token, "wrong-secret")


class TestRefreshToken:
    def test_create_and_decode(self):
        token = create_refresh_token(2, "user", SECRET, expiry_days=1)
        payload = decode_token(token, SECRET)

        assert payload.sub == 2
        assert payload.role == "user"
        assert payload.type == "refresh"

    def test_type_is_refresh(self):
        token = create_refresh_token(1, "admin", SECRET)
        payload = decode_token(token, SECRET)
        assert payload.type == "refresh"


class TestDecodeToken:
    def test_invalid_token_string(self):
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token("not-a-real-token", SECRET)

    def test_tampered_token(self):
        token = create_access_token(1, "user", SECRET)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(pyjwt.InvalidTokenError):
            decode_token(tampered, SECRET)
