# Jarvis

Assistente conversacional de estudo construído com LangChain + LangGraph.
Projeto educacional para aprender tool calling, grafos de agentes e memória persistente.

## Stack e Arquitetura

- **Linguagem**: Python 3.11+
- **LLM Framework**: LangChain + LangGraph
- **Modelo padrão**: gpt-4.1-mini (configurável via `.env`)
- **Persistência**: SQLite via `langgraph-checkpoint-sqlite`
- **CLI**: argparse + Rich (streaming com Markdown)
- **API**: FastAPI + Uvicorn
- **Frontend**: React + Vite + TypeScript
- **Testes**: pytest + pytest-asyncio

Mapa de diretórios:
- `backend/src/jarvis/` — Código principal do assistente (Python/FastAPI)
- `backend/tests/` — Testes unitários
- `frontend/` — Interface web (React + Vite + TypeScript)
- `trilha/` — Documentação incremental da trilha de aprendizado (etapas 00–05)

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
- Ver @README.md para overview e instruções de uso
- Ver @trilha/README.md para roadmap das etapas de aprendizado
- Ver @backend/pyproject.toml para dependências e entry points
