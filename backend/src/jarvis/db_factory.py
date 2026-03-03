"""Factory para selecionar backend de auth DB (SQLite ou PostgreSQL)."""

from typing import Any


async def create_auth_db(settings: Any):
    """Cria conexao/pool de auth DB baseado na configuracao.

    Se DATABASE_URL estiver definido, usa PostgreSQL (asyncpg pool).
    Senao, usa SQLite (aiosqlite connection).
    """
    if settings.database_url:
        from .db_postgres import init_db
        return await init_db(settings.database_url)
    else:
        from .db import init_db
        return await init_db(settings.auth_db_path)


def get_db_module(settings: Any):
    """Retorna o modulo de DB correto baseado na configuracao.

    Permite que admin.py e deps.py importem funcoes do modulo certo.
    """
    if settings.database_url:
        from . import db_postgres as mod
    else:
        from . import db as mod
    return mod


def get_integrity_error(settings: Any) -> type:
    """Retorna a classe IntegrityError correta para o backend ativo."""
    if settings.database_url:
        import asyncpg
        return asyncpg.UniqueViolationError
    else:
        from aiosqlite import IntegrityError
        return IntegrityError
