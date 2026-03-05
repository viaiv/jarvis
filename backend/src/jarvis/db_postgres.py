"""Banco de dados de autenticacao e configuracao (PostgreSQL via asyncpg)."""

import json
from datetime import datetime, timezone
from typing import Any

import asyncpg

from .auth import hash_password

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_config (
    user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    config_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS global_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS agent_runs (
    id SERIAL PRIMARY KEY,
    repo TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    issue_title TEXT NOT NULL,
    action TEXT NOT NULL,
    category TEXT,
    status TEXT NOT NULL DEFAULT 'processing',
    tool_steps INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TEXT NOT NULL,
    finished_at TEXT
);
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_to_user(record: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": record["id"],
        "username": record["username"],
        "email": record["email"],
        "hashed_password": record["hashed_password"],
        "role": record["role"],
        "is_active": bool(record["is_active"]),
        "created_at": record["created_at"],
        "updated_at": record["updated_at"],
    }


async def init_db(database_url: str) -> asyncpg.Pool:
    """Cria pool de conexoes e tabelas se necessario."""
    pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
    async with pool.acquire() as conn:
        await conn.execute(SCHEMA_SQL)
        await conn.execute(
            "INSERT INTO global_config (id, config_json) VALUES (1, '{}') "
            "ON CONFLICT (id) DO NOTHING"
        )
    return pool


# --- Users CRUD ---

async def create_user(
    pool: asyncpg.Pool,
    username: str,
    email: str,
    plain_password: str,
    role: str = "user",
) -> dict[str, Any]:
    """Cria usuario e retorna dict com dados (sem senha em texto)."""
    now = _now_iso()
    hashed = hash_password(plain_password)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at)
               VALUES ($1, $2, $3, $4, TRUE, $5, $6)
               RETURNING id""",
            username, email, hashed, role, now, now,
        )
    return {
        "id": row["id"],
        "username": username,
        "email": email,
        "hashed_password": hashed,
        "role": role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


async def get_user_by_id(
    pool: asyncpg.Pool, user_id: int
) -> dict[str, Any] | None:
    """Busca usuario por ID."""
    async with pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
    return _record_to_user(record) if record else None


async def get_user_by_username(
    pool: asyncpg.Pool, username: str
) -> dict[str, Any] | None:
    """Busca usuario por username."""
    async with pool.acquire() as conn:
        record = await conn.fetchrow(
            "SELECT * FROM users WHERE username = $1", username
        )
    return _record_to_user(record) if record else None


async def list_users(pool: asyncpg.Pool) -> list[dict[str, Any]]:
    """Lista todos os usuarios."""
    async with pool.acquire() as conn:
        records = await conn.fetch("SELECT * FROM users ORDER BY id")
    return [_record_to_user(r) for r in records]


async def update_user(
    pool: asyncpg.Pool,
    user_id: int,
    **fields: Any,
) -> dict[str, Any] | None:
    """Atualiza campos do usuario. Campos permitidos: email, role, is_active."""
    allowed = {"email", "role", "is_active"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return await get_user_by_id(pool, user_id)

    updates["updated_at"] = _now_iso()
    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), 1):
        set_parts.append(f"{k} = ${i}")
        values.append(v)

    values.append(user_id)
    set_clause = ", ".join(set_parts)

    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE users SET {set_clause} WHERE id = ${len(values)}",  # noqa: S608
            *values,
        )
    return await get_user_by_id(pool, user_id)


async def update_user_password(
    pool: asyncpg.Pool,
    user_id: int,
    plain_password: str,
) -> bool:
    """Atualiza senha do usuario. Retorna True se encontrou o usuario."""
    hashed = hash_password(plain_password)
    now = _now_iso()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE users SET hashed_password = $1, updated_at = $2 WHERE id = $3",
            hashed, now, user_id,
        )
    return result.endswith("1")


async def delete_user(pool: asyncpg.Pool, user_id: int) -> bool:
    """Remove usuario. Retorna True se existia."""
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM users WHERE id = $1", user_id)
    return result.endswith("1")


# --- Config ---

async def get_user_config(
    pool: asyncpg.Pool, user_id: int
) -> dict[str, Any]:
    """Retorna config do usuario (dict vazio se nao houver)."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT config_json FROM user_config WHERE user_id = $1", user_id
        )
    if row:
        return json.loads(row["config_json"])
    return {}


