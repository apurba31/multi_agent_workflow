from __future__ import annotations

from typing import get_type_hints

from graph.state import AgentState


class TestAgentState:
    def test_has_all_required_fields(self):
        hints = get_type_hints(AgentState, include_extras=True)
        expected = {
            "messages",
            "task",
            "subtask",
            "next_agent",
            "result",
            "agent_scratchpad",
            "error",
            "iteration",
            "error_count",
            "metadata",
        }
        assert expected == set(hints.keys())

    def test_can_instantiate_with_defaults(self, base_state):
        state: AgentState = base_state
        assert state["task"] == "Test task"
        assert state["iteration"] == 0
        assert state["error"] is None
        assert state["error_count"] == 0
        assert isinstance(state["messages"], list)
        assert isinstance(state["metadata"], dict)

    def test_messages_field_is_list(self, base_state):
        assert isinstance(base_state["messages"], list)
        assert len(base_state["messages"]) == 1
