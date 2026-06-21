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


def test_relay_fact_ids_are_globally_unique_across_calls():
    # Regression: IDs used to restart at relay0 every call, so a by-id dict overwrote
    # an earlier hop's fact with a later one of the same id.
    a = facts_from_text("Maya is vegetarian.")
    b = facts_from_text("Keep dinners under $40.")
    ids = [f.fact_id for f in a + b]
    assert len(ids) == len(set(ids))
    assert a[0].fact_id != b[0].fact_id


def test_raw_tokens_not_inflated_by_multilabel_expansion():
    # A combined sentence expands to several facts internally, but the RAW baseline must
    # reflect the ORIGINAL input (counted once), not the duplicated expansion.
    from raven.tokens import count_tokens

    text = "Maya is vegetarian and keep dinner under $40 and always confirm before paying."
    res = build_relay_passport(text, "plan dinner", "budget")
    assert res.raw_tokens == count_tokens(text, backend="fallback")


def test_handoff_raw_tokens_match_original_input():
    from raven.relay import build_relay_handoff
    from raven.tokens import count_tokens

    prior = "Maya is vegetarian and keep dinner under $40 and confirm before paying."
    msg = "I recommend Green Bowl."
    h = build_relay_handoff(prior, msg, "plan", "budget")
    assert h.raw_tokens == count_tokens((prior + "\n" + msg).strip(), backend="fallback")


def test_facts_from_text_ids_unique_across_three_hops():
    a = facts_from_text("Maya is vegetarian.")
    b = facts_from_text("Keep dinners under $40.")
    c = facts_from_text("Always confirm before paying.")
    ids = [f.fact_id for f in a + b + c]
    assert len(ids) == len(set(ids))  # no by-id overwrite across a multi-hop chain


def test_facts_from_text_multilabel_combined_sentence():
    facts = facts_from_text("Maya is vegetarian and keep dinner under $40 and confirm before paying.")
    types = {f.type for f in facts}
    assert {"dietary", "budget_limit", "permission"} <= types


def test_relay_handoff_preserves_message_floor_and_compresses_prior():
    from raven.relay import build_relay_handoff

    prior = (
        "Maya is vegetarian. Keep dinners under $40. Always confirm before paying. "
        "The weather is nice. Concert tickets are $65. The library is open late."
    )
    msg = "I recommend Green Bowl, a vegetarian-friendly quiet spot at about $28 per person."
    h = build_relay_handoff(prior, msg, "plan dinner", "budget")
    assert h.message_preserved is True
    assert "Green Bowl" in h.handoff_text                       # latest message kept verbatim
    assert "$40" in h.handoff_text and "confirm" in h.handoff_text.lower()  # back-context criticals
    assert "$65" not in h.handoff_text                          # noise dropped from compressed prior
    # (net compression magnitude is scale-dependent; the corpus-scale win is in bench/run_relay.py)
    assert h.last_message_tokens < h.raw_tokens                 # the floor is far smaller than full forward


def test_relay_handoff_floor_survives_when_role_filter_would_drop_it():
    # A bare recommendation has no budget-typed facts; the message floor must still carry it.
    from raven.relay import build_relay_handoff

    h = build_relay_handoff("", "Restaurant agent recommends Green Bowl.", "plan", "budget")
    assert "Green Bowl" in h.handoff_text and h.message_preserved is True


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
