---
globs: ["app/tests/**/*.py"]
---

# Convenções de Teste

- Arquivo de teste espelha módulo: `test_<módulo>.py`
- Nomear testes: `test_<funcionalidade>_<cenário>` (ex: `test_calculator_division_by_zero`)
- Usar `pytest.mark.asyncio` para testes de funções async
- Preferir rodar testes individuais durante desenvolvimento: `python -m pytest tests/test_tools.py -v`
- Mocks para chamadas de API/LLM — nunca depender de chamadas reais em testes
- Fixtures compartilhadas no `conftest.py` quando reutilizáveis
