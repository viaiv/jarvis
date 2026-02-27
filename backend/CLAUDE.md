# Jarvis App

Pacote Python instalável com o assistente conversacional.

## Módulos

- `cli.py` — Entry point (`jarvis-chat`), parsing de args, loop interativo com Rich
- `config.py` — `Settings` dataclass, leitura de `.env`, overrides de CLI
- `graph.py` — `build_graph()`, `_trim_and_prepend_system()`, `_sanitize_tool_sequences()`
- `chat.py` — `invoke_chat()` e `stream_chat()` (retorna eventos tipados: token/tool_start/tool_end)
- `chat_once.py` — Entrypoint legado, redireciona para `cli.main()`
- `tools.py` — Ferramentas: `calculator`, `current_time` + registro em `ALL_TOOLS`
- `api.py` — Entry point da API REST (`jarvis-api`), endpoints HTTP + WebSocket

## Fluxo de Dados

1. `cli.py` / `api.py` carrega `Settings` via `config.load_settings()`
2. Aplica overrides de CLI com `config.apply_cli_overrides()` (apenas CLI)
3. Constrói grafo com `graph.build_graph()` (model, system prompt, checkpointer)
4. Executa via `chat.stream_chat()` (streaming de eventos dict) ou `chat.invoke_chat()`
5. `stream_chat()` emite eventos `tool_start` / `tool_end` / `token` — API repassa via WS, CLI filtra tokens

## Dependências Chave

- `langchain-openai` — Wrapper do ChatOpenAI
- `langgraph` — StateGraph, ToolNode, checkpointer
- `langgraph-checkpoint-sqlite` — Persistência async com SQLite
- `rich` — Renderização Markdown no terminal
- `python-dotenv` — Leitura do `.env`
- `fastapi` + `uvicorn` — API REST
