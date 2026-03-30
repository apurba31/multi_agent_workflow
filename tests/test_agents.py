from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


class TestOrchestrator:
    def test_routes_to_end_on_max_iterations(self, base_state):
        base_state["iteration"] = 10
        from agents.orchestrator import orchestrator

        result = orchestrator(base_state)
        assert result["next_agent"] == "END"

    def test_routes_to_end_on_error_count(self, base_state):
        base_state["error_count"] = 2
        from agents.orchestrator import orchestrator

        result = orchestrator(base_state)
        assert result["next_agent"] == "END"

    def test_routes_to_research(self, base_state, orchestrator_llm_research):
        with patch("agents.orchestrator.get_llm", return_value=orchestrator_llm_research):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["next_agent"] == "research"
            assert result["subtask"] == "Search for LLM benchmarks"
            assert result["iteration"] == 1

    def test_routes_to_end(self, base_state, orchestrator_llm_end):
        with patch("agents.orchestrator.get_llm", return_value=orchestrator_llm_end):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["next_agent"] == "END"

    def test_increments_iteration(self, base_state, orchestrator_llm_end):
        base_state["iteration"] = 3
        with patch("agents.orchestrator.get_llm", return_value=orchestrator_llm_end):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["iteration"] == 4

    def test_increments_error_count_on_previous_error(self, base_state, orchestrator_llm_end):
        base_state["error"] = "some previous error"
        base_state["error_count"] = 0
        with patch("agents.orchestrator.get_llm", return_value=orchestrator_llm_end):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["error_count"] == 1

    def test_resets_error_count_on_no_error(self, base_state, orchestrator_llm_end):
        base_state["error"] = None
        base_state["error_count"] = 1
        with patch("agents.orchestrator.get_llm", return_value=orchestrator_llm_end):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["error_count"] == 0

    def test_handles_invalid_agent_name(self, base_state, mock_llm_response):
        llm = mock_llm_response(
            json.dumps({"next_agent": "invalid_agent", "subtask": "", "reasoning": ""})
        )
        with patch("agents.orchestrator.get_llm", return_value=llm):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["next_agent"] == "END"

    def test_handles_non_json_with_embedded_json(self, base_state, mock_llm_response):
        llm = mock_llm_response(
            'Sure! Here is my decision: '
            '{"next_agent": "code", "subtask": "write fib", "reasoning": "needs code"}'
        )
        with patch("agents.orchestrator.get_llm", return_value=llm):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["next_agent"] == "code"

    def test_handles_complete_garbage_output(self, base_state, mock_llm_response):
        llm = mock_llm_response("I don't know what to do")
        with patch("agents.orchestrator.get_llm", return_value=llm):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["next_agent"] == "END"

    def test_handles_llm_exception(self, base_state):
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM is down")
        with patch("agents.orchestrator.get_llm", return_value=llm):
            from agents.orchestrator import orchestrator

            result = orchestrator(base_state)
            assert result["next_agent"] == "END"
            assert "LLM is down" in result["error"]


class TestResearchAgent:
    def test_returns_result_on_success(self, base_state, mock_llm_response):
        llm = mock_llm_response("Here are the research findings about LLMs.")
        with patch("agents.research_agent.get_llm", return_value=llm):
            from agents.research_agent import research_agent

            result = research_agent(base_state)
            assert result["result"] == "Here are the research findings about LLMs."
            assert result["error"] is None
            assert len(result["messages"]) == 1
            assert result["messages"][0].name == "research"

    def test_handles_exception(self, base_state):
        llm = MagicMock()
        llm.bind_tools.side_effect = RuntimeError("Tool binding failed")
        with patch("agents.research_agent.get_llm", return_value=llm):
            from agents.research_agent import research_agent

            result = research_agent(base_state)
            assert result["error"] is not None
            assert result["result"] is None
            assert "Tool binding failed" in result["error"]


