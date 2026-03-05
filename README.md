# Jarvis

Projeto de estudo para aprender `LangChain` e `LangGraph` por etapas.

## Estrutura

- `backend/`: codigo executavel do assistente (Python/FastAPI).
- `frontend/`: interface web (React + Vite + TypeScript).
- `trilha/`: documentacao incremental da trilha de aprendizado.

Arquitetura atual do backend (`backend/src/jarvis/`):

- `cli.py`: interface de linha de comando e loop interativo.
- `config.py`: leitura e validacao de configuracoes do `.env`, campos auth/JWT/infra, system prompt com instrucoes Cartola FC.
- `tools/`: pacote de ferramentas (calculator, current_time, Cartola FC, GitHub).
- `cartola/`: subpacote com ferramentas do Cartola FC (client HTTP, tools, scraper).
- `graph.py`: definicao e compilacao do fluxo no LangGraph (`build_graph` para chat, `build_github_graph` para agente GitHub com classificador) + sanitizacao de historico.
- `nodes/`: nos do grafo GitHub Agent (classificador de issues via LLM).
- `graph_cache.py`: LRU cache de grafos compilados por config.
- `chat.py`: streaming de eventos tipados (token, tool_start, tool_end) e invocacao do grafo.
- `api.py`: API REST (HTTP + WebSocket) com FastAPI, auth JWT.
- `auth.py`: hash bcrypt, JWT encode/decode.
- `db.py`: banco auth SQLite (aiosqlite) com CRUD users e config.
- `db_postgres.py`: banco auth PostgreSQL (asyncpg), mesma interface que `db.py`.
- `db_factory.py`: factory que seleciona SQLite ou PostgreSQL baseado em `DATABASE_URL`.
- `checkpoint.py`: factory de checkpointer (AsyncSqliteSaver ou AsyncPostgresSaver).
- `cache.py`: wrapper Redis com `cached_get()` e fallback sem Redis.
- `deps.py`: FastAPI dependencies para autenticacao.
- `admin.py`: APIRouter `/admin` com CRUD usuarios, config e logs.
- `logs.py`: extracao read-only de threads e mensagens do checkpoint (SQLite ou PostgreSQL).
- `schemas.py`: Pydantic models para auth, admin e logs.

## Setup rapido

1. Crie e ative um ambiente virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instale as dependencias do backend:

```bash
pip install -e ./backend
```

3. Instale as dependencias do frontend:

```bash
cd frontend && npm install
```

4. Configure ambiente:

```bash
cp backend/.env.example .env
```

Edite `.env` e preencha as variaveis necessarias:

```env
OPENAI_API_KEY=sk-...
JWT_SECRET=uma-chave-secreta-forte
ADMIN_USERNAME=admin
ADMIN_PASSWORD=senha-do-admin
```

### Infraestrutura opcional

Por padrao, o Jarvis usa SQLite para tudo (zero config). Para produção, configure PostgreSQL e/ou Redis:

```env
# PostgreSQL (auth + checkpoint — substitui SQLite)
DATABASE_URL=postgresql://user:pass@localhost:5432/jarvis

# Redis (cache para tools do Cartola FC)
REDIS_URL=redis://localhost:6379
```

Sem essas variaveis, tudo continua funcionando com SQLite e sem cache (backward compatible).

### GitHub Agent (opcional)

Para usar as ferramentas de automacao GitHub (ler issues, criar PRs, etc):

```bash
pip install -e "./backend[github]"
```

Configure no `.env`:

```env
GITHUB_TOKEN=ghp_...
GITHUB_WEBHOOK_SECRET=seu-webhook-secret
```

## Desenvolvimento

Para subir backend + frontend juntos:

```bash
python run.py
```

O script verifica dependencias (Python, backend, frontend), testa conectividade com PostgreSQL e Redis (se configurados), roda migrations do Alembic (se PostgreSQL), pergunta a porta do backend (default 8000) e sobe ambos os processos. O proxy do Vite aponta automaticamente para a porta escolhida.

Para usar uma porta customizada sem o script:

```bash
JARVIS_PORT=9000 jarvis-api
```

### Migrations (Alembic)

Com PostgreSQL configurado, `run.py` roda `alembic upgrade head` automaticamente. Para gerenciar migrations manualmente:

```bash
cd backend
alembic upgrade head      # aplica migrations pendentes
alembic current           # verifica versao atual
alembic history           # lista migrations
alembic revision -m "descricao"  # cria nova migration
```

Com SQLite (default), tabelas sao criadas em runtime via `db.py` e Alembic e ignorado.

## Autenticacao

A API usa JWT stateless para autenticacao. No primeiro boot, um usuario admin e criado automaticamente com as credenciais definidas no `.env`.

