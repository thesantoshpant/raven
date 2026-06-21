"""Pure logic for the RAVEN MCP server (NO `mcp` import -> fully offline-testable).

The MCP server (raven/mcp/server.py) is a thin transport wrapper around these functions,
mirroring how web/api.py wraps web/services.py. Everything here is deterministic, keyless,
and makes no LLM/network calls.
"""

from __future__ import annotations

from ..relay import build_relay_handoff, build_relay_passport
from ..roles import ROLE_ORDER, ROLES

_DEFAULT_ROLE = "writer"


def _role_or_default(role: str) -> str:
    r = (role or "").strip().lower()
    return r if r in ROLES else _DEFAULT_ROLE


def compress_response(memory: str, task: str = "general task", role: str = "writer") -> str:
    """Compress a memory/context blob into a recipient-aware passport for `role`.
    Returns a readable string: the passport + a one-line token-savings summary."""
    role = _role_or_default(role)
    task = (task or "").strip() or "general task"
    memory = (memory or "").strip()
    if not memory:
        return ("No memory provided. Pass the notes/context to compress, e.g. "
                "compress_memory(memory='Maya is vegetarian. Keep dinner under $40.', role='budget').")
    res = build_relay_passport(memory, task, role)
    if not res.fact_ids:
        return (f"No facts in your memory were relevant to the '{role}' agent. "
                f"Try a different role ({', '.join(ROLE_ORDER)}) or include {role}-relevant details.")
    if res.saved_tokens > 0:
        savings = f"{res.relayed_tokens} tokens, saved {res.saved_pct:.0f}% vs {res.raw_tokens} raw"
    else:
        savings = f"{res.relayed_tokens} tokens (input too small for net compression; structure added)"
    return f"RAVEN context passport for '{role}' (task: {task}) -- {savings}\n\n{res.passport_text}"


def relay_response(prior_context: str, latest_message: str,
                   role: str = "writer", task: str = "general task") -> str:
    """Agent->agent handoff: forward the latest message verbatim + a compressed recipient-aware
    passport of the prior context. Returns the handoff text + a savings summary."""
    role = _role_or_default(role)
    task = (task or "").strip() or "general task"
    if not (prior_context or "").strip() and not (latest_message or "").strip():
        return "Provide prior_context and/or latest_message to build a handoff."
    res = build_relay_handoff(prior_context or "", latest_message or "", task, role)
    note = "latest message preserved verbatim" if res.message_preserved else "WARNING: message not preserved"
    if res.saved_vs_full_pct > 0:
        savings = f"{res.relayed_tokens} tokens, saved {res.saved_vs_full_pct:.0f}% vs {res.raw_tokens} full-transcript"
    else:
        savings = (f"{res.relayed_tokens} tokens (prior context too small to net-compress; the message "
                   f"+ standing rules are preserved)")
    return f"RAVEN RELAY handoff to '{role}' -- {savings} ({note})\n\n{res.handoff_text}"


def roles_list() -> list:
    """The recipient roles RAVEN can compress for."""
    return list(ROLE_ORDER)
