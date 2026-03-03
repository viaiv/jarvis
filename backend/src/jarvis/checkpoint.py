"""Factory de checkpointer (SQLite ou PostgreSQL)."""

from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def create_checkpointer(settings: Any):
    """Cria checkpointer baseado na configuracao.

    Se DATABASE_URL estiver definido, usa PostgreSQL (AsyncPostgresSaver).
    Senao, usa SQLite (AsyncSqliteSaver).

    Retorna async context manager — usar com ``async with``.
    """
    if settings.database_url:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        async with AsyncPostgresSaver.from_conn_string(settings.database_url) as checkpointer:
            await checkpointer.setup()
            yield checkpointer
    else:
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        conn_string = settings.db_path if settings.persist_memory else ":memory:"
        checkpointer = AsyncSqliteSaver.from_conn_string(conn_string)
        try:
            yield checkpointer
        finally:
            pass
