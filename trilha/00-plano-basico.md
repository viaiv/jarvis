# Plano Básico (LangChain + LangGraph)

## 1) Fundação

- Aprender: `LLM`, `Prompt`, `Chain`, `Tool`, `Agent`, `Graph`.
- Construir: setup do projeto (`.env`, cliente de modelo, estrutura inicial).
- Resultado esperado: script simples respondendo com o modelo.

## 2) Assistente mínimo com LangChain

- Aprender: `System Prompt`, mensagens e pipeline de execução.
- Construir: chat básico com histórico curto em memória.
- Resultado esperado: manter contexto em 2-3 mensagens.

## 3) Tool Calling básico

- Aprender: quando e como o modelo chama ferramentas.
- Construir: 2 tools iniciais (ex.: calculadora e hora atual).
- Resultado esperado: assistente aciona tools quando necessário.

## 4) Migração para LangGraph

- Aprender: estado explícito, nós e transições.
- Construir: fluxo `entrada -> roteador -> tool/resposta -> saída`.
- Resultado esperado: fluxo claro e fácil de depurar.

## 5) Memória e robustez inicial

- Aprender: memória por sessão e tratamento de erros.
- Construir: persistência simples (arquivo/SQLite), retry e logs.
- Resultado esperado: conversas sobrevivem reinício da aplicação.

## 6) Mini projeto consolidado

- Aprender: organização para escala.
- Construir: Jarvis v1 com comandos claros e testes básicos.
- Resultado esperado: base pronta para evoluções sem retrabalho.