class TestBrowserAgent:
    def test_returns_result_on_success(self, base_state, mock_llm_response):
        llm = mock_llm_response("Extracted 5 stories from Hacker News.")
        with patch("agents.browser_agent.get_llm", return_value=llm):
            from agents.browser_agent import browser_agent

            result = browser_agent(base_state)
            assert result["result"] == "Extracted 5 stories from Hacker News."
            assert result["error"] is None
            assert result["messages"][0].name == "browser"

    def test_handles_exception(self, base_state):
        llm = MagicMock()
        llm.bind_tools.side_effect = RuntimeError("Playwright not installed")
        with patch("agents.browser_agent.get_llm", return_value=llm):
            from agents.browser_agent import browser_agent

            result = browser_agent(base_state)
            assert result["error"] is not None
            assert "Playwright not installed" in result["error"]


class TestCommsAgent:
    def test_returns_result_on_success(self, base_state, mock_llm_response):
        llm = mock_llm_response("Message sent to Telegram (message_id=123).")
        with patch("agents.comms_agent.get_llm", return_value=llm):
            from agents.comms_agent import comms_agent

            result = comms_agent(base_state)
            assert "message_id=123" in result["result"]
            assert result["error"] is None
            assert result["messages"][0].name == "comms"

    def test_handles_exception(self, base_state):
        llm = MagicMock()
        llm.bind_tools.side_effect = RuntimeError("Telegram API down")
        with patch("agents.comms_agent.get_llm", return_value=llm):
            from agents.comms_agent import comms_agent

            result = comms_agent(base_state)
            assert result["error"] is not None


class TestCodeAgent:
    def test_returns_result_on_success(self, base_state, mock_llm_response):
        llm = mock_llm_response("Code written and tests passed: 3/3.")
        with patch("agents.code_agent.get_llm", return_value=llm):
            from agents.code_agent import code_agent

            result = code_agent(base_state)
            assert "tests passed" in result["result"]
            assert result["error"] is None
            assert result["messages"][0].name == "code"

    def test_handles_exception(self, base_state):
        llm = MagicMock()
        llm.bind_tools.side_effect = RuntimeError("Sandbox error")
        with patch("agents.code_agent.get_llm", return_value=llm):
            from agents.code_agent import code_agent

            result = code_agent(base_state)
            assert result["error"] is not None
            assert "Sandbox error" in result["error"]


class TestReflectionAgent:
    def test_pass_quality(self, base_state, mock_llm_response):
        review = json.dumps({
            "quality": "pass",
            "issues_found": [],
            "fix_suggestions": [],
            "retry_required": False,
        })
        llm = mock_llm_response(review)
        with patch("agents.reflection_agent.get_llm", return_value=llm):
            from agents.reflection_agent import reflection_agent

            result = reflection_agent(base_state)
            assert result["error"] is None
            assert result["messages"][0].name == "reflection"

    def test_fail_quality_triggers_retry(self, base_state, mock_llm_response):
        review = json.dumps({
            "quality": "fail",
            "issues_found": ["Missing sources"],
            "fix_suggestions": ["Add citations"],
            "retry_required": True,
        })
        llm = mock_llm_response(review)
        with patch("agents.reflection_agent.get_llm", return_value=llm):
            from agents.reflection_agent import reflection_agent

            result = reflection_agent(base_state)
            assert result["error"] is not None
            assert "Missing sources" in result["error"]

    def test_handles_non_json_gracefully(self, base_state, mock_llm_response):
        llm = mock_llm_response("This is not JSON at all")
        with patch("agents.reflection_agent.get_llm", return_value=llm):
            from agents.reflection_agent import reflection_agent

            result = reflection_agent(base_state)
            assert result["error"] is None

    def test_handles_exception(self, base_state):
        llm = MagicMock()
        llm.invoke.side_effect = RuntimeError("LLM crashed")
        with patch("agents.reflection_agent.get_llm", return_value=llm):
            from agents.reflection_agent import reflection_agent

            result = reflection_agent(base_state)
            assert result["error"] is None
