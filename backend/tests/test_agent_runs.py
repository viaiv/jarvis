"""Testes para CRUD de agent_runs (SQLite)."""

import pytest
import pytest_asyncio

from jarvis.db import (
    create_agent_run,
    get_agent_run,
    init_db,
    list_agent_runs,
    update_agent_run,
)


@pytest_asyncio.fixture
async def db():
    conn = await init_db(":memory:")
    yield conn
    await conn.close()


class TestAgentRunsCrud:
    @pytest.mark.asyncio
    async def test_create_agent_run(self, db):
        run = await create_agent_run(
            db, "viaiv/jarvis", 42, "Bug no login", "opened",
        )
        assert run["id"] is not None
        assert run["repo"] == "viaiv/jarvis"
        assert run["issue_number"] == 42
        assert run["issue_title"] == "Bug no login"
        assert run["action"] == "opened"
        assert run["status"] == "processing"
        assert run["category"] is None
        assert run["tool_steps"] == 0
        assert run["started_at"] is not None
        assert run["finished_at"] is None

    @pytest.mark.asyncio
    async def test_get_agent_run(self, db):
        run = await create_agent_run(db, "repo/test", 1, "Title", "opened")
        fetched = await get_agent_run(db, run["id"])
        assert fetched is not None
        assert fetched["repo"] == "repo/test"

    @pytest.mark.asyncio
    async def test_get_nonexistent_run(self, db):
        assert await get_agent_run(db, 999) is None

    @pytest.mark.asyncio
    async def test_update_agent_run_completed(self, db):
        run = await create_agent_run(db, "repo/test", 1, "Title", "opened")
        updated = await update_agent_run(
            db, run["id"],
            category="BUG",
            status="completed",
            tool_steps=5,
            finished_at="2026-03-05T12:00:00+00:00",
        )
        assert updated["category"] == "BUG"
        assert updated["status"] == "completed"
        assert updated["tool_steps"] == 5
        assert updated["finished_at"] == "2026-03-05T12:00:00+00:00"

    @pytest.mark.asyncio
    async def test_update_agent_run_failed(self, db):
        run = await create_agent_run(db, "repo/test", 1, "Title", "opened")
        updated = await update_agent_run(
            db, run["id"],
            status="failed",
            error_message="Connection timeout",
            finished_at="2026-03-05T12:00:00+00:00",
        )
        assert updated["status"] == "failed"
        assert updated["error_message"] == "Connection timeout"

    @pytest.mark.asyncio
    async def test_update_nonexistent_run(self, db):
        result = await update_agent_run(db, 999, status="completed")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_agent_runs_empty(self, db):
        runs, total = await list_agent_runs(db)
        assert runs == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_list_agent_runs_ordered_desc(self, db):
        await create_agent_run(db, "repo/a", 1, "First", "opened")
        await create_agent_run(db, "repo/b", 2, "Second", "edited")
        runs, total = await list_agent_runs(db)
        assert total == 2
        assert runs[0]["issue_title"] == "Second"
        assert runs[1]["issue_title"] == "First"

    @pytest.mark.asyncio
    async def test_list_agent_runs_filter_by_status(self, db):
        run1 = await create_agent_run(db, "repo/a", 1, "First", "opened")
        await create_agent_run(db, "repo/b", 2, "Second", "opened")
        await update_agent_run(db, run1["id"], status="completed")

        runs, total = await list_agent_runs(db, status="processing")
        assert total == 1
        assert runs[0]["issue_title"] == "Second"

        runs, total = await list_agent_runs(db, status="completed")
        assert total == 1
        assert runs[0]["issue_title"] == "First"

    @pytest.mark.asyncio
    async def test_list_agent_runs_pagination(self, db):
        for i in range(5):
            await create_agent_run(db, "repo/test", i, f"Issue {i}", "opened")

        runs, total = await list_agent_runs(db, limit=2, offset=0)
        assert total == 5
        assert len(runs) == 2

        runs, total = await list_agent_runs(db, limit=2, offset=4)
        assert total == 5
        assert len(runs) == 1

    @pytest.mark.asyncio
    async def test_update_ignores_disallowed_fields(self, db):
        run = await create_agent_run(db, "repo/test", 1, "Title", "opened")
        updated = await update_agent_run(
            db, run["id"], repo="hacked", issue_number=999,
        )
        assert updated["repo"] == "repo/test"
        assert updated["issue_number"] == 1
