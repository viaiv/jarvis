"""Cache Redis para ferramentas do Cartola FC (opcional)."""

from __future__ import annotations

import json
import os
from typing import Any, Callable

import redis

_client: redis.Redis | None = None


def get_redis(redis_url: str = "") -> redis.Redis | None:
    """Retorna cliente Redis sync. None se nao configurado."""
    global _client
    if _client is not None:
        return _client
    url = redis_url or os.getenv("REDIS_URL", "")
    if not url:
        return None
    _client = redis.from_url(url, decode_responses=True)
    return _client


def cached_get(key: str, ttl: int, fetch_fn: Callable[[], Any]) -> Any:
    """Busca no Redis; se miss, chama fetch_fn e salva com TTL.

    Funciona sem Redis (fallback = chamada direta).
    """
    r = get_redis()
    if r:
        try:
            cached = r.get(key)
            if cached is not None:
                return json.loads(cached)
        except redis.RedisError:
            pass

    result = fetch_fn()

    if r:
        try:
            r.setex(key, ttl, json.dumps(result, ensure_ascii=False))
        except (redis.RedisError, TypeError):
            pass

    return result
