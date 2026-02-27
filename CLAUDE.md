# Jarvis

Assistente conversacional de estudo construído com LangChain + LangGraph.
Projeto educacional para aprender tool calling, grafos de agentes e memória persistente.

## Stack e Arquitetura

- **Linguagem**: Python 3.11+
- **LLM Framework**: LangChain + LangGraph
- **Modelo padrão**: gpt-4.1-mini (configurável via `.env`)
- **Persistência**: SQLite via `langgraph-checkpoint-sqlite`
- **Auth**: JWT stateless (PyJWT + bcrypt), SQLite separado para auth
- **CLI**: argparse + Rich (streaming com Markdown)
- **API**: FastAPI + Uvicorn
- **Frontend**: React + Vite + TypeScript + React Router v7
- **Testes**: pytest + pytest-asyncio

Mapa de diretórios:
- `backend/src/jarvis/` — Código principal do assistente (Python/FastAPI)
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

# Executar frontend (dev)
cd frontend && npm run dev

# Testes
cd backend && python -m pytest tests/ -v
python -m pytest tests/test_tools.py -v   # teste individual

# Variáveis de ambiente
cp backend/.env.example .env       # configurar OPENAI_API_KEY
```

## Arquitetura do Grafo (LangGraph)

Fluxo: `START → assistant → [tools → assistant]* → END`
- O nó `assistant` chama o LLM com system prompt + histórico trimado
- Se há `tool_calls` na resposta e não atingiu `max_tool_steps`, vai para `tools`
- O nó `tools` executa as ferramentas e incrementa o contador
- Sem `tool_calls` → encerra
- `_sanitize_tool_sequences` valida consistência de tool calls no histórico antes de enviar ao modelo
- `_trim_and_prepend_system` aplica janela de histórico + sanitização + system prompt

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
- Banco auth separado (`.jarvis-auth.db`) via aiosqlite — tabelas: `users`, `global_config`, `user_config`
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
- `graph_cache.py`: LRU cache de grafos compilados por (model_name, system_prompt, history_window)

### Frontend (`/admin/*`)
- Rota protegida por `AdminRoute` (role=admin)
- Layout com sidebar (Usuarios, Logs, Config) + link para voltar ao chat
- `adminApi.ts`: client tipado para todos os endpoints admin
- Paginas: `UsersPage` (CRUD tabela), `LogsPage` (viewer de threads), `ConfigPage` (editor global/por usuario)

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
