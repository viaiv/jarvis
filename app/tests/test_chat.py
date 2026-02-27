from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage
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

    def invoke(self, state, config=None):
        ai_msg = AIMessage(content=self.response_content)
        if self.tool_calls:
            ai_msg.tool_calls = self.tool_calls
        return {"messages": state["messages"] + [ai_msg]}


class TestInvokeChat:
    def test_returns_ai_response(self):
        graph = FakeGraph(response_content="Oi, tudo bem!")
        result = invoke_chat(
            graph=graph,
            user_input="Ola",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == "Oi, tudo bem!"

    def test_returns_tool_limit_when_tool_calls_remain(self):
        graph = FakeGraph(
            response_content="",
            tool_calls=[{"name": "calculator", "args": {"expression": "1+1"}, "id": "1"}],
        )
        result = invoke_chat(
            graph=graph,
            user_input="calcule",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == TOOL_LIMIT_MESSAGE

    def test_empty_response_fallback(self):
        graph = FakeGraph(response_content="")
        result = invoke_chat(
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == "Nao foi possivel gerar resposta."

    def test_no_ai_message_fallback(self):
        class EmptyGraph:
            def invoke(self, state, config=None):
                return {"messages": []}

        result = invoke_chat(
            graph=EmptyGraph(),
            user_input="oi",
            max_tool_steps=5,
            thread_id="test",
        )
        assert result == "Nao foi possivel gerar resposta."

    def test_list_content_rendering(self):
        class ListContentGraph:
            def invoke(self, state, config=None):
                msg = AIMessage(content=[{"text": "parte1"}, {"text": "parte2"}])
                return {"messages": [msg]}

        result = invoke_chat(
            graph=ListContentGraph(),
            user_input="oi",
            max_tool_steps=5,
            thread_id="test",
        )
        assert "parte1" in result
        assert "parte2" in result

    def test_sends_human_message(self):
        class CapturingGraph:
            def __init__(self):
                self.captured_state = None

            def invoke(self, state, config=None):
                self.captured_state = state
                return {"messages": [AIMessage(content="ok")]}

        graph = CapturingGraph()
        invoke_chat(
            graph=graph,
            user_input="nova pergunta",
            max_tool_steps=5,
            thread_id="test",
        )
        messages = graph.captured_state["messages"]
        assert len(messages) == 1
        assert isinstance(messages[0], HumanMessage)
        assert messages[0].content == "nova pergunta"

    def test_thread_id_in_config(self):
        class ConfigCapturingGraph:
            def __init__(self):
                self.captured_config = None

            def invoke(self, state, config=None):
                self.captured_config = config
                return {"messages": [AIMessage(content="ok")]}

        graph = ConfigCapturingGraph()
        invoke_chat(
            graph=graph,
            user_input="oi",
            max_tool_steps=5,
            thread_id="minha-sessao",
        )
        assert graph.captured_config["configurable"]["thread_id"] == "minha-sessao"


class FakeStreamGraph:
    """Simula graph.stream() retornando (AIMessageChunk, metadata)."""

    def __init__(self, events=None, raise_recursion=False):
        self.events = events or []
        self.raise_recursion = raise_recursion
        self.captured_config = None

    def stream(self, state, config=None, stream_mode=None):
        self.captured_config = config
        if self.raise_recursion:
            raise GraphRecursionError("recursion limit")
        yield from self.events


class TestStreamChat:
    def test_yields_tokens(self):
        events = [
            (AIMessageChunk(content="Ola"), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content=" mundo"), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content="!"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        tokens = list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="t"))
        assert tokens == ["Ola", " mundo", "!"]

    def test_filters_non_assistant_nodes(self):
        events = [
            (AIMessageChunk(content="ignorar"), {"langgraph_node": "tools"}),
            (AIMessageChunk(content="ok"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        tokens = list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="t"))
        assert tokens == ["ok"]

    def test_skips_empty_content_chunks(self):
        events = [
            (AIMessageChunk(content=""), {"langgraph_node": "assistant"}),
            (AIMessageChunk(content="texto"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        tokens = list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="t"))
        assert tokens == ["texto"]

    def test_recursion_error_yields_tool_limit(self):
        graph = FakeStreamGraph(raise_recursion=True)
        tokens = list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="t"))
        assert tokens == [TOOL_LIMIT_MESSAGE]

    def test_no_content_yields_fallback(self):
        graph = FakeStreamGraph(events=[])
        tokens = list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="t"))
        assert tokens == ["Nao foi possivel gerar resposta."]

    def test_tool_limit_when_only_tool_chunks(self):
        chunk = AIMessageChunk(content="")
        chunk.tool_call_chunks = [{"name": "calc", "args": "", "id": "1", "index": 0}]
        events = [
            (chunk, {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        tokens = list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="t"))
        assert tokens == [TOOL_LIMIT_MESSAGE]

    def test_config_includes_thread_id(self):
        events = [
            (AIMessageChunk(content="ok"), {"langgraph_node": "assistant"}),
        ]
        graph = FakeStreamGraph(events=events)
        list(stream_chat(graph, "oi", max_tool_steps=5, thread_id="minha-sessao"))
        assert graph.captured_config["configurable"]["thread_id"] == "minha-sessao"
