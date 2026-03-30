from __future__ import annotations

from langgraph.graph import END, StateGraph

from agents.browser_agent import browser_agent
from agents.code_agent import code_agent
from agents.comms_agent import comms_agent
from agents.orchestrator import orchestrator
from agents.reflection_agent import reflection_agent
from agents.research_agent import research_agent
from graph.state import AgentState


def _route_after_orchestrator(state: AgentState) -> str:
    """Conditional edge: read next_agent from state and route accordingly."""
    next_agent = state.get("next_agent", "END")
    if next_agent == "END":
        return END
    agent_map = {
        "research": "research",
        "browser": "browser",
        "comms": "comms",
        "code": "code",
    }
    return agent_map.get(next_agent, END)


def _route_after_reflection(state: AgentState) -> str:
    """If reflection found issues, loop back to orchestrator; otherwise END the cycle."""
    if state.get("error"):
        return "orchestrator"
    return "orchestrator"


def build_graph(checkpointer=None):
    """Construct the multi-agent LangGraph.

    Flow:
        orchestrator → (conditional) → agent → reflection → orchestrator (loop)
                     → END (when done or max iterations)
    """
    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator)
    graph.add_node("research", research_agent)
    graph.add_node("browser", browser_agent)
    graph.add_node("comms", comms_agent)
    graph.add_node("code", code_agent)
    graph.add_node("reflection", reflection_agent)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges(
        "orchestrator",
        _route_after_orchestrator,
        {
            "research": "research",
            "browser": "browser",
            "comms": "comms",
            "code": "code",
            END: END,
        },
    )

    for agent_name in ["research", "browser", "comms", "code"]:
        graph.add_edge(agent_name, "reflection")

    graph.add_edge("reflection", "orchestrator")

    return graph.compile(checkpointer=checkpointer)
