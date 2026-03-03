from unittest.mock import patch

from jarvis.cartola.scraper import scrape_tips, SOURCES


class TestScrapeTips:
    @patch.dict("os.environ", {}, clear=True)
    def test_no_api_key_returns_error(self):
        result = scrape_tips()
        assert "FIRECRAWL_API_KEY" in result
        assert "nao configurada" in result

    @patch.dict("os.environ", {"FIRECRAWL_API_KEY": "test-key"})
    def test_invalid_source_returns_options(self):
        result = scrape_tips("fonte_invalida")
        assert "invalida" in result
        assert "cartolafcbrasil" in result
        assert "cartolafcmix" in result

    def test_known_sources_exist(self):
        assert "cartolafcbrasil" in SOURCES
        assert "cartolafcmix" in SOURCES
        assert len(SOURCES) >= 2
