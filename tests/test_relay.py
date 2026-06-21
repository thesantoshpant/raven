"""RELAY (agent->agent handoff compression): compresses the handoff and preserves the
recipient's action-critical facts while dropping noise."""

from raven.relay import build_relay_passport, facts_from_text

UPSTREAM = (
    "Maya is vegetarian. Keep dinners under $40. Always confirm before paying. "
    "The weather is nice today. We chatted about a concert with $65 tickets. "
    "The library is open late this week."
)


def test_relay_compresses_and_keeps_budget_criticals():
    res = build_relay_passport(UPSTREAM, task="plan a friday dinner", to_role="budget")
    assert res.relayed_tokens < res.raw_tokens   # the handoff got smaller
    assert res.saved_tokens > 0 and res.saved_pct > 0
    assert "$40" in res.passport_text             # budget_limit kept
    assert "confirm" in res.passport_text.lower() # permission kept
    assert "$65" not in res.passport_text         # expense / noise dropped
    assert "weather" not in res.passport_text.lower()


def test_relay_is_recipient_aware():
    # The SAME upstream produces different passports for different roles.
    budget = build_relay_passport(UPSTREAM, "plan dinner", "budget").passport_text.lower()
    restaurant = build_relay_passport(UPSTREAM, "plan dinner", "restaurant").passport_text.lower()
    assert "vegetarian" in restaurant          # dietary goes to the restaurant agent
    assert "vegetarian" not in budget          # but NOT to the budget agent


def test_relay_reports_nonpositive_savings_on_tiny_input():
    # A 1-line handoff is smaller than the passport's fixed structure -> no net win.
    # The math must stay honest (saved can be <= 0); callers must not claim compression.
    res = build_relay_passport("Keep dinners under $40.", "plan dinner", "budget")
    assert res.relayed_tokens >= res.raw_tokens
    assert res.saved_tokens == res.raw_tokens - res.relayed_tokens
    assert res.saved_tokens <= 0


def test_facts_from_text_skips_fragments():
    facts = facts_from_text("Maya is vegetarian. ok")
    texts = [f.text for f in facts]
    assert "Maya is vegetarian." in texts
    assert "ok" not in texts  # < 3 chars dropped
