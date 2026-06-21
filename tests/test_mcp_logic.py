"""RAVEN MCP tool logic -- offline, deterministic. Imports raven.mcp._logic ONLY (never the
server module, never the `mcp` SDK), so the no-heavy-deps test invariant holds."""

from raven.mcp._logic import compress_response, relay_response, roles_list


def test_compress_response_budget_keeps_cap_drops_noise():
    out = compress_response(
        "Maya is vegetarian. Keep dinners under $40. Always confirm before paying. "
        "Concert tickets are $65.",
        task="plan dinner", role="budget",
    )
    assert "$40" in out and "confirm" in out.lower()
    assert "$65" not in out  # irrelevant receipt not in the budget passport


def test_compress_response_unknown_role_defaults_to_writer():
    out = compress_response("Keep dinners under $40.", role="wizard")
    assert "'writer'" in out


def test_compress_response_empty_memory_message():
    assert "no memory" in compress_response("", role="budget").lower()


def test_relay_response_preserves_latest_message():
    out = relay_response("Maya is vegetarian. Keep under $40.", "Booked Green Bowl at 7pm.", role="writer")
    assert "Green Bowl at 7pm" in out          # latest message forwarded verbatim
    assert "relay" in out.lower()              # (savings may be negative on a tiny transcript)


def test_roles_list_shape():
    roles = roles_list()
    assert {"restaurant", "calendar", "budget", "writer"} <= set(roles)
