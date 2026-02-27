"""Testes para o modulo db (CRUD usuarios e config)."""

import pytest
import pytest_asyncio

from jarvis.db import (
    create_user,
    delete_user,
    get_global_config,
    get_user_by_id,
    get_user_by_username,
    get_user_config,
    init_db,
    list_users,
    seed_admin_if_needed,
    set_global_config,
    set_user_config,
    update_user,
    update_user_password,
)
from jarvis.auth import verify_password


@pytest_asyncio.fixture
async def db():
    conn = await init_db(":memory:")
    yield conn
    await conn.close()


class TestUserCrud:
    @pytest.mark.asyncio
    async def test_create_and_get_user(self, db):
        user = await create_user(db, "alice", "alice@test.com", "senha123")
        assert user["username"] == "alice"
        assert user["email"] == "alice@test.com"
        assert user["role"] == "user"
        assert user["is_active"] is True
        assert "hashed_password" in user

        fetched = await get_user_by_id(db, user["id"])
        assert fetched is not None
        assert fetched["username"] == "alice"

    @pytest.mark.asyncio
    async def test_get_user_by_username(self, db):
        await create_user(db, "bob", "bob@test.com", "senha")
        user = await get_user_by_username(db, "bob")
        assert user is not None
        assert user["email"] == "bob@test.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user_returns_none(self, db):
        assert await get_user_by_id(db, 999) is None
        assert await get_user_by_username(db, "ghost") is None

    @pytest.mark.asyncio
    async def test_list_users(self, db):
        await create_user(db, "u1", "u1@test.com", "s1")
        await create_user(db, "u2", "u2@test.com", "s2")
        users = await list_users(db)
        assert len(users) == 2
        assert users[0]["username"] == "u1"
        assert users[1]["username"] == "u2"

    @pytest.mark.asyncio
    async def test_update_user_fields(self, db):
        user = await create_user(db, "carol", "carol@test.com", "s")
        updated = await update_user(db, user["id"], email="new@test.com", role="admin")
        assert updated["email"] == "new@test.com"
        assert updated["role"] == "admin"

    @pytest.mark.asyncio
    async def test_update_user_is_active(self, db):
        user = await create_user(db, "dan", "dan@test.com", "s")
        updated = await update_user(db, user["id"], is_active=False)
        assert updated["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_user_password(self, db):
        user = await create_user(db, "eve", "eve@test.com", "old")
        result = await update_user_password(db, user["id"], "new")
        assert result is True
        refreshed = await get_user_by_id(db, user["id"])
        assert verify_password("new", refreshed["hashed_password"])

    @pytest.mark.asyncio
    async def test_delete_user(self, db):
        user = await create_user(db, "frank", "frank@test.com", "s")
        assert await delete_user(db, user["id"]) is True
        assert await get_user_by_id(db, user["id"]) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, db):
        assert await delete_user(db, 999) is False

    @pytest.mark.asyncio
    async def test_duplicate_username_raises(self, db):
        await create_user(db, "dup", "dup1@test.com", "s")
        with pytest.raises(Exception):
            await create_user(db, "dup", "dup2@test.com", "s")

    @pytest.mark.asyncio
    async def test_duplicate_email_raises(self, db):
        await create_user(db, "a", "same@test.com", "s")
        with pytest.raises(Exception):
            await create_user(db, "b", "same@test.com", "s")


class TestConfig:
    @pytest.mark.asyncio
    async def test_global_config_default_empty(self, db):
        config = await get_global_config(db)
        assert config == {}

    @pytest.mark.asyncio
    async def test_set_and_get_global_config(self, db):
        await set_global_config(db, {"model_name": "gpt-4o"})
        config = await get_global_config(db)
        assert config["model_name"] == "gpt-4o"

    @pytest.mark.asyncio
    async def test_global_config_merge(self, db):
        await set_global_config(db, {"model_name": "gpt-4o"})
        await set_global_config(db, {"history_window": 5})
        config = await get_global_config(db)
        assert config["model_name"] == "gpt-4o"
        assert config["history_window"] == 5

    @pytest.mark.asyncio
    async def test_user_config_default_empty(self, db):
        user = await create_user(db, "u", "u@t.com", "s")
        config = await get_user_config(db, user["id"])
        assert config == {}

    @pytest.mark.asyncio
    async def test_set_and_get_user_config(self, db):
        user = await create_user(db, "u", "u@t.com", "s")
        await set_user_config(db, user["id"], {"max_tool_steps": 10})
        config = await get_user_config(db, user["id"])
        assert config["max_tool_steps"] == 10

    @pytest.mark.asyncio
    async def test_user_config_merge(self, db):
        user = await create_user(db, "u", "u@t.com", "s")
        await set_user_config(db, user["id"], {"a": 1})
        await set_user_config(db, user["id"], {"b": 2})
        config = await get_user_config(db, user["id"])
        assert config == {"a": 1, "b": 2}


class TestSeedAdmin:
    @pytest.mark.asyncio
    async def test_seed_creates_admin(self, db):
        await seed_admin_if_needed(db, "root", "root@t.com", "pass")
        users = await list_users(db)
        assert len(users) == 1
        assert users[0]["role"] == "admin"
        assert users[0]["username"] == "root"

    @pytest.mark.asyncio
    async def test_seed_skips_if_admin_exists(self, db):
        await create_user(db, "existing", "ex@t.com", "s", role="admin")
        await seed_admin_if_needed(db, "root", "root@t.com", "pass")
        users = await list_users(db)
        assert len(users) == 1
        assert users[0]["username"] == "existing"
