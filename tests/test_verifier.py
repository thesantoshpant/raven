"""Verifier loop: catches a dropped action-critical fact and learns a guideline.
Offline + deterministic via a FakeLLM answerer (no network)."""

from raven.guidelines import GuidelineStore
from raven.llm import FakeLLM
from raven.schemas import Fact, Passport
from raven.verifier import verify_and_repair


def _answerer(system, user):
    # Split the prompt into context vs question so we can answer ONLY from context.
    parts = user.split("QUESTION:")
    ctx = parts[0].lower()
    q = (parts[1] if len(parts) > 1 else "").lower()
    if "confirm" in q or "paying" in q:
        return "yes" if ("confirm" in ctx and "pay" in ctx) else "UNKNOWN"
    if "dietary" in q or "maya" in q:
        return "vegetarian" if "vegetarian" in ctx else "UNKNOWN"
    if "budget" in q or "limit" in q:
        return "under $40" if ("$40" in ctx or "budget" in ctx) else "UNKNOWN"
    if "busy" in q or "friday" in q:
        return "until 5:30" if ("5:30" in ctx or "lab" in ctx or "until" in ctx) else "UNKNOWN"
    return "UNKNOWN"


def _facts():
    return [
        Fact("b1", "Keep dinners under $40.", "Keep dinners under $40.", "n1", "budget"),
        Fact("p1", "Always confirm before paying.", "Always confirm before paying.", "n2", "permission"),
    ]


def test_verifier_re_adds_dropped_permission_and_learns():
    facts = _facts()
    by_id = {f.fact_id: f for f in facts}
    passport = Passport(task="t", for_agent="budget_agent", facts=["b1"])  # permission MISSING
    g = GuidelineStore()

    passport, learned, tokens = verify_and_repair(
        FakeLLM(_answerer), "budget", passport, by_id, facts, g
    )

    assert "p1" in passport.facts, "verifier should re-add the dropped permission fact"
    assert "permission" in learned
    assert "permission" in g.keep_types("budget")
    assert tokens > 0  # verifier token cost is real and counted


def _drift_answerer(system, user):
    """Same fact present in both contexts, but answers in DIFFERENT words for the
    full context (which contains the 'weather' noise marker) vs the passport."""
    parts = user.split("QUESTION:")
    ctx = parts[0].lower()
    q = (parts[1] if len(parts) > 1 else "").lower()
    if "confirm" in q or "paying" in q:
        if "confirm" in ctx and "pay" in ctx:
            return "Yes, the user requires confirmation before any payment." if "weather" in ctx else "yes"
        return "UNKNOWN"
    return "UNKNOWN"


def test_verifier_no_false_learn_on_phrasing_drift():
    # Passport ALREADY has the permission fact; only the wording differs between
    # full and passport answers. The verifier must NOT claim a repair/learn.
    facts = _facts() + [Fact("n1", "The weather is nice today.", "x", "n3", "other")]
    by_id = {f.fact_id: f for f in facts}
    passport = Passport(task="t", for_agent="budget_agent", facts=["b1", "p1"])  # complete
    g = GuidelineStore()

    passport, learned, _ = verify_and_repair(FakeLLM(_drift_answerer), "budget", passport, by_id, facts, g)

    assert set(passport.facts) == {"b1", "p1"}  # nothing re-added
    assert learned == []  # phrasing drift alone is not a real repair
    assert g.keep_types("budget") == set()


def test_verifier_noop_when_passport_complete():
    facts = _facts()
    by_id = {f.fact_id: f for f in facts}
    passport = Passport(task="t", for_agent="budget_agent", facts=["b1", "p1"])  # complete
    g = GuidelineStore()

    passport, learned, _ = verify_and_repair(FakeLLM(_answerer), "budget", passport, by_id, facts, g)

    assert set(passport.facts) == {"b1", "p1"}
    assert learned == []
