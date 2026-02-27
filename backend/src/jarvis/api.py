from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from pydantic import BaseModel

from .chat import invoke_chat, stream_chat
from .config import load_settings
from .graph import build_graph


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

    async with AsyncSqliteSaver.from_conn_string(conn_string) as checkpointer:
        graph = build_graph(
            model_name=settings.model_name,
            system_prompt=settings.system_prompt,
            history_window=settings.history_window,
            checkpointer=checkpointer,
        )
        app.state.graph = graph
        app.state.settings = settings
        yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    settings = app.state.settings
    thread_id = request.thread_id or settings.session_id

    response = await invoke_chat(
        graph=app.state.graph,
        user_input=request.message,
        max_tool_steps=settings.max_tool_steps,
        thread_id=thread_id,
    )

    return ChatResponse(response=response, thread_id=thread_id)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    settings = app.state.settings

    try:
        while True:
            data = await ws.receive_json()

            message = data.get("message")
            if not message:
                await ws.send_json(
                    {"type": "error", "content": "Campo 'message' e obrigatorio."}
                )
                continue

            thread_id = data.get("thread_id") or settings.session_id

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
