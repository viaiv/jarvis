# Jarvis App

Pacote Python instalável com o assistente conversacional.

## Módulos

- `cli.py` — Entry point (`jarvis-chat`), parsing de args, loop interativo com Rich
- `config.py` — `Settings` dataclass, leitura de `.env`, overrides de CLI
- `graph.py` — `build_graph()` compila o StateGraph do LangGraph (assistant ↔ tools)
- `chat.py` — `invoke_chat()` e `stream_chat()` para execução do grafo
- `chat_once.py` — Entrypoint legado, redireciona para `cli.main()`
- `tools.py` — Ferramentas: `calculator`, `current_time` + registro em `ALL_TOOLS`

## Fluxo de Dados

1. `cli.py` carrega `Settings` via `config.load_settings()`
2. Aplica overrides de CLI com `config.apply_cli_overrides()`
3. Constrói grafo com `graph.build_graph()` (model, system prompt, checkpointer)
4. Executa via `chat.stream_chat()` (streaming) ou `chat.invoke_chat()`

## Dependências Chave

- `langchain-openai` — Wrapper do ChatOpenAI
- `langgraph` — StateGraph, ToolNode, checkpointer
- `langgraph-checkpoint-sqlite` — Persistência async com SQLite
- `rich` — Renderização Markdown no terminal
- `python-dotenv` — Leitura do `.env`
