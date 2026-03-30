from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from graph.state import AgentState
from llm.ollama_client import get_llm
from tools.comms_tools import COMMS_TOOLS

SYSTEM_PROMPT = """You are the Comms Agent — a specialist in sending notifications and messages.

Available tools: format_markdown, format_html, send_telegram, send_email.

Rules:
- Format before sending — never send raw agent output.
- Telegram messages must be under 4096 chars.
- Use Telegram MarkdownV2 — escape special characters.
- Confirm before sending sensitive data (PII).
- Always return a delivery receipt (message_id or timestamp).
- If Telegram fails, format output as a file and report it.

Anti-patterns:
- DO NOT send the same message twice.
- DO NOT send raw Python tracebacks.
- DO NOT include API keys or secrets in messages."""


def comms_agent(state: AgentState) -> dict:
    """LangGraph node: sends notifications via Telegram or email."""
    subtask = state.get("subtask", state.get("task", ""))
    logger.info("Comms agent activated — subtask: {}", subtask)

    try:
        llm = get_llm().bind_tools(COMMS_TOOLS)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        tool_map = {t.name: t for t in COMMS_TOOLS}
        iterations = 0
        max_tool_rounds = 4

        while iterations < max_tool_rounds:
            response = llm.invoke(messages)
            messages.append(response)

            if not response.tool_calls:
                break

            for tc in response.tool_calls:
                tool_fn = tool_map.get(tc["name"])
                if tool_fn is None:
                    result = f"Unknown tool: {tc['name']}"
                else:
                    result = tool_fn.invoke(tc["args"])
                from langchain_core.messages import ToolMessage

                messages.append(
                    ToolMessage(content=str(result), tool_call_id=tc["id"])
                )
            iterations += 1

        final_content = response.content if response.content else "No result produced."
        return {
            "messages": [AIMessage(content=final_content, name="comms")],
            "result": final_content,
            "error": None,
        }
    except Exception as exc:
        logger.error("Comms agent failed: {}", exc)
        return {
            "messages": [AIMessage(content=f"Comms error: {exc}", name="comms")],
            "result": None,
            "error": str(exc),
        }
