# Etapa 5: Memoria persistente

## Objetivo

Manter historico de conversa entre execucoes do app usando armazenamento local por sessao.

## Checklist de aprendizado

- [x] Entender diferenca entre memoria de contexto (janela curta) e memoria persistente.
- [x] Entender isolamento por sessao (`session_id`).
- [ ] Entender estrategia de evolucao para SQLite/checkpointer.

## Checklist de implementacao

- [x] Criar persistencia local em JSON.
- [x] Carregar historico salvo no inicio da execucao.
- [x] Salvar historico apos cada resposta.
- [x] Adicionar configuracoes de memoria no `.env` e CLI.
- [ ] Validar fluxo completo em 2 execucoes separadas com mesma sessao.

## Entregavel da etapa

Assistente com memoria por sessao sobrevivendo reinicios do processo.

## Como testar rapido

1. `jarvis-chat --session-id aula` e enviar duas mensagens.
2. Encerrar com `sair`.
3. Rodar novamente `jarvis-chat --session-id aula` e confirmar recarga do historico.
4. Opcional: `jarvis-chat --no-memory` para modo sem persistencia.

## Proximo passo

Evoluir de JSON local para armazenamento robusto (SQLite/checkpointer) e observabilidade.
