from __future__ import annotations

import sys

from loguru import logger

from config.settings import settings
from graph.runner import stream_graph_run


def setup_logging() -> None:
    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format=(
            "<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level>"
            " | <cyan>{name}</cyan> — {message}"
        ),
    )


def run(task: str, thread_id: str | None = None) -> str:
    """Execute a task through the multi-agent graph.

    Args:
        task: The user's request in natural language.
        thread_id: Optional thread ID for checkpointing continuity.

    Returns:
        The final result string from the agent pipeline.
    """
    final_state: dict | None = None
    for node_name, node_output in stream_graph_run(task, thread_id=thread_id):
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
        print("UI: streamlit run ui/app.py")
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    settings.apply_langsmith_env()
    result = run(task)

    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)
    print(result)


if __name__ == "__main__":
    main()
