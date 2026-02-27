# Jarvis

Projeto de estudo para aprender `LangChain` e `LangGraph` por etapas.

## Estrutura

- `backend/`: codigo executavel do assistente (Python/FastAPI).
- `frontend/`: interface web (React + Vite + TypeScript).
- `trilha/`: documentacao incremental da trilha de aprendizado.

Arquitetura atual do backend (`backend/src/jarvis/`):

- `cli.py`: interface de linha de comando e loop interativo.
- `config.py`: leitura e validacao de configuracoes do `.env`, campos auth/JWT.
- `tools.py`: ferramentas disponiveis para o agente.
- `graph.py`: definicao e compilacao do fluxo no LangGraph + sanitizacao de historico.
- `graph_cache.py`: LRU cache de grafos compilados por config.
- `chat.py`: streaming de eventos tipados (token, tool_start, tool_end) e invocacao do grafo.
- `api.py`: API REST (HTTP + WebSocket) com FastAPI, auth JWT.
- `auth.py`: hash bcrypt, JWT encode/decode.
- `db.py`: banco auth (aiosqlite) com CRUD users e config.
- `deps.py`: FastAPI dependencies para autenticacao.
- `admin.py`: APIRouter `/admin` com CRUD usuarios, config e logs.
- `logs.py`: extracao read-only de threads e mensagens do checkpoint.
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

## Autenticacao

A API usa JWT stateless para autenticacao. No primeiro boot, um usuario admin e criado automaticamente com as credenciais definidas no `.env`.

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
JARVIS_MAX_TOOL_STEPS=5
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

### Tools iniciais

- `calculator(expression)`: calculos aritmeticos.
- `current_time(timezone_name)`: horario atual por fuso (ex.: `UTC`, `America/Sao_Paulo`).

Exemplos:

```bash
jarvis-chat "Quanto e (15 + 7) * 3?"
jarvis-chat "Que horas sao em America/Sao_Paulo?"
```

### Memoria persistente

- A conversa e salva por sessao em SQLite (`.jarvis.db`) via checkpointer do LangGraph.
- Ao reiniciar o app, o historico da sessao e recarregado automaticamente.
- A janela curta (`JARVIS_HISTORY_WINDOW`) limita o contexto enviado ao modelo,
  mas o historico completo continua salvo no banco.
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

## Trilha

Veja os arquivos em `trilha/` para acompanhar o plano e a evolucao.
