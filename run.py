#!/usr/bin/env python3
"""Script de startup do Jarvis: verifica deps, testa conexoes, roda migrations e sobe servicos."""

from __future__ import annotations

import asyncio
import os
import signal
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# ---------------------------------------------------------------------------
# Helpers de output
# ---------------------------------------------------------------------------

def _ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def _warn(msg: str) -> None:
    print(f"  [WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_python_version(minimum: tuple[int, int] = (3, 11)) -> bool:
    """Verifica se a versao do Python atende ao minimo."""
    current = sys.version_info[:2]
    if current >= minimum:
        _ok(f"Python {current[0]}.{current[1]}")
        return True
    _fail(f"Python {current[0]}.{current[1]} (minimo {minimum[0]}.{minimum[1]})")
    return False


def check_env_file() -> bool:
    """Verifica se .env existe em backend/ ou na raiz."""
    for candidate in [BACKEND_DIR / ".env", PROJECT_ROOT / ".env"]:
        if candidate.exists():
            _ok(f".env encontrado em {candidate.relative_to(PROJECT_ROOT)}")
            return True
    _warn(".env nao encontrado — crie a partir de backend/.env.example")
    return True  # aviso, nao bloqueante


def check_backend_deps() -> bool:
    """Verifica se o pacote jarvis esta instalado."""
    try:
        import jarvis  # noqa: F401
        _ok("Backend (pacote jarvis) instalado")
        return True
    except ImportError:
        _fail("Pacote jarvis nao encontrado — execute: pip install -e ./backend")
        return False


def check_frontend_deps() -> bool:
    """Verifica se node_modules existe no frontend."""
    if (FRONTEND_DIR / "node_modules").is_dir():
        _ok("Frontend (node_modules) instalado")
        return True
    _warn("node_modules nao encontrado — execute: cd frontend && npm install")
    return True  # aviso, nao bloqueante


def _load_env_vars() -> dict[str, str]:
    """Le .env e retorna dict com variaveis (parsing simples)."""
    env_vars: dict[str, str] = {}
    for candidate in [BACKEND_DIR / ".env", PROJECT_ROOT / ".env"]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, value = line.partition("=")
                    env_vars[key.strip()] = value.strip().strip("'\"")
            break
    return env_vars


async def check_postgres(database_url: str) -> bool:
    """Testa conexao com PostgreSQL."""
    try:
        import asyncpg
        conn = await asyncpg.connect(database_url)
        await conn.close()
        _ok("PostgreSQL conectado")
        return True
    except Exception as exc:
        _fail(f"PostgreSQL indisponivel: {exc}")
        return False


def check_redis(redis_url: str) -> bool:
    """Testa conexao com Redis."""
    try:
        import redis as redis_lib
        r = redis_lib.from_url(redis_url)
        r.ping()
        r.close()
        _ok("Redis conectado")
        return True
    except Exception as exc:
        _warn(f"Redis indisponivel: {exc}")
        return True  # aviso, nao bloqueante


# ---------------------------------------------------------------------------
# Alembic migrations
# ---------------------------------------------------------------------------

def _table_exists(database_url: str, table: str) -> bool:
    """Verifica se uma tabela existe no banco (sync, para pre-check)."""
    try:
        from sqlalchemy import create_engine, text
        url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        engine = create_engine(url)
        with engine.connect() as conn:
            if "postgresql" in url:
                result = conn.execute(text(
                    "SELECT EXISTS (SELECT FROM information_schema.tables "
                    f"WHERE table_name = '{table}')"
                ))
                return result.scalar()
            else:
                result = conn.execute(text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
                ))
                return result.fetchone() is not None
    except Exception:
        return False


def run_alembic_migrations(database_url: str) -> bool:
    """Roda alembic upgrade head, com stamp se banco pre-existente."""
    has_users = _table_exists(database_url, "users")
    has_alembic = _table_exists(database_url, "alembic_version")

    if has_users and not has_alembic:
        # Banco criado pelo CREATE IF NOT EXISTS antigo — marcar como migrado
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "stamp", "head"],
            cwd=str(BACKEND_DIR),
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            _ok("Alembic stamp head (banco pre-existente)")
            return True
        _fail(f"Alembic stamp falhou: {result.stderr.strip()}")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        _ok("Alembic migrations aplicadas")
        return True
    _fail(f"Alembic upgrade falhou: {result.stderr.strip()}")
    return False


# ---------------------------------------------------------------------------
# Porta
# ---------------------------------------------------------------------------

def parse_port(raw: str, default: int = 8000) -> int:
    """Interpreta input do usuario como porta. Retorna default se vazio."""
    stripped = raw.strip()
    if not stripped:
        return default
    try:
        port = int(stripped)
        if not (1 <= port <= 65535):
            raise ValueError
        return port
    except ValueError:
        print(f"  Porta invalida: {stripped!r} — usando default {default}")
        return default


# ---------------------------------------------------------------------------
# Process management
# ---------------------------------------------------------------------------

def start_services(port: int) -> None:
    """Sobe backend (uvicorn --reload) e frontend como subprocessos."""
    env = {**os.environ, "JARVIS_PORT": str(port)}

    backend_proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "jarvis.api:app",
            "--host", "0.0.0.0",
            "--port", str(port),
            "--reload",
            "--reload-dir", str(BACKEND_DIR / "src"),
        ],
        env=env,
    )
    frontend_proc = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=str(FRONTEND_DIR),
        env=env,
    )

    print(f"\n  Backend na porta {port} (reload ativo) | Frontend em http://localhost:5173")
    print("  Ctrl+C para encerrar\n")

    def _shutdown(signum, frame):
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait(timeout=5)
        frontend_proc.wait(timeout=5)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Espera qualquer um terminar
    try:
        while True:
            if backend_proc.poll() is not None:
                print("  Backend encerrou — parando frontend...")
                frontend_proc.terminate()
                break
            if frontend_proc.poll() is not None:
                print("  Frontend encerrou — parando backend...")
                backend_proc.terminate()
                break
            signal.pause()
    except KeyboardInterrupt:
        _shutdown(None, None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("\n  Jarvis — Startup\n")

    # 1. Python version
    if not check_python_version():
        sys.exit(1)

    # 2. .env
    check_env_file()

    # 3. Backend deps
    if not check_backend_deps():
        sys.exit(1)

    # 4. Frontend deps
    check_frontend_deps()

    # Carrega .env no ambiente (subprocessos herdam)
    env_vars = _load_env_vars()
    os.environ.update(env_vars)

    # 5-6. Infra checks (PostgreSQL / Redis)
    database_url = env_vars.get("DATABASE_URL", "")
    redis_url = env_vars.get("REDIS_URL", "")

    if database_url:
        if not asyncio.run(check_postgres(database_url)):
            sys.exit(1)
    else:
        _ok("SQLite (sem DATABASE_URL)")

    if redis_url:
        check_redis(redis_url)
    else:
        _ok("Sem Redis (cache desabilitado)")

    # 7. Alembic migrations
    if database_url:
        if not run_alembic_migrations(database_url):
            sys.exit(1)
    else:
        _ok("Alembic skip (SQLite — tabelas criadas em runtime)")

    # 8. Porta
    try:
        raw_port = input("\n  Porta do backend [8000]: ")
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    port = parse_port(raw_port)

    # 9. Start services
    start_services(port)


if __name__ == "__main__":
    main()