async def set_user_config(
    pool: asyncpg.Pool, user_id: int, config: dict[str, Any]
) -> None:
    """Salva config do usuario (merge com existente)."""
    existing = await get_user_config(pool, user_id)
    merged = {**existing, **config}
    config_json = json.dumps(merged)
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO user_config (user_id, config_json) VALUES ($1, $2)
               ON CONFLICT (user_id) DO UPDATE SET config_json = $2""",
            user_id, config_json,
        )


async def get_global_config(pool: asyncpg.Pool) -> dict[str, Any]:
    """Retorna config global."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT config_json FROM global_config WHERE id = 1"
        )
    if row:
        return json.loads(row["config_json"])
    return {}


async def set_global_config(
    pool: asyncpg.Pool, config: dict[str, Any]
) -> None:
    """Salva config global (merge com existente)."""
    existing = await get_global_config(pool)
    merged = {**existing, **config}
    config_json = json.dumps(merged)
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE global_config SET config_json = $1 WHERE id = 1",
            config_json,
        )


# --- Agent Runs ---


def _record_to_agent_run(record: asyncpg.Record) -> dict[str, Any]:
    return {
        "id": record["id"],
        "repo": record["repo"],
        "issue_number": record["issue_number"],
        "issue_title": record["issue_title"],
        "action": record["action"],
        "category": record["category"],
        "status": record["status"],
        "tool_steps": record["tool_steps"],
        "error_message": record["error_message"],
        "started_at": record["started_at"],
        "finished_at": record["finished_at"],
    }


async def create_agent_run(
    pool: asyncpg.Pool,
    repo: str,
    issue_number: int,
    issue_title: str,
    action: str,
) -> dict[str, Any]:
    """Cria registro de execucao do agente GitHub."""
    now = _now_iso()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """INSERT INTO agent_runs (repo, issue_number, issue_title, action, status, started_at)
               VALUES ($1, $2, $3, $4, 'processing', $5)
               RETURNING id""",
            repo, issue_number, issue_title, action, now,
        )
    return {
        "id": row["id"],
        "repo": repo,
        "issue_number": issue_number,
        "issue_title": issue_title,
        "action": action,
        "category": None,
        "status": "processing",
        "tool_steps": 0,
        "error_message": None,
        "started_at": now,
        "finished_at": None,
    }


async def update_agent_run(
    pool: asyncpg.Pool,
    run_id: int,
    **fields: Any,
) -> dict[str, Any] | None:
    """Atualiza campos de um agent run."""
    allowed = {"category", "status", "tool_steps", "error_message", "finished_at"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return await get_agent_run(pool, run_id)

    set_parts = []
    values = []
    for i, (k, v) in enumerate(updates.items(), 1):
        set_parts.append(f"{k} = ${i}")
        values.append(v)

    values.append(run_id)
    set_clause = ", ".join(set_parts)

    async with pool.acquire() as conn:
        await conn.execute(
            f"UPDATE agent_runs SET {set_clause} WHERE id = ${len(values)}",  # noqa: S608
            *values,
        )
    return await get_agent_run(pool, run_id)


async def get_agent_run(
    pool: asyncpg.Pool, run_id: int
) -> dict[str, Any] | None:
    """Busca agent run por ID."""
    async with pool.acquire() as conn:
        record = await conn.fetchrow("SELECT * FROM agent_runs WHERE id = $1", run_id)
    return _record_to_agent_run(record) if record else None


async def list_agent_runs(
    pool: asyncpg.Pool,
    limit: int = 50,
    offset: int = 0,
    status: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """Lista agent runs com paginacao e filtro opcional por status."""
    async with pool.acquire() as conn:
        if status:
            row = await conn.fetchrow(
                "SELECT COUNT(*) AS cnt FROM agent_runs WHERE status = $1", status,
            )
            total = row["cnt"] if row else 0
            records = await conn.fetch(
                "SELECT * FROM agent_runs WHERE status = $1 ORDER BY id DESC LIMIT $2 OFFSET $3",
                status, limit, offset,
            )
        else:
            row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM agent_runs")
            total = row["cnt"] if row else 0
            records = await conn.fetch(
                "SELECT * FROM agent_runs ORDER BY id DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
    return [_record_to_agent_run(r) for r in records], total


# --- Seed ---

async def seed_admin_if_needed(
    pool: asyncpg.Pool,
    username: str,
    email: str,
    password: str,
) -> None:
    """Cria usuario admin se nao existir nenhum admin."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COUNT(*) AS cnt FROM users WHERE role = 'admin'"
        )
    if row and row["cnt"] > 0:
        return
    await create_user(pool, username, email, password, role="admin")
