# Jarvis

Projeto de estudo para aprender `LangChain` e `LangGraph` por etapas.

## Estrutura

- `backend/`: codigo executavel do assistente (Python/FastAPI).
- `frontend/`: interface web (React + Vite + TypeScript).
- `trilha/`: documentacao incremental da trilha de aprendizado.

Arquitetura atual do backend (`backend/src/jarvis/`):

- `cli.py`: interface de linha de comando e loop interativo.
- `config.py`: leitura e validacao de configuracoes do `.env`.
- `tools.py`: ferramentas disponiveis para o agente.
- `graph.py`: definicao e compilacao do fluxo no LangGraph.
- `chat.py`: invocacao do grafo e tratamento de historico.
- `memory.py`: persistencia de historico por sessao.
- `api.py`: API REST com FastAPI.

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

Edite `.env` e preencha `OPENAI_API_KEY`.

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
JARVIS_MEMORY_FILE=.jarvis_memory.json
JARVIS_SESSION_ID=default
JARVIS_PERSIST_MEMORY=true
```

Ou sobrescrever por comando:

```bash
jarvis-chat --max-turns 2
jarvis-chat --max-tool-steps 3
jarvis-chat --session-id estudo
jarvis-chat --memory-file ./data/memoria.json
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

- A conversa e salva por sessao em arquivo JSON.
- Ao reiniciar o app, o historico da sessao e recarregado automaticamente.
- A janela curta (`JARVIS_HISTORY_WINDOW`) limita o contexto enviado ao modelo,
  mas o historico completo continua salvo no arquivo.

## Frontend

Interface web para o assistente, construida com React + Vite + TypeScript.

```bash
cd frontend
npm install
npm run dev
```

O dev server sobe em `http://localhost:5173`.

## Trilha

Veja os arquivos em `trilha/` para acompanhar o plano e a evolucao.
