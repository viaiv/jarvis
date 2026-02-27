# Jarvis App

Codigo fonte do assistente usado na trilha de aprendizado com LangChain e LangGraph.
Fluxo atual: CLI com tool calling basico orquestrado por LangGraph.

## Modulos

- `jarvis/cli.py`: entrada principal da aplicacao.
- `jarvis/config.py`: configuracao por ambiente.
- `jarvis/tools.py`: tools (calculadora e horario).
- `jarvis/graph.py`: montagem do StateGraph.
- `jarvis/chat.py`: execucao do chat sobre o grafo.
- `jarvis/memory.py`: persistencia de historico por sessao em JSON.
- `jarvis/chat_once.py`: compatibilidade com entrypoint legado.
