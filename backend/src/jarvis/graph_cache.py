"""Cache LRU de grafos compilados por configuracao."""

from functools import lru_cache

from .graph import build_graph


@lru_cache(maxsize=16)
def _cached_build(
    model_name: str,
    system_prompt: str,
    history_window: int,
) -> object:
    """Constroi grafo sem checkpointer (usado como chave de cache)."""
    return build_graph(
        model_name=model_name,
        system_prompt=system_prompt,
        history_window=history_window,
        checkpointer=None,
    )


def get_or_build_graph(
    model_name: str,
    system_prompt: str,
    history_window: int,
    checkpointer=None,
):
    """Retorna grafo do cache ou constroi novo.

    Se checkpointer for fornecido, sempre constroi novo (checkpointer
    nao e hashable). Se nao, usa cache LRU.
    """
    if checkpointer is not None:
        return build_graph(
            model_name=model_name,
            system_prompt=system_prompt,
            history_window=history_window,
            checkpointer=checkpointer,
        )

    return _cached_build(model_name, system_prompt, history_window)


def cache_info():
    """Retorna stats do cache."""
    return _cached_build.cache_info()


def cache_clear():
    """Limpa cache de grafos."""
    _cached_build.cache_clear()
