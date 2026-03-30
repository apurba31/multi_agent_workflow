from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from graph.state import AgentState
from llm.ollama_client import get_llm
from tools.search_tools import RESEARCH_TOOLS

SYSTEM_PROMPT = """\
You are the Research Agent — a specialist in information retrieval \
and summarization.

Available tools: duckduckgo_search, wikipedia_search, scrape_url, summarize_text.

Rules:
- Always search before answering — never hallucinate facts.
- Cross-reference at least 2 sources for factual claims.
- Cite your sources with URLs.
- Be concise — your output goes to other agents.
- Do not exceed 5 tool calls.

Output a structured research result with Summary, Key Facts, and Sources."""


def research_agent(state: AgentState) -> dict:
    """LangGraph node: performs web research on the current subtask."""
    subtask = state.get("subtask", state.get("task", ""))
    logger.info("Research agent activated — subtask: {}", subtask)

    try:
        llm = get_llm().bind_tools(RESEARCH_TOOLS)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        tool_map = {t.name: t for t in RESEARCH_TOOLS}
        iterations = 0
        max_tool_rounds = 5

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
            "messages": [AIMessage(content=final_content, name="research")],
            "result": final_content,
            "error": None,
        }
    except Exception as exc:
        logger.error("Research agent failed: {}", exc)
        return {
            "messages": [AIMessage(content=f"Research error: {exc}", name="research")],
            "result": None,
            "error": str(exc),
        }
