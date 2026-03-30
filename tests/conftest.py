from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from langchain_core.messages import AIMessage, HumanMessage


@pytest.fixture()
def base_state() -> dict[str, Any]:
    """Minimal valid AgentState for testing agent nodes."""
    return {
        "messages": [HumanMessage(content="Test task")],
        "task": "Test task",
        "subtask": "Do something specific",
        "next_agent": "",
        "result": None,
        "agent_scratchpad": [],
        "error": None,
        "iteration": 0,
        "error_count": 0,
        "metadata": {},
    }


@pytest.fixture()
def mock_llm_response():
    """Factory fixture: returns a mock LLM that produces a given response."""

    def _factory(content: str, tool_calls: list | None = None):
        response = MagicMock(spec=AIMessage)
        response.content = content
        response.tool_calls = tool_calls or []
        llm = MagicMock()
        llm.invoke.return_value = response
        llm.bind_tools.return_value = llm
        return llm

    return _factory


@pytest.fixture()
def orchestrator_llm_end(mock_llm_response):
    """Mock LLM that makes the orchestrator route to END."""
    return mock_llm_response(
        json.dumps({
            "next_agent": "END",
            "subtask": "",
            "reasoning": "Task is complete.",
        })
    )


@pytest.fixture()
def orchestrator_llm_research(mock_llm_response):
    """Mock LLM that makes the orchestrator route to research."""
    return mock_llm_response(
        json.dumps({
            "next_agent": "research",
            "subtask": "Search for LLM benchmarks",
            "reasoning": "User wants web data.",
        })
    )
