from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # LLM
    ollama_base_url: str = "http://localhost:11434"
    default_model: str = "llama3.1:8b"
    reasoning_model: str = "llama3.1:70b"

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "multi-agent-system"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Email
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""
    email_to: str = ""

    # Agent limits
    max_iterations: int = 10
    max_tool_calls_per_agent: int = 5
    code_execution_timeout: int = 30
    agent_workspace: Path = Field(default=Path("/tmp/agent_workspace"))

    def apply_langsmith_env(self) -> None:
        """Push LangSmith vars into os.environ so LangChain picks them up."""
        os.environ["LANGCHAIN_TRACING_V2"] = str(self.langchain_tracing_v2).lower()
        os.environ["LANGCHAIN_API_KEY"] = self.langchain_api_key
        os.environ["LANGCHAIN_PROJECT"] = self.langchain_project


settings = Settings()
