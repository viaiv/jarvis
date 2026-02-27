# Etapa 4: Migracao para LangGraph

## Objetivo

Trocar o loop manual de tools por um grafo com estado explicito e roteamento entre nos.

## Checklist de aprendizado

- [x] Entender `StateGraph` com estado de mensagens.
- [x] Entender ciclo `assistant -> tools -> assistant`.
- [x] Entender condicao de parada por ausencia de `tool_calls`.
- [ ] Entender trade-off entre limite de recursao e limite de tool steps.

## Checklist de implementacao

- [x] Migrar execucao para `LangGraph`.
- [x] Preservar tools existentes (`calculator`, `current_time`).
- [x] Preservar CLI atual (`jarvis-chat`, `--max-turns`, `--max-tool-steps`).
- [x] Preservar memoria curta de conversa.
- [x] Refatorar em modulos (`cli`, `config`, `tools`, `graph`, `chat`).
- [ ] Validar fluxo completo com chamadas reais de ferramenta.

## Entregavel da etapa

Assistente executando por grafo compilado no LangGraph, com controle de tool steps.

## Como testar rapido

1. `jarvis-chat "Quanto e (15 + 7) * 3?"`
2. `jarvis-chat "Que horas sao em America/Sao_Paulo?"`
3. `jarvis-chat --max-tool-steps 1 "Resolva esta conta e explique o resultado."`

## Proximo passo

Depois desta etapa, seguir para persistencia de memoria e observabilidade.
