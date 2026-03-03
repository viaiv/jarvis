import json
from unittest.mock import patch, MagicMock

import pytest

from jarvis.cartola.client import (
    POSICAO_MAP,
    POSICAO_SIGLA_TO_ID,
    STATUS_MAP,
    fetch_market_status,
    fetch_players,
    fetch_scored,
    fetch_matches,
)


class TestMappings:
    def test_posicao_map_has_all_positions(self):
        assert set(POSICAO_MAP.keys()) == {1, 2, 3, 4, 5, 6}

    def test_posicao_sigla_to_id_uppercase(self):
        assert POSICAO_SIGLA_TO_ID["GOL"] == 1
        assert POSICAO_SIGLA_TO_ID["ATA"] == 5

    def test_posicao_sigla_to_id_lowercase(self):
        assert POSICAO_SIGLA_TO_ID["goleiro"] == 1
        assert POSICAO_SIGLA_TO_ID["atacante"] == 5

    def test_status_map_has_provavel(self):
        assert STATUS_MAP[7] == "Provavel"

    def test_status_map_has_duvida(self):
        assert STATUS_MAP[2] == "Duvida"


def _mock_urlopen(response_data):
    """Cria mock de urlopen que retorna JSON."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=cm)
    cm.__exit__ = MagicMock(return_value=False)
    cm.read.return_value = json.dumps(response_data).encode("utf-8")
    return cm


class TestFetchMarketStatus:
    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_returns_parsed_json(self, mock_urlopen):
        payload = {"rodada_atual": 10, "status_mercado": 1}
        mock_urlopen.return_value = _mock_urlopen(payload)
        result = fetch_market_status()
        assert result["rodada_atual"] == 10

    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_calls_correct_url(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({})
        fetch_market_status()
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        assert req.full_url == "https://api.cartola.globo.com/mercado/status"


class TestFetchPlayers:
    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_returns_parsed_json(self, mock_urlopen):
        payload = {"atletas": [], "clubes": {}}
        mock_urlopen.return_value = _mock_urlopen(payload)
        result = fetch_players()
        assert "atletas" in result

    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_calls_correct_url(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({})
        fetch_players()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.cartola.globo.com/atletas/mercado"


class TestFetchScored:
    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_current_round(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"atletas": {}})
        fetch_scored()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.cartola.globo.com/atletas/pontuados"

    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_specific_round(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"atletas": {}})
        fetch_scored(5)
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.cartola.globo.com/atletas/pontuados/5"


class TestFetchMatches:
    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_current_round(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"partidas": []})
        fetch_matches()
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.cartola.globo.com/partidas"

    @patch("jarvis.cartola.client.urllib.request.urlopen")
    def test_specific_round(self, mock_urlopen):
        mock_urlopen.return_value = _mock_urlopen({"partidas": []})
        fetch_matches(3)
        req = mock_urlopen.call_args[0][0]
        assert req.full_url == "https://api.cartola.globo.com/partidas/3"
