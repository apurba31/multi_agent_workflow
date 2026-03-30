from __future__ import annotations

import json

from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from graph.state import AgentState
from llm.ollama_client import get_llm

SYSTEM_PROMPT = """\
You are the Reflection Agent — a quality-control reviewer for a \
multi-agent system.

Your job:
- Review the latest agent output in the conversation.
- Detect errors, inconsistencies, missing steps, or incomplete answers.
- Decide if the result is acceptable or needs a retry.

Output ONLY valid JSON:
{
  "quality": "pass" | "fail",
  "issues_found": ["issue1", "issue2"],
  "fix_suggestions": ["suggestion1", "suggestion2"],
  "retry_required": true | false
}

Rules:
- Be critical but precise — only flag real problems.
- Do not over-correct style or formatting.
- Focus on factual correctness and task completeness.
- If the output is good enough, return quality=pass and retry_required=false."""


def reflection_agent(state: AgentState) -> dict:
    """LangGraph node: reviews the last agent's output for quality."""
    logger.info("Reflection agent activated")

    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = llm.invoke(messages)
        content = response.content or "{}"

        try:
            review = json.loads(content)
        except json.JSONDecodeError:
            review = {
                "quality": "pass",
                "issues_found": [],
                "fix_suggestions": [],
                "retry_required": False,
            }

        retry = review.get("retry_required", False)
        quality = review.get("quality", "pass")

        if retry:
            error_msg = f"Reflection: quality={quality}, issues={review.get('issues_found', [])}"
            logger.warning(error_msg)
            return {
                "messages": [AIMessage(content=content, name="reflection")],
                "error": error_msg,
                "result": state.get("result"),
            }

        return {
            "messages": [AIMessage(content=content, name="reflection")],
            "error": None,
            "result": state.get("result"),
        }
    except Exception as exc:
        logger.error("Reflection agent failed: {}", exc)
        return {
            "messages": [AIMessage(content=f"Reflection error: {exc}", name="reflection")],
            "error": None,
            "result": state.get("result"),
        }
