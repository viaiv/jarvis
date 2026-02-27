# Etapa 3: Tool Calling basico

## Objetivo

Permitir que o assistente use ferramentas simples para responder tarefas objetivas.

## Checklist de aprendizado

- [x] Entender fluxo: pergunta -> decisao de tool -> execucao -> resposta final.
- [x] Entender `tool_call` e retorno via `ToolMessage`.
- [x] Entender limites operacionais (ex.: maximo de passos por resposta).

## Checklist de implementacao

- [x] Criar tool `calculator(expression)`.
- [x] Criar tool `current_time(timezone_name)`.
- [x] Integrar tools no `jarvis-chat`.
- [x] Adicionar limite de passos (`JARVIS_MAX_TOOL_STEPS` / `--max-tool-steps`).
- [x] Validar com testes manuais de calculo e horario.

## Entregavel da etapa

Assistente CLI capaz de usar ferramentas automaticamente para calculos e horario.

## Como testar rapido

1. `jarvis-chat "Quanto e (12 + 8) * 4?"`
2. `jarvis-chat "Que horas sao em UTC?"`
3. `jarvis-chat` e pedir dois calculos em sequencia.

## Proximo passo

Depois desta etapa, seguir para `trilha/04-migracao-langgraph.md`.
