import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from starlette.testclient import TestClient

from jarvis.api import app
from jarvis.config import Settings


class FakeGraph:
    """Simula ainvoke para testes HTTP."""

    def __init__(self, response_content="resposta fake"):
        self.response_content = response_content

    async def ainvoke(self, state, config=None):
        ai_msg = AIMessage(content=self.response_content)
        return {"messages": state["messages"] + [ai_msg]}


class FakeStreamGraph:
    """Simula astream para testes WebSocket."""

    def __init__(self, tokens=None):
        self.tokens = tokens or ["Ola", " mundo"]

    async def astream(self, state, config=None, stream_mode=None):
        for token in self.tokens:
            yield (
                AIMessageChunk(content=token),
                {"langgraph_node": "assistant"},
            )


class FakeStreamGraphWithTools:
    """Simula astream com tool_start e tool_end."""

    async def astream(self, state, config=None, stream_mode=None):
        chunk = AIMessageChunk(content="")
        chunk.tool_call_chunks = [
            {"name": "calculator", "args": '{"expression": "2+2"}', "id": "call_1", "index": 0}
        ]
        yield (chunk, {"langgraph_node": "assistant"})

        yield (
            ToolMessage(content="4", name="calculator", tool_call_id="call_1"),
            {"langgraph_node": "tools"},
        )

        yield (
            AIMessageChunk(content="O resultado e 4."),
            {"langgraph_node": "assistant"},
        )


def fake_settings(**overrides):
    defaults = dict(
        system_prompt="prompt teste",
        model_name="gpt-test",
        history_window=3,
        max_tool_steps=5,
        db_path=":memory:",
        session_id="test-session",
        persist_memory=False,
    )
    defaults.update(overrides)
    return Settings(**defaults)


@pytest.fixture()
def setup_app():
    """Injeta FakeGraph + settings no app.state (bypass lifespan)."""
    app.state.graph = FakeGraph()
    app.state.settings = fake_settings()
    yield
    del app.state.graph
    del app.state.settings


@pytest.fixture()
def setup_app_stream():
    """Injeta FakeStreamGraph + settings no app.state (bypass lifespan)."""
    app.state.graph = FakeStreamGraph()
    app.state.settings = fake_settings()
    yield
    del app.state.graph
    del app.state.settings


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_response_with_default_thread(self, setup_app):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/chat", json={"message": "Ola"})

        assert resp.status_code == 200
        body = resp.json()
        assert body["response"] == "resposta fake"
        assert body["thread_id"] == "test-session"

    @pytest.mark.asyncio
    async def test_chat_response_with_custom_thread(self, setup_app):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/chat",
                json={"message": "Ola", "thread_id": "custom-123"},
            )

        assert resp.status_code == 200
        assert resp.json()["thread_id"] == "custom-123"

    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self, setup_app):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/chat", json={})

        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_response_fallback(self, setup_app):
        from httpx import ASGITransport, AsyncClient

        app.state.graph = FakeGraph(response_content="")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/chat", json={"message": "Ola"})

        assert resp.status_code == 200
        assert resp.json()["response"] == "Nao foi possivel gerar resposta."


@pytest.fixture()
def setup_app_stream_tools():
    """Injeta FakeStreamGraphWithTools + settings no app.state."""
    app.state.graph = FakeStreamGraphWithTools()
    app.state.settings = fake_settings()
    yield
    del app.state.graph
    del app.state.settings


class TestWebSocketEndpoint:
    def test_streaming_tokens(self, setup_app_stream):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"message": "Ola"})

            data1 = ws.receive_json()
            assert data1 == {"type": "token", "content": "Ola"}

            data2 = ws.receive_json()
            assert data2 == {"type": "token", "content": " mundo"}

            data3 = ws.receive_json()
            assert data3 == {"type": "end"}

    def test_missing_message_returns_error(self, setup_app_stream):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"text": "Ola"})

            data = ws.receive_json()
            assert data["type"] == "error"
            assert "message" in data["content"].lower()

    def test_multiple_messages_same_connection(self, setup_app_stream):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            # First message
            ws.send_json({"message": "Ola"})
            tokens = []
            while True:
                data = ws.receive_json()
                if data["type"] == "end":
                    break
                tokens.append(data["content"])
            assert tokens == ["Ola", " mundo"]

            # Second message on same connection
            ws.send_json({"message": "Tudo bem?"})
            tokens2 = []
            while True:
                data = ws.receive_json()
                if data["type"] == "end":
                    break
                tokens2.append(data["content"])
            assert tokens2 == ["Ola", " mundo"]

    def test_tool_events_through_ws(self, setup_app_stream_tools):
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            ws.send_json({"message": "Quanto e 2+2?"})

            events = []
            while True:
                data = ws.receive_json()
                if data["type"] == "end":
                    break
                events.append(data)

            types = [e["type"] for e in events]
            assert "tool_start" in types
            assert "tool_end" in types
            assert "token" in types

            tool_start = next(e for e in events if e["type"] == "tool_start")
            assert tool_start["name"] == "calculator"
            assert tool_start["call_id"] == "call_1"

            tool_end = next(e for e in events if e["type"] == "tool_end")
            assert tool_end["name"] == "calculator"
            assert tool_end["output"] == "4"
