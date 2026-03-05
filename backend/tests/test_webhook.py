"""Testes para o webhook do GitHub."""

import hashlib
import hmac
import json
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from jarvis.webhook import verify_signature


def _make_signature(payload: bytes, secret: str) -> str:
    """Gera assinatura HMAC-SHA256 no formato do GitHub."""
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


class TestVerifySignature:
    def test_valid_signature(self):
        payload = b'{"action": "opened"}'
        secret = "mysecret"
        sig = _make_signature(payload, secret)
        assert verify_signature(payload, sig, secret) is True

    def test_invalid_signature(self):
        payload = b'{"action": "opened"}'
        assert verify_signature(payload, "sha256=invalid", "mysecret") is False

    def test_empty_signature(self):
        assert verify_signature(b"data", "", "secret") is False

    def test_empty_secret(self):
        assert verify_signature(b"data", "sha256=abc", "") is False

    def test_missing_prefix(self):
        payload = b"data"
        secret = "mysecret"
        digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        assert verify_signature(payload, digest, secret) is False

    def test_tampered_payload(self):
        secret = "mysecret"
        sig = _make_signature(b"original", secret)
        assert verify_signature(b"tampered", sig, secret) is False


def _issue_payload(action: str = "opened", number: int = 42) -> dict:
    """Cria payload de evento issues do GitHub."""
    return {
        "action": action,
        "issue": {
            "number": number,
            "title": "Bug no login",
            "body": "O login falha com senha correta",
        },
        "repository": {
            "full_name": "viaiv/jarvis",
        },
    }


@pytest.fixture
def app():
    """Cria app FastAPI com settings para teste."""
    from unittest.mock import MagicMock

    from jarvis.api import app as real_app

    settings = MagicMock()
    settings.github_webhook_secret = "test-secret"
    settings.model_name = "gpt-4.1-mini"
    settings.system_prompt = "Test prompt"
    real_app.state.settings = settings

    return real_app


class TestWebhookEndpoint:
    @pytest.mark.asyncio
    @patch("jarvis.webhook._handle_issue_event")
    async def test_ping_event(self, mock_handle, app):
        payload = json.dumps({"zen": "test"}).encode()
        sig = _make_signature(payload, "test-secret")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "ping",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "pong"
        mock_handle.assert_not_called()

    @pytest.mark.asyncio
    @patch("jarvis.webhook._handle_issue_event")
    async def test_issue_opened_accepted(self, mock_handle, app):
        payload_dict = _issue_payload("opened")
        payload = json.dumps(payload_dict).encode()
        sig = _make_signature(payload, "test-secret")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "issues",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["issue_number"] == 42
        assert data["action"] == "opened"

    @pytest.mark.asyncio
    @patch("jarvis.webhook._handle_issue_event")
    async def test_issue_edited_accepted(self, mock_handle, app):
        payload_dict = _issue_payload("edited")
        payload = json.dumps(payload_dict).encode()
        sig = _make_signature(payload, "test-secret")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "issues",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"

    @pytest.mark.asyncio
    @patch("jarvis.webhook._handle_issue_event")
    async def test_issue_closed_ignored(self, mock_handle, app):
        payload_dict = _issue_payload("closed")
        payload = json.dumps(payload_dict).encode()
        sig = _make_signature(payload, "test-secret")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "issues",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        mock_handle.assert_not_called()

    @pytest.mark.asyncio
    @patch("jarvis.webhook._handle_issue_event")
    async def test_push_event_ignored(self, mock_handle, app):
        payload = json.dumps({"ref": "refs/heads/main"}).encode()
        sig = _make_signature(payload, "test-secret")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ignored"
        mock_handle.assert_not_called()

    @pytest.mark.asyncio
    async def test_invalid_signature_rejected(self, app):
        payload = json.dumps(_issue_payload()).encode()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "issues",
                    "X-Hub-Signature-256": "sha256=invalid",
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    @patch("jarvis.webhook._handle_issue_event")
    async def test_no_secret_skips_validation(self, mock_handle, app):
        """Se webhook_secret nao esta configurado, aceita sem validar."""
        app.state.settings.github_webhook_secret = ""
        payload = json.dumps(_issue_payload()).encode()

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/webhook/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "issues",
                    "Content-Type": "application/json",
                },
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "accepted"
