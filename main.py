from __future__ import annotations

import sys
import uuid

from langchain_core.messages import HumanMessage
from loguru import logger

from config.settings import settings
from graph.checkpointer import get_checkpointer
from graph.graph_builder import build_graph


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <cyan>{name}</cyan> — {message}",
    )


def run(task: str, thread_id: str | None = None) -> str:
    """Execute a task through the multi-agent graph.

    Args:
        task: The user's request in natural language.
        thread_id: Optional thread ID for checkpointing continuity.

    Returns:
        The final result string from the agent pipeline.
    """
    settings.apply_langsmith_env()

    checkpointer = get_checkpointer()
    graph = build_graph(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id or uuid.uuid4().hex}}

    initial_state = {
        "messages": [HumanMessage(content=task)],
        "task": task,
        "subtask": "",
        "next_agent": "",
        "result": None,
        "agent_scratchpad": [],
        "error": None,
        "iteration": 0,
        "error_count": 0,
        "metadata": {},
    }

    logger.info("Starting multi-agent pipeline for task: {}", task[:100])

    final_state = None
    for step in graph.stream(initial_state, config=config):
        node_name = list(step.keys())[0]
        node_output = step[node_name]
        logger.info(
            "Step: {} → next_agent={}, error={}",
            node_name,
            node_output.get("next_agent", "—"),
            node_output.get("error", "None"),
        )
        final_state = node_output

    result = (final_state or {}).get("result", "No result produced.")
    logger.info("Pipeline complete. Result length: {} chars", len(str(result)))
    return result


def main() -> None:
    setup_logging()

    if len(sys.argv) < 2:
        print("Usage: python main.py '<task>'")
        print('Example: python main.py "Research the latest LLM benchmarks and send me a summary"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    result = run(task)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
