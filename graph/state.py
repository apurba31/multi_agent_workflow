from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Shared state flowing through every node in the graph.

    Fields:
        messages: Chat history managed by LangGraph's add_messages reducer.
        task: The original user request.
        subtask: Current sub-task assigned by the orchestrator.
        next_agent: Which agent to route to next (set by orchestrator).
        result: Latest agent output.
        agent_scratchpad: Intermediate working memory for the active agent.
        error: Last error message, or None.
        iteration: How many orchestrator loops have run.
        error_count: Consecutive errors (used for circuit-breaking).
        metadata: Arbitrary key-value bag for inter-agent data passing.
    """

    messages: Annotated[list[AnyMessage], add_messages]
    task: str
    subtask: str
    next_agent: str
    result: str | None
    agent_scratchpad: list[dict[str, Any]]
    error: str | None
    iteration: int
    error_count: int
    metadata: dict[str, Any]
