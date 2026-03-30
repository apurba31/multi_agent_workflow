# Multi-Agent System

A production-grade multi-agent system built with **LangGraph** for orchestration, **Ollama** for local LLM inference, **Playwright** for browser automation, and **LangSmith** for observability.

## Architecture

```
User Task
    │
    ▼
┌──────────────┐
│ Orchestrator  │◄─────────────────────────────┐
│ (supervisor)  │                               │
└──────┬───────┘                               │
       │ routes to                              │
       ▼                                        │
┌──────────────┐    ┌──────────────┐    ┌──────┴───────┐
│   research   │    │   browser    │    │  reflection   │
│   comms      │    │   code       │    │  (QA review)  │
└──────┬───────┘    └──────┬───────┘    └──────────────┘
       │                   │                    ▲
       └───────────────────┴────────────────────┘
                    after every agent
```

The system follows a **supervisor loop**:

1. **Orchestrator** decomposes the user task, picks the right specialist, writes a precise subtask
2. **Specialist agent** (research / browser / comms / code) executes via a ReAct tool-calling loop
3. **Reflection agent** reviews the output for quality — can trigger retries
4. **Orchestrator** re-evaluates: route to the next agent, retry, or END
5. **Circuit breakers**: max 10 iterations, max 2 consecutive errors

## Agents

| Agent | Role | Tools |
|-------|------|-------|
| **Orchestrator** | Decomposes tasks, routes to specialists | — (LLM-only) |
| **Research** | Web search, Wikipedia, URL scraping, summarization | `duckduckgo_search`, `wikipedia_search`, `scrape_url`, `summarize_text` |
| **Browser** | Playwright-based web automation | `navigate_to`, `click_element`, `fill_input`, `extract_text`, `take_screenshot`, `wait_for_element`, `get_page_links`, `close_browser` |
| **Comms** | Telegram and email notifications | `send_telegram`, `send_email`, `format_markdown`, `format_html` |
| **Code** | Write, execute, test, and lint Python | `write_file`, `read_file`, `execute_python`, `execute_shell`, `run_pytest`, `lint_code` |
| **Reflection** | Reviews the last agent output; may set `retry_required` and surface issues | — (LLM-only JSON review) |

This repository’s **single user-facing doc** for setup, running, configuration, UI, tests, and CI is this file. Agent/orchestrator **prompts and Cursor rules** live under `.cursor/rules/` (not duplicated here).

## Project Structure

```
multi_agent/
├── .cursor/rules/             # Cursor rules + agent system prompts
├── agents/
│   ├── orchestrator.py        # Central router
│   ├── research_agent.py      # Web research
│   ├── browser_agent.py       # Playwright automation
│   ├── comms_agent.py         # Telegram + email
│   ├── code_agent.py          # Code execution
│   └── reflection_agent.py    # Quality reviewer
├── tools/
│   ├── search_tools.py        # DuckDuckGo, Wikipedia, scraping
│   ├── browser_tools.py       # Playwright wrappers
│   ├── comms_tools.py         # Telegram API, SMTP
│   └── code_tools.py          # File I/O, subprocess, pytest
├── graph/
│   ├── state.py               # AgentState TypedDict
│   ├── graph_builder.py       # LangGraph node/edge wiring
│   ├── runner.py              # Initial state + streaming API (CLI + UI)
│   └── checkpointer.py        # State persistence
├── ui/
│   ├── app.py                 # Streamlit dashboard (steps + upload)
│   └── upload_parser.py       # Parse uploaded files into prompt text
├── llm/
│   └── ollama_client.py       # ChatOllama factory
├── config/
│   └── settings.py            # Pydantic Settings from .env
├── tests/
│   ├── test_state.py          # State schema tests
│   ├── test_tools.py          # Tool unit tests
│   ├── test_agents.py         # Agent node tests (mocked LLM)
│   ├── test_graph.py          # Graph compilation + routing
│   ├── test_upload_parser.py  # Upload parsing + prompt building
│   ├── test_runner.py         # Graph runner / streaming helpers
│   └── conftest.py            # Shared fixtures
├── main.py                    # CLI entry point
├── pyproject.toml             # Dependencies + config
├── docker-compose.yml         # Ollama with GPU
├── .env.example               # Environment template
└── .github/workflows/ci.yml   # GitHub Actions CI
```

