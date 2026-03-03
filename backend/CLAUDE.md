# Jarvis App

Pacote Python instalável com o assistente conversacional.

## Módulos

- `cli.py` — Entry point (`jarvis-chat`), parsing de args, loop interativo com Rich
- `config.py` — `Settings` dataclass com campos auth/JWT/infra, leitura de `.env`, overrides de CLI, system prompt com instrucoes Cartola FC
- `graph.py` — `build_graph()`, `_trim_and_prepend_system()` (trim por turnos humanos), `_sanitize_tool_sequences()`
- `graph_cache.py` — LRU cache de grafos compilados: `get_or_build_graph()`, `cache_info()`, `cache_clear()`
- `chat.py` — `invoke_chat()` e `stream_chat()` (retorna eventos tipados: token/tool_start/tool_end)
- `chat_once.py` — Entrypoint legado, redireciona para `cli.main()`
- `tools.py` — Ferramentas: `calculator`, `current_time` + `CARTOLA_TOOLS` registradas em `ALL_TOOLS`
- `cartola/` — Subpacote Cartola FC:
  - `client.py` — HTTP client (`urllib.request`), constantes `POSICAO_MAP`, `STATUS_MAP`, cache Redis opcional
  - `tools.py` — 5 `@tool` functions: market_status, players, round_scores, matches, expert_tips
  - `scraper.py` — Firecrawl scraper (import lazy, dependencia opcional via `pip install -e './backend[cartola]'`)
- `api.py` — Entry point da API REST (`jarvis-api`), endpoints HTTP + WS + auth, porta via `JARVIS_PORT` env var (default 8000)
- `auth.py` — Hash bcrypt, JWT encode/decode, `TokenPayload` dataclass
- `db.py` — Banco auth SQLite (aiosqlite): CRUD users, config global/por usuario, `seed_admin_if_needed()`
- `db_postgres.py` — Banco auth PostgreSQL (asyncpg): mesma interface que `db.py`, pool com min=2/max=10
- `db_factory.py` — Factory: `create_auth_db()`, `get_db_module()`, `get_integrity_error()` — seleciona SQLite ou PostgreSQL
- `checkpoint.py` — Factory: `create_checkpointer()` — AsyncSqliteSaver ou AsyncPostgresSaver
- `cache.py` — Wrapper Redis: `get_redis()`, `cached_get(key, ttl, fetch_fn)` — fallback sem Redis
- `deps.py` — FastAPI dependencies: `get_current_user()`, `get_current_active_user()`, `get_admin_user()`
- `admin.py` — APIRouter `/admin`: CRUD usuarios, config, logs de conversa
- `logs.py` — Extracao read-only de threads e mensagens do checkpoint (SQLite ou PostgreSQL)
- `schemas.py` — Pydantic models para auth, admin e logs
- `alembic/` — Migrations Alembic:
  - `env.py` — Resolve `DATABASE_URL` ou SQLite, configura SQLAlchemy engine
  - `versions/001_initial_auth_schema.py` — Tabelas `users`, `user_config`, `global_config`

## Fluxo de Dados

1. `cli.py` / `api.py` carrega `Settings` via `config.load_settings()`
2. Aplica overrides de CLI com `config.apply_cli_overrides()` (apenas CLI)
3. Cria auth DB via `db_factory.create_auth_db()` (SQLite ou PostgreSQL baseado em `DATABASE_URL`)
4. Cria checkpointer via `checkpoint.create_checkpointer()` (idem)
5. Constrói grafo com `graph.build_graph()` (model, system prompt, checkpointer)
6. Executa via `chat.stream_chat()` (streaming de eventos dict) ou `chat.invoke_chat()`
7. `stream_chat()` emite eventos `tool_start` / `tool_end` / `token` — API repassa via WS, CLI filtra tokens

## Dependências Chave

- `langchain-openai` — Wrapper do ChatOpenAI
- `langgraph` — StateGraph, ToolNode, checkpointer
- `langgraph-checkpoint-sqlite` — Persistência async com SQLite
- `langgraph-checkpoint-postgres` — Persistência async com PostgreSQL (via `DATABASE_URL`)
- `aiosqlite` — Banco SQLite async para auth e config
- `asyncpg` — Banco PostgreSQL async para auth e config (via `DATABASE_URL`)
- `redis` — Cache opcional para tools do Cartola (via `REDIS_URL`)
- `bcrypt` — Hash de senhas
- `pyjwt` — JWT encode/decode (access + refresh tokens)
- `rich` — Renderização Markdown no terminal
- `python-dotenv` — Leitura do `.env`
- `alembic` — Migrations de schema do banco auth
- `fastapi` + `uvicorn` — API REST
