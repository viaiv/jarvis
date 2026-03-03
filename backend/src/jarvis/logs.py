"""Extracao de logs de conversas do checkpoint do LangGraph (read-only)."""

from typing import Any

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


async def _list_threads_sqlite(
    db_path: str,
    user_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[dict[str, Any]], int]:
    """Lista threads via SQLite checkpoint DB."""
    async with aiosqlite.connect(db_path) as conn:
        if user_id is not None:
            prefix = f"{user_id}:"
            count_row = await (
                await conn.execute(
                    "SELECT COUNT(DISTINCT thread_id) FROM checkpoints WHERE thread_id LIKE ?",
                    (f"{prefix}%",),
                )
            ).fetchone()
            total = count_row[0] if count_row else 0

            cursor = await conn.execute(
                "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE ? ORDER BY thread_id LIMIT ? OFFSET ?",
                (f"{prefix}%", limit, offset),
            )
        else:
            count_row = await (
                await conn.execute(
                    "SELECT COUNT(DISTINCT thread_id) FROM checkpoints"
                )
            ).fetchone()
            total = count_row[0] if count_row else 0

            cursor = await conn.execute(
                "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id LIMIT ? OFFSET ?",
                (limit, offset),
            )

        rows = await cursor.fetchall()

    return [row[0] for row in rows], total


async def _list_threads_postgres(
    database_url: str,
    user_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[str], int]:
    """Lista threads via PostgreSQL checkpoint DB."""
    import asyncpg

    conn = await asyncpg.connect(database_url)
    try:
        if user_id is not None:
            prefix = f"{user_id}:"
            count_row = await conn.fetchrow(
                "SELECT COUNT(DISTINCT thread_id) AS cnt FROM checkpoints WHERE thread_id LIKE $1",
                f"{prefix}%",
            )
            total = count_row["cnt"] if count_row else 0

            rows = await conn.fetch(
                "SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE $1 ORDER BY thread_id LIMIT $2 OFFSET $3",
                f"{prefix}%", limit, offset,
            )
        else:
            count_row = await conn.fetchrow(
                "SELECT COUNT(DISTINCT thread_id) AS cnt FROM checkpoints"
            )
            total = count_row["cnt"] if count_row else 0

            rows = await conn.fetch(
                "SELECT DISTINCT thread_id FROM checkpoints ORDER BY thread_id LIMIT $1 OFFSET $2",
                limit, offset,
            )
    finally:
        await conn.close()

    return [row["thread_id"] for row in rows], total


async def list_threads(
    settings: Any,
    user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Lista threads do checkpoint DB com filtro opcional por user_id.

    Thread IDs sao no formato '{user_id}:{thread_name}'.
    Retorna (lista de resumos, total).
    """
    if settings.database_url:
        thread_ids, total = await _list_threads_postgres(
            settings.database_url, user_id, limit, offset,
        )
    else:
        thread_ids, total = await _list_threads_sqlite(
            settings.db_path, user_id, limit, offset,
        )

    threads = []
    for thread_id in thread_ids:
        parts = thread_id.split(":", 1)
        tid_user_id = int(parts[0]) if len(parts) == 2 and parts[0].isdigit() else None
        thread_name = parts[1] if len(parts) == 2 else thread_id

        threads.append({
            "thread_id": thread_id,
            "user_id": tid_user_id,
            "thread_name": thread_name,
        })

    return threads, total


async def get_thread_messages(
    checkpointer: Any,
    thread_id: str,
) -> list[dict[str, Any]]:
    """Extrai mensagens de um thread do checkpoint.

    Recebe checkpointer generico (SQLite ou PostgreSQL).
    Retorna lista de dicts com role, content e metadados.
    """
    config = {"configurable": {"thread_id": thread_id}}
    checkpoint_tuple = await checkpointer.aget_tuple(config)

    if not checkpoint_tuple:
        return []

    checkpoint = checkpoint_tuple.checkpoint
    channel_values = checkpoint.get("channel_values", {})
    messages = channel_values.get("messages", [])

    result = []
    for msg in messages:
        entry: dict[str, Any] = {"content": ""}

        if isinstance(msg, HumanMessage):
            entry["role"] = "user"
            entry["content"] = msg.content
        elif isinstance(msg, AIMessage):
            entry["role"] = "assistant"
            entry["content"] = msg.content
            if msg.tool_calls:
                entry["tool_calls"] = [
                    {"name": tc["name"], "id": tc["id"]}
                    for tc in msg.tool_calls
                ]
        elif isinstance(msg, ToolMessage):
            entry["role"] = "tool"
            entry["content"] = msg.content
            entry["tool_call_id"] = msg.tool_call_id
            entry["name"] = msg.name
        else:
            continue

        result.append(entry)

    return result
