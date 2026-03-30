from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from langchain_core.tools import tool
from loguru import logger

from config.settings import settings


def _workspace() -> Path:
    """Ensure the agent workspace directory exists and return it."""
    ws = settings.agent_workspace
    ws.mkdir(parents=True, exist_ok=True)
    return ws


@tool
def write_file(filename: str, content: str) -> str:
    """Write content to a file in the agent workspace."""
    path = _workspace() / filename
    logger.info("Writing file: {}", path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return f"File written: {path} ({len(content)} chars)"


@tool
def read_file(filename: str) -> str:
    """Read a file from the agent workspace."""
    path = _workspace() / filename
    if not path.exists():
        return f"File not found: {path}"
    return path.read_text(encoding="utf-8")


@tool
def execute_python(filename: str) -> str:
    """Execute a Python script from the agent workspace. Returns stdout and stderr."""
    path = _workspace() / filename
    if not path.exists():
        return f"File not found: {path}"
    logger.info("Executing: {}", path)
    try:
        result = subprocess.run(
            [sys.executable, str(path)],
            capture_output=True,
            text=True,
            timeout=settings.code_execution_timeout,
            cwd=str(_workspace()),
        )
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
        output += f"Exit code: {result.returncode}"
        return output
    except subprocess.TimeoutExpired:
        return f"Execution timed out after {settings.code_execution_timeout}s"
    except Exception as exc:
        return f"Execution error: {exc}"


@tool
def execute_shell(command: str) -> str:
    """Run a shell command in the agent workspace. Limited to safe commands."""
    blocked = ["rm -rf", "sudo", "mkfs", "dd if=", ":(){ :|:& };:"]
    for b in blocked:
        if b in command:
            return f"Blocked dangerous command: {command}"

    logger.info("Shell: {}", command)
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=settings.code_execution_timeout,
            cwd=str(_workspace()),
        )
        output = ""
        if result.stdout:
            output += result.stdout
        if result.stderr:
            output += f"\nSTDERR: {result.stderr}"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Command timed out after {settings.code_execution_timeout}s"
    except Exception as exc:
        return f"Shell error: {exc}"


@tool
def run_pytest(path: str = ".") -> str:
    """Run pytest on a file or directory in the agent workspace."""
    target = _workspace() / path
    logger.info("Running pytest on: {}", target)
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", str(target), "-v", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=settings.code_execution_timeout * 2,
            cwd=str(_workspace()),
        )
        return result.stdout + (f"\nSTDERR: {result.stderr}" if result.stderr else "")
    except subprocess.TimeoutExpired:
        return "Pytest timed out."
    except Exception as exc:
        return f"Pytest error: {exc}"


@tool
def lint_code(filename: str) -> str:
    """Run ruff linter on a Python file in the agent workspace."""
    path = _workspace() / filename
    if not path.exists():
        return f"File not found: {path}"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", str(path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return "All checks passed."
        return result.stdout or result.stderr
    except Exception as exc:
        return f"Lint error: {exc}"


CODE_TOOLS = [write_file, read_file, execute_python, execute_shell, run_pytest, lint_code]
