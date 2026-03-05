# Monitoramento do Agente GitHub — Plano de Implementacao

## Objetivo
Persistir cada execucao do agente GitHub e expor no admin panel, permitindo acompanhar issues processadas, status, categoria, duracao e erros.

## Arquivos a criar/modificar

### Backend

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `backend/src/jarvis/db.py` | MODIFICAR | Adicionar tabela `agent_runs` no SCHEMA_SQL + CRUD functions (SQLite) |
| `backend/src/jarvis/db_postgres.py` | MODIFICAR | Mesmo CRUD com sintaxe PostgreSQL |
| `backend/src/jarvis/schemas.py` | MODIFICAR | Adicionar `AgentRunResponse`, `AgentRunListResponse` |
| `backend/src/jarvis/admin.py` | MODIFICAR | Adicionar `GET /admin/agent-runs`, `GET /admin/agent-runs/{run_id}` |
| `backend/src/jarvis/webhook.py` | MODIFICAR | Registrar inicio/fim da execucao na tabela `agent_runs` |
| `backend/alembic/versions/002_agent_runs.py` | CRIAR | Migration para PostgreSQL |
| `backend/tests/test_agent_runs.py` | CRIAR | Testes para CRUD e endpoints |

### Frontend

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `frontend/src/types.ts` | MODIFICAR | Adicionar `AgentRun`, `AgentRunListResponse` |
| `frontend/src/api/adminApi.ts` | MODIFICAR | Adicionar `listAgentRuns()`, `getAgentRun()` |
| `frontend/src/pages/admin/AgentRunsPage.tsx` | CRIAR | Pagina com tabela + detalhe |
| `frontend/src/layouts/AdminLayout.tsx` | MODIFICAR | Adicionar "Agent" no nav |
| `frontend/src/routes.tsx` | MODIFICAR | Adicionar rota `/admin/agent-runs` |

### Docs

| Arquivo | Acao |
|---------|------|
| `CLAUDE.md` | MODIFICAR |
| `backend/CLAUDE.md` | MODIFICAR |
| `README.md` | MODIFICAR |

## Schema da tabela `agent_runs`

```sql
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,  -- SERIAL no PostgreSQL
    repo TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    issue_title TEXT NOT NULL,
    action TEXT NOT NULL,                   -- opened/edited/labeled
    category TEXT,                          -- BUG/FEATURE/DOCS/QUESTION/SECURITY (null enquanto classifica)
    status TEXT NOT NULL DEFAULT 'processing', -- processing/completed/failed
    tool_steps INTEGER NOT NULL DEFAULT 0,
    error_message TEXT,
    started_at TEXT NOT NULL,               -- ISO 8601 UTC
    finished_at TEXT                        -- ISO 8601 UTC (null enquanto processa)
);
```

## Fluxo

1. Webhook recebe issue → cria registro `agent_runs` com status=processing
2. `_handle_issue_event()` executa o grafo
3. Ao final, atualiza o registro com category, tool_steps, status=completed/failed, finished_at
4. Admin consulta `/admin/agent-runs` para ver historico

## CRUD Functions (ambos db.py e db_postgres.py)

- `create_agent_run(conn, repo, issue_number, issue_title, action) -> dict`
- `update_agent_run(conn, run_id, **fields) -> dict | None`
- `list_agent_runs(conn, limit=50, offset=0, status=None) -> tuple[list[dict], int]`
- `get_agent_run(conn, run_id) -> dict | None`

## Endpoints Admin

- `GET /admin/agent-runs?limit=50&offset=0&status=processing` → `AgentRunListResponse`
- `GET /admin/agent-runs/{run_id}` → `AgentRunResponse`

## Frontend AgentRunsPage

Segue padrao do LogsPage:
- Tabela com colunas: Status (badge colorido), Issue, Repo, Categoria, Steps, Duracao, Data
- Filtro por status (all/processing/completed/failed)
- Paginacao
- Click numa row mostra detalhe com error_message se houver
- Badge de status: processing=amarelo pulsante, completed=verde, failed=vermelho

## Ordem de implementacao

1. Schema + CRUD em db.py e db_postgres.py
2. Migration Alembic (002)
3. Schemas Pydantic
4. Endpoints admin
5. Modificar webhook para registrar runs
6. Testes backend
7. Types + API client frontend
8. AgentRunsPage + rotas + nav
9. Docs
10. Commit e push
