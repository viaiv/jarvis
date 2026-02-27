from dataclasses import dataclass, replace
import os

from dotenv import load_dotenv

DEFAULT_SYSTEM_PROMPT = (
    "Voce e um assistente tecnico, direto e didatico. "
    "Use as ferramentas disponiveis quando a pergunta exigir calculos "
    "ou data/hora."
)


@dataclass(frozen=True)
class Settings:
    system_prompt: str
    model_name: str
    history_window: int
    max_tool_steps: int
    memory_file: str
    session_id: str
    persist_memory: bool


def _read_non_negative_int(key: str, default: str) -> int:
    raw_value = os.getenv(key, default)
    try:
        parsed_value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{key} deve ser um numero inteiro.") from exc

    if parsed_value < 0:
        raise RuntimeError(f"{key} nao pode ser negativo.")
    return parsed_value


def _read_bool(key: str, default: bool) -> bool:
    raw_value = os.getenv(key)
    if raw_value is None:
        return default

    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{key} deve ser booleano (true/false).")


def load_settings() -> Settings:
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY nao encontrado. Configure no arquivo .env."
        )

    return Settings(
        system_prompt=os.getenv("JARVIS_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
        model_name=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        history_window=_read_non_negative_int("JARVIS_HISTORY_WINDOW", "3"),
        max_tool_steps=_read_non_negative_int("JARVIS_MAX_TOOL_STEPS", "5"),
        memory_file=os.getenv("JARVIS_MEMORY_FILE", ".jarvis_memory.json"),
        session_id=os.getenv("JARVIS_SESSION_ID", "default"),
        persist_memory=_read_bool("JARVIS_PERSIST_MEMORY", True),
    )


def apply_cli_overrides(
    settings: Settings,
    max_turns: int | None,
    max_tool_steps: int | None,
    session_id: str | None,
    memory_file: str | None,
    disable_memory: bool,
) -> Settings:
    updated = settings

    if max_turns is not None:
        if max_turns < 0:
            raise SystemExit("--max-turns nao pode ser negativo.")
        updated = replace(updated, history_window=max_turns)

    if max_tool_steps is not None:
        if max_tool_steps < 0:
            raise SystemExit("--max-tool-steps nao pode ser negativo.")
        updated = replace(updated, max_tool_steps=max_tool_steps)

    if session_id is not None:
        stripped = session_id.strip()
        if not stripped:
            raise SystemExit("--session-id nao pode ser vazio.")
        updated = replace(updated, session_id=stripped)

    if memory_file is not None:
        stripped = memory_file.strip()
        if not stripped:
            raise SystemExit("--memory-file nao pode ser vazio.")
        updated = replace(updated, memory_file=stripped)

    if disable_memory:
        updated = replace(updated, persist_memory=False)

    return updated