## Prerequisites

- **Python 3.11+**
- **Ollama** running locally (or via Docker)
- **Playwright browsers** installed (for browser agent)

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url> && cd multi_agent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

# Install dependencies (core + tests/lint + Streamlit UI)
pip install -e ".[dev,ui]"

# Install Playwright browsers
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your keys (Telegram, SMTP, LangSmith)
```

### 3. Start Ollama

**Option A — Docker (recommended):**

```bash
docker compose up -d
docker exec ollama ollama pull llama3.1:8b
```

**Option B — Native install:**

```bash
ollama serve
ollama pull llama3.1:8b
```

### 4. Run a task

**CLI:**

```bash
python main.py "Research the latest LLM benchmarks and send me a Telegram summary"
```

**Streamlit UI** (step timeline, file upload) — uses the `[ui]` extra (already included if you ran `pip install -e ".[dev,ui]"` above):

```bash
streamlit run ui/app.py
```

Open the URL Streamlit prints (usually `http://localhost:8501`). Enter a task, optionally upload a `.txt`, `.md`, `.csv`, `.json`, or similar file — the parsed text is injected into the first message so agents can use it. Each graph node appears in an expandable timeline with subtask, result, and errors.

```bash
python main.py "Go to https://news.ycombinator.com and get the top 5 stories"
```

```bash
python main.py "Write a Python function to calculate Fibonacci numbers and test it"
```

## Configuration

All configuration is via environment variables (or `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `DEFAULT_MODEL` | `llama3.1:8b` | Default LLM for agents |
| `REASONING_MODEL` | `llama3.1:70b` | Larger model for complex reasoning |
| `LANGCHAIN_TRACING_V2` | `true` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `LANGCHAIN_PROJECT` | `multi-agent-system` | LangSmith project name |
| `TELEGRAM_BOT_TOKEN` | — | Telegram bot token |
| `TELEGRAM_CHAT_ID` | — | Telegram chat/channel ID |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_USER` | — | SMTP username |
| `SMTP_PASSWORD` | — | SMTP app password |
| `EMAIL_FROM` | — | Sender email |
| `EMAIL_TO` | — | Default recipient |
| `MAX_ITERATIONS` | `10` | Max orchestrator loops |
| `CODE_EXECUTION_TIMEOUT` | `30` | Seconds before code exec times out |
| `AGENT_WORKSPACE` | `/tmp/agent_workspace` | Sandbox directory for code agent |

## Optional extras

| Extra | Purpose |
|-------|---------|
| `dev` | pytest, ruff, pytest-mock |
| `ui` | Streamlit dashboard (`streamlit run ui/app.py`) |

```bash
pip install -e ".[dev,ui]"
```

## Running Tests

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --tb=short

# Run a specific test file
pytest tests/test_tools.py -v

# Lint the codebase
ruff check .
```

## CI Pipeline

GitHub Actions runs on every push and pull request:

1. **Lint** — `ruff check .` across the entire codebase
2. **Test** — `pytest` with Python 3.11 and 3.12
3. **Import check** — verifies all modules import cleanly

See `.github/workflows/ci.yml` for details.

## Design Decisions

- **Every agent is a pure function** `(AgentState) -> dict` — no side effects on shared state
- **Typed state** via `TypedDict` with LangGraph's `add_messages` reducer
- **Tools use LangChain's `@tool` decorator** — LLM decides when to call them
- **Single LLM abstraction** (`ollama_client.py`) — model names never hardcoded in agents
- **Reflection loop** — every agent output is reviewed before the orchestrator re-routes
- **Circuit breakers** — max iterations and consecutive error limits prevent infinite loops

## License

MIT
