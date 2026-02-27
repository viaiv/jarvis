"""Testes para extracao de logs do checkpoint."""

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from jarvis.logs import get_thread_messages, list_threads


async def _seed_checkpoint(checkpointer, thread_id: str, messages: list):
    """Salva um estado no checkpoint para teste."""
    from langgraph.graph import END, START, StateGraph
    from langgraph.graph.message import add_messages
    from typing import Annotated, TypedDict, List
    from langchain_core.messages import BaseMessage

    class State(TypedDict):
        messages: Annotated[List[BaseMessage], add_messages]

    def passthrough(state):
        return state

    graph = StateGraph(State)
    graph.add_node("pass", passthrough)
    graph.add_edge(START, "pass")
    graph.add_edge("pass", END)
    compiled = graph.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}
    await compiled.ainvoke({"messages": messages}, config)


class TestListThreads:
    @pytest.mark.asyncio
    async def test_list_empty(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            await saver.setup()

        threads, total = await list_threads(db_path)
        assert threads == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_with_threads(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            await _seed_checkpoint(
                saver, "1:session-a",
                [HumanMessage(content="ola"), AIMessage(content="oi")],
            )
            await _seed_checkpoint(
                saver, "2:session-b",
                [HumanMessage(content="hey")],
            )

        threads, total = await list_threads(db_path)
        assert total == 2
        assert len(threads) == 2

        thread_ids = {t["thread_id"] for t in threads}
        assert "1:session-a" in thread_ids
        assert "2:session-b" in thread_ids

    @pytest.mark.asyncio
    async def test_list_filtered_by_user(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            await _seed_checkpoint(
                saver, "1:sess-1",
                [HumanMessage(content="a")],
            )
            await _seed_checkpoint(
                saver, "2:sess-2",
                [HumanMessage(content="b")],
            )

        threads, total = await list_threads(db_path, user_id=1)
        assert total == 1
        assert threads[0]["user_id"] == 1

    @pytest.mark.asyncio
    async def test_list_pagination(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            for i in range(5):
                await _seed_checkpoint(
                    saver, f"1:sess-{i}",
                    [HumanMessage(content=f"msg-{i}")],
                )

        threads, total = await list_threads(db_path, limit=2, offset=0)
        assert total == 5
        assert len(threads) == 2

        threads2, _ = await list_threads(db_path, limit=2, offset=2)
        assert len(threads2) == 2

        all_ids = {t["thread_id"] for t in threads + threads2}
        assert len(all_ids) == 4  # sem overlap


class TestGetThreadMessages:
    @pytest.mark.asyncio
    async def test_get_messages(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            await _seed_checkpoint(
                saver, "1:test",
                [HumanMessage(content="Ola"), AIMessage(content="Oi!")],
            )

        messages = await get_thread_messages(db_path, "1:test")
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[0]["content"] == "Ola"
        assert messages[1]["role"] == "assistant"
        assert messages[1]["content"] == "Oi!"

    @pytest.mark.asyncio
    async def test_nonexistent_thread(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        async with AsyncSqliteSaver.from_conn_string(db_path) as saver:
            await saver.setup()

        messages = await get_thread_messages(db_path, "nonexistent")
        assert messages == []
