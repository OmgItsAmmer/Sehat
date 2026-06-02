"""LangGraph triage graph — compile once, invoke from webhook or scratch scripts."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import TriageState

def _route_after_classify(state: TriageState) -> str:
    priority = state.get("priority")
    if priority == "P1":
        return "emergency_exit"
    if priority == "OOS":
        return "oos_exit"
    return "slot_check"


def _route_after_slot_check(state: TriageState) -> str:
    if state.get("slots_complete"):
        return "route"
    return "gather_slots"


def _route_after_gather_slots(state: TriageState) -> str:
    """Pause after asking a slot question; resume on the next message (Phase 6 memory)."""
    if state.get("slots_complete"):
        return "slot_check"
    return "__end__"


def _route_after_route(state: TriageState) -> str:
    priority = state.get("priority")
    if state.get("escalated") or priority in ("P1", "P2"):
        return "notify_human"
    return "confirm_user"


def build_graph() -> StateGraph:
    builder = StateGraph(TriageState)

    builder.add_node("classify", nodes.classify_node)
    builder.add_node("emergency_exit", nodes.emergency_exit_node)
    builder.add_node("oos_exit", nodes.oos_exit_node)
    builder.add_node("slot_check", nodes.slot_check_node)
    builder.add_node("gather_slots", nodes.gather_slots_node)
    builder.add_node("route", nodes.route_node)
    builder.add_node("notify_human", nodes.notify_human_node)
    builder.add_node("confirm_user", nodes.confirm_user_node)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges(
        "classify",
        _route_after_classify,
        {
            "emergency_exit": "emergency_exit",
            "oos_exit": "oos_exit",
            "slot_check": "slot_check",
        },
    )
    builder.add_edge("emergency_exit", "notify_human")
    builder.add_edge("oos_exit", "confirm_user")
    builder.add_conditional_edges(
        "slot_check",
        _route_after_slot_check,
        {"route": "route", "gather_slots": "gather_slots"},
    )
    builder.add_conditional_edges(
        "gather_slots",
        _route_after_gather_slots,
        {"slot_check": "slot_check", "__end__": END},
    )
    builder.add_conditional_edges(
        "route",
        _route_after_route,
        {"notify_human": "notify_human", "confirm_user": "confirm_user"},
    )
    builder.add_edge("notify_human", "confirm_user")
    builder.add_edge("confirm_user", END)

    return builder


# Compiled graph — import as `from app.agent.graph import graph`.
graph = build_graph().compile()
