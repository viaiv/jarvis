from langchain_core.messages import AIMessage, HumanMessage

from jarvis.chat import (
    TOOL_LIMIT_MESSAGE,
    invoke_chat,
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
