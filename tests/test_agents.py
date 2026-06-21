"""Role agents + aggregation, offline via FakeLLM.

Two kinds of test:
  1) plumbing: the agent calls the LLM, parses JSON, accounts tokens.
  2) experiment logic: a 'rational' FakeLLM that uses ONLY the context it is given
     -> a FULL context yields the correct venue, a STARVED context picks wrong.
"""

import json

from raven.agents import aggregate, run_budget_agent, run_calendar_agent, run_restaurant_agent
from raven.llm import FakeLLM
from raven.score import score_structured

# Candidates ordered so a clueless agent (no constraints known) picks WRONG first.
CANDIDATES = [
    {"id": "prime_steak", "name": "Prime Steak", "vegetarian": False, "price": 55, "noise": "quiet"},
    {"id": "loud_cantina", "name": "Loud Cantina", "vegetarian": True, "price": 22, "noise": "loud"},
    {"id": "green_bowl", "name": "Green Bowl", "vegetarian": True, "price": 28, "noise": "quiet"},
]
VENUES_BY_ID = {c["id"]: c for c in CANDIDATES}

SPECS = [
    {"id": "vegetarian", "field": "dietary_ok", "structured": {"type": "is_true"}},
    {"id": "budget", "field": "price", "structured": {"type": "max_dollar", "value": 40}},
    {"id": "quiet", "field": "quiet", "structured": {"type": "is_true"}},
]


def _rational_restaurant(system, user):
    ctx = user.split("CANDIDATE VENUES:")[0].lower()  # only the context, not the candidate attrs
    need_veg = "vegetarian" in ctx or "no meat" in ctx or "vegan" in ctx
    need_budget = "$40" in user.split("CANDIDATE VENUES:")[0] or "budget" in ctx or "under $40" in ctx
    need_quiet = "loud" in ctx or "quiet" in ctx or "noisy" in ctx
    for c in CANDIDATES:
        if need_veg and not c["vegetarian"]:
            continue
        if need_budget and c["price"] > 40:
            continue
        if need_quiet and c["noise"] != "quiet":
            continue
        return json.dumps({"venue_id": c["id"]})
    return json.dumps({"venue_id": CANDIDATES[0]["id"]})


def test_restaurant_agent_parses_and_accounts_tokens():
    llm = FakeLLM(lambda s, u: '{"venue_id": "green_bowl"}')
    out = run_restaurant_agent(llm, "ctx", "plan dinner", CANDIDATES)
    assert out["venue_id"] == "green_bowl"
    assert out["tokens"] > 0


def test_aggregate_uses_ground_truth_venue_attrs():
    plan = aggregate(
        {"venue_id": "green_bowl"}, {"time": "19:00"}, {"requires_confirmation": True}, VENUES_BY_ID
    )
    assert plan["price"] == 28 and plan["dietary_ok"] is True and plan["quiet"] is True
    assert plan["time"] == "19:00" and plan["requires_confirmation"] is True


def test_full_context_beats_starved_context():
    llm = FakeLLM(_rational_restaurant)
    full_ctx = "Maya is vegetarian. Keep it under $40. She dislikes loud places."
    starved_ctx = "Dinner with Maya on Friday."

    full = aggregate(run_restaurant_agent(llm, full_ctx, "plan", CANDIDATES), {"time": "19:00"}, {"requires_confirmation": True}, VENUES_BY_ID)
    starved = aggregate(run_restaurant_agent(llm, starved_ctx, "plan", CANDIDATES), {"time": "19:00"}, {"requires_confirmation": True}, VENUES_BY_ID)

    _, full_n = score_structured(full, SPECS)
    _, starved_n = score_structured(starved, SPECS)
    assert full["venue_id"] == "green_bowl"          # correct pick
    assert full_n == 3                               # veg + budget + quiet
    assert starved_n < full_n                        # missing facts -> wrong venue -> fewer constraints
