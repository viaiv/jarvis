"""Configuracao do Alembic para migrations do banco auth."""

import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool

# Carrega .env do backend ou raiz do projeto
for candidate in [Path(__file__).resolve().parent.parent / ".env",
                  Path(__file__).resolve().parent.parent.parent / ".env"]:
    if candidate.exists():
        load_dotenv(candidate)
        break

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _get_url() -> str:
    """Resolve URL do banco baseado em DATABASE_URL."""
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        # asyncpg usa postgres:// mas SQLAlchemy precisa de driver sincrono
        url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url
    # Fallback SQLite
    db_path = Path(__file__).resolve().parent.parent.parent / ".jarvis-auth.db"
    return f"sqlite:///{db_path}"


def run_migrations_offline() -> None:
    """Roda migrations em modo offline (gera SQL sem conectar)."""
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Roda migrations conectando ao banco."""
    url = _get_url()
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
