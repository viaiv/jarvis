"""Webhook endpoint para eventos do GitHub.

Recebe eventos de issues (opened/edited) e dispara o agente GitHub
em background para classificar, analisar e responder.
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from .config import Settings
from .graph import build_github_graph
from .prompts import GITHUB_AGENT_PROMPT

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


def verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Valida assinatura HMAC-SHA256 do GitHub.

    Args:
        payload: Corpo raw da requisicao.
        signature: Header X-Hub-Signature-256 (formato sha256=<hex>).
        secret: Webhook secret configurado.

    Returns:
        True se a assinatura e valida.
    """
    if not signature or not secret:
        return False

    if not signature.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)


async def _handle_issue_event(
    action: str,
    issue: dict,
    repo_full_name: str,
    settings: Settings,
) -> None:
    """Processa evento de issue em background.

    Constroi o grafo GitHub, executa classificacao e resposta autonoma.
    """
    issue_number = issue.get("number", 0)
    title = issue.get("title", "")
    body = issue.get("body") or ""

    logger.info(
        "Processando issue #%d (%s) em %s — acao: %s",
        issue_number, title, repo_full_name, action,
    )

    try:
        graph = build_github_graph(
            model_name=settings.model_name,
            system_prompt=GITHUB_AGENT_PROMPT,
            max_tool_steps=15,
        )

        initial_state = {
            "messages": [],
            "tool_steps": 0,
            "max_tool_steps": 15,
            "issue_title": title,
            "issue_body": body,
            "issue_number": issue_number,
            "repo": repo_full_name,
            "issue_category": None,
        }

        result = await graph.ainvoke(initial_state)

        category = result.get("issue_category", "QUESTION")
        logger.info(
            "Issue #%d classificada como %s — %d tool steps executados",
            issue_number, category, result.get("tool_steps", 0),
        )

    except Exception:
        logger.exception("Erro ao processar issue #%d em %s", issue_number, repo_full_name)


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Recebe webhooks do GitHub e dispara processamento em background.

    Valida assinatura HMAC-SHA256, filtra eventos de issues (opened/edited)
    e agenda execucao do agente GitHub.
    """
    settings: Settings = request.app.state.settings

    # Validar assinatura
    body = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    if settings.github_webhook_secret:
        if not verify_signature(body, signature, settings.github_webhook_secret):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assinatura invalida.",
            )

    # Parsear evento
    event_type = request.headers.get("X-GitHub-Event", "")
    payload = await request.json()

    # Ping event (GitHub envia ao configurar webhook)
    if event_type == "ping":
        return {"status": "pong"}

    # Filtrar apenas eventos de issues
    if event_type != "issues":
        return {"status": "ignored", "reason": f"evento '{event_type}' nao processado"}

    action = payload.get("action", "")
    if action not in ("opened", "edited"):
        return {"status": "ignored", "reason": f"acao '{action}' nao processada"}

    issue = payload.get("issue", {})
    repo = payload.get("repository", {})
    repo_full_name = repo.get("full_name", "")

    if not issue or not repo_full_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payload incompleto: issue ou repository ausente.",
        )

    # Disparar processamento em background
    background_tasks.add_task(
        _handle_issue_event,
        action=action,
        issue=issue,
        repo_full_name=repo_full_name,
        settings=settings,
    )

    return {
        "status": "accepted",
        "issue_number": issue.get("number"),
        "action": action,
    }
