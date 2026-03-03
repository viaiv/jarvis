"""Testes para o modulo cache (Redis wrapper)."""

import json
from unittest.mock import MagicMock, patch

from jarvis.cache import cached_get


class TestCachedGet:
    def test_cache_hit_returns_stored_data(self):
        """Cache hit retorna dados salvos sem chamar fetch_fn."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps({"key": "value"})

        fetch_fn = MagicMock(return_value={"key": "fresh"})

        with patch("jarvis.cache.get_redis", return_value=mock_redis):
            result = cached_get("test:key", 300, fetch_fn)

        assert result == {"key": "value"}
        fetch_fn.assert_not_called()
        mock_redis.setex.assert_not_called()

    def test_cache_miss_calls_fetch_fn(self):
        """Cache miss chama fetch_fn e salva resultado."""
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        data = {"status": "ok", "rodada": 10}
        fetch_fn = MagicMock(return_value=data)

        with patch("jarvis.cache.get_redis", return_value=mock_redis):
            result = cached_get("test:miss", 600, fetch_fn)

        assert result == data
        fetch_fn.assert_called_once()
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args
        assert args[0][0] == "test:miss"
        assert args[0][1] == 600
        assert json.loads(args[0][2]) == data

    def test_no_redis_calls_fetch_directly(self):
        """Sem Redis configurado, funciona normalmente (bypass)."""
        data = [1, 2, 3]
        fetch_fn = MagicMock(return_value=data)

        with patch("jarvis.cache.get_redis", return_value=None):
            result = cached_get("test:no-redis", 300, fetch_fn)

        assert result == data
        fetch_fn.assert_called_once()

    def test_redis_read_error_falls_back_to_fetch(self):
        """Erro ao ler do Redis faz fallback para fetch_fn."""
        import redis

        mock_redis = MagicMock()
        mock_redis.get.side_effect = redis.RedisError("Connection refused")

        data = {"fallback": True}
        fetch_fn = MagicMock(return_value=data)

        with patch("jarvis.cache.get_redis", return_value=mock_redis):
            result = cached_get("test:error", 300, fetch_fn)

        assert result == data
        fetch_fn.assert_called_once()

    def test_redis_write_error_still_returns_data(self):
        """Erro ao escrever no Redis nao afeta retorno."""
        import redis

        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_redis.setex.side_effect = redis.RedisError("Write failed")

        data = {"write_fail": True}
        fetch_fn = MagicMock(return_value=data)

        with patch("jarvis.cache.get_redis", return_value=mock_redis):
            result = cached_get("test:write-err", 300, fetch_fn)

        assert result == data
        fetch_fn.assert_called_once()