O banco de auth usa SQLite por padrao (`.jarvis-auth.db`) ou PostgreSQL quando `DATABASE_URL` esta configurado. A selecao e automatica via `db_factory.py`.

- `POST /auth/login` — retorna access + refresh token
- `POST /auth/refresh` — renova access token
- `GET /auth/me` — dados do usuario autenticado

O WebSocket recebe o token via query param: `/ws?token=<jwt>`.

Registro de novos usuarios e feito apenas pelo admin via painel administrativo.

A CLI continua funcionando sem autenticacao (backward compatible).

## Admin Panel

Acessivel em `/admin` para usuarios com role `admin`.

- **Usuarios**: CRUD completo (criar, editar, desativar, resetar senha).
- **Logs**: visualizar conversas de qualquer usuario com filtro e paginacao.
- **Config**: editar configuracao global e por usuario (model, system prompt, history window, max tool steps).

Endpoints do backend em `/admin/*`, protegidos por `get_admin_user` dependency.

## Chat atual (Etapa 5)

O assistente agora roda com `LangGraph` no ciclo:

- `assistant -> tools -> assistant` (quando houver `tool_calls`)
- encerramento quando nao houver chamada de ferramenta

Mensagem unica:

```bash
jarvis-chat "Explique em 3 linhas o que e um prompt."
```

Modo interativo (multi-turno):

```bash
jarvis-chat
```

No modo interativo, digite `sair` para encerrar.

Configurar memoria curta e limite de tools no `.env`:

```env
JARVIS_HISTORY_WINDOW=3
JARVIS_MAX_TOOL_STEPS=10
JARVIS_SESSION_ID=default
JARVIS_PERSIST_MEMORY=true
```

Ou sobrescrever por comando:

```bash
jarvis-chat --max-turns 2
jarvis-chat --max-tool-steps 3
jarvis-chat --session-id estudo
jarvis-chat --no-memory
```

### Tools

- `calculator(expression)`: calculos aritmeticos.
- `current_time(timezone_name)`: horario atual por fuso (ex.: `UTC`, `America/Sao_Paulo`).

#### Cartola FC

5 ferramentas para consultar dados do Cartola FC via API publica (`api.cartola.globo.com`):

- `cartola_market_status`: status do mercado (rodada, fechamento, times escalados).
- `cartola_players`: busca jogadores com filtros (posicao, clube, preco, media, status).
- `cartola_round_scores`: top pontuadores de uma rodada com scouts.
- `cartola_matches`: partidas de uma rodada com placares.
- `cartola_expert_tips`: dicas de especialistas via Firecrawl (requer `FIRECRAWL_API_KEY`).

Respostas da API sao cacheadas automaticamente no Redis quando `REDIS_URL` esta configurado (TTLs de 5 a 30 minutos). Sem Redis, funciona normalmente sem cache.

Para usar dicas de especialistas, instale a dependencia opcional:

```bash
pip install -e "./backend[cartola]"
```

E configure no `.env`:

```env
FIRECRAWL_API_KEY=fc-...
```

Exemplos:

```bash
jarvis-chat "Qual o status do mercado do Cartola?"
jarvis-chat "Me mostra os melhores atacantes provaveis ate 15 cartoletas"
jarvis-chat "Quem mais pontuou na ultima rodada?"
jarvis-chat "Quais os jogos da proxima rodada?"
```

#### GitHub

8 ferramentas para interagir com repositorios GitHub via PyGithub (requer `GITHUB_TOKEN`):

- `github_read_issue`: le titulo, corpo e labels de uma issue.
- `github_read_file`: le conteudo de um arquivo do repositorio.
- `github_list_files`: lista arquivos e diretorios.
- `github_comment_issue`: comenta em uma issue.
- `github_create_branch`: cria branch a partir de outra.
- `github_create_or_update_file`: cria ou atualiza arquivo com commit.
- `github_create_pr`: abre PR como draft.
- `github_add_label`: adiciona label a uma issue/PR.

Instale a dependencia opcional:

```bash
pip install -e "./backend[github]"
```

Exemplos:

```bash
jarvis-chat "Leia a issue #1 do repo viaiv/jarvis"
jarvis-chat "Liste os arquivos na raiz do repo viaiv/jarvis"
jarvis-chat "Crie uma branch fix/42 no repo viaiv/jarvis"
```

### Memoria persistente

- A conversa e salva por sessao via checkpointer do LangGraph (SQLite ou PostgreSQL via `checkpoint.py`).
- Ao reiniciar o app, o historico da sessao e recarregado automaticamente.
- A janela curta (`JARVIS_HISTORY_WINDOW`) conta turnos humanos (HumanMessage), nao mensagens individuais — preserva blocos completos de tool calls dentro de cada turno.
- `_sanitize_tool_sequences` garante que o historico trimado nao contenha
  sequencias incompletas de tool calls (evita erros da API da OpenAI).

