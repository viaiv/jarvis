---
globs: ["backend/src/jarvis/tools.py"]
---

# Regras para Tools

- Toda tool usa o decorator `@tool` de `langchain_core.tools`
- Docstring da tool é a descrição que o LLM vê — ser conciso e preciso
- Registrar toda nova tool em `ALL_TOOLS` no final de `tools.py`
- Validar inputs dentro da tool e retornar mensagem de erro amigável (não levantar exceção)
- Tools retornam `str` — formato legível para o modelo
- Calculator usa avaliação segura via AST — NUNCA usar `eval()`
