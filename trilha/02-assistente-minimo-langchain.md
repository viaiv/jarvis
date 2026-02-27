# Etapa 2: Assistente minimo com LangChain

## Objetivo

Evoluir de single-turn para multi-turno com historico curto em memoria, mantendo interface simples por CLI.

## Checklist de aprendizado

- [x] Entender `System Prompt` e impacto no comportamento do assistente.
- [x] Entender mensagens `Human` e `AI` no contexto de conversa.
- [x] Entender como limitar memoria por janela de turnos.

## Checklist de implementacao

- [x] Adaptar CLI para modo interativo continuo.
- [x] Manter modo de mensagem unica por argumento.
- [x] Implementar historico curto configuravel (`JARVIS_HISTORY_WINDOW`).
- [x] Validar com conversa real de 3+ turnos.

## Entregavel da etapa

Comando `jarvis-chat` rodando em modo conversacional, com saida por turnos e memoria curta.

## Como testar rapido

1. `jarvis-chat`
2. Fazer 3 perguntas sequenciais com contexto entre elas.
3. Encerrar com `sair`.

Opcional:

- `jarvis-chat --max-turns 2`

## Proximo passo

Depois desta etapa, seguir para `trilha/03-tool-calling-basico.md`.
