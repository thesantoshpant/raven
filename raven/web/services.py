"""Offline-testable business logic for the M4 web demo. No fastapi import here.

Reuses the M1-M3 engine. `run_benchmark` accepts an injected LLM so tests use FakeLLM
and only the live API path (api.py) constructs a real AnthropicLLM. Every function
returns plain JSON-able dicts.
"""

from __future__ import annotations

import json
import os
from typing import List, Optional

from ..agents import aggregate, run_budget_agent, run_calendar_agent, run_restaurant_agent
from ..baselines import generic_factstore_unaware, serialize_corpus
from ..compress import build_passport, render_passport
from ..handlers import handle_compress_request
from ..ingest import ingest_corpus, load_corpus
from ..llm import BaseLLM
from ..roles import ROLE_ORDER
from ..score import score_structured
from ..tokens import count_tokens
from .pricing import est_cost_usd

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "data")

# Substrings the UI highlights in the messy memory (the 5 buried gold constraints).
GOLD_HIGHLIGHTS = ["vegetarian", "no meat", "under $40", "$40", "5:30", "lab", "confirm", "auto-charge", "loud"]

# Scripted agent outputs for the RELAY demo (deterministic, no LLM) -- match bench/run_relay.py.
_RESTAURANT_OUT = (
    "After reviewing the candidate venues and the user's notes, I recommend Green Bowl, "
    "a vegetarian-friendly and quiet spot at roughly $28 per person. I ruled out the "
    "steakhouse because Maya is vegetarian, and I avoided the loud cantina. We still need "
    "to confirm the timing against the user's calendar and clear the spend with the budget agent."
)
_BUDGET_OUT = (
    "I checked the recommendation against the user's finances. Green Bowl at about $28 is "
    "comfortably under the $40 dinner cap for this month. Per the user's standing rule I am "
    "NOT auto-paying; I have flagged the payment to await the user's confirmation before booking."
)


def _load():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    with open(os.path.join(DATA, "task_friday_dinner.json"), encoding="utf-8") as fh:
        task = json.load(fh)
    with open(os.path.join(DATA, "venues_friday_dinner.json"), encoding="utf-8") as fh:
        venues = json.load(fh)
    return corpus, task, venues


def _task_text(task: dict) -> str:
    return task.get("request_m2", task["request"])


def get_scenario() -> dict:
    corpus, task, venues = _load()
    facts = ingest_corpus(corpus)
    return {
        "task": _task_text(task),
        "memory_items": [
            {"id": it.get("id"), "kind": it.get("kind"), "text": it.get("text", "")} for it in corpus
        ],
        "highlights": GOLD_HIGHLIGHTS,
        "roles": ROLE_ORDER,
        "candidates": venues["candidates"],
        "gold_constraints": [g["id"] for g in task["gold_constraints"]],
        "counts": {"items": len(corpus), "facts": len(facts)},
    }


def role_passports(task: Optional[str] = None) -> dict:
    """Per-role passports from the corpus (the memory -> agent edge), with the
    least-privilege view (what each agent does NOT see). No LLM."""
    corpus, taskj, _ = _load()
    task = task or _task_text(taskj)
    facts = ingest_corpus(corpus)
    by_id = {f.fact_id: f for f in facts}
    full_tokens = count_tokens(serialize_corpus(corpus), backend="fallback")

    out: List[dict] = []
    for role in ROLE_ORDER:
        p = build_passport(facts, task, role)
        rendered = render_passport(p, by_id)
        tok = count_tokens(rendered, backend="fallback")
        kept = [{"text": by_id[fid].text, "type": by_id[fid].type} for fid in p.facts]
        out.append({
            "role": role,
            "passport_text": rendered,
            "facts": kept,
            "tokens": tok,
            "raw_tokens": full_tokens,
            "saved_pct": round((1 - tok / full_tokens) * 100, 1) if full_tokens else 0.0,
            "excluded_count": len(facts) - len(p.facts),
            # a passport is context the agent only READS -> price as 100% input tokens
            "est_usd_per_send": est_cost_usd(tok, in_frac=1.0),
        })
    return {"full_tokens": full_tokens, "n_facts": len(facts), "roles": out}


def compress(role: str, task: str, memory: str) -> dict:
    """Free-form: compress a pasted memory blob for a role (the chat-agent path)."""
    reply, stats = handle_compress_request(f"role: {role}\ntask: {task}\nmemory: {memory}")
    return {"reply": reply, "stats": stats}


