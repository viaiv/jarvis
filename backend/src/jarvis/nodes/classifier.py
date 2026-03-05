"""No classificador de issues para o grafo GitHub do Jarvis.

Analisa titulo e corpo da issue e classifica em uma categoria
antes do agente decidir como agir.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

ISSUE_CATEGORIES = ("BUG", "FEATURE", "DOCS", "QUESTION", "SECURITY")

IssueCategory = Literal["BUG", "FEATURE", "DOCS", "QUESTION", "SECURITY"]

CLASSIFIER_PROMPT = (
    "Voce e um classificador de issues do GitHub. "
    "Analise o titulo e corpo da issue e responda com EXATAMENTE uma palavra: "
    "BUG, FEATURE, DOCS, QUESTION ou SECURITY.\n\n"
    "Criterios:\n"
    "- BUG: algo esta quebrado, erro, comportamento inesperado, regressao\n"
    "- FEATURE: nova funcionalidade, melhoria, enhancement, request\n"
    "- DOCS: documentacao, typo, README, exemplos, comentarios\n"
    "- QUESTION: duvida, pergunta, como fazer, help wanted\n"
    "- SECURITY: vulnerabilidade, exposicao de dados, CVE, dependencia insegura\n\n"
    "Responda APENAS com a categoria, sem explicacao."
)


async def classify_issue(
    title: str,
    body: str,
    model_name: str = "gpt-4.1-mini",
) -> IssueCategory:
    """Classifica uma issue do GitHub em uma categoria.

    Args:
        title: Titulo da issue.
        body: Corpo da issue.
        model_name: Modelo LLM a usar.

    Returns:
        Categoria da issue (BUG, FEATURE, DOCS, QUESTION ou SECURITY).
    """
    model = ChatOpenAI(model=model_name, temperature=0)

    user_content = f"Titulo: {title}\n\nCorpo:\n{body or '(sem descricao)'}"

    response = await model.ainvoke([
        SystemMessage(content=CLASSIFIER_PROMPT),
        HumanMessage(content=user_content),
    ])

    raw = response.content.strip().upper()

    # Extrair categoria valida da resposta (pode conter texto extra)
    for category in ISSUE_CATEGORIES:
        if category in raw:
            return category

    # Fallback se o modelo responder algo inesperado
    return "QUESTION"
