import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage
from starlette.testclient import TestClient

from jarvis.api import app
from jarvis.auth import create_access_token
from jarvis.config import Settings
from jarvis.db import create_user, init_db


def _make_settings(**overrides) -> Settings:
    defaults = dict(
        system_prompt="prompt teste",
        model_name="gpt-test",
        history_window=3,
        max_tool_steps=5,
        db_path=":memory:",
        session_id="test-session",
        persist_memory=False,
        jwt_secret="test-secret",
        jwt_access_expiry_minutes=30,
        jwt_refresh_expiry_days=7,
        auth_db_path=":memory:",
        admin_username="admin",
        admin_email="admin@test.local",
        admin_password="admin123",
    )
    defaults.update(overrides)
    return Settings(**defaults)


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


JWT_SECRET = "test-secret"


@pytest_asyncio.fixture()
async def setup_auth():
    """Cria auth DB com usuario de teste e injeta no app.state."""
    conn = await init_db(":memory:")
    user = await create_user(conn, "testuser", "test@test.com", "testpass")
    admin = await create_user(conn, "admin", "admin@test.com", "adminpass", role="admin")

    settings = _make_settings(jwt_secret=JWT_SECRET)

    app.state.settings = settings
    app.state.auth_db = conn
    app.state.graph = FakeGraph()

    token = create_access_token(user["id"], user["role"], JWT_SECRET)
    admin_token = create_access_token(admin["id"], admin["role"], JWT_SECRET)

    yield {
        "user": user,
        "admin": admin,
        "token": token,
        "admin_token": admin_token,
        "conn": conn,
    }

    await conn.close()
    for attr in ("graph", "settings", "auth_db"):
        if hasattr(app.state, attr):
            delattr(app.state, attr)


@pytest_asyncio.fixture()
async def setup_auth_stream(setup_auth):
    """Mesmo que setup_auth mas com FakeStreamGraph."""
    app.state.graph = FakeStreamGraph()
    yield setup_auth


@pytest_asyncio.fixture()
async def setup_auth_stream_tools(setup_auth):
    """Mesmo que setup_auth mas com FakeStreamGraphWithTools."""
    app.state.graph = FakeStreamGraphWithTools()
    yield setup_auth


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/auth/login",
                json={"username": "testuser", "password": "testpass"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/auth/login",
                json={"username": "testuser", "password": "wrong"},
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/auth/login",
                json={"username": "ghost", "password": "x"},
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_token(self, setup_auth):
        from httpx import ASGITransport, AsyncClient
        from jarvis.auth import create_refresh_token

        refresh = create_refresh_token(
            setup_auth["user"]["id"], "user", JWT_SECRET,
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/auth/refresh",
                json={"refresh_token": refresh},
            )

        assert resp.status_code == 200
        assert "access_token" in resp.json()

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/auth/refresh",
                json={"refresh_token": setup_auth["token"]},
            )

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {setup_auth['token']}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["username"] == "testuser"
        assert body["role"] == "user"

    @pytest.mark.asyncio
    async def test_me_without_token_returns_401(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/auth/me")

        assert resp.status_code == 401


class TestChatEndpoint:
    @pytest.mark.asyncio
    async def test_chat_response_with_auth(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/chat",
                json={"message": "Ola"},
                headers={"Authorization": f"Bearer {setup_auth['token']}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["response"] == "resposta fake"

    @pytest.mark.asyncio
    async def test_chat_without_auth_returns_401(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/chat", json={"message": "Ola"})

        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_chat_with_custom_thread(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/chat",
                json={"message": "Ola", "thread_id": "custom-123"},
                headers={"Authorization": f"Bearer {setup_auth['token']}"},
            )

        assert resp.status_code == 200
        assert resp.json()["thread_id"] == "custom-123"

    @pytest.mark.asyncio
    async def test_missing_message_returns_422(self, setup_auth):
        from httpx import ASGITransport, AsyncClient

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/chat",
                json={},
                headers={"Authorization": f"Bearer {setup_auth['token']}"},
            )

        assert resp.status_code == 422


class TestWebSocketEndpoint:
    @pytest.mark.asyncio
    async def test_streaming_tokens_with_auth(self, setup_auth_stream):
        ctx = setup_auth_stream
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={ctx['token']}") as ws:
            ws.send_json({"message": "Ola"})

            data1 = ws.receive_json()
            assert data1 == {"type": "token", "content": "Ola"}

            data2 = ws.receive_json()
            assert data2 == {"type": "token", "content": " mundo"}

            data3 = ws.receive_json()
            assert data3 == {"type": "end"}

    @pytest.mark.asyncio
    async def test_ws_without_token_closes(self, setup_auth):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws") as ws:
                ws.send_json({"message": "Ola"})

    @pytest.mark.asyncio
    async def test_ws_with_invalid_token_closes(self, setup_auth):
        client = TestClient(app)
        with pytest.raises(Exception):
            with client.websocket_connect("/ws?token=bad-token") as ws:
                ws.send_json({"message": "Ola"})

    @pytest.mark.asyncio
    async def test_missing_message_returns_error(self, setup_auth_stream):
        ctx = setup_auth_stream
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={ctx['token']}") as ws:
            ws.send_json({"text": "Ola"})

            data = ws.receive_json()
            assert data["type"] == "error"
            assert "message" in data["content"].lower()

    @pytest.mark.asyncio
    async def test_tool_events_through_ws(self, setup_auth_stream_tools):
        ctx = setup_auth_stream_tools
        client = TestClient(app)
        with client.websocket_connect(f"/ws?token={ctx['token']}") as ws:
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