def relay_demo() -> dict:
    """Agent->agent handoff comparison (full_transcript / last_message / RELAY) + a
    back-context preservation check. Deterministic, no LLM."""
    from ..relay import build_relay_handoff

    corpus, taskj, _ = _load()
    task = _task_text(taskj)
    memory = serialize_corpus(corpus)
    hops = [
        ("restaurant", memory, ""),
        ("budget", memory, _RESTAURANT_OUT),
        ("writer", memory + "\n" + _RESTAURANT_OUT, _BUDGET_OUT),
    ]
    probe = "vegetarian"
    rows: List[dict] = []
    tot_full = tot_last = tot_relay = relay_keeps = last_keeps = 0
    for to_role, prior, msg in hops:
        h = build_relay_handoff(prior, msg, task, to_role, backend="fallback")
        tot_full += h.raw_tokens
        tot_last += h.last_message_tokens
        tot_relay += h.relayed_tokens
        relay_keeps += int(probe in h.handoff_text.lower())
        last_keeps += int(probe in msg.lower())
        rows.append({
            "to_role": to_role, "full": h.raw_tokens, "last_message": h.last_message_tokens,
            "relay": h.relayed_tokens, "saved_vs_full_pct": round(h.saved_vs_full_pct, 1),
        })
    return {
        "hops": rows,
        "totals": {
            "full": tot_full, "last_message": tot_last, "relay": tot_relay,
            "saved_vs_full_pct": round((1 - tot_relay / tot_full) * 100, 1) if tot_full else 0.0,
        },
        "preservation": {"probe": probe, "relay_keeps": relay_keeps,
                         "last_keeps": last_keeps, "hops": len(hops)},
    }


def run_benchmark(llm: BaseLLM) -> dict:
    """The M2 decision-preservation benchmark, parameterized by an injected LLM.
    raw (full memory) / generic (role-unaware, equal budget) / raven (recipient-aware)."""
    corpus, taskj, venues = _load()
    request = _task_text(taskj)
    specs = taskj["gold_constraints"]
    candidates = venues["candidates"]
    venues_by_id = {c["id"]: c for c in candidates}
    facts = ingest_corpus(corpus)
    by_id = {f.fact_id: f for f in facts}

    agent_roles = ["restaurant", "calendar", "budget"]
    # NOTE: these are PRE-verifier passports. They equal bench/run_m2.py's budget as long as
    # the verifier is a no-op (true in this scenario -- the static guard already keeps the
    # criticals). If a future scenario needs the verifier to repair a passport, run that path
    # here too so the per-agent budget stays in lockstep with the bench.
    raven_ctx = {r: render_passport(build_passport(facts, request, r), by_id) for r in agent_roles}
    per_agent_budget = max(1, round(sum(count_tokens(raven_ctx[r], "fallback") for r in agent_roles) / len(agent_roles)))

    full_ctx = serialize_corpus(corpus)
    generic_ctx, _ = generic_factstore_unaware(facts, request, per_agent_budget, backend="fallback")

    def ctx(cond: str, role: str) -> str:
        return full_ctx if cond == "raw" else generic_ctx if cond == "generic" else raven_ctx[role]

    conditions = {}
    for cond in ["raw", "generic", "raven"]:
        r_out = run_restaurant_agent(llm, ctx(cond, "restaurant"), request, candidates)
        c_out = run_calendar_agent(llm, ctx(cond, "calendar"), request)
        b_out = run_budget_agent(llm, ctx(cond, "budget"), request)
        plan = aggregate(r_out, c_out, b_out, venues_by_id)
        per_constraint, n = score_structured(plan, specs)
        agent_tok = r_out["tokens"] + c_out["tokens"] + b_out["tokens"]
        conditions[cond] = {
            "constraints": n, "total": len(specs), "agent_tokens": agent_tok,
            "plan": {k: plan.get(k) for k in ("venue_id", "price", "dietary_ok", "quiet", "time", "requires_confirmation")},
            "per_constraint": per_constraint,
            "missed": [k for k, v in per_constraint.items() if not v],
            "est_usd": est_cost_usd(agent_tok),
        }
    return {"per_agent_budget": per_agent_budget, "conditions": conditions}
