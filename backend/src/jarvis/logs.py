"""Extracao de logs de conversas do checkpoint do LangGraph (read-only)."""

from typing import Any

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage


async def list_threads(
    db_path: str,
    user_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict[str, Any]], int]:
    """Lista threads do checkpoint DB com filtro opcional por user_id.

    Thread IDs sao no formato '{user_id}:{thread_name}'.
    Retorna (lista de resumos, total).
    """
    async with aiosqlite.connect(db_path) as conn:
        # Busca thread_ids distintos da tabela de checkpoints
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

    threads = []
    for row in rows:
        thread_id = row[0]
        # Extrair user_id e nome do thread
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
    db_path: str,
    thread_id: str,
) -> list[dict[str, Any]]:
    """Extrai mensagens de um thread do checkpoint.

    Le o checkpoint mais recente e deserializa as mensagens.
    Retorna lista de dicts com role, content e metadados.
    """
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(db_path) as checkpointer:
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
