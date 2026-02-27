import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from jarvis.memory import (
    MemoryStoreError,
    load_session_history,
    save_session_history,
)


@pytest.fixture()
def memory_file(tmp_path):
    return str(tmp_path / "memory.json")


class TestLoadSessionHistory:
    def test_file_not_found_returns_empty(self, memory_file):
        result = load_session_history(memory_file, "s1")
        assert result == []

    def test_loads_saved_session(self, memory_file):
        data = {
            "s1": [
                {"role": "human", "content": "oi"},
                {"role": "ai", "content": "ola!"},
            ]
        }
        with open(memory_file, "w") as f:
            json.dump(data, f)

        result = load_session_history(memory_file, "s1")

        assert len(result) == 2
        assert isinstance(result[0], HumanMessage)
        assert result[0].content == "oi"
        assert isinstance(result[1], AIMessage)
        assert result[1].content == "ola!"

    def test_missing_session_returns_empty(self, memory_file):
        with open(memory_file, "w") as f:
            json.dump({"other": []}, f)

        result = load_session_history(memory_file, "s1")
        assert result == []

    def test_corrupted_json_raises(self, memory_file):
        with open(memory_file, "w") as f:
            f.write("{invalid json")

        with pytest.raises(MemoryStoreError, match="JSON invalido"):
            load_session_history(memory_file, "s1")

    def test_non_dict_root_raises(self, memory_file):
        with open(memory_file, "w") as f:
            json.dump([1, 2, 3], f)

        with pytest.raises(MemoryStoreError, match="objeto JSON"):
            load_session_history(memory_file, "s1")

    def test_non_list_session_raises(self, memory_file):
        with open(memory_file, "w") as f:
            json.dump({"s1": "not a list"}, f)

        with pytest.raises(MemoryStoreError, match="lista de turnos"):
            load_session_history(memory_file, "s1")

    def test_skips_malformed_turns(self, memory_file):
        data = {
            "s1": [
                {"role": "human", "content": "valido"},
                {"role": "unknown", "content": "ignorado"},
                "not a dict",
                {"role": "ai", "content": 123},  # content nao e str
                {"role": "ai", "content": "ok"},
            ]
        }
        with open(memory_file, "w") as f:
            json.dump(data, f)

        result = load_session_history(memory_file, "s1")
        assert len(result) == 2
        assert result[0].content == "valido"
        assert result[1].content == "ok"


class TestSaveSessionHistory:
    def test_save_creates_file(self, memory_file):
        messages = [
            HumanMessage(content="oi"),
            AIMessage(content="ola!"),
        ]
        save_session_history(memory_file, "s1", messages)

        with open(memory_file) as f:
            data = json.load(f)

        assert data == {
            "s1": [
                {"role": "human", "content": "oi"},
                {"role": "ai", "content": "ola!"},
            ]
        }

    def test_save_preserves_other_sessions(self, memory_file):
        initial = {"s1": [{"role": "human", "content": "primeiro"}]}
        with open(memory_file, "w") as f:
            json.dump(initial, f)

        save_session_history(
            memory_file, "s2", [HumanMessage(content="segundo")]
        )

        with open(memory_file) as f:
            data = json.load(f)

        assert "s1" in data
        assert "s2" in data
        assert data["s1"][0]["content"] == "primeiro"
        assert data["s2"][0]["content"] == "segundo"

    def test_save_overwrites_session(self, memory_file):
        save_session_history(
            memory_file, "s1", [HumanMessage(content="v1")]
        )
        save_session_history(
            memory_file, "s1", [HumanMessage(content="v2")]
        )

        with open(memory_file) as f:
            data = json.load(f)

        assert len(data["s1"]) == 1
        assert data["s1"][0]["content"] == "v2"

    def test_save_creates_subdirectory(self, tmp_path):
        deep_file = str(tmp_path / "sub" / "dir" / "memory.json")
        save_session_history(deep_file, "s1", [HumanMessage(content="oi")])

        with open(deep_file) as f:
            data = json.load(f)

        assert data["s1"][0]["content"] == "oi"
