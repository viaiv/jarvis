from unittest.mock import patch

import pytest

from jarvis.cartola.tools import (
    cartola_market_status,
    cartola_players,
    cartola_round_scores,
    cartola_matches,
    cartola_expert_tips,
)


# --- Fixtures de dados ---

MARKET_STATUS_OPEN = {
    "rodada_atual": 10,
    "status_mercado": 1,
    "fechamento": {"timestamp": 1700000000},
    "times_escalados": 500000,
}

MARKET_STATUS_CLOSED = {
    "rodada_atual": 10,
    "status_mercado": 2,
    "fechamento": {},
    "times_escalados": 800000,
}

PLAYERS_DATA = {
    "atletas": [
        {
            "apelido": "Arrascaeta",
            "posicao_id": 4,
            "clube_id": 262,
            "status_id": 7,
            "media_num": 8.5,
            "preco_num": 18.0,
            "pontos_num": 12.0,
        },
        {
            "apelido": "Pedro",
            "posicao_id": 5,
            "clube_id": 262,
            "status_id": 7,
            "media_num": 7.2,
            "preco_num": 14.0,
            "pontos_num": 5.0,
        },
        {
            "apelido": "Raphael Veiga",
            "posicao_id": 4,
            "clube_id": 275,
            "status_id": 7,
            "media_num": 6.0,
            "preco_num": 12.0,
            "pontos_num": 3.0,
        },
        {
            "apelido": "Jogador Duvida",
            "posicao_id": 5,
            "clube_id": 275,
            "status_id": 2,
            "media_num": 9.0,
            "preco_num": 20.0,
            "pontos_num": 0.0,
        },
    ],
    "clubes": {
        "262": {"nome": "Flamengo", "abreviacao": "FLA"},
        "275": {"nome": "Palmeiras", "abreviacao": "PAL"},
    },
    "posicoes": {
        "4": {"nome": "Meia", "abreviacao": "MEI"},
        "5": {"nome": "Atacante", "abreviacao": "ATA"},
    },
}

SCORED_DATA = {
    "atletas": {
        "123": {
            "apelido": "Arrascaeta",
            "pontuacao": 15.5,
            "scout": {"G": 1, "A": 1, "SG": 1},
        },
        "456": {
            "apelido": "Pedro",
            "pontuacao": 8.0,
            "scout": {"G": 1},
        },
    }
}

MATCHES_DATA = {
    "clubes": {
        "262": {"nome": "Flamengo"},
        "275": {"nome": "Palmeiras"},
    },
    "partidas": [
        {
            "clube_casa_id": 262,
            "clube_visitante_id": 275,
            "placar_oficial_mandante": 2,
            "placar_oficial_visitante": 1,
            "local": "Maracana",
            "timestamp": 1700000000,
        },
        {
            "clube_casa_id": 275,
            "clube_visitante_id": 262,
            "placar_oficial_mandante": None,
            "placar_oficial_visitante": None,
            "local": "Allianz Parque",
            "timestamp": None,
        },
    ],
}


class TestCartolaMarketStatus:
    @patch("jarvis.cartola.tools.client.fetch_market_status")
    def test_market_open(self, mock_fetch):
        mock_fetch.return_value = MARKET_STATUS_OPEN
        result = cartola_market_status.invoke({})
        assert "Rodada: 10" in result
        assert "Aberto" in result
        assert "500000" in result

    @patch("jarvis.cartola.tools.client.fetch_market_status")
    def test_market_closed(self, mock_fetch):
        mock_fetch.return_value = MARKET_STATUS_CLOSED
        result = cartola_market_status.invoke({})
        assert "Fechado" in result
        assert "Nao informado" in result

    @patch("jarvis.cartola.tools.client.fetch_market_status")
    def test_http_error(self, mock_fetch):
        mock_fetch.side_effect = Exception("Connection timeout")
        result = cartola_market_status.invoke({})
        assert "Erro" in result
        assert "Connection timeout" in result


