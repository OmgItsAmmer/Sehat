"""LangGraph triage graph — compile once, invoke from webhook or scratch scripts."""

from __future__ import annotations

from typing import cast

from langgraph.graph import END, START, StateGraph

from app.agent import nodes
from app.agent.state import TriageState, missing_slots
from app.config import settings


def _can_offer_appointment(state: TriageState) -> bool:
    return nodes._can_offer_appointment(state)


def _route_from_start(state: TriageState) -> str:
    """Resume mid-conversation without re-classifying short slot answers."""
    if state.get("awaiting_human_review"):
        return "__end__"

    if state.get("appointment_consent") is True and not state.get("appointment_booked"):
        return "book_appointment"
    if state.get("appointment_consent") is False and state.get("appointment_offered"):
        return "decline_appointment"

    priority = state.get("priority")
    if priority == "P1":
        if state.get("reply") and state.get("escalated"):
            return "notify_human"
        return "emergency_exit"
    if priority == "OOS":
        if state.get("slots_complete"):
            return "confirm_user"
        return "oos_exit"
    if priority in ("P2", "P3") and (missing_slots(state) or not state.get("slots_complete")):
        return "slot_check"
    if priority in ("P2", "P3") and state.get("slots_complete"):
        if _can_offer_appointment(state):
            return "offer_appointment"
        if state.get("escalated") or priority == "P2":
            return "notify_human"
        return "confirm_user"
    return "classify"


def _route_after_classify(state: TriageState) -> str:
    priority = state.get("priority")
    if priority == "P1":
        return "emergency_exit"
    if priority == "OOS":
        return "oos_exit"
    if state.get("awaiting_human_review"):
        return "__end__"
    confidence = state.get("confidence") or 0.0
    if confidence < 0.75 and not state.get("human_review_resolved"):
        return "await_human_review"
    return "route"


def _route_after_slot_check(state: TriageState) -> str:
    if not state.get("slots_complete"):
        return "gather_slots"
    if _can_offer_appointment(state):
        return "offer_appointment"
    priority = state.get("priority")
    if state.get("escalated") or priority in ("P1", "P2"):
        return "notify_human"
    return "confirm_user"


def _route_after_gather_slots(state: TriageState) -> str:
    """Pause after asking a slot question; resume on the next message."""
    if state.get("slots_complete"):
        if state.get("reply_intent"):
            if _can_offer_appointment(state):
                return "offer_appointment"
            if state.get("escalated") or state.get("priority") in ("P1", "P2"):
                return "notify_human"
            return "confirm_user"
        return "slot_check"
    return "compose_reply"


def _route_after_offer(state: TriageState) -> str:
    return "compose_reply"


def _route_after_notify(state: TriageState) -> str:
    if _can_offer_appointment(state):
        return "offer_appointment"
    return "confirm_user"


def build_graph() -> StateGraph:
    builder = StateGraph(TriageState)

    builder.add_node("ingress", lambda state: {})
    builder.add_node("classify", nodes.classify_node)
    builder.add_node("emergency_exit", nodes.emergency_exit_node)
    builder.add_node("oos_exit", nodes.oos_exit_node)
    builder.add_node("slot_check", nodes.slot_check_node)
    builder.add_node("gather_slots", nodes.gather_slots_node)
    builder.add_node("route", nodes.route_node)
    builder.add_node("notify_human", nodes.notify_human_node)
    builder.add_node("confirm_user", nodes.confirm_user_node)
    builder.add_node("await_human_review", nodes.await_human_review_node)
    builder.add_node("offer_appointment", nodes.offer_appointment_node)
    builder.add_node("book_appointment", nodes.book_appointment_node)
    builder.add_node("decline_appointment", nodes.decline_appointment_node)
    builder.add_node("compose_reply", nodes.compose_reply_node)

    builder.add_edge(START, "ingress")
    builder.add_conditional_edges(
        "ingress",
        _route_from_start,
        {
            "classify": "classify",
            "slot_check": "slot_check",
            "emergency_exit": "emergency_exit",
            "oos_exit": "oos_exit",
            "notify_human": "notify_human",
            "confirm_user": "confirm_user",
            "offer_appointment": "offer_appointment",
            "book_appointment": "book_appointment",
            "decline_appointment": "decline_appointment",
            "__end__": END,
        },
    )
    builder.add_conditional_edges(
        "classify",
        _route_after_classify,
        {
            "emergency_exit": "emergency_exit",
            "oos_exit": "oos_exit",
            "route": "route",
            "await_human_review": "await_human_review",
            "__end__": END,
        },
    )
    builder.add_edge("route", "slot_check")
    builder.add_edge("emergency_exit", "notify_human")
    builder.add_edge("oos_exit", "confirm_user")
    builder.add_conditional_edges(
        "slot_check",
        _route_after_slot_check,
        {
            "gather_slots": "gather_slots",
            "notify_human": "notify_human",
            "confirm_user": "confirm_user",
            "offer_appointment": "offer_appointment",
        },
    )
    builder.add_conditional_edges(
        "gather_slots",
        _route_after_gather_slots,
        {
            "slot_check": "slot_check",
            "notify_human": "notify_human",
            "confirm_user": "confirm_user",
            "offer_appointment": "offer_appointment",
            "compose_reply": "compose_reply",
        },
    )
    builder.add_conditional_edges(
        "notify_human",
        _route_after_notify,
        {
            "offer_appointment": "offer_appointment",
            "confirm_user": "confirm_user",
        },
    )
    builder.add_conditional_edges(
        "offer_appointment",
        _route_after_offer,
        {"compose_reply": "compose_reply"},
    )
    builder.add_edge("book_appointment", "compose_reply")
    builder.add_edge("decline_appointment", "compose_reply")
    builder.add_edge("confirm_user", "compose_reply")
    builder.add_edge("await_human_review", "compose_reply")
    builder.add_edge("compose_reply", END)

    return builder


graph = build_graph().compile()


def invoke_graph(state: TriageState) -> TriageState:
    """Run the compiled graph and return typed triage state."""
    return cast(
        TriageState,
        graph.invoke(
            state,
            config={"recursion_limit": settings.langgraph_recursion_limit},
        ),
    )
