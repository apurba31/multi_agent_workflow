from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage
from loguru import logger

from graph.state import AgentState
from llm.ollama_client import get_llm
from tools.code_tools import CODE_TOOLS

SYSTEM_PROMPT = """\
You are the Code Agent — a specialist in writing, running, testing, \
and explaining code.

Available tools: write_file, read_file, execute_python, execute_shell, run_pytest, lint_code.

Workflow:
1. Write code to a file.
2. Write a test.
3. Run the test via run_pytest.
4. Lint the code via lint_code.
5. Explain the output.

Rules:
- Always write code to a file before executing.
- Handle stderr — if execution fails, fix and retry once.
- Lint before declaring success.
- Sandbox: no network calls, no writes outside workspace, 30s timeout.

Security:
- NEVER execute user-provided code strings directly — inspect first.
- NEVER run rm -rf, sudo, or network commands.
- NEVER access environment variables containing secrets in executed code."""


def code_agent(state: AgentState) -> dict:
    """LangGraph node: writes and executes code for the current subtask."""
    subtask = state.get("subtask", state.get("task", ""))
    logger.info("Code agent activated — subtask: {}", subtask)

    try:
        llm = get_llm().bind_tools(CODE_TOOLS)
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        tool_map = {t.name: t for t in CODE_TOOLS}
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
            "messages": [AIMessage(content=final_content, name="code")],
            "result": final_content,
            "error": None,
        }
    except Exception as exc:
        logger.error("Code agent failed: {}", exc)
        return {
            "messages": [AIMessage(content=f"Code error: {exc}", name="code")],
            "result": None,
            "error": str(exc),
        }