class TestCartolaPlayers:
    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_default_filter_provavel(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({})
        assert "Arrascaeta" in result
        assert "Pedro" in result
        assert "Jogador Duvida" not in result

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_filter_by_position(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"position": "ATA"})
        assert "Pedro" in result
        assert "Arrascaeta" not in result

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_filter_by_club(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"club": "Palmeiras"})
        assert "Raphael Veiga" in result
        assert "Arrascaeta" not in result

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_filter_by_max_price(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"max_price": 15.0})
        assert "Pedro" in result
        assert "Raphael Veiga" in result
        assert "Arrascaeta" not in result

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_order_by_preco(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"order_by": "preco"})
        lines = result.strip().split("\n")
        assert "Arrascaeta" in lines[0]

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_limit(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"limit": 1})
        lines = result.strip().split("\n")
        assert len(lines) == 1

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_invalid_position(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"position": "XXX"})
        assert "invalida" in result

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_no_results(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"club": "TimeFicticio"})
        assert "Nenhum jogador encontrado" in result

    @patch("jarvis.cartola.tools.client.fetch_players")
    def test_filter_status_todos(self, mock_fetch):
        mock_fetch.return_value = PLAYERS_DATA
        result = cartola_players.invoke({"status": "todos"})
        assert "Jogador Duvida" in result
        assert "Arrascaeta" in result


class TestCartolaRoundScores:
    @patch("jarvis.cartola.tools.client.fetch_scored")
    def test_formats_scores_with_scouts(self, mock_fetch):
        mock_fetch.return_value = SCORED_DATA
        result = cartola_round_scores.invoke({})
        assert "Arrascaeta" in result
        assert "15.5" in result
        assert "G:1" in result

    @patch("jarvis.cartola.tools.client.fetch_scored")
    def test_sorted_by_score(self, mock_fetch):
        mock_fetch.return_value = SCORED_DATA
        result = cartola_round_scores.invoke({})
        lines = result.strip().split("\n")
        assert "Arrascaeta" in lines[0]
        assert "Pedro" in lines[1]

    @patch("jarvis.cartola.tools.client.fetch_scored")
    def test_no_scored_players(self, mock_fetch):
        mock_fetch.return_value = {"atletas": {}}
        result = cartola_round_scores.invoke({})
        assert "Nenhum jogador pontuado" in result

    @patch("jarvis.cartola.tools.client.fetch_scored")
    def test_specific_round(self, mock_fetch):
        mock_fetch.return_value = SCORED_DATA
        cartola_round_scores.invoke({"round_number": 5})
        mock_fetch.assert_called_once_with(5)


class TestCartolaMatches:
    @patch("jarvis.cartola.tools.client.fetch_matches")
    def test_formats_matches_with_score(self, mock_fetch):
        mock_fetch.return_value = MATCHES_DATA
        result = cartola_matches.invoke({})
        assert "Flamengo" in result
        assert "2 x 1" in result
        assert "Maracana" in result

    @patch("jarvis.cartola.tools.client.fetch_matches")
    def test_pending_score(self, mock_fetch):
        mock_fetch.return_value = MATCHES_DATA
        result = cartola_matches.invoke({})
        assert "A definir" in result

    @patch("jarvis.cartola.tools.client.fetch_matches")
    def test_no_matches(self, mock_fetch):
        mock_fetch.return_value = {"clubes": {}, "partidas": []}
        result = cartola_matches.invoke({})
        assert "Nenhuma partida encontrada" in result


class TestCartolaExpertTips:
    @patch("jarvis.cartola.tools.scraper.scrape_tips")
    def test_delegates_to_scraper(self, mock_scrape):
        mock_scrape.return_value = "Dicas aqui..."
        result = cartola_expert_tips.invoke({})
        assert result == "Dicas aqui..."
        mock_scrape.assert_called_once_with("cartolafcbrasil")

    @patch("jarvis.cartola.tools.scraper.scrape_tips")
    def test_custom_source(self, mock_scrape):
        mock_scrape.return_value = "Dicas do mix..."
        result = cartola_expert_tips.invoke({"source": "cartolafcmix"})
        mock_scrape.assert_called_once_with("cartolafcmix")
