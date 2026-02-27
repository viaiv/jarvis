"""Fixtures compartilhadas para testes."""

import pytest

from jarvis.config import Settings


def make_settings(**overrides) -> Settings:
    """Cria Settings com defaults de teste."""
    defaults = dict(
        system_prompt="prompt teste",
        model_name="gpt-test",
        history_window=3,
        max_tool_steps=5,
        db_path=":memory:",
        session_id="test-session",
        persist_memory=False,
        jwt_secret="test-secret-key",
        jwt_access_expiry_minutes=30,
        jwt_refresh_expiry_days=7,
        auth_db_path=":memory:",
        admin_username="admin",
        admin_email="admin@test.local",
        admin_password="admin123",
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture()
def test_settings():
    return make_settings()
