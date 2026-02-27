# Etapa 06 — Autenticacao, Multi-usuario e Admin Panel

## Objetivo

Adicionar autenticacao JWT, isolamento de conversas por usuario e painel administrativo completo ao Jarvis.

## O que foi implementado

### Fase 1: Backend Auth

- Banco SQLite separado (`.jarvis-auth.db`) para dados de auth via aiosqlite
- Tabelas: `users`, `global_config`, `user_config`
- Hash de senhas com bcrypt (direto, sem passlib)
- JWT stateless com PyJWT: access token (30min) + refresh token (7 dias)
- Endpoints: `POST /auth/login`, `POST /auth/refresh`, `GET /auth/me`
- FastAPI dependencies: `get_current_user`, `get_current_active_user`, `get_admin_user`
- WebSocket auth via query param `?token=<jwt>`
- Thread namespace: `thread_id = f"{user_id}:{provided_thread}"` isola conversas
- Seed automatico de admin no boot
- CLI sem auth (backward compatible)

### Fase 2: Frontend Auth

- React Router v7 com rotas protegidas
- `AuthContext` com login/logout, tokens em localStorage, auto-refresh
- `ProtectedRoute` redireciona para `/login` se nao autenticado
- `authFetch` wrapper com Bearer token e refresh automatico em 401
- Tela de login com design consistente (dark/cyan)
- WebSocket envia token via query param

### Fase 3: Admin Backend

- APIRouter `/admin` com protecao `get_admin_user`
- CRUD usuarios: criar, listar, editar, deletar, resetar senha
- Config: global e por usuario (model_name, system_prompt, history_window, max_tool_steps)
- Logs: listar threads paginado com filtro por usuario, ver mensagens de um thread
- `graph_cache.py`: LRU cache de grafos compilados por configuracao
- `logs.py`: extracao read-only de threads/mensagens do checkpoint LangGraph
- `schemas.py`: Pydantic models para todos os endpoints

### Fase 4: Admin Frontend

- `AdminRoute` protege rota para role=admin
- `AdminLayout` com sidebar (Usuarios, Logs, Config) e link para voltar ao chat
- `UsersPage`: tabela com CRUD inline, criacao de usuarios, toggle ativo/inativo
- `LogsPage`: lista de threads paginada, filtro por user ID, viewer de mensagens
- `ConfigPage`: editor de config global e por usuario com feedback visual
- `adminApi.ts`: client tipado para todos os endpoints admin

## Decisoes tecnicas

1. **JWT stateless** — sem necessidade de blacklist ou estado no servidor
2. **Banco auth separado** — `.jarvis-auth.db` nao interfere no `.jarvis.db` do LangGraph
3. **bcrypt direto** — passlib tinha incompatibilidade com bcrypt 5.x
4. **PyJWT sub como string** — spec JWT exige `sub` string, convertemos user_id com `str()`/`int()`
5. **Registro apenas via admin** — sem self-registration, admin cria usuarios
6. **LRU cache de grafos** — configs diferentes por usuario sem rebuild constante
7. **CLI sem auth** — manter backward compatibility, auth apenas na API

## Checklist

- [x] Backend auth (JWT, bcrypt, db, dependencies)
- [x] Frontend auth (router, context, login, protected routes)
- [x] Admin backend (users CRUD, config, logs, graph cache)
- [x] Admin frontend (layout, pages, API client)
- [x] 150 testes passando
- [x] Documentacao atualizada

## Variaveis de ambiente novas

```env
JWT_SECRET=chave-secreta-para-jwt
JWT_ACCESS_EXPIRY_MINUTES=30
JWT_REFRESH_EXPIRY_DAYS=7
AUTH_DB_PATH=.jarvis-auth.db
ADMIN_USERNAME=admin
ADMIN_EMAIL=admin@jarvis.local
ADMIN_PASSWORD=senha-do-admin
```
