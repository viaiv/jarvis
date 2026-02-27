from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from jarvis.graph import _trim_and_prepend_system


class TestTrimAndPrependSystem:
    def test_single_message_no_trim(self):
        messages = [HumanMessage(content="oi")]
        result = _trim_and_prepend_system(messages, "system", history_window=3)
        assert len(result) == 2
        assert isinstance(result[0], SystemMessage)
        assert result[0].content == "system"
        assert result[1].content == "oi"

    def test_filters_existing_system_messages(self):
        messages = [
            SystemMessage(content="old system"),
            HumanMessage(content="oi"),
        ]
        result = _trim_and_prepend_system(messages, "new system", history_window=3)
        assert len(result) == 2
        assert result[0].content == "new system"
        assert result[1].content == "oi"

    def test_window_zero_keeps_only_current(self):
        messages = [
            HumanMessage(content="1"), AIMessage(content="r1"),
            HumanMessage(content="2"), AIMessage(content="r2"),
            HumanMessage(content="3"),
        ]
        result = _trim_and_prepend_system(messages, "sys", history_window=0)
        assert len(result) == 2
        assert result[0].content == "sys"
        assert result[1].content == "3"

    def test_trims_to_window(self):
        messages = [
            HumanMessage(content="1"), AIMessage(content="r1"),
            HumanMessage(content="2"), AIMessage(content="r2"),
            HumanMessage(content="3"), AIMessage(content="r3"),
            HumanMessage(content="4"),
        ]
        # history_window=1 → mantém 1 par anterior + mensagem atual
        result = _trim_and_prepend_system(messages, "sys", history_window=1)
        assert len(result) == 4  # sys + 1 par + current
        assert result[0].content == "sys"
        assert result[1].content == "3"
        assert result[2].content == "r3"
        assert result[3].content == "4"

    def test_fewer_than_window(self):
        messages = [
            HumanMessage(content="1"), AIMessage(content="r1"),
            HumanMessage(content="2"),
        ]
        result = _trim_and_prepend_system(messages, "sys", history_window=5)
        assert len(result) == 4  # sys + all 3 messages
        assert result[0].content == "sys"
        assert result[1].content == "1"

    def test_empty_messages(self):
        result = _trim_and_prepend_system([], "sys", history_window=3)
        assert len(result) == 1
        assert result[0].content == "sys"

    def test_window_two_with_many_turns(self):
        messages = [
            HumanMessage(content="1"), AIMessage(content="r1"),
            HumanMessage(content="2"), AIMessage(content="r2"),
            HumanMessage(content="3"), AIMessage(content="r3"),
            HumanMessage(content="4"), AIMessage(content="r4"),
            HumanMessage(content="5"),
        ]
        # history_window=2 → mantém 2 pares anteriores + mensagem atual
        result = _trim_and_prepend_system(messages, "sys", history_window=2)
        assert len(result) == 6  # sys + 4 msgs de historico + current
        assert result[0].content == "sys"
        assert result[1].content == "3"
        assert result[2].content == "r3"
        assert result[3].content == "4"
        assert result[4].content == "r4"
        assert result[5].content == "5"
