"""Testes para o modulo deps (FastAPI dependencies)."""

import pytest
from fastapi import HTTPException

from jarvis.auth import create_access_token, create_refresh_token
from jarvis.config import Settings
from jarvis.deps import get_admin_user, get_current_active_user, get_current_user


class FakeCredentials:
    def __init__(self, token: str):
        self.credentials = token


class FakeAppState:
    def __init__(self, settings, auth_db):
        self.settings = settings
        self.auth_db = auth_db


class FakeRequest:
    def __init__(self, app_state):
        self.app = type("App", (), {"state": app_state})()


SECRET = "test-secret"


def _fake_settings():
    return Settings(
        system_prompt="test",
        model_name="gpt-test",
        history_window=3,
        max_tool_steps=5,
        db_path=":memory:",
        session_id="test",
        persist_memory=False,
        jwt_secret=SECRET,
    )


class TestGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token(self):
        from jarvis.db import create_user, init_db

        conn = await init_db(":memory:")
        user = await create_user(conn, "alice", "alice@t.com", "s")

        token = create_access_token(user["id"], "user", SECRET)
        creds = FakeCredentials(token)
        request = FakeRequest(FakeAppState(_fake_settings(), conn))

        result = await get_current_user(request, creds)
        assert result["username"] == "alice"
        await conn.close()

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self):
        from jarvis.db import init_db

        conn = await init_db(":memory:")
        creds = FakeCredentials("bad-token")
        request = FakeRequest(FakeAppState(_fake_settings(), conn))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, creds)
        assert exc_info.value.status_code == 401
        await conn.close()

    @pytest.mark.asyncio
    async def test_refresh_token_rejected(self):
        from jarvis.db import create_user, init_db

        conn = await init_db(":memory:")
        user = await create_user(conn, "bob", "bob@t.com", "s")

        token = create_refresh_token(user["id"], "user", SECRET)
        creds = FakeCredentials(token)
        request = FakeRequest(FakeAppState(_fake_settings(), conn))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, creds)
        assert exc_info.value.status_code == 401
        await conn.close()

    @pytest.mark.asyncio
    async def test_deleted_user_raises(self):
        from jarvis.db import create_user, delete_user, init_db

        conn = await init_db(":memory:")
        user = await create_user(conn, "carol", "carol@t.com", "s")
        token = create_access_token(user["id"], "user", SECRET)
        await delete_user(conn, user["id"])

        creds = FakeCredentials(token)
        request = FakeRequest(FakeAppState(_fake_settings(), conn))

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(request, creds)
        assert exc_info.value.status_code == 401
        await conn.close()


class TestGetCurrentActiveUser:
    @pytest.mark.asyncio
    async def test_active_user_passes(self):
        user = {"id": 1, "username": "a", "is_active": True, "role": "user"}
        result = await get_current_active_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_inactive_user_raises(self):
        user = {"id": 1, "username": "a", "is_active": False, "role": "user"}
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(user)
        assert exc_info.value.status_code == 403


class TestGetAdminUser:
    @pytest.mark.asyncio
    async def test_admin_passes(self):
        user = {"id": 1, "username": "a", "is_active": True, "role": "admin"}
        result = await get_admin_user(user)
        assert result == user

    @pytest.mark.asyncio
    async def test_non_admin_raises(self):
        user = {"id": 1, "username": "a", "is_active": True, "role": "user"}
        with pytest.raises(HTTPException) as exc_info:
            await get_admin_user(user)
        assert exc_info.value.status_code == 403
