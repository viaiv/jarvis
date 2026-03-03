"""Testes para funcoes utilitarias do run.py."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Adiciona raiz do projeto ao path para importar run.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import run  # noqa: E402


class TestCheckPythonVersion:
    def test_version_ok(self):
        """Versao atual do Python deve passar (estamos rodando >= 3.11)."""
        assert run.check_python_version((3, 11)) is True

    def test_version_too_low(self):
        """Simula versao abaixo do minimo."""
        with patch.object(sys, "version_info", (3, 10, 0)):
            assert run.check_python_version((3, 11)) is False

    def test_version_exact_match(self):
        """Versao exatamente igual ao minimo deve passar."""
        with patch.object(sys, "version_info", (3, 11, 0)):
            assert run.check_python_version((3, 11)) is True

    def test_version_above(self):
        """Versao acima do minimo deve passar."""
        with patch.object(sys, "version_info", (3, 12, 0)):
            assert run.check_python_version((3, 11)) is True


class TestCheckEnvFile:
    def test_env_exists(self, tmp_path):
        """Deve retornar True quando .env existe."""
        env_file = tmp_path / "backend" / ".env"
        env_file.parent.mkdir()
        env_file.write_text("KEY=value")
        with patch.object(run, "BACKEND_DIR", tmp_path / "backend"), \
             patch.object(run, "PROJECT_ROOT", tmp_path):
            assert run.check_env_file() is True

    def test_env_missing(self, tmp_path):
        """Deve retornar True (warn, nao bloqueante) quando .env nao existe."""
        with patch.object(run, "BACKEND_DIR", tmp_path / "backend"), \
             patch.object(run, "PROJECT_ROOT", tmp_path):
            assert run.check_env_file() is True


class TestParsePort:
    def test_default_on_empty(self):
        """Input vazio retorna porta default."""
        assert run.parse_port("") == 8000
        assert run.parse_port("  ") == 8000

    def test_custom_port(self):
        """Input numerico valido retorna a porta."""
        assert run.parse_port("9000") == 9000
        assert run.parse_port(" 3000 ") == 3000

    def test_invalid_returns_default(self):
        """Input nao numerico retorna default."""
        assert run.parse_port("abc") == 8000

    def test_out_of_range_returns_default(self):
        """Porta fora de range retorna default."""
        assert run.parse_port("0") == 8000
        assert run.parse_port("70000") == 8000

    def test_custom_default(self):
        """Parametro default personalizado funciona."""
        assert run.parse_port("", default=3000) == 3000
