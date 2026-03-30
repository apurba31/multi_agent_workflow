from __future__ import annotations

from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer() -> MemorySaver:
    """Return a LangGraph checkpointer for state persistence.

    Uses in-memory storage by default. Swap to SqliteSaver or
    PostgresSaver for production persistence.
    """
    return MemorySaver()
