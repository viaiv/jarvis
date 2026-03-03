"""Scraper de dicas de especialistas via Firecrawl (dependencia opcional)."""

from __future__ import annotations

import os

_MAX_CHARS = 3000

SOURCES: dict[str, str] = {
    "cartolafcbrasil": "https://www.cartolafcbrasil.com.br/dicas",
    "cartolafcmix": "https://www.cartolafcmix.com",
}


def scrape_tips(source: str = "cartolafcbrasil") -> str:
    """Busca dicas de especialistas via Firecrawl scrape."""
    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        return (
            "FIRECRAWL_API_KEY nao configurada. "
            "Defina no .env para usar dicas de especialistas."
        )

    if source not in SOURCES:
        opcoes = ", ".join(sorted(SOURCES.keys()))
        return f"Source invalida: '{source}'. Opcoes: {opcoes}"

    try:
        from firecrawl import FirecrawlApp  # type: ignore[import-untyped]
    except ImportError:
        return (
            "firecrawl-py nao instalado. "
            "Instale com: pip install -e './backend[cartola]'"
        )

    app = FirecrawlApp(api_key=api_key)
    url = SOURCES[source]
    result = app.scrape_url(url, params={
        "formats": ["markdown"],
        "onlyMainContent": True,
    })

    markdown = result.get("markdown", "")
    if not markdown:
        return f"Nenhum conteudo extraido de {url}."

    if len(markdown) > _MAX_CHARS:
        markdown = markdown[:_MAX_CHARS] + "\n\n[... truncado]"
    return markdown
