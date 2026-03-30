from __future__ import annotations

from unittest.mock import MagicMock, patch

from graph.runner import create_initial_state, stream_graph_run


class TestCreateInitialState:
    def test_minimal(self):
        s = create_initial_state("hello")
        assert s["task"] == "hello"
        assert s["iteration"] == 0
        assert s["error"] is None
        assert s["metadata"] == {}
        assert len(s["messages"]) == 1
        assert s["messages"][0].content == "hello"

    def test_metadata_merged(self):
        s = create_initial_state("t", metadata={"upload_kind": "csv"})
        assert s["metadata"]["upload_kind"] == "csv"


class TestStreamGraphRun:
    def test_yields_steps(self):
        fake_graph = MagicMock()
        fake_graph.stream.return_value = [
            {"orchestrator": {"next_agent": "research", "iteration": 1}},
            {"research": {"result": "done"}},
        ]

        with patch("graph.checkpointer.get_checkpointer", return_value=MagicMock()):
            with patch("graph.runner.build_graph", return_value=fake_graph):
                with patch("graph.runner.settings") as mock_settings:
                    mock_settings.apply_langsmith_env = MagicMock()
                    steps = list(
                        stream_graph_run("task", metadata={"upload_kind": "text"})
                    )

        assert len(steps) == 2
        assert steps[0][0] == "orchestrator"
        assert steps[0][1]["next_agent"] == "research"
        assert steps[1][0] == "research"
        fake_graph.stream.assert_called_once()
        call_kw = fake_graph.stream.call_args[0][0]
        assert call_kw["task"] == "task"
        assert call_kw["metadata"]["upload_kind"] == "text"
