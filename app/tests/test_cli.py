from io import StringIO

import pytest
from langchain_core.messages import AIMessageChunk
from rich.console import Console

from jarvis.cli import _stream_response


class FakeStreamGraph:
    """Simula graph.astream() para testes de _stream_response."""

    def __init__(self, events=None):
        self.events = events or []

    async def astream(self, state, config=None, stream_mode=None):
        for event in self.events:
            yield event


class TestStreamResponse:
    def _make_console(self):
        buf = StringIO()
        return Console(file=buf, force_terminal=True), buf

    @pytest.mark.asyncio
    async def test_stream_response_renders_markdown(self):
        events = [
            (AIMessageChunk(content="**bold**"), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content=" and `code`"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        console, buf = self._make_console()

        await _stream_response(
            console=console,
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="t",
        )

        output = buf.getvalue()
        assert "Jarvis:" in output
        assert "bold" in output
        assert "code" in output

    @pytest.mark.asyncio
    async def test_stream_response_fallback(self):
        graph = FakeStreamGraph(events=[])
        console, buf = self._make_console()

        await _stream_response(
            console=console,
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="t",
        )

        output = buf.getvalue()
        assert "Nao foi possivel gerar resposta." in output

    @pytest.mark.asyncio
    async def test_stream_response_no_terminal(self):
        buf = StringIO()
        console = Console(file=buf, force_terminal=False)
        events = [
            (AIMessageChunk(content="hello"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)

        await _stream_response(
            console=console,
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="t",
        )

        output = buf.getvalue()
        assert "hello" in output
