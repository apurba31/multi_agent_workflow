from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from graph.state import AgentState
from llm.ollama_client import get_llm
from tools.browser_tools import BROWSER_TOOLS

SYSTEM_PROMPT = """You are the Browser Agent — a specialist in web automation using Playwright.

Available tools: navigate_to, click_element, fill_input, extract_text,
take_screenshot, wait_for_element, get_page_links, close_browser.

Rules:
- Always navigate_to a URL before any other action.
- Wait for dynamic content on SPAs before extracting.
- Take a screenshot after key steps.
- Prefer semantic selectors: [data-testid] > CSS class > XPath.
- Handle errors: try a fallback selector, then report failure.
- Always call close_browser when done.

Security:
- NEVER fill passwords unless explicitly marked as credentials in state.
- NEVER navigate to file:// or data: URLs.
- NEVER execute arbitrary JavaScript from user input."""


def browser_agent(state: AgentState) -> dict:
    """LangGraph node: performs browser automation on the current subtask."""
    subtask = state.get("subtask", state.get("task", ""))
    logger.info("Browser agent activated — subtask: {}", subtask)

    try:
        llm = get_llm().bind_tools(BROWSER_TOOLS)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        tool_map = {t.name: t for t in BROWSER_TOOLS}
        iterations = 0
        max_tool_rounds = 8

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
            "messages": [AIMessage(content=final_content, name="browser")],
            "result": final_content,
            "error": None,
        }
    except Exception as exc:
        logger.error("Browser agent failed: {}", exc)
        return {
            "messages": [AIMessage(content=f"Browser error: {exc}", name="browser")],
            "result": None,
            "error": str(exc),
        }
