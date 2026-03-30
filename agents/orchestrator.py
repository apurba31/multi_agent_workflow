from __future__ import annotations

import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from loguru import logger

from config.settings import settings
from graph.state import AgentState
from llm.ollama_client import get_llm

SYSTEM_PROMPT = """You are the Orchestrator — the central supervisor in a multi-agent system.
Your job is to decompose complex user tasks and route sub-tasks to the correct specialist agent.

Available agents:
- research: Web search, Wikipedia lookup, summarization, fact extraction
- browser: Navigate URLs, click elements, fill forms, take screenshots
- comms: Send Telegram messages, send emails, format notifications
- code: Write Python/bash, execute code, run tests, explain output

Decision framework:
1. Parse the user task into atomic sub-tasks
2. Classify each sub-task to the most capable agent
3. Sequence sub-tasks — identify dependencies
4. Route to the first pending agent in the sequence
5. Aggregate results and decide if the task is complete

Routing rules:
- Real-time web data or summarizing a topic → research
- Visiting a URL, form interaction, or visual scraping → browser
- Sending notifications or messages → comms
- Writing, running, or explaining code → code
- If a previous agent returned an error: retry once with a clarified prompt, then END
- If iteration >= 10: ALWAYS route to END

Output ONLY valid JSON — no other text:
{
  "next_agent": "research | browser | comms | code | END",
  "subtask": "Precise instruction for the next agent",
  "reasoning": "1-2 sentence explanation"
}"""


def orchestrator(state: AgentState) -> dict:
    """LangGraph node: decides which agent to route to next."""
    iteration = state.get("iteration", 0)
    error_count = state.get("error_count", 0)

    if iteration >= settings.max_iterations:
        logger.warning("Max iterations reached ({}), routing to END", iteration)
        return {
            "next_agent": "END",
            "subtask": "",
            "iteration": iteration,
        }

    if error_count >= 2:
        logger.warning("Error count {} >= 2, routing to END", error_count)
        return {
            "next_agent": "END",
            "subtask": "",
            "iteration": iteration,
        }

    try:
        llm = get_llm()
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = llm.invoke(messages)
        content = response.content or ""

        try:
            decision = json.loads(content)
        except json.JSONDecodeError:
            start = content.find("{")
            end = content.rfind("}") + 1
            if start != -1 and end > start:
                decision = json.loads(content[start:end])
            else:
                logger.error("Orchestrator returned non-JSON: {}", content[:200])
                decision = {
                    "next_agent": "END",
                    "subtask": "",
                    "reasoning": "Failed to parse orchestrator output.",
                }

        next_agent = decision.get("next_agent", "END")
        subtask = decision.get("subtask", "")
        reasoning = decision.get("reasoning", "")

        valid_agents = {"research", "browser", "comms", "code", "END"}
        if next_agent not in valid_agents:
            logger.warning("Invalid agent '{}', defaulting to END", next_agent)
            next_agent = "END"

        logger.info(
            "Orchestrator decision: {} — subtask: {} — reason: {}",
            next_agent,
            subtask[:80],
            reasoning,
        )

        new_error_count = error_count + 1 if state.get("error") else 0

        return {
            "messages": [AIMessage(content=content, name="orchestrator")],
            "next_agent": next_agent,
            "subtask": subtask,
            "iteration": iteration + 1,
            "error_count": new_error_count,
            "error": None,
        }
    except Exception as exc:
        logger.error("Orchestrator failed: {}", exc)
        return {
            "messages": [
                AIMessage(content=f"Orchestrator error: {exc}", name="orchestrator")
            ],
            "next_agent": "END",
            "subtask": "",
            "iteration": iteration + 1,
            "error": str(exc),
        }
