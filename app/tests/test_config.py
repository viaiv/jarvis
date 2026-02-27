import pytest

from jarvis.config import Settings, apply_cli_overrides, load_settings


@pytest.fixture()
def base_settings():
    return Settings(
        system_prompt="test prompt",
        model_name="gpt-4.1-mini",
        history_window=3,
        max_tool_steps=5,
        memory_file=".jarvis_memory.json",
        session_id="default",
        persist_memory=True,
    )


class TestLoadSettings:
    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            load_settings()

    def test_valid_settings(self, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        monkeypatch.setenv("JARVIS_HISTORY_WINDOW", "5")
        monkeypatch.setenv("JARVIS_MAX_TOOL_STEPS", "10")
        monkeypatch.setenv("JARVIS_SESSION_ID", "minha-sessao")
        monkeypatch.setenv("JARVIS_PERSIST_MEMORY", "false")

        settings = load_settings()

        assert settings.model_name == "gpt-4o"
        assert settings.history_window == 5
        assert settings.max_tool_steps == 10
        assert settings.session_id == "minha-sessao"
        assert settings.persist_memory is False

    def test_defaults(self, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        monkeypatch.delenv("JARVIS_HISTORY_WINDOW", raising=False)
        monkeypatch.delenv("JARVIS_MAX_TOOL_STEPS", raising=False)
        monkeypatch.delenv("JARVIS_SESSION_ID", raising=False)
        monkeypatch.delenv("JARVIS_PERSIST_MEMORY", raising=False)

        settings = load_settings()

        assert settings.model_name == "gpt-4.1-mini"
        assert settings.history_window == 3
        assert settings.max_tool_steps == 5
        assert settings.session_id == "default"
        assert settings.persist_memory is True

    def test_invalid_int_env(self, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("JARVIS_HISTORY_WINDOW", "abc")

        with pytest.raises(RuntimeError, match="numero inteiro"):
            load_settings()

    def test_negative_int_env(self, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("JARVIS_MAX_TOOL_STEPS", "-1")

        with pytest.raises(RuntimeError, match="negativo"):
            load_settings()

    def test_invalid_bool_env(self, monkeypatch):
        monkeypatch.setattr("jarvis.config.load_dotenv", lambda: None)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("JARVIS_PERSIST_MEMORY", "maybe")

        with pytest.raises(RuntimeError, match="booleano"):
            load_settings()


class TestApplyCliOverrides:
    def test_override_max_turns(self, base_settings):
        updated = apply_cli_overrides(
            base_settings, max_turns=10, max_tool_steps=None,
            session_id=None, memory_file=None, disable_memory=False,
        )
        assert updated.history_window == 10

    def test_override_max_tool_steps(self, base_settings):
        updated = apply_cli_overrides(
            base_settings, max_turns=None, max_tool_steps=2,
            session_id=None, memory_file=None, disable_memory=False,
        )
        assert updated.max_tool_steps == 2

    def test_override_session_id(self, base_settings):
        updated = apply_cli_overrides(
            base_settings, max_turns=None, max_tool_steps=None,
            session_id="aula", memory_file=None, disable_memory=False,
        )
        assert updated.session_id == "aula"

    def test_override_memory_file(self, base_settings):
        updated = apply_cli_overrides(
            base_settings, max_turns=None, max_tool_steps=None,
            session_id=None, memory_file="/tmp/mem.json", disable_memory=False,
        )
        assert updated.memory_file == "/tmp/mem.json"

    def test_disable_memory(self, base_settings):
        updated = apply_cli_overrides(
            base_settings, max_turns=None, max_tool_steps=None,
            session_id=None, memory_file=None, disable_memory=True,
        )
        assert updated.persist_memory is False

    def test_negative_max_turns_exits(self, base_settings):
        with pytest.raises(SystemExit, match="negativo"):
            apply_cli_overrides(
                base_settings, max_turns=-1, max_tool_steps=None,
                session_id=None, memory_file=None, disable_memory=False,
            )

    def test_empty_session_id_exits(self, base_settings):
        with pytest.raises(SystemExit, match="vazio"):
            apply_cli_overrides(
                base_settings, max_turns=None, max_tool_steps=None,
                session_id="  ", memory_file=None, disable_memory=False,
            )

    def test_no_overrides_returns_same(self, base_settings):
        updated = apply_cli_overrides(
            base_settings, max_turns=None, max_tool_steps=None,
            session_id=None, memory_file=None, disable_memory=False,
        )
        assert updated == base_settings
