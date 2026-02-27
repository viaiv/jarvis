import json
import os
import tempfile
from typing import Any, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage


class MemoryStoreError(RuntimeError):
    """Erro de leitura/escrita da memoria persistente."""


def _messages_to_turns(messages: List[BaseMessage]) -> List[dict[str, str]]:
    turns: List[dict[str, str]] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            turns.append({"role": "human", "content": message.content})
        elif isinstance(message, AIMessage):
            turns.append({"role": "ai", "content": message.content})
    return turns


def _turns_to_messages(turns: Any) -> List[BaseMessage]:
    if not isinstance(turns, list):
        raise MemoryStoreError("Formato invalido na memoria: esperado lista de turnos.")

    messages: List[BaseMessage] = []
    for item in turns:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if not isinstance(content, str):
            continue
        if role == "human":
            messages.append(HumanMessage(content=content))
        elif role == "ai":
            messages.append(AIMessage(content=content))
    return messages


def _read_store(memory_file: str) -> dict[str, Any]:
    if not os.path.exists(memory_file):
        return {}

    try:
        with open(memory_file, "r", encoding="utf-8") as file:
            data = json.load(file)
    except OSError as exc:
        raise MemoryStoreError(
            f"Falha ao ler arquivo de memoria '{memory_file}': {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise MemoryStoreError(
            f"Arquivo de memoria '{memory_file}' possui JSON invalido."
        ) from exc

    if not isinstance(data, dict):
        raise MemoryStoreError(
            f"Arquivo de memoria '{memory_file}' deve conter um objeto JSON."
        )
    return data


def _write_store(memory_file: str, store: dict[str, Any]) -> None:
    directory = os.path.dirname(memory_file)
    if directory:
        os.makedirs(directory, exist_ok=True)

    temp_fd, temp_path = tempfile.mkstemp(
        prefix=".jarvis-memory-",
        suffix=".tmp",
        dir=directory or None,
        text=True,
    )
    try:
        with os.fdopen(temp_fd, "w", encoding="utf-8") as file:
            json.dump(store, file, ensure_ascii=True, indent=2)
        os.replace(temp_path, memory_file)
    except OSError as exc:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise MemoryStoreError(
            f"Falha ao escrever arquivo de memoria '{memory_file}': {exc}"
        ) from exc


def load_session_history(memory_file: str, session_id: str) -> List[BaseMessage]:
    store = _read_store(memory_file)
    return _turns_to_messages(store.get(session_id, []))


def save_session_history(
    memory_file: str,
    session_id: str,
    history: List[BaseMessage],
) -> None:
    store = _read_store(memory_file)
    store[session_id] = _messages_to_turns(history)
    _write_store(memory_file, store)
