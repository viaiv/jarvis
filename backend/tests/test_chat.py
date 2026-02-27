import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from jarvis.chat import (
    TOOL_LIMIT_MESSAGE,
    invoke_chat,
    stream_chat,
)


class FakeGraph:
    """Simula o grafo do LangGraph para testes."""

    def __init__(self, response_content="resposta do modelo", tool_calls=None):
        self.response_content = response_content
        self.tool_calls = tool_calls or []

    async def ainvoke(self, state, config=None):
        ai_msg = AIMessage(content=self.response_content)
        if self.tool_calls:
            ai_msg.tool_calls = self.tool_calls
        return {"messages": state["messages"] + [ai_msg]}


class TestInvokeChat:
    @pytest.mark.asyncio
    async def test_returns_ai_response(self):
        graph = FakeGraph(response_content="Oi, tudo bem!")
        result = await invoke_chat(
            graph=graph,
            user_input="Ola",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == "Oi, tudo bem!"

    @pytest.mark.asyncio
    async def test_returns_tool_limit_when_tool_calls_remain(self):
        graph = FakeGraph(
            response_content="",
            tool_calls=[{"name": "calculator", "args": {"expression": "1+1"}, "id": "1"}],
        )
        result = await invoke_chat(
            graph=graph,
            user_input="calcule",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == TOOL_LIMIT_MESSAGE

    @pytest.mark.asyncio
    async def test_empty_response_fallback(self):
        graph = FakeGraph(response_content="")
        result = await invoke_chat(
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == "Nao foi possivel gerar resposta."

    @pytest.mark.asyncio
    async def test_no_ai_message_fallback(self):
        class EmptyGraph:
            async def ainvoke(self, state, config=None):
                return {"messages": []}

        result = await invoke_chat(
            graph=EmptyGraph(),
            user_input="oi",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == "Nao foi possivel gerar resposta."

    @pytest.mark.asyncio
    async def test_list_content_rendering(self):
        class ListContentGraph:
            async def ainvoke(self, state, config=None):
                msg = AIMessage(content=[{"text": "parte1"}, {"text": "parte2"}])
                return {"messages": [msg]}

        result = await invoke_chat(
            graph=ListContentGraph(),
            user_input="oi",
            max_tool_steps=5,
            thread_id="test",
        )
        assert "parte1" in result
        assert "parte2" in result

    @pytest.mark.asyncio
    async def test_sends_human_message(self):
        class CapturingGraph:
            def __init__(self):
                self.captured_state = None

            async def ainvoke(self, state, config=None):
                self.captured_state = state
                return {"messages": [AIMessage(content="ok")]}

        graph = CapturingGraph()
        await invoke_chat(
            graph=graph,
            user_input="nova pergunta",
            max_tool_steps=5,
            thread_id="test",
        )
        messages = graph.captured_state["messages"]
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "nova pergunta"

    @pytest.mark.asyncio
    async def test_thread_id_in_config(self):
        class ConfigCapturingGraph:
            def __init__(self):
                self.captured_config = None

            async def ainvoke(self, state, config=None):
                self.captured_config = config
                return {"messages": [AIMessage(content="ok")]}

        graph = ConfigCapturingGraph()
        await invoke_chat(
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="minha-sessao",
        )
        assert graph.captured_config["configurable"]["thread_id"] == "minha-sessao"


class FakeStreamGraph:
    """Simula graph.astream() retornando (chunk, metadata)."""

    def __init__(self, events=None, raise_recursion=False):
        self.events = events or []
        self.raise_recursion = raise_recursion
        self.captured_config = None

    async def astream(self, state, config=None, stream_mode=None):
        self.captured_config = config
        if self.raise_recursion:
            raise GraphRecursionError("recursion limit")
        for event in self.events:
            yield event


class TestStreamChat:
    @pytest.mark.asyncio
    async def test_yields_token_events(self):
        events = [
            (AIMessageChunk(content="Ola"), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content=" mundo"), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content="!"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results == [
            {"type": "token", "content": "Ola"},
            {"type": "token", "content": " mundo"},
            {"type": "token", "content": "!"},
        ]

    @pytest.mark.asyncio
    async def test_skips_non_assistant_text_chunks(self):
        events = [
            (AIMessageChunk(content="ignorar"), {"langgraph_node": "other"}),
            (AIMessageChunk(content="ok"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results == [{"type": "token", "content": "ok"}]

    @pytest.mark.asyncio
    async def test_skips_empty_content_chunks(self):
        events = [
            (AIMessageChunk(content=""), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content="texto"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results == [{"type": "token", "content": "texto"}]

    @pytest.mark.asyncio
    async def test_recursion_error_yields_tool_limit(self):
        graph = FakeStreamGraph(raise_recursion=True)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results == [{"type": "token", "content": TOOL_LIMIT_MESSAGE}]

    @pytest.mark.asyncio
    async def test_no_content_yields_fallback(self):
        graph = FakeStreamGraph(events=[])
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results == [{"type": "token", "content": "Nao foi possivel gerar resposta."}]

    @pytest.mark.asyncio
    async def test_tool_limit_when_only_tool_chunks(self):
        chunk = AIMessageChunk(content="")
        chunk.tool_call_chunks = [{"name": "calc", "args": "", "id": "1", "index": 0}]
        events = [
            (chunk, {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results == [
            {"type": "tool_start", "name": "calc", "call_id": "1"},
            {"type": "token", "content": TOOL_LIMIT_MESSAGE},
        ]

    @pytest.mark.asyncio
    async def test_config_includes_thread_id(self):
        events = [
            (AIMessageChunk(content="ok"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="minha-sessao")]
        assert graph.captured_config["configurable"]["thread_id"] == "minha-sessao"

    @pytest.mark.asyncio
    async def test_emits_tool_start_on_tool_call_chunks(self):
        chunk = AIMessageChunk(content="")
        chunk.tool_call_chunks = [
            {"name": "calculator", "args": '{"expression": "2+2"}', "id": "call_abc", "index": 0}
        ]
        text_chunk = AIMessageChunk(content="O resultado e 4.")
        events = [
            (chunk, {"langgraph_node": "assistant"}),
            (text_chunk, {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results[0] == {
            "type": "tool_start",
            "name": "calculator",
            "call_id": "call_abc",
        }
        assert results[1] == {"type": "token", "content": "O resultado e 4."}

    @pytest.mark.asyncio
    async def test_emits_tool_end_on_tool_message(self):
        tool_msg = ToolMessage(
            content="4",
            name="calculator",
            tool_call_id="call_abc",
        )
        text_chunk = AIMessageChunk(content="Resultado: 4")
        events = [
            (tool_msg, {"langgraph_node": "tools"}),
            (text_chunk, {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        assert results[0] == {
            "type": "tool_end",
            "name": "calculator",
            "call_id": "call_abc",
            "output": "4",
        }
        assert results[1] == {"type": "token", "content": "Resultado: 4"}

    @pytest.mark.asyncio
    async def test_no_duplicate_tool_start_for_same_id(self):
        chunk1 = AIMessageChunk(content="")
        chunk1.tool_call_chunks = [
            {"name": "calculator", "args": "", "id": "call_abc", "index": 0}
        ]
        chunk2 = AIMessageChunk(content="")
        chunk2.tool_call_chunks = [
            {"name": "calculator", "args": '{"expression": "2+2"}', "id": "call_abc", "index": 0}
        ]
        events = [
            (chunk1, {"langgraph_node": "assistant"}),
            (chunk2, {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        results = [ev async for ev in stream_chat(graph, "oi", max_tool_steps=5, thread_id="t")]
        tool_starts = [e for e in results if e["type"] == "tool_start"]
        assert len(tool_starts) == 1
