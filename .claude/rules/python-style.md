---
globs: ["app/src/jarvis/**/*.py"]
---

# Estilo Python — Jarvis

- Usar type hints em todas as assinaturas de função
- Preferir `dataclass(frozen=True)` para objetos de configuração
- Usar `async def` para funções que interagem com LLM ou grafo
- Imports relativos dentro do pacote: `from .module import ...`
- Manter strings do usuário sem acentos (ASCII only)
- Docstrings em português, estilo imperativo ("Aplica...", "Retorna...")
- Não usar `eval()` — toda avaliação de expressão via AST seguro
- Tratar erros com mensagens claras em português para o usuário final
