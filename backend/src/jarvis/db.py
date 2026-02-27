"""Banco de dados de autenticacao e configuracao (SQLite via aiosqlite)."""

import json
from datetime import datetime, timezone
from typing import Any

import aiosqlite

from .auth import hash_password

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    is_active INTEGER NOT NULL DEFAULT 1,
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
"""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_user(row: aiosqlite.Row) -> dict[str, Any]:
    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "hashed_password": row[3],
        "role": row[4],
        "is_active": bool(row[5]),
        "created_at": row[6],
        "updated_at": row[7],
    }


async def init_db(db_path: str) -> aiosqlite.Connection:
    """Abre conexao e cria tabelas se necessario."""
    conn = await aiosqlite.connect(db_path)
    await conn.executescript(SCHEMA_SQL)
    await conn.execute(
        "INSERT OR IGNORE INTO global_config (id, config_json) VALUES (1, '{}')"
    )
    await conn.commit()
    return conn


# --- Users CRUD ---

async def create_user(
    conn: aiosqlite.Connection,
    username: str,
    email: str,
    plain_password: str,
    role: str = "user",
) -> dict[str, Any]:
    """Cria usuario e retorna dict com dados (sem senha em texto)."""
    now = _now_iso()
    hashed = hash_password(plain_password)
    cursor = await conn.execute(
        """INSERT INTO users (username, email, hashed_password, role, is_active, created_at, updated_at)
           VALUES (?, ?, ?, ?, 1, ?, ?)""",
        (username, email, hashed, role, now, now),
    )
    await conn.commit()
    return {
        "id": cursor.lastrowid,
        "username": username,
        "email": email,
        "hashed_password": hashed,
        "role": role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }


async def get_user_by_id(
    conn: aiosqlite.Connection, user_id: int
) -> dict[str, Any] | None:
    """Busca usuario por ID."""
    cursor = await conn.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = await cursor.fetchone()
    return _row_to_user(row) if row else None


async def get_user_by_username(
    conn: aiosqlite.Connection, username: str
) -> dict[str, Any] | None:
    """Busca usuario por username."""
    cursor = await conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    )
    row = await cursor.fetchone()
    return _row_to_user(row) if row else None


async def list_users(conn: aiosqlite.Connection) -> list[dict[str, Any]]:
    """Lista todos os usuarios."""
    cursor = await conn.execute("SELECT * FROM users ORDER BY id")
    rows = await cursor.fetchall()
    return [_row_to_user(r) for r in rows]


async def update_user(
    conn: aiosqlite.Connection,
    user_id: int,
    **fields: Any,
) -> dict[str, Any] | None:
    """Atualiza campos do usuario. Campos permitidos: email, role, is_active."""
    allowed = {"email", "role", "is_active"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return await get_user_by_id(conn, user_id)

    updates["updated_at"] = _now_iso()
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [user_id]

    await conn.execute(
        f"UPDATE users SET {set_clause} WHERE id = ?",  # noqa: S608
        values,
    )
    await conn.commit()
    return await get_user_by_id(conn, user_id)


async def update_user_password(
    conn: aiosqlite.Connection,
    user_id: int,
    plain_password: str,
) -> bool:
    """Atualiza senha do usuario. Retorna True se encontrou o usuario."""
    hashed = hash_password(plain_password)
    now = _now_iso()
    cursor = await conn.execute(
        "UPDATE users SET hashed_password = ?, updated_at = ? WHERE id = ?",
        (hashed, now, user_id),
    )
    await conn.commit()
    return cursor.rowcount > 0


async def delete_user(conn: aiosqlite.Connection, user_id: int) -> bool:
    """Remove usuario. Retorna True se existia."""
    cursor = await conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    await conn.commit()
    return cursor.rowcount > 0


# --- Config ---

async def get_user_config(
    conn: aiosqlite.Connection, user_id: int
) -> dict[str, Any]:
    """Retorna config do usuario (dict vazio se nao houver)."""
    cursor = await conn.execute(
        "SELECT config_json FROM user_config WHERE user_id = ?", (user_id,)
    )
    row = await cursor.fetchone()
    if row:
        return json.loads(row[0])
    return {}


async def set_user_config(
    conn: aiosqlite.Connection, user_id: int, config: dict[str, Any]
) -> None:
    """Salva config do usuario (merge com existente)."""
    existing = await get_user_config(conn, user_id)
    merged = {**existing, **config}
    config_json = json.dumps(merged)
    await conn.execute(
        """INSERT INTO user_config (user_id, config_json) VALUES (?, ?)
           ON CONFLICT(user_id) DO UPDATE SET config_json = ?""",
        (user_id, config_json, config_json),
    )
    await conn.commit()


async def get_global_config(conn: aiosqlite.Connection) -> dict[str, Any]:
    """Retorna config global."""
    cursor = await conn.execute(
        "SELECT config_json FROM global_config WHERE id = 1"
    )
    row = await cursor.fetchone()
    if row:
        return json.loads(row[0])
    return {}


async def set_global_config(
    conn: aiosqlite.Connection, config: dict[str, Any]
) -> None:
    """Salva config global (merge com existente)."""
    existing = await get_global_config(conn)
    merged = {**existing, **config}
    config_json = json.dumps(merged)
    await conn.execute(
        "UPDATE global_config SET config_json = ? WHERE id = 1",
        (config_json,),
    )
    await conn.commit()


# --- Seed ---

async def seed_admin_if_needed(
    conn: aiosqlite.Connection,
    username: str,
    email: str,
    password: str,
) -> None:
    """Cria usuario admin se nao existir nenhum admin."""
    cursor = await conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'admin'"
    )
    row = await cursor.fetchone()
    if row and row[0] > 0:
        return
    await create_user(conn, username, email, password, role="admin")
