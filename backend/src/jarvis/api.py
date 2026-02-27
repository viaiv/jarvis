from contextlib import asynccontextmanager

import jwt as pyjwt
import uvicorn
from fastapi import Depends, FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from .admin import router as admin_router
from .auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from .chat import invoke_chat, stream_chat
from .config import load_settings
from .db import get_user_by_id, get_user_by_username, init_db, seed_admin_if_needed
from .deps import get_current_active_user
from .graph import build_graph
from .schemas import LoginRequest, MeResponse, RefreshRequest, TokenResponse


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    thread_id: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    conn_string = settings.db_path if settings.persist_memory else ":memory:"

    auth_conn = await init_db(settings.auth_db_path)

    await seed_admin_if_needed(
        auth_conn,
        username=settings.admin_username,
        email=settings.admin_email,
        password=settings.admin_password,
    )

    async with AsyncSqliteSaver.from_conn_string(conn_string) as checkpointer:
        graph = build_graph(
            model_name=settings.model_name,
            system_prompt=settings.system_prompt,
            history_window=settings.history_window,
            checkpointer=checkpointer,
        )
        app.state.graph = graph
        app.state.settings = settings
        app.state.auth_db = auth_conn
        app.state.checkpointer = checkpointer
        yield

    await auth_conn.close()


app = FastAPI(lifespan=lifespan)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Auth endpoints ---

@app.post("/auth/login", response_model=TokenResponse)
async def login(request: LoginRequest):
    """Autentica usuario e retorna access + refresh tokens."""
    conn = app.state.auth_db
    settings = app.state.settings

    user = await get_user_by_username(conn, request.username)
    if not user or not verify_password(request.password, user["hashed_password"]):
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais invalidas.",
        )

    if not user["is_active"]:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desativado.",
        )

    access = create_access_token(
        user["id"], user["role"], settings.jwt_secret,
        settings.jwt_access_expiry_minutes,
    )
    refresh = create_refresh_token(
        user["id"], user["role"], settings.jwt_secret,
        settings.jwt_refresh_expiry_days,
    )

    return TokenResponse(access_token=access, refresh_token=refresh)


@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshRequest):
    """Gera novo par de tokens a partir de refresh token valido."""
    from fastapi import HTTPException, status

    settings = app.state.settings
    conn = app.state.auth_db

    try:
        payload = decode_token(request.refresh_token, settings.jwt_secret)
    except pyjwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalido ou expirado.",
        )

    if payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido (tipo incorreto).",
        )

    user = await get_user_by_id(conn, payload.sub)
    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario nao encontrado ou desativado.",
        )

    access = create_access_token(
        user["id"], user["role"], settings.jwt_secret,
        settings.jwt_access_expiry_minutes,
    )
    refresh = create_refresh_token(
        user["id"], user["role"], settings.jwt_secret,
        settings.jwt_refresh_expiry_days,
    )

    return TokenResponse(access_token=access, refresh_token=refresh)


@app.get("/auth/me", response_model=MeResponse)
async def me(user: dict = Depends(get_current_active_user)):
    """Retorna dados do usuario autenticado."""
    return MeResponse(
        id=user["id"],
        username=user["username"],
        email=user["email"],
        role=user["role"],
    )


# --- Chat endpoints (protegidos) ---

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    user: dict = Depends(get_current_active_user),
):
    settings = app.state.settings
    provided_thread = request.thread_id or settings.session_id
    thread_id = f"{user['id']}:{provided_thread}"

    response = await invoke_chat(
        graph=app.state.graph,
        user_input=request.message,
        max_tool_steps=settings.max_tool_steps,
        thread_id=thread_id,
    )

    return ChatResponse(response=response, thread_id=provided_thread)


@app.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str = Query(default=""),
):
    """WebSocket com auth via query param ?token=<jwt>."""
    settings = app.state.settings
    conn = app.state.auth_db

    # Validar token antes de aceitar conexao
    if not token:
        await ws.close(code=4001, reason="Token ausente.")
        return

    try:
        payload = decode_token(token, settings.jwt_secret)
    except pyjwt.InvalidTokenError:
        await ws.close(code=4001, reason="Token invalido.")
        return

    if payload.type != "access":
        await ws.close(code=4001, reason="Token invalido (tipo incorreto).")
        return

    user = await get_user_by_id(conn, payload.sub)
    if not user or not user["is_active"]:
        await ws.close(code=4001, reason="Usuario invalido.")
        return

    await ws.accept()

    try:
        while True:
            data = await ws.receive_json()

            message = data.get("message")
            if not message:
                await ws.send_json(
                    {"type": "error", "content": "Campo 'message' e obrigatorio."}
                )
                continue

            provided_thread = data.get("thread_id") or settings.session_id
            thread_id = f"{user['id']}:{provided_thread}"

            try:
                async for event in stream_chat(
                    graph=app.state.graph,
                    user_input=message,
                    max_tool_steps=settings.max_tool_steps,
                    thread_id=thread_id,
                ):
                    await ws.send_json(event)

                await ws.send_json({"type": "end"})
            except Exception as exc:
                await ws.send_json({"type": "error", "content": str(exc)})

    except WebSocketDisconnect:
        pass


def main():
    uvicorn.run("jarvis.api:app", host="0.0.0.0", port=8000)
