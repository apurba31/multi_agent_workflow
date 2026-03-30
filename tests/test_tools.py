from __future__ import annotations

import re
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.code_tools import CODE_TOOLS, execute_shell, lint_code, read_file, write_file
from tools.comms_tools import (
    COMMS_TOOLS,
    _escape_markdown_v2,
    format_html,
    format_markdown,
    send_email,
    send_telegram,
)
from tools.search_tools import RESEARCH_TOOLS


class TestSearchTools:
    def test_research_tools_list_has_four_tools(self):
        assert len(RESEARCH_TOOLS) == 4

    def test_tool_names(self):
        names = {t.name for t in RESEARCH_TOOLS}
        assert names == {"duckduckgo_search", "wikipedia_search", "scrape_url", "summarize_text"}

    @patch("tools.search_tools.DDGS")
    def test_duckduckgo_search_returns_results(self, mock_ddgs_cls):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.text.return_value = [
            {"title": "Result 1", "href": "https://example.com", "body": "Body 1"},
        ]
        mock_ddgs_cls.return_value = mock_instance

        from tools.search_tools import duckduckgo_search

        result = duckduckgo_search.invoke({"query": "test"})
        assert "Result 1" in result
        assert "https://example.com" in result

    @patch("tools.search_tools.DDGS")
    def test_duckduckgo_search_no_results(self, mock_ddgs_cls):
        mock_instance = MagicMock()
        mock_instance.__enter__ = MagicMock(return_value=mock_instance)
        mock_instance.__exit__ = MagicMock(return_value=False)
        mock_instance.text.return_value = []
        mock_ddgs_cls.return_value = mock_instance

        from tools.search_tools import duckduckgo_search

        result = duckduckgo_search.invoke({"query": "nonexistent"})
        assert result == "No results found."

    @patch("tools.search_tools.wikipedia")
    def test_wikipedia_search_success(self, mock_wiki):
        mock_wiki.summary.return_value = "Python is a programming language."

        from tools.search_tools import wikipedia_search

        result = wikipedia_search.invoke({"query": "Python"})
        assert "Python" in result

    @patch("tools.search_tools.wikipedia")
    def test_wikipedia_search_page_not_found(self, mock_wiki):
        import wikipedia as wiki_mod

        mock_wiki.PageError = wiki_mod.PageError
        mock_wiki.DisambiguationError = wiki_mod.DisambiguationError
        mock_wiki.summary.side_effect = wiki_mod.PageError("xyz")

        from tools.search_tools import wikipedia_search

        result = wikipedia_search.invoke({"query": "xyz_nonexistent_page_12345"})
        assert "No Wikipedia page found" in result


class TestCommsTools:
    def test_comms_tools_list_has_four_tools(self):
        assert len(COMMS_TOOLS) == 4

    def test_escape_markdown_v2(self):
        assert _escape_markdown_v2("hello_world") == r"hello\_world"
        assert _escape_markdown_v2("price: $10.00") == r"price: $10\.00"

    def test_format_markdown_with_title(self):
        result = format_markdown.invoke({"content": "Hello world", "title": "Report"})
        assert "Report" in result

    def test_format_markdown_without_title(self):
        result = format_markdown.invoke({"content": "Just text"})
        assert "Just text" in result

    def test_format_html_with_title(self):
        result = format_html.invoke({"content": "Hello world", "title": "Report"})
        assert "<h2>Report</h2>" in result
        assert "<html>" in result
        assert "</html>" in result

    def test_format_html_without_title(self):
        result = format_html.invoke({"content": "Paragraph one\n\nParagraph two"})
        assert "<p>Paragraph one</p>" in result
        assert "<p>Paragraph two</p>" in result

    def test_send_telegram_not_configured(self):
        with patch("tools.comms_tools.settings") as mock_settings:
            mock_settings.telegram_bot_token = ""
            mock_settings.telegram_chat_id = ""
            result = send_telegram.invoke({"message": "test"})
            assert "not configured" in result

    def test_send_email_not_configured(self):
        with patch("tools.comms_tools.settings") as mock_settings:
            mock_settings.smtp_user = ""
            mock_settings.smtp_password = ""
            result = send_email.invoke({"subject": "Test", "body": "Body"})
            assert "not configured" in result


class TestCodeTools:
    def test_code_tools_list_has_six_tools(self):
        assert len(CODE_TOOLS) == 6

    def test_write_and_read_file(self, tmp_path):
        with patch("tools.code_tools.settings") as mock_settings:
            mock_settings.agent_workspace = tmp_path
            write_result = write_file.invoke({"filename": "test.py", "content": "print('hi')"})
            assert "File written" in write_result

            read_result = read_file.invoke({"filename": "test.py"})
            assert read_result == "print('hi')"

    def test_read_file_not_found(self, tmp_path):
        with patch("tools.code_tools.settings") as mock_settings:
            mock_settings.agent_workspace = tmp_path
            result = read_file.invoke({"filename": "nonexistent.py"})
            assert "File not found" in result

    def test_execute_shell_blocks_dangerous_commands(self, tmp_path):
        with patch("tools.code_tools.settings") as mock_settings:
            mock_settings.agent_workspace = tmp_path
            mock_settings.code_execution_timeout = 5
            result = execute_shell.invoke({"command": "rm -rf /"})
            assert "Blocked" in result

    def test_execute_shell_blocks_sudo(self, tmp_path):
        with patch("tools.code_tools.settings") as mock_settings:
            mock_settings.agent_workspace = tmp_path
            mock_settings.code_execution_timeout = 5
            result = execute_shell.invoke({"command": "sudo apt install something"})
            assert "Blocked" in result

    def test_execute_shell_safe_command(self, tmp_path):
        with patch("tools.code_tools.settings") as mock_settings:
            mock_settings.agent_workspace = tmp_path
            mock_settings.code_execution_timeout = 10
            result = execute_shell.invoke({"command": "echo hello"})
            assert "hello" in result


class TestBrowserTools:
    def test_browser_tools_list_has_eight_tools(self):
        from tools.browser_tools import BROWSER_TOOLS

        assert len(BROWSER_TOOLS) == 8

    def test_browser_tool_names(self):
        from tools.browser_tools import BROWSER_TOOLS

        names = {t.name for t in BROWSER_TOOLS}
        expected = {
            "navigate_to",
            "click_element",
            "fill_input",
            "extract_text",
            "take_screenshot",
            "wait_for_element",
            "get_page_links",
            "close_browser",
        }
        assert names == expected
