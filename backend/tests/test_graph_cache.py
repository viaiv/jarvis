"""Testes para cache de grafos."""

import os

import pytest

from jarvis.graph_cache import cache_clear, cache_info, get_or_build_graph


@pytest.fixture(autouse=True)
def _clear_cache(monkeypatch):
    """Limpa cache e seta OPENAI_API_KEY fake para build_graph."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fake-test-key")
    cache_clear()
    yield
    cache_clear()


class TestGraphCache:
    def test_cache_returns_same_object(self):
        g1 = get_or_build_graph("gpt-test", "prompt", 3)
        g2 = get_or_build_graph("gpt-test", "prompt", 3)
        assert g1 is g2

    def test_different_params_return_different_graphs(self):
        g1 = get_or_build_graph("gpt-test", "prompt-a", 3)
        g2 = get_or_build_graph("gpt-test", "prompt-b", 3)
        assert g1 is not g2

    def test_cache_info_tracks_hits(self):
        get_or_build_graph("gpt-test", "prompt", 3)
        get_or_build_graph("gpt-test", "prompt", 3)
        info = cache_info()
        assert info.hits == 1
        assert info.misses == 1

    def test_with_checkpointer_bypasses_cache(self):
        from langgraph.checkpoint.memory import InMemorySaver

        g1 = get_or_build_graph("gpt-test", "prompt", 3, checkpointer=InMemorySaver())
        g2 = get_or_build_graph("gpt-test", "prompt", 3, checkpointer=InMemorySaver())
        assert g1 is not g2
        # Cache nao deve ter sido usado
        info = cache_info()
        assert info.hits == 0
        assert info.misses == 0

    def test_cache_clear_resets(self):
        get_or_build_graph("gpt-test", "prompt", 3)
        cache_clear()
        info = cache_info()
        assert info.currsize == 0
