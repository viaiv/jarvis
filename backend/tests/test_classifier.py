"""Testes para o classificador de issues."""

from unittest.mock import AsyncMock, patch

import pytest

from jarvis.nodes.classifier import (
    CLASSIFIER_PROMPT,
    ISSUE_CATEGORIES,
    classify_issue,
)


class TestIssueCategories:
    def test_all_categories_present(self):
        assert ISSUE_CATEGORIES == ("BUG", "FEATURE", "DOCS", "QUESTION", "SECURITY")

    def test_prompt_mentions_all_categories(self):
        for cat in ISSUE_CATEGORIES:
            assert cat in CLASSIFIER_PROMPT


class TestClassifyIssue:
    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_bug(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "BUG"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Login quebrado", "O login falha com senha correta")

        assert result == "BUG"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_feature(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "FEATURE"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Adicionar dark mode", "Implementar tema escuro")

        assert result == "FEATURE"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_docs(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "DOCS"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Typo no README", "Corrigir erro de digitacao")

        assert result == "DOCS"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_security(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "SECURITY"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("CVE em dependencia", "Vulnerabilidade critica")

        assert result == "SECURITY"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_question(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "QUESTION"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Como configurar?", "Como faco para usar o Docker?")

        assert result == "QUESTION"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_extracts_category_from_noisy_response(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "Eu acho que e um BUG critico"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Erro 500", "Servidor retorna erro")

        assert result == "BUG"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_fallback_to_question(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "Nao sei classificar isso"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Titulo vago", "Corpo vago")

        assert result == "QUESTION"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_case_insensitive(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "feature"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Nova feature", "Adicionar algo novo")

        assert result == "FEATURE"

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_empty_body(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "BUG"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        result = await classify_issue("Algo quebrado", "")

        assert result == "BUG"
        # Verifica que o corpo vazio gera "(sem descricao)" no prompt
        call_args = mock_model.ainvoke.call_args[0][0]
        user_msg = call_args[1].content
        assert "(sem descricao)" in user_msg

    @pytest.mark.asyncio
    @patch("jarvis.nodes.classifier.ChatOpenAI")
    async def test_classify_uses_correct_model(self, mock_chat):
        mock_model = AsyncMock()
        mock_response = AsyncMock()
        mock_response.content = "BUG"
        mock_model.ainvoke.return_value = mock_response
        mock_chat.return_value = mock_model

        await classify_issue("Titulo", "Corpo", model_name="gpt-4o")

        mock_chat.assert_called_once_with(model="gpt-4o", temperature=0)
