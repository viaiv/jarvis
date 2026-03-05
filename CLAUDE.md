# Jarvis

Assistente conversacional de estudo construído com LangChain + LangGraph.
Projeto educacional para aprender tool calling, grafos de agentes e memória persistente.

## Stack e Arquitetura

- **Linguagem**: Python 3.11+
- **LLM Framework**: LangChain + LangGraph
- **Modelo padrão**: gpt-4.1-mini (configurável via `.env`)
- **Persistência**: SQLite ou PostgreSQL via factory (`checkpoint.py`, `db_factory.py`)
- **Auth**: JWT stateless (PyJWT + bcrypt), SQLite ou PostgreSQL para auth
- **Cache**: Redis opcional para tools do Cartola FC (`cache.py`)
- **CLI**: argparse + Rich (streaming com Markdown)
- **API**: FastAPI + Uvicorn
- **Frontend**: React + Vite + TypeScript + React Router v7
- **Migrations**: Alembic (migrations manuais com SQL raw)
- **Testes**: pytest + pytest-asyncio

Mapa de diretórios:
- `backend/src/jarvis/` — Código principal do assistente (Python/FastAPI)
- `backend/src/jarvis/tools/` — Pacote de ferramentas (base, GitHub, Cartola FC)
- `backend/src/jarvis/cartola/` — Ferramentas do Cartola FC (client HTTP, tools, scraper)
- `backend/src/jarvis/nodes/` — Nos do grafo GitHub Agent (classificador de issues)
- `backend/src/jarvis/prompts/` — System prompts especializados (GitHub Agent)
- `backend/tests/` — Testes unitários
- `frontend/` — Interface web (React + Vite + TypeScript)
- `trilha/` — Documentação incremental da trilha de aprendizado (etapas 00–06)

## Comandos Essenciais

```bash
# Setup backend
python -m venv .venv && source .venv/bin/activate
pip install -e ./backend
pip install -e "./backend[dev]"    # inclui pytest

# Setup frontend
cd frontend && npm install

# Executar CLI
jarvis-chat "Pergunta aqui"   # single-turn
jarvis-chat                    # modo interativo (multi-turno)

# Dev (backend + frontend juntos)
python run.py                      # checks, migrations, pergunta porta, sobe tudo

# Executar frontend (dev, standalone)
cd frontend && npm run dev

# Testes
cd backend && python -m pytest tests/ -v
python -m pytest tests/test_tools.py -v   # teste individual

# Alembic (migrations manuais — apenas com PostgreSQL)
cd backend && alembic upgrade head    # aplica migrations
cd backend && alembic current         # verifica versao atual
cd backend && alembic history         # lista migrations

# Variáveis de ambiente
cp backend/.env.example .env       # configurar OPENAI_API_KEY
```

## Arquitetura do Grafo (LangGraph)

### Grafo Conversacional (Chat)

Fluxo: `START → assistant → [tools → assistant]* → END`
- O nó `assistant` chama o LLM com system prompt + histórico trimado
- Se há `tool_calls` na resposta e não atingiu `max_tool_steps`, vai para `tools`
- O nó `tools` executa as ferramentas e incrementa o contador
- Sem `tool_calls` → encerra
- `_sanitize_tool_sequences` valida consistência de tool calls no histórico antes de enviar ao modelo
- `_trim_and_prepend_system` conta turnos humanos (HumanMessage) para trimming — preserva blocos completos de tool calls dentro de cada turno

### Grafo GitHub Agent

Fluxo: `START → classifier → assistant → [tools → assistant]* → END`
- O nó `classifier` classifica a issue (BUG, FEATURE, DOCS, QUESTION, SECURITY) via LLM e injeta contexto no historico
- O nó `assistant` usa apenas `GITHUB_TOOLS` (8 tools via PyGithub)
- `GitHubGraphState` extende o state com campos de issue: `issue_title`, `issue_body`, `issue_number`, `repo`, `issue_category`
- `build_github_graph()` constroi o grafo completo com classificador como entry point
- Classificador em `nodes/classifier.py`: prompt estruturado, fallback para QUESTION se resposta invalida
- System prompt dedicado em `prompts/github_agent.py` (`GITHUB_AGENT_PROMPT`): instrucoes por categoria (labels, branches, PRs, comentarios)

