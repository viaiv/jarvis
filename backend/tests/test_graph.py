from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from jarvis.graph import _sanitize_tool_sequences, _trim_and_prepend_system


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
        # history_window=1 → mantém 1 turno humano anterior + turno atual
        result = _trim_and_prepend_system(messages, "sys", history_window=1)
        # sys + HumanMessage("3") + AIMessage("r3") + HumanMessage("4")
        assert len(result) == 4
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
        # history_window=2 → mantém 2 turnos humanos anteriores + turno atual
        result = _trim_and_prepend_system(messages, "sys", history_window=2)
        assert len(result) == 6  # sys + 4 msgs de historico + current
        assert result[0].content == "sys"
        assert result[1].content == "3"
        assert result[2].content == "r3"
        assert result[3].content == "4"
        assert result[4].content == "r4"
        assert result[5].content == "5"

    def test_drops_orphan_tool_messages_after_trim(self):
        ai_with_tc = AIMessage(content="")
        ai_with_tc.tool_calls = [
            {"name": "calc", "args": {"expression": "1+1"}, "id": "c1"}
        ]
        messages = [
            HumanMessage(content="1"),
            ai_with_tc,
            ToolMessage(content="2", tool_call_id="c1"),
            AIMessage(content="r1"),
            HumanMessage(content="2"),
            AIMessage(content="r2"),
            HumanMessage(content="3"),
            AIMessage(content="r3"),
            HumanMessage(content="4"),
        ]
        # window=1 → mantém turno "4" (atual) + turno "3" (anterior)
        # Turno "1" com tool calls é removido pelo trim
        result = _trim_and_prepend_system(messages, "sys", history_window=1)
        assert result[0].content == "sys"
        assert not any(isinstance(m, ToolMessage) for m in result)

    def test_drops_leading_ai_with_tool_calls_after_trim(self):
        ai_with_tc = AIMessage(content="")
        ai_with_tc.tool_calls = [
            {"name": "calc", "args": {"expression": "1+1"}, "id": "c1"}
        ]
        messages = [
            HumanMessage(content="old"),
            ai_with_tc,
            ToolMessage(content="2", tool_call_id="c1"),
            AIMessage(content="result"),
            HumanMessage(content="middle"),
            AIMessage(content="middle reply"),
            HumanMessage(content="recent"),
            AIMessage(content="recent reply"),
            HumanMessage(content="new"),
        ]
        # window=1 → mantém turno "new" (atual) + turno "recent" (anterior)
        # Turno "old" com tool calls é removido pelo trim
        result = _trim_and_prepend_system(messages, "sys", history_window=1)
        assert result[0].content == "sys"
        assert not any(
            isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
            for m in result
        )

    def test_keeps_complete_tool_sequence_in_history(self):
        ai_with_tc = AIMessage(content="")
        ai_with_tc.tool_calls = [
            {"name": "calc", "args": {"expression": "2+2"}, "id": "c1"}
        ]
        messages = [
            HumanMessage(content="quanto e 2+2"),
            ai_with_tc,
            ToolMessage(content="4", tool_call_id="c1"),
            AIMessage(content="O resultado e 4."),
            HumanMessage(content="obrigado"),
        ]
        result = _trim_and_prepend_system(messages, "sys", history_window=5)
        # Sequencia completa deve ser preservada
        assert any(isinstance(m, ToolMessage) for m in result)
        assert any(
            isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
            for m in result
        )

    def test_trim_counts_human_turns_not_messages(self):
        """Com 3 HumanMessages e 10 ToolMessages, nao perde contexto."""
        # Simula: turno 1 (pedido inicial) com 3 tool calls em sequencia
        ai_tc1 = AIMessage(content="")
        ai_tc1.tool_calls = [{"name": "market", "args": {}, "id": "t1"}]
        ai_tc2 = AIMessage(content="")
        ai_tc2.tool_calls = [{"name": "players", "args": {}, "id": "t2"}]
        ai_tc3 = AIMessage(content="")
        ai_tc3.tool_calls = [{"name": "players", "args": {}, "id": "t3"}]

        messages = [
            # Turno 1: pedido com muitas tool calls
            HumanMessage(content="Monte escalacao 4-3-3 com 114 cartoletas"),
            ai_tc1,
            ToolMessage(content="rodada 10", tool_call_id="t1"),
            ai_tc2,
            ToolMessage(content="goleiros...", tool_call_id="t2"),
            ai_tc3,
            ToolMessage(content="atacantes...", tool_call_id="t3"),
            AIMessage(content="Aqui esta a escalacao..."),
            # Turno 2
            HumanMessage(content="Troca o goleiro"),
            AIMessage(content="Troquei o goleiro."),
            # Turno 3
            HumanMessage(content="E o tecnico?"),
        ]

        # history_window=3 deve manter todos os 3 turnos humanos
        result = _trim_and_prepend_system(messages, "sys", history_window=3)
        assert result[0].content == "sys"
        # O primeiro HumanMessage (pedido com orcamento) deve estar presente
        human_msgs = [m for m in result if isinstance(m, HumanMessage)]
        assert len(human_msgs) == 3
        assert human_msgs[0].content == "Monte escalacao 4-3-3 com 114 cartoletas"

    def test_trim_preserves_tool_blocks_within_turn(self):
        """Tool call blocks ficam intactos apos trim."""
        ai_tc1 = AIMessage(content="")
        ai_tc1.tool_calls = [{"name": "market", "args": {}, "id": "t1"}]
        ai_tc2 = AIMessage(content="")
        ai_tc2.tool_calls = [{"name": "players", "args": {}, "id": "t2"}]

        messages = [
            # Turno antigo (sera cortado)
            HumanMessage(content="turno antigo"),
            AIMessage(content="resposta antiga"),
            # Turno recente com tool calls
            HumanMessage(content="busca jogadores"),
            ai_tc1,
            ToolMessage(content="rodada 10", tool_call_id="t1"),
            ai_tc2,
            ToolMessage(content="jogadores...", tool_call_id="t2"),
            AIMessage(content="Encontrei os jogadores."),
            # Turno atual
            HumanMessage(content="agora monta"),
        ]

        # window=2 → mantém turno atual + 2 anteriores
        # Turno "turno antigo" nao cabe, mas "busca jogadores" e "agora monta" sim
        result = _trim_and_prepend_system(messages, "sys", history_window=2)
        assert result[0].content == "sys"
        # Tool blocks intactos
        tool_msgs = [m for m in result if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 2
        # AIMessage com tool_calls presente
        ai_tc_msgs = [
            m for m in result
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
        ]
        assert len(ai_tc_msgs) == 2

    def test_trim_many_tool_calls_single_turn_window_3(self):
        """6 tool calls do Cartola (12 mensagens) nao estourar window=3."""
        tool_pairs = []
        for i in range(6):
            ai = AIMessage(content="")
            ai.tool_calls = [{"name": f"tool_{i}", "args": {}, "id": f"t{i}"}]
            tool_pairs.append(ai)
            tool_pairs.append(ToolMessage(content=f"result_{i}", tool_call_id=f"t{i}"))

        messages = [
            HumanMessage(content="Monta escalacao com 114 cartoletas"),
            *tool_pairs,  # 12 mensagens (6 AI + 6 Tool)
            AIMessage(content="Escalacao montada."),
            HumanMessage(content="Troca lateral"),
            AIMessage(content="Lateral trocado."),
            HumanMessage(content="Quanto ficou o total?"),
        ]

        result = _trim_and_prepend_system(messages, "sys", history_window=3)
        assert result[0].content == "sys"
        # Todos os 3 turnos humanos preservados
        human_msgs = [m for m in result if isinstance(m, HumanMessage)]
        assert len(human_msgs) == 3
        assert human_msgs[0].content == "Monta escalacao com 114 cartoletas"
        # As 12 mensagens de tool calls do primeiro turno preservadas
        tool_msgs = [m for m in result if isinstance(m, ToolMessage)]
        assert len(tool_msgs) == 6


class TestSanitizeToolSequences:
    def test_keeps_complete_sequence(self):
        ai_tc = AIMessage(content="")
        ai_tc.tool_calls = [{"name": "calc", "args": {}, "id": "c1"}]
        messages = [
            HumanMessage(content="oi"),
            ai_tc,
            ToolMessage(content="4", tool_call_id="c1"),
            AIMessage(content="resultado"),
        ]
        result = _sanitize_tool_sequences(messages)
        assert len(result) == 4

    def test_drops_orphan_tool_message(self):
        messages = [
            ToolMessage(content="4", tool_call_id="c1"),
            HumanMessage(content="oi"),
        ]
        result = _sanitize_tool_sequences(messages)
        assert len(result) == 1
        assert isinstance(result[0], HumanMessage)

    def test_drops_ai_tool_calls_without_responses(self):
        ai_tc = AIMessage(content="")
        ai_tc.tool_calls = [{"name": "calc", "args": {}, "id": "c1"}]
        messages = [
            HumanMessage(content="oi"),
            ai_tc,
            AIMessage(content="desculpe"),
            HumanMessage(content="novo"),
        ]
        result = _sanitize_tool_sequences(messages)
        assert len(result) == 3
        assert not any(
            isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
            for m in result
        )

    def test_drops_ai_tool_calls_with_partial_responses(self):
        ai_tc = AIMessage(content="")
        ai_tc.tool_calls = [
            {"name": "calc", "args": {}, "id": "c1"},
            {"name": "time", "args": {}, "id": "c2"},
        ]
        messages = [
            HumanMessage(content="oi"),
            ai_tc,
            ToolMessage(content="4", tool_call_id="c1"),
            # c2 esta faltando
            AIMessage(content="resposta"),
        ]
        result = _sanitize_tool_sequences(messages)
        assert len(result) == 2  # H + AI(text)
        assert not any(isinstance(m, ToolMessage) for m in result)

    def test_keeps_multiple_complete_sequences(self):
        ai_tc1 = AIMessage(content="")
        ai_tc1.tool_calls = [{"name": "calc", "args": {}, "id": "c1"}]
        ai_tc2 = AIMessage(content="")
        ai_tc2.tool_calls = [{"name": "time", "args": {}, "id": "c2"}]
        messages = [
            HumanMessage(content="pergunta1"),
            ai_tc1,
            ToolMessage(content="4", tool_call_id="c1"),
            AIMessage(content="resposta1"),
            HumanMessage(content="pergunta2"),
            ai_tc2,
            ToolMessage(content="15:00", tool_call_id="c2"),
            AIMessage(content="resposta2"),
        ]
        result = _sanitize_tool_sequences(messages)
        assert len(result) == 8  # tudo preservado

    def test_drops_middle_incomplete_keeps_rest(self):
        ai_tc_ok = AIMessage(content="")
        ai_tc_ok.tool_calls = [{"name": "calc", "args": {}, "id": "c1"}]
        ai_tc_bad = AIMessage(content="")
        ai_tc_bad.tool_calls = [{"name": "calc", "args": {}, "id": "c2"}]
        messages = [
            HumanMessage(content="p1"),
            ai_tc_ok,
            ToolMessage(content="4", tool_call_id="c1"),
            AIMessage(content="r1"),
            HumanMessage(content="p2"),
            ai_tc_bad,
            # ToolMessage para c2 faltando
            AIMessage(content="r2"),
            HumanMessage(content="p3"),
        ]
        result = _sanitize_tool_sequences(messages)
        # ai_tc_bad removido, resto preservado
        assert len(result) == 7
        tool_call_msgs = [
            m for m in result
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None)
        ]
        assert len(tool_call_msgs) == 1  # so o completo
