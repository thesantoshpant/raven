"""Pure agent message logic (offline, no uagents/network)."""

import json

from raven.handlers import handle_compress_request


def test_compress_request_for_budget_role():
    text = (
        "role: budget\ntask: plan a friday dinner\n"
        "memory: Maya is vegetarian and eats no meat. Keep dinners under $40 this month. "
        "Always confirm before paying for anything. The weather has been really nice lately. "
        "We chatted about a concert with $65 tickets which is steep. The library is open late. "
        "I spent $18.75 on notebooks yesterday. My phone screen is acting up again. "
        "The group chat is arguing about a TV finale. I should water the plants and back up my laptop."
    )
    reply, stats = handle_compress_request(text)
    assert stats["ok"] is True and stats["role"] == "budget"
    assert stats["relayed_tokens"] < stats["raw_tokens"]  # realistic memory -> real compression
    assert "$40" in reply and "confirm" in reply.lower()  # criticals kept
    assert "$65" not in reply and "weather" not in reply.lower()  # noise dropped


def test_compress_request_json_calendar():
    text = json.dumps({
        "role": "calendar", "task": "schedule",
        "memory": "Lab runs until 5:30 on Friday. She's free after 7pm. Note about the weather.",
    })
    reply, stats = handle_compress_request(text)
    assert stats["ok"] is True and stats["role"] == "calendar"
    assert "5:30" in reply and "free" in reply.lower()  # both availability facts kept


def test_compress_request_empty_memory_returns_help():
    reply, stats = handle_compress_request("role: budget")
    assert stats["ok"] is False
    assert "memory" in reply.lower()


def test_compress_request_tiny_input_makes_no_false_savings_claim():
    reply, stats = handle_compress_request("role: budget\nmemory: Keep dinners under $40.")
    assert stats["ok"] is True
    if stats["saved_tokens"] <= 0:
        assert "too small for net compression" in reply.lower()


def test_unknown_role_defaults_to_writer():
    reply, stats = handle_compress_request("role: wizard\nmemory: I like quiet cafes and tea.")
    assert stats["ok"] is True and stats["role"] == "writer"


def test_single_line_with_mention_and_inline_role():
    # The real ASI:One/Agentverse format: one line, leading @mention, inline role.
    reply, stats = handle_compress_request(
        "@agent1qfry9xyz role: budget Maya is vegetarian. Keep dinners under $40. Always confirm before paying."
    )
    assert stats["ok"] is True and stats["role"] == "budget"
    assert "$40" in reply and "confirm" in reply.lower()
    assert "@agent1qfry9xyz" not in reply  # mention stripped, not leaked into memory


def test_plain_text_no_markers_is_memory_for_writer():
    reply, stats = handle_compress_request("Maya is vegetarian and keep dinners under $40.")
    assert stats["ok"] is True and stats["role"] == "writer"
    assert stats["facts"] >= 1 and "$40" in reply


def test_pipe_delimited_format_no_separator_leak():
    # the exact format _HELP advertises -- pipes must not leak into task/memory.
    reply, stats = handle_compress_request(
        "role: budget | task: plan a friday dinner | memory: Maya is vegetarian. "
        "Keep dinners under $40. Always confirm before paying."
    )
    assert stats["ok"] is True and stats["role"] == "budget"
    assert "(task: plan a friday dinner)" in reply  # no trailing pipe in the task
    assert "$40" in reply and "confirm" in reply.lower()
    assert "| Maya" not in reply  # no leading pipe leaked into the first fact


def test_role_with_trailing_punctuation_still_parses():
    _, stats = handle_compress_request("role: budget. memory: Keep dinners under $40.")
    assert stats["role"] == "budget"


def test_prose_with_unknown_role_word_not_corrupted():
    # "role: organizer" isn't a known role -> must NOT be excised; defaults to writer.
    _, stats = handle_compress_request("I mentioned my role: organizer keeps everyone calm. Maya is vegetarian.")
    assert stats["role"] == "writer"


def test_role_without_colon_still_parses():
    _, stats = handle_compress_request("role budget memory: Keep dinners under $40. Always confirm before paying.")
    assert stats["role"] == "budget"


def test_prose_with_memory_word_not_corrupted():
    # "memory:" appears mid-prose -> it must NOT be treated as a marker; whole text is memory.
    reply, stats = handle_compress_request(
        "Just a note for your memory: keep dinners under $40 and always confirm before paying."
    )
    assert stats["role"] == "writer" and stats["facts"] >= 1
    assert "$40" in reply


def test_combined_sentence_does_not_yield_empty_budget_passport():
    # Regression: a single combined sentence used to classify as ONE type (dietary) and
    # leave the budget passport empty while still claiming success.
    reply, stats = handle_compress_request(
        "role: budget\nmemory: Maya is vegetarian and keep dinner under $40 and always confirm before paying."
    )
    assert stats["ok"] is True and stats["facts"] >= 1
    assert "$40" in reply and "confirm" in reply.lower()


def test_irrelevant_memory_reports_empty_honestly():
    reply, stats = handle_compress_request("role: budget\nmemory: The weather is nice and the sky is blue.")
    assert stats["ok"] is True and stats["facts"] == 0
    assert "no facts" in reply.lower() and "relevant" in reply.lower()
    assert stats["saved_tokens"] == 0  # must NOT claim savings on an empty passport
