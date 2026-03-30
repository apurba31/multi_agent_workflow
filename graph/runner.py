from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings
from graph.graph_builder import build_graph


def create_initial_state(
    task: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the LangGraph initial state dict for a run."""
    return {
        "messages": [HumanMessage(content=task)],
        "task": task,
        "subtask": "",
        "next_agent": "",
        "result": None,
        "agent_scratchpad": [],
        "error": None,
        "iteration": 0,
        "error_count": 0,
        "metadata": dict(metadata or {}),
    }


def stream_graph_run(
    task: str,
    *,
    thread_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Stream graph execution as (node_name, node_output) pairs.

    Yields once per completed node. Does not mutate caller state.
    """
    settings.apply_langsmith_env()

    from graph.checkpointer import get_checkpointer

    checkpointer = get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id or uuid.uuid4().hex}}
    initial = create_initial_state(task, metadata=metadata)

    logger.info("Streaming graph run, task prefix: {}", task[:100])

    for step in graph.stream(initial, config=config):
        node_name = next(iter(step.keys()))
        node_output = step[node_name]
        yield node_name, node_output
