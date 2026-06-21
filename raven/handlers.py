"""Pure message logic for the RAVEN uAgent (no uagents / no network imports here).

The Chat-Protocol agent (raven/fetch/raven_agent.py) is a thin wrapper: it parses a
ChatMessage's text, calls `handle_compress_request`, and sends the reply back. Keeping
the brains here means the behaviour is fully unit-testable offline.
"""

from __future__ import annotations

import json
import re
from typing import Dict, Tuple

from .relay import build_relay_passport
from .roles import ROLES

_HELP = (
    "Send your memory/context to compress. Example:\n"
    "  role: budget | task: plan a friday dinner | memory: Maya is vegetarian. "
    "Keep dinners under $40. Always confirm before paying.\n"
    "(role/task/memory markers are optional and can appear anywhere; plain text is "
    "treated as memory for the 'writer' role.)"
)

_MAX_MEMORY_CHARS = 12_000  # cap pasted input so a huge blob can't block the agent loop
_SEP = " |,\t\r\n"          # marker separators to strip from captured values
_MENTION = re.compile(r"^\s*@\S+\s*")
_ROLE = re.compile(r"\brole\b\s*[:=]?\s*([A-Za-z]+)", re.I)       # ':' optional; letters only; validated before use
_TASK = re.compile(r"\btask\s*[:=]\s*(.+?)(?=\s*[|,]?\s*\bmemory\s*[:=]|$)", re.I | re.S)
_MEMORY = re.compile(r"\bmemory\s*[:=]\s*(.+)$", re.I | re.S)
_DANGLING = re.compile(r"(?i)\b(?:role|task|memory)\s*[:=]\s*$")   # a marker with no value left


def _parse(text: str) -> Tuple[str, str, str]:
    """Return (role, task, memory). Robust to how real chats arrive:
    - JSON {role,task,memory};
    - a leading @agent mention (ASI:One/Agentverse prepend it) is stripped;
    - role/task/memory markers anywhere, ':'/'=', single- or multi-line, '|'/',' separated;
    - plain text -> the whole thing is memory (role defaults to writer).
    An invalid `role:` value is left in the memory rather than excised (so prose that merely
    says 'my role: organizer ...' isn't corrupted)."""
    text = (text or "").strip()
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return (str(d.get("role") or "writer"), str(d.get("task") or "general task"),
                    str(d.get("memory") or ""))
    except (json.JSONDecodeError, ValueError):
        pass

    text = _MENTION.sub("", text)  # drop a leading "@agent1q..." mention
    role, task = "writer", "general task"

    rm = _ROLE.search(text)
    if rm and rm.group(1).lower() in ROLES:  # only consume a VALID role marker
        role = rm.group(1).lower()
        text = text[:rm.start()] + " " + text[rm.end():]

    tm = _TASK.search(text)
    if tm:
        cand = tm.group(1).strip(_SEP)
        if cand:
            task = cand
        text = text[:tm.start()] + " " + text[tm.end():]

    mm = _MEMORY.search(text)
    if mm:
        leftover = text[:mm.start()].strip(_SEP)
        memval = mm.group(1).strip(_SEP)
        memory = (leftover + " " + memval).strip() if leftover else memval
    else:
        memory = _DANGLING.sub("", text).strip(_SEP)  # drop a value-less trailing 'memory:'
    return role, task, " ".join(memory.split())


def handle_compress_request(text: str, backend: str = "fallback") -> Tuple[str, Dict]:
    """Core of the RAVEN agent: compress a memory blob into a recipient-aware passport
    for the requested role. Returns (reply_text, stats)."""
    role, task, memory = _parse(text)
    if role not in ROLES:
        role = "writer"
    memory = memory[:_MAX_MEMORY_CHARS]  # bound work so a huge paste can't stall the agent
    if not memory.strip():
        return _HELP, {"ok": False, "reason": "no memory supplied"}

    res = build_relay_passport(memory, task, role, backend=backend)
    if not res.fact_ids:
        return (
            f"No facts in your memory were relevant to the '{role}' agent. "
            f"Try a different role, or include {role}-relevant details.",
            {"ok": True, "role": role, "facts": 0, "raw_tokens": res.raw_tokens,
             "relayed_tokens": 0, "saved_tokens": 0, "saved_pct": 0.0},
        )
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
        "facts": len(res.fact_ids),
        "raw_tokens": res.raw_tokens,
        "relayed_tokens": res.relayed_tokens,
        "saved_tokens": res.saved_tokens,
        "saved_pct": round(res.saved_pct, 1),
    }
    return reply, stats
