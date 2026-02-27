# Etapa 1: Fundação

## Objetivo

Subir a base do projeto para executar um primeiro chat com modelo e preparar terreno para as próximas etapas.

## Checklist de aprendizado

- [ ] Entender diferença entre `LLM`, `Prompt`, `Chain`, `Tool`, `Agent`, `Graph`.
- [x] Entender fluxo mínimo: `input -> prompt -> modelo -> output`.
- [x] Entender configuração via variáveis de ambiente.

## Checklist de implementação

- [x] Definir estrutura inicial de pastas do projeto.
- [x] Configurar `.env` com chave do provedor.
- [x] Criar script mínimo para enviar uma mensagem ao modelo.
- [x] Validar execução local sem erros.

## Entregável da etapa

Um comando local que recebe texto e retorna resposta do modelo.

## Notas e decisões

- Vamos manter o código simples e modular para migrar para LangGraph sem refatoração grande.
- Cada nova etapa vai gerar um novo arquivo em `trilha/`.
- Comando inicial da etapa: `jarvis-chat`.
- Código do app concentrado em `app/`.

## Próximo passo

Quando esta etapa estiver concluída, seguir para `trilha/02-assistente-minimo-langchain.md`.
