# Multi-Agent System — Cursor Rules

## Project Philosophy

This is a production-grade multi-agent system built with:
- LangGraph for orchestration (state machine, conditional edges, human-in-the-loop)
- LangChain for tool/chain primitives
- LangSmith for observability, tracing, and evals
- Ollama / vLLM for open-source LLM inference (Llama 3, Mistral, Qwen)
- Playwright for browser automation
- python-telegram-bot for messaging

## Architecture Rules

### 1. Every agent is a LangGraph node
- All agents are pure functions: `(state: AgentState) -> dict`
- Agents NEVER mutate state directly — they return partial updates
- State is always a TypedDict or BaseModel (Pydantic v2)

### 2. Typed state is non-negotiable
```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    task: str
    result: str | None
    agent_scratchpad: list[dict]
    error: str | None
    iteration: int
```

### 3. Tool definitions follow the LangChain @tool pattern
```python
from langchain_core.tools import tool

@tool
def my_tool(query: str) -> str:
    """One-line description used by the LLM to decide when to call this."""
    ...
```

### 4. All LLM calls go through the OllamaLLM abstraction
- Default model: `llama3.1:8b` for fast agents, `llama3.1:70b` for reasoning
- Never hardcode model names — always use `settings.DEFAULT_MODEL`
- Always set `temperature=0` for deterministic tool-use agents

### 5. LangSmith tracing is always on in dev
```python
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "multi-agent-system"
```

### 6. Error handling in agents
- Every agent node must catch exceptions and write to `state["error"]`
- Orchestrator checks `state["error"]` before routing
- Max iterations guard: if `state["iteration"] >= MAX_ITER`, route to END

### 7. Playwright usage
- Always use `async_playwright` — never sync
- Always close browser in `finally` block
- Screenshot on error for debugging

### 8. File structure
```
multi_agent_system/
├── .cursor/rules/
│   ├── agent.md
│   ├── orchestrator.md
│   ├── research_agent.md
│   ├── browser_agent.md
│   ├── comms_agent.md
│   └── code_agent.md
├── agents/
│   ├── orchestrator.py
│   ├── research_agent.py
│   ├── browser_agent.py
│   ├── comms_agent.py
│   └── code_agent.py
├── tools/
│   ├── search_tools.py
│   ├── browser_tools.py
│   ├── comms_tools.py
│   └── code_tools.py
├── graph/
│   ├── state.py
│   ├── graph_builder.py
│   ├── runner.py
│   └── checkpointer.py
├── ui/
│   ├── app.py
│   └── upload_parser.py
├── llm/
│   └── ollama_client.py
├── config/
│   └── settings.py
├── main.py
├── .env.example
├── pyproject.toml
└── docker-compose.yml
```

## Code Style
- Python 3.11+
- Type hints on every function signature
- Async-first: all I/O is `async def`
- Pydantic v2 for settings and validation
- loguru for structured logging
- pytest-asyncio for tests
