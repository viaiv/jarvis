"""Testes para endpoints admin."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from jarvis.api import app
from jarvis.auth import create_access_token
from jarvis.config import Settings
from jarvis.db import create_user, init_db


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        system_prompt="prompt teste",
        model_name="gpt-test",
        history_window=3,
        max_tool_steps=5,
        db_path=":memory:",
        session_id="test-session",
        persist_memory=False,
        jwt_secret="test-secret",
        jwt_access_expiry_minutes=30,
        jwt_refresh_expiry_days=7,
        auth_db_path=":memory:",
        admin_username="admin",
        admin_email="admin@test.local",
        admin_password="admin123",
    )
    defaults.update(overrides)
    return Settings(**defaults)


JWT_SECRET = "test-secret"


@pytest_asyncio.fixture()
async def setup_admin():
    """Cria auth DB com admin e usuario regular."""
    conn = await init_db(":memory:")
    admin = await create_user(conn, "admin", "admin@test.com", "adminpass", role="admin")
    user = await create_user(conn, "testuser", "test@test.com", "testpass")

    settings = _make_settings(jwt_secret=JWT_SECRET)

    app.state.settings = settings
    app.state.auth_db = conn
    app.state.graph = None

    admin_token = create_access_token(admin["id"], admin["role"], JWT_SECRET)
    user_token = create_access_token(user["id"], user["role"], JWT_SECRET)

    yield {
        "admin": admin,
        "user": user,
        "admin_token": admin_token,
        "user_token": user_token,
        "conn": conn,
    }

    await conn.close()
    for attr in ("graph", "settings", "auth_db"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)


def _admin_headers(ctx):
    return {"Authorization": f"Bearer {ctx['admin_token']}"}


def _user_headers(ctx):
    return {"Authorization": f"Bearer {ctx['user_token']}"}


class TestAdminUsersEndpoints:
    @pytest.mark.asyncio
    async def test_list_users(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/users", headers=_admin_headers(setup_admin))

        assert resp.status_code == 200
        users = resp.json()
        assert len(users) == 2
        usernames = {u["username"] for u in users}
        assert "admin" in usernames
        assert "testuser" in usernames

    @pytest.mark.asyncio
    async def test_list_users_non_admin_forbidden(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/admin/users", headers=_user_headers(setup_admin))

        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_user(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/admin/users",
                json={"username": "newuser", "email": "new@test.com", "password": "pass123"},
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newuser"
        assert body["role"] == "user"
        assert body["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_duplicate_user(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/admin/users",
                json={"username": "testuser", "email": "dup@test.com", "password": "pass123"},
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_get_user(self, setup_admin):
        user_id = setup_admin["user"]["id"]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/admin/users/{user_id}",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 200
        assert resp.json()["username"] == "testuser"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/admin/users/999",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_user(self, setup_admin):
        user_id = setup_admin["user"]["id"]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                f"/admin/users/{user_id}",
                json={"email": "updated@test.com", "role": "admin"},
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "updated@test.com"
        assert body["role"] == "admin"

    @pytest.mark.asyncio
    async def test_delete_user(self, setup_admin):
        user_id = setup_admin["user"]["id"]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                f"/admin/users/{user_id}",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.delete(
                "/admin/users/999",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_password(self, setup_admin):
        user_id = setup_admin["user"]["id"]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                f"/admin/users/{user_id}/password",
                json={"password": "newpass123"},
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 204


class TestAdminConfigEndpoints:
    @pytest.mark.asyncio
    async def test_get_global_config(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/admin/config",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_set_global_config(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                "/admin/config",
                json={"model_name": "gpt-4o", "history_window": 5},
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["model_name"] == "gpt-4o"
        assert body["history_window"] == 5

    @pytest.mark.asyncio
    async def test_get_user_config(self, setup_admin):
        user_id = setup_admin["user"]["id"]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                f"/admin/users/{user_id}/config",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_set_user_config(self, setup_admin):
        user_id = setup_admin["user"]["id"]
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.put(
                f"/admin/users/{user_id}/config",
                json={"system_prompt": "custom prompt", "max_tool_steps": 3},
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["system_prompt"] == "custom prompt"
        assert body["max_tool_steps"] == 3

    @pytest.mark.asyncio
    async def test_user_config_nonexistent_user(self, setup_admin):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/admin/users/999/config",
                headers=_admin_headers(setup_admin),
            )

        assert resp.status_code == 404
