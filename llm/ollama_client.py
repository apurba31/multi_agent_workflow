from __future__ import annotations

from functools import lru_cache

from langchain_ollama import ChatOllama

from config.settings import settings


@lru_cache(maxsize=4)
def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
    **kwargs,
) -> ChatOllama:
    """Return a cached ChatOllama instance.

    Uses the default model from settings unless overridden.
    Temperature defaults to 0 for deterministic tool-use agents.
    """
    return ChatOllama(
        base_url=settings.ollama_base_url,
        model=model or settings.default_model,
        temperature=temperature,
        **kwargs,
    )


def get_reasoning_llm(temperature: float = 0.0) -> ChatOllama:
    """Return an LLM tuned for complex reasoning (larger model)."""
    return get_llm(model=settings.reasoning_model, temperature=temperature)
