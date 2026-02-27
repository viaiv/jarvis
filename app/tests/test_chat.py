from langchain_core.messages import AIMessage, HumanMessage

from jarvis.chat import (
    TOOL_LIMIT_MESSAGE,
    invoke_chat,
    trim_history,
)


class TestTrimHistory:
    def test_empty_history(self):
        assert trim_history([], 3) == []

    def test_max_turns_zero(self):
        history = [HumanMessage(content="a"), AIMessage(content="b")]
        assert trim_history(history, 0) == []

    def test_keeps_last_n_turns(self):
        history = [
            HumanMessage(content="1"), AIMessage(content="r1"),
            HumanMessage(content="2"), AIMessage(content="r2"),
            HumanMessage(content="3"), AIMessage(content="r3"),
        ]
        result = trim_history(history, 2)
        assert len(result) == 4
        assert result[0].content == "2"
        assert result[-1].content == "r3"

    def test_fewer_than_max(self):
        history = [HumanMessage(content="a"), AIMessage(content="b")]
        result = trim_history(history, 5)
        assert len(result) == 2


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
            system_prompt="Voce e um assistente.",
            history=[],
            user_input="Ola",
            max_tool_steps=5,
        )
        assert result == "Oi, tudo bem!"

    def test_returns_tool_limit_when_tool_calls_remain(self):
        graph = FakeGraph(
            response_content="",
            tool_calls=[{"name": "calculator", "args": {"expression": "1+1"}, "id": "1"}],
        )
        result = invoke_chat(
            graph=graph,
            system_prompt="test",
            history=[],
            user_input="calcule",
            max_tool_steps=5,
        )
        assert result == TOOL_LIMIT_MESSAGE

    def test_empty_response_fallback(self):
        graph = FakeGraph(response_content="")
        result = invoke_chat(
            graph=graph,
            system_prompt="test",
            history=[],
            user_input="oi",
            max_tool_steps=5,
        )
        assert result == "Nao foi possivel gerar resposta."

    def test_no_ai_message_fallback(self):
        class EmptyGraph:
            def invoke(self, state, config=None):
                return {"messages": []}

        result = invoke_chat(
            graph=EmptyGraph(),
            system_prompt="test",
            history=[],
            user_input="oi",
            max_tool_steps=5,
        )
        assert result == "Nao foi possivel gerar resposta."

    def test_list_content_rendering(self):
        class ListContentGraph:
            def invoke(self, state, config=None):
                msg = AIMessage(content=[{"text": "parte1"}, {"text": "parte2"}])
                return {"messages": [msg]}

        result = invoke_chat(
            graph=ListContentGraph(),
            system_prompt="test",
            history=[],
            user_input="oi",
            max_tool_steps=5,
        )
        assert "parte1" in result
        assert "parte2" in result

    def test_history_is_included(self):
        class CapturingGraph:
            def __init__(self):
                self.captured_messages = None

            def invoke(self, state, config=None):
                self.captured_messages = state["messages"]
                return {"messages": [AIMessage(content="ok")]}

        graph = CapturingGraph()
        history = [
            HumanMessage(content="pergunta anterior"),
            AIMessage(content="resposta anterior"),
        ]
        invoke_chat(
            graph=graph,
            system_prompt="system",
            history=history,
            user_input="nova pergunta",
            max_tool_steps=5,
        )
        contents = [m.content for m in graph.captured_messages]
        assert "system" in contents
        assert "pergunta anterior" in contents
        assert "resposta anterior" in contents
        assert "nova pergunta" in contents
