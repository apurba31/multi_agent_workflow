from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from langgraph.graph import END

from graph.graph_builder import _route_after_orchestrator, _route_after_reflection, build_graph


class TestRouting:
    def test_route_to_research(self):
        state = {"next_agent": "research"}
        assert _route_after_orchestrator(state) == "research"

    def test_route_to_browser(self):
        state = {"next_agent": "browser"}
        assert _route_after_orchestrator(state) == "browser"

    def test_route_to_comms(self):
        state = {"next_agent": "comms"}
        assert _route_after_orchestrator(state) == "comms"

    def test_route_to_code(self):
        state = {"next_agent": "code"}
        assert _route_after_orchestrator(state) == "code"

    def test_route_to_end_explicit(self):
        state = {"next_agent": "END"}
        assert _route_after_orchestrator(state) == END

    def test_route_to_end_on_missing_key(self):
        state = {}
        assert _route_after_orchestrator(state) == END

    def test_route_to_end_on_invalid_agent(self):
        state = {"next_agent": "nonexistent"}
        assert _route_after_orchestrator(state) == END

    def test_reflection_routes_to_orchestrator_on_error(self):
        state = {"error": "something went wrong"}
        assert _route_after_reflection(state) == "orchestrator"

    def test_reflection_routes_to_orchestrator_on_success(self):
        state = {"error": None}
        assert _route_after_reflection(state) == "orchestrator"


class TestGraphCompilation:
    def test_graph_compiles_without_checkpointer(self):
        graph = build_graph()
        assert graph is not None

    def test_graph_compiles_with_checkpointer(self):
        from graph.checkpointer import get_checkpointer

        cp = get_checkpointer()
        graph = build_graph(checkpointer=cp)
        assert graph is not None

    def test_graph_has_all_nodes(self):
        graph = build_graph()
        node_names = set(graph.get_graph().nodes.keys())
        expected = {"orchestrator", "research", "browser", "comms", "code", "reflection"}
        assert expected.issubset(node_names)


class TestCheckpointer:
    def test_get_checkpointer_returns_memory_saver(self):
        from graph.checkpointer import get_checkpointer
        from langgraph.checkpoint.memory import MemorySaver

        cp = get_checkpointer()
        assert isinstance(cp, MemorySaver)
