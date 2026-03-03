"""Cliente HTTP para a API publica do Cartola FC."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from ..cache import cached_get

BASE_URL = "https://api.cartola.globo.com"
_TIMEOUT = 15
_USER_AGENT = "Jarvis/1.0"

# Mapeamentos de posicao (id -> nome e sigla -> id)
POSICAO_MAP: dict[int, str] = {
    1: "Goleiro",
    2: "Lateral",
    3: "Zagueiro",
    4: "Meia",
    5: "Atacante",
    6: "Tecnico",
}

POSICAO_SIGLA_TO_ID: dict[str, int] = {
    "GOL": 1,
    "LAT": 2,
    "ZAG": 3,
    "MEI": 4,
    "ATA": 5,
    "TEC": 6,
    "goleiro": 1,
    "lateral": 2,
    "zagueiro": 3,
    "meia": 4,
    "atacante": 5,
    "tecnico": 6,
}

# Status do jogador (id -> nome)
STATUS_MAP: dict[int, str] = {
    2: "Duvida",
    3: "Suspenso",
    5: "Contundido",
    6: "Nulo",
    7: "Provavel",
}


def _get_json(path: str) -> dict[str, Any]:
    """Faz GET na API do Cartola e retorna o JSON parseado."""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_market_status() -> dict[str, Any]:
    """Retorna status do mercado: rodada, status, fechamento."""
    return cached_get("cartola:market_status", 300, lambda: _get_json("/mercado/status"))


def fetch_players() -> dict[str, Any]:
    """Retorna lista de jogadores disponiveis no mercado."""
    return cached_get("cartola:players", 600, lambda: _get_json("/atletas/mercado"))


def fetch_scored(round_number: int | None = None) -> dict[str, Any]:
    """Retorna jogadores pontuados (rodada atual ou especifica)."""
    path = "/atletas/pontuados"
    if round_number:
        path = f"{path}/{round_number}"
    key = f"cartola:scored:{round_number or 'current'}"
    return cached_get(key, 300, lambda: _get_json(path))


def fetch_matches(round_number: int | None = None) -> dict[str, Any]:
    """Retorna partidas (rodada atual ou especifica)."""
    path = "/partidas"
    if round_number:
        path = f"{path}/{round_number}"
    key = f"cartola:matches:{round_number or 'current'}"
    return cached_get(key, 1800, lambda: _get_json(path))
