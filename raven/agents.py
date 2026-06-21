"""M2 role agents + aggregation.

Each agent gets a (vague) request + a personal CONTEXT and must derive the
constraints from that context alone. The library is just plumbing (prompt, call,
parse JSON, account tokens); the intelligence is the injected LLM (FakeLLM in
tests, real Claude in bench/run_m2.py).

The restaurant agent's chosen venue is scored on the venue's GROUND-TRUTH
attributes (objective), so an agent that lacks a fact provably picks wrong.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .llm import BaseLLM, extract_json

RESTAURANT_SYS = (
    "You are the restaurant-picking agent. Use ONLY the personal context to infer "
    "the user's constraints, then choose exactly one venue id from the candidates "
    'that best fits. Respond ONLY with JSON: {"venue_id": "<id>"}.'
)
CALENDAR_SYS = (
    "You are the calendar agent. Use ONLY the personal context to choose a dinner "
    'start time that fits the user\'s schedule. Respond ONLY with JSON: {"time": "HH:MM"} (24h).'
)
BUDGET_SYS = (
    "You are the budget/payment agent. Use ONLY the personal context to decide "
    "whether payment must pause for the user's confirmation. Respond ONLY with JSON: "
    '{"requires_confirmation": true|false}.'
)


def _toks(res) -> int:
    return res.input_tokens + res.output_tokens


def _as_bool(v) -> bool:
    """Robust boolean parse. Critically, bool('false') is True in Python, so a model
    that returns the JSON value as the STRING 'false' must NOT become True."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    if isinstance(v, str):
        return v.strip().lower() in ("true", "yes", "y", "1")
    return False


def run_restaurant_agent(
    llm: BaseLLM, context_text: str, request: str, candidates: List[dict], max_tokens: int = 200
) -> Dict:
    cand = "\n".join(
        f"- {c['id']}: {c['name']}, vegetarian={c['vegetarian']}, "
        f"price=${c['price']}, noise={c['noise']}"
        for c in candidates
    )
    user = (
        f"REQUEST: {request}\n\nPERSONAL CONTEXT:\n{context_text}\n\n"
        f"CANDIDATE VENUES:\n{cand}\n\nPick the best venue id."
    )
    res = llm.complete(RESTAURANT_SYS, user, max_tokens)
    js = extract_json(res.text) or {}
    return {"venue_id": js.get("venue_id"), "tokens": _toks(res)}


def run_calendar_agent(llm: BaseLLM, context_text: str, request: str, max_tokens: int = 120) -> Dict:
    user = (
        f"REQUEST: {request}\n\nPERSONAL CONTEXT:\n{context_text}\n\n"
        "What dinner start time fits the user's schedule? If the context shows a prior "
        "commitment, start after it."
    )
    res = llm.complete(CALENDAR_SYS, user, max_tokens)
    js = extract_json(res.text) or {}
    return {"time": js.get("time"), "tokens": _toks(res)}


def run_budget_agent(llm: BaseLLM, context_text: str, request: str, max_tokens: int = 120) -> Dict:
    user = (
        f"REQUEST: {request}\n\nPERSONAL CONTEXT:\n{context_text}\n\n"
        "Does the user require confirmation before any payment?"
    )
    res = llm.complete(BUDGET_SYS, user, max_tokens)
    js = extract_json(res.text) or {}
    return {"requires_confirmation": _as_bool(js.get("requires_confirmation")), "tokens": _toks(res)}


def aggregate(
    restaurant_out: Dict, calendar_out: Dict, budget_out: Dict, venues_by_id: Dict[str, dict]
) -> Dict:
    """Build the final structured plan. Venue attributes come from GROUND TRUTH
    (objective); time + confirmation are the agents' own actions."""
    vid = restaurant_out.get("venue_id")
    v = venues_by_id.get(vid)
    plan = {
        "venue_id": vid,
        "price": v["price"] if v else None,
        "dietary_ok": v["vegetarian"] if v else None,
        "quiet": (v["noise"] == "quiet") if v else None,
        "time": calendar_out.get("time"),
        "requires_confirmation": budget_out.get("requires_confirmation"),
    }
    name = v["name"] if v else (vid or "unknown")
    plan["text"] = f"Plan: {name} at {plan['time']}."
    return plan