## Frontend

Interface web para o assistente, construida com React + Vite + TypeScript.
Design escuro com estetica de command interface (cyan accent, tipografia Syne/Outfit/JetBrains Mono).

```bash
cd frontend
npm install
npm run dev
```

O dev server sobe em `http://localhost:5173`.

### Streaming via WebSocket

O frontend conecta ao backend via WebSocket (`/ws`) e recebe eventos tipados:

- `token`: texto incremental da resposta.
- `tool_start`: indica que uma ferramenta foi chamada (exibe indicador visual com dot pulsante).
- `tool_end`: resultado da ferramenta (atualiza indicador com output e dot verde).
- `end`: fim da resposta.

### Design

- Paleta escura com base navy (#050a14) e accent cyan (#00d4ff).
- Mensagens do usuario: cards com fundo cyan translucido, alinhados a direita.
- Mensagens do assistente: texto com borda esquerda cyan, sem card de fundo.
- Tool calls: pills monospace inline com indicador de status (pulsando/concluido).
- Input: estilo command prompt com prefixo `>` e glow on focus.
- Fontes: Syne (display), Outfit (body), JetBrains Mono (code/tools) via Google Fonts.

### Arquivos

- `src/App.tsx`: componente principal com chat, tool calls e empty state.
- `src/useChat.ts`: hook de conexao WebSocket e gerenciamento de mensagens.
- `src/types.ts`: tipos de chat, auth e admin.
- `src/index.css`: tema customizado (Tailwind v4 @theme), animacoes e prose overrides.
- `src/routes.tsx`: rotas da aplicacao (login, chat, admin).
- `src/auth/AuthContext.tsx`: provider de autenticacao com login/logout e auto-refresh.
- `src/auth/ProtectedRoute.tsx`: redirect para login se nao autenticado.
- `src/auth/AdminRoute.tsx`: redirect se nao admin.
- `src/auth/authFetch.ts`: wrapper fetch com Bearer token e auto-refresh em 401.
- `src/pages/LoginPage.tsx`: tela de login.
- `src/layouts/AdminLayout.tsx`: layout com sidebar para area admin.
- `src/pages/admin/UsersPage.tsx`: CRUD de usuarios.
- `src/pages/admin/LogsPage.tsx`: viewer de conversas.
- `src/pages/admin/ConfigPage.tsx`: editor de config global e por usuario.
- `src/api/adminApi.ts`: client tipado para endpoints admin.

## Docker (Deploy)

O projeto inclui Dockerfiles separados para backend e frontend, prontos para deploy no EasyPanel ou qualquer plataforma com containers.

### Build

```bash
docker build -t jarvis-backend -f backend/Dockerfile ./backend
docker build -t jarvis-frontend -f frontend/Dockerfile ./frontend
```

### Teste local com Docker

```bash
docker network create jarvis-net

docker run -d --name backend --network jarvis-net \
  -e OPENAI_API_KEY=sk-... \
  -e JWT_SECRET=secret \
  -e ADMIN_USERNAME=admin \
  -e ADMIN_PASSWORD=admin \
  jarvis-backend

docker run -d --name frontend --network jarvis-net \
  -e BACKEND_URL=http://backend:8000 \
  -p 3000:80 \
  jarvis-frontend
```

Acesse `http://localhost:3000`.

### EasyPanel

1. **Servico backend**: Dockerfile `backend/Dockerfile`. Env vars: `OPENAI_API_KEY`, `JWT_SECRET`, `DATABASE_URL` (PostgreSQL), `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `REDIS_URL` (opcional).
2. **Servico frontend**: Dockerfile `frontend/Dockerfile`. Env var: `BACKEND_URL=http://<nome-servico-backend>:8000`.
3. Exponha o frontend com dominio/HTTPS. O nginx interno do frontend faz proxy reverso para o backend pela rede Docker.

### Arquivos Docker

- `backend/Dockerfile` — Multi-stage (python:3.12-slim): instala pacote + copia Alembic config
- `backend/entrypoint.sh` — Roda migrations (se PostgreSQL) e sobe uvicorn
- `frontend/Dockerfile` — Multi-stage (node:22-alpine + nginx:alpine): build + serve estatico
- `frontend/nginx.conf.template` — Nginx com proxy reverso (envsubst `$BACKEND_URL`), WebSocket upgrade, SPA fallback
- `.dockerignore` — Exclui .venv, node_modules, .env, .git, *.db

## Trilha

Veja os arquivos em `trilha/` para acompanhar o plano e a evolucao.