### Webhook GitHub

- `POST /webhook/github` — Recebe webhooks do GitHub (eventos de issues)
- Validacao HMAC-SHA256 via `GITHUB_WEBHOOK_SECRET` (opcional, se nao configurado aceita tudo)
- Filtra apenas eventos `issues` com acoes `opened`, `edited` e `labeled`
- So processa issues com label `jarvis-agent` (ignora as demais)
- Processa em background via FastAPI `BackgroundTasks` — responde 200 imediatamente
- Registra cada execucao na tabela `agent_runs` (status: processing → completed/failed, categoria, tool_steps, error_message)
- Evento `ping` retorna `{"status": "pong"}` (usado pelo GitHub ao configurar webhook)

### GitHub Actions

- Workflow `.github/workflows/jarvis-agent.yml` — alternativa ao webhook para processar issues
- Trigger: `issues: [opened, edited, labeled]`
- Condicao: `if: contains(github.event.issue.labels.*.name, 'jarvis-agent')` — so executa com label
- Permissions: `contents: write`, `issues: write`, `pull-requests: write`
- Executa inline Python que le `GITHUB_EVENT_PATH`, constroi o grafo GitHub e invoca com dados da issue
- Usa `GITHUB_AGENT_PROMPT` como system prompt (mesmo prompt do webhook)
- Secrets necessarios: `OPENAI_API_KEY`, `GITHUB_TOKEN`, `GITHUB_WEBHOOK_SECRET`

## Streaming e Protocolo WebSocket

`stream_chat()` retorna `AsyncGenerator[dict, None]` com eventos tipados:

```jsonc
{"type": "token", "content": "texto"}                                    // texto incremental
{"type": "tool_start", "name": "calculator", "call_id": "call_xxx"}      // início de tool call
{"type": "tool_end", "name": "calculator", "call_id": "call_xxx", "output": "4"}  // resultado
{"type": "end"}                                                          // fim (emitido pela API)
{"type": "error", "content": "..."}                                      // erro (emitido pela API)
```

- O WS handler (`api.py`) repassa os dicts diretamente ao frontend
- A CLI filtra apenas eventos `type=token` para renderizar Markdown no terminal
- O frontend exibe indicadores visuais de tool calls antes da resposta de texto

## Autenticacao e Multi-usuario

