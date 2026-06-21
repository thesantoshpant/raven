"""Pure message logic for the RAVEN uAgent (no uagents / no network imports here).

The Chat-Protocol agent (raven/fetch/raven_agent.py) is a thin wrapper: it parses a
ChatMessage's text, calls `handle_compress_request`, and sends the reply back. Keeping
the brains here means the behaviour is fully unit-testable offline.
"""

from __future__ import annotations

import json
from typing import Dict, Tuple

from .relay import build_relay_passport
from .roles import ROLES

_HELP = (
    "Send your memory/context to compress. Example:\n"
    "  role: budget\n  task: plan a friday dinner\n"
    "  memory: Maya is vegetarian. Keep dinners under $40. Always confirm before paying."
)


def _parse(text: str) -> Tuple[str, str, str]:
    """Return (role, task, memory). Accepts JSON {role,task,memory} or line markers
    'role:'/'task:'/'memory:'; everything else is treated as memory."""
    text = (text or "").strip()
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return (str(d.get("role") or "writer"), str(d.get("task") or "general task"),
                    str(d.get("memory") or ""))
    except (json.JSONDecodeError, ValueError):
        pass

    role, task = "writer", "general task"
    mem = []
    for ln in text.splitlines():
        s = ln.strip()
        low = s.lower()
        if low.startswith("role:") or low.startswith("role="):
            role = s.split("=", 1)[-1].split(":", 1)[-1].strip() or role
        elif low.startswith("task:") or low.startswith("task="):
            task = s.split("=", 1)[-1].split(":", 1)[-1].strip() or task
        elif low.startswith("memory:") or low.startswith("memory="):
            rest = s.split("=", 1)[-1].split(":", 1)[-1].strip()
            if rest:
                mem.append(rest)
        elif s:
            mem.append(s)
    return role, task, "\n".join(mem)


def handle_compress_request(text: str, backend: str = "fallback") -> Tuple[str, Dict]:
    """Core of the RAVEN agent: compress a memory blob into a recipient-aware passport
    for the requested role. Returns (reply_text, stats)."""
    role, task, memory = _parse(text)
    if role not in ROLES:
        role = "writer"
    if not memory.strip():
        return _HELP, {"ok": False, "reason": "no memory supplied"}

    res = build_relay_passport(memory, task, role, backend=backend)
    if res.saved_tokens > 0:
        tokens_line = f"{res.relayed_tokens} tokens, saved {res.saved_pct:.0f}% vs raw {res.raw_tokens}"
    else:
        tokens_line = (
            f"{res.relayed_tokens} tokens (raw was {res.raw_tokens}; input too small "
            f"for net compression -- the passport adds structure)"
        )
    reply = (
        f"RAVEN context passport for '{role}' (task: {task})\n"
        f"Tokens: {tokens_line}\n\n"
        f"{res.passport_text}"
    )
    stats = {
        "ok": True,
        "role": role,
        "raw_tokens": res.raw_tokens,
        "relayed_tokens": res.relayed_tokens,
        "saved_tokens": res.saved_tokens,
        "saved_pct": round(res.saved_pct, 1),
    }
    return reply, stats