- JWT stateless com access token (30min) e refresh token (7 dias)
- Banco auth: SQLite (`.jarvis-auth.db`) ou PostgreSQL (via `DATABASE_URL`) — tabelas: `users`, `global_config`, `user_config`, `agent_runs`
- `db_factory.py` seleciona backend automaticamente: `create_auth_db()`, `get_db_module()`, `get_integrity_error()`
- Senhas com bcrypt (hash direto, sem passlib)
- PyJWT: `sub` claim e string (`str(user_id)` / `int(data["sub"])`)
- Endpoints: `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- WebSocket auth via query param `?token=<jwt>`
- Thread namespace: `thread_id = f"{user_id}:{provided_thread}"` — isola conversas por usuario
- Registro apenas via admin (sem self-registration)
- CLI sem auth (backward compatible)

## Admin Panel

### Backend (`/admin/*`)
- Protegido por `dependencies=[Depends(get_admin_user)]`
- Users CRUD: `GET/POST /admin/users`, `GET/PUT/DELETE /admin/users/{id}`, `PUT /admin/users/{id}/password`
- Config: `GET/PUT /admin/config` (global), `GET/PUT /admin/users/{id}/config` (por usuario)
- Logs: `GET /admin/logs` (lista threads paginada), `GET /admin/logs/{thread_id}` (mensagens)
- Agent Runs: `GET /admin/agent-runs` (lista paginada com filtro por status), `GET /admin/agent-runs/{id}` (detalhes)
- `graph_cache.py`: LRU cache de grafos compilados por (model_name, system_prompt, history_window)

### Frontend (`/admin/*`)
- Rota protegida por `AdminRoute` (role=admin)
- Layout com sidebar (Usuarios, Logs, Agent, Config) + link para voltar ao chat
- `adminApi.ts`: client tipado para todos os endpoints admin
- Paginas: `UsersPage` (CRUD tabela), `LogsPage` (viewer de threads), `AgentRunsPage` (monitoramento de execucoes do agente GitHub), `ConfigPage` (editor global/por usuario)

## Cartola FC Tools

Subpacote `backend/src/jarvis/cartola/` com 5 ferramentas para o Cartola FC:

- `cartola_market_status` — Status do mercado (rodada, fechamento, times escalados)
- `cartola_players` — Busca jogadores com filtros (posicao, clube, preco, media, status)
- `cartola_round_scores` — Top pontuadores de uma rodada com scouts
- `cartola_matches` — Partidas de uma rodada com placares
- `cartola_expert_tips` — Dicas de especialistas via Firecrawl (dependencia opcional)

Arquitetura:
- `client.py`: HTTP client usando `urllib.request` (sem dependencia extra), constantes de mapeamento, cache Redis opcional via `cached_get()`
- `tools.py`: 5 `@tool` functions registradas em `CARTOLA_TOOLS`, importadas por `tools/__init__.py` → `ALL_TOOLS`
- `scraper.py`: Import lazy de `firecrawl-py`, `FIRECRAWL_API_KEY` via `os.getenv`
- `cache.py`: Wrapper Redis com `get_redis()` e `cached_get(key, ttl, fetch_fn)` — fallback sem Redis
- API publica: `api.cartola.globo.com` (sem autenticacao)
- Cache Redis: market_status=5min, players=10min, scored=5min, matches=30min
- Zero mudanca no grafo/chat/api — integracao via `ALL_TOOLS`
- System prompt (`DEFAULT_SYSTEM_PROMPT`) instrui o LLM a usar ferramentas cartola_* proativamente e guia montagem de escalacoes passo a passo

## GitHub Tools

Modulo `backend/src/jarvis/tools/github.py` com 8 ferramentas para interagir com repositorios GitHub via PyGithub:

- `github_read_issue` — Le titulo, corpo e labels de uma issue
- `github_read_file` — Le conteudo de um arquivo do repositorio (trunca em 15k chars)
- `github_list_files` — Lista arquivos e diretorios de um caminho
- `github_comment_issue` — Comenta em uma issue
- `github_create_branch` — Cria branch a partir de outra
- `github_create_or_update_file` — Cria ou atualiza arquivo com commit
- `github_create_pr` — Abre PR como draft
- `github_add_label` — Adiciona label a uma issue/PR

Arquitetura:
- `tools/github.py`: 8 `@tool` functions, cliente PyGithub via `_get_client()` com lazy init
- `tools/base.py`: tools basicas (calculator, current_time) extraidas do antigo `tools.py`
- `tools/__init__.py`: agrega `BASE_TOOLS` + `CARTOLA_TOOLS` + `GITHUB_TOOLS` em `ALL_TOOLS`
- Dependencia opcional: `pip install -e './backend[github]'` (PyGithub)
- Env var: `GITHUB_TOKEN` (Personal Access Token com permissoes de repo)
- Validacao de inputs dentro das tools, retorna mensagem de erro amigavel
- Zero mudanca no grafo/chat/api — integracao via `ALL_TOOLS`

## Startup (run.py)

`run.py` na raiz do projeto substitui o antigo `dev.sh`. Fluxo:

1. Verifica Python >= 3.11
2. Verifica `.env` (warn se ausente)
3. Verifica pacote `jarvis` instalado
4. Verifica `frontend/node_modules/` (warn se ausente)
5. Se `DATABASE_URL` configurado: testa conexao PostgreSQL via `asyncpg`
6. Se `REDIS_URL` configurado: testa conexao Redis via `redis.ping()`
7. Se PostgreSQL: roda `alembic upgrade head` (ou `stamp head` se banco pre-existente sem alembic_version)
8. Pergunta porta (default 8000)
9. Sobe `jarvis-api` + `npm run dev` como subprocessos

Funcoes utilitarias exportadas: `check_python_version()`, `check_env_file()`, `parse_port()` — testadas em `test_run.py`.

## Alembic Migrations

- Config em `backend/alembic.ini`, `backend/alembic/env.py`
- Migrations manuais com SQL raw em `backend/alembic/versions/`
- `env.py` resolve URL dinamicamente: `DATABASE_URL` → `postgresql+psycopg://`, senao `sqlite:///`
- Migration `001_initial_auth_schema.py`: cria tabelas `users`, `user_config`, `global_config` (detecta dialect para DDL correto)
- Migration `002_agent_runs.py`: cria tabela `agent_runs` para monitoramento de execucoes do agente GitHub
- Bancos pre-existentes (criados pelo `CREATE IF NOT EXISTS`): `run.py` detecta e faz `alembic stamp head`
- SQLite: tabelas continuam sendo criadas em runtime via `db.py` (Alembic e skip)
- Novas migrations: `cd backend && alembic revision -m "descricao"` e editar manualmente

## Docker (Deploy / EasyPanel)

Dockerfiles separados para backend e frontend, pensados para EasyPanel (cada servico = container independente).

Arquivos:
- `backend/Dockerfile` — Multi-stage build (python:3.12-slim): builder instala pacote, runtime copia site-packages + Alembic config
- `backend/entrypoint.sh` — Roda `alembic upgrade head` se `DATABASE_URL` definido, depois sobe uvicorn
- `frontend/Dockerfile` — Multi-stage build (node:22-alpine + nginx:alpine): build com `npm ci` + `npm run build`, serve com nginx
- `frontend/nginx.conf.template` — Template nginx com `$BACKEND_URL` (envsubst): proxy `/ws`, `/auth`, `/chat`, `/admin/(users|config|logs|agent-runs)` para backend, SPA fallback para React Router
- `.dockerignore` — Exclui .venv, node_modules, .env, .git, *.db, caches

Nginx distingue rotas frontend (SPA) vs backend (API):
- `/admin/(users|config|logs)` → proxy backend (API endpoints)
- `/admin` (pagina), `/login`, `/` → try_files (SPA React Router)
- `/ws` → WebSocket proxy com upgrade
- `/auth`, `/chat` → proxy backend

Build:
```bash
docker build -t jarvis-backend -f backend/Dockerfile ./backend
docker build -t jarvis-frontend -f frontend/Dockerfile ./frontend
```

EasyPanel:
1. Servico backend: Dockerfile `backend/Dockerfile`, env vars: `OPENAI_API_KEY`, `JWT_SECRET`, `DATABASE_URL`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `REDIS_URL` (opcional)
2. Servico frontend: Dockerfile `frontend/Dockerfile`, env var: `BACKEND_URL=http://<nome-backend>:8000`
3. Frontend exposto com dominio/HTTPS. Trafego API proxied pelo nginx para o backend via rede interna Docker.

## Estilo de Código

- Python moderno (type hints, dataclasses, async/await)
- Imports relativos dentro do pacote `jarvis` (ex: `from .config import ...`)
- Strings sem acentos no código-fonte (ASCII only em mensagens ao usuário)
- Docstrings em português
- Funções async para interações com LLM/grafo
- `@tool` decorator do LangChain para definir ferramentas

## Convenções de Teste

- Cada módulo tem um `test_<módulo>.py` correspondente
- Usar pytest-asyncio para testes de funções async
- Nomear testes descritivamente: `test_<funcionalidade>_<cenário>`

## Avisos Importantes

- NUNCA adicionar `Co-authored-by` em mensagens de commit
- NUNCA commitar `.env` — contém `OPENAI_API_KEY`
- O arquivo `.jarvis.db` é criado em runtime para persistência de memória
- **ANTES de cada commit**, SEMPRE atualizar a documentação (CLAUDE.md, backend/CLAUDE.md, README.md) para refletir as mudanças feitas no código. Docs desatualizadas são tratadas como bug.
- Ver @README.md para overview e instruções de uso
- Ver @trilha/README.md para roadmap das etapas de aprendizado
- Ver @backend/pyproject.toml para dependências e entry points
