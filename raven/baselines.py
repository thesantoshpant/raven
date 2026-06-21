"""Baselines for a DEFENSIBLE benchmark table.

Four conditions:
  raw_once                  full memory serialized once (honesty baseline)
  raw_broadcast             full memory sent to every agent (multi-agent reality)
  generic_truncation        naive role-UNaware truncation (the weak "normal team" baseline)
  generic_factstore_unaware SAME fact store as RAVEN, role-UNaware, at RAVEN's EXACT
                            total rendered-token budget (the FAIR baseline)
"""

from __future__ import annotations

from typing import List, Tuple

from .retrieve import rank_facts
from .schemas import Fact
from .tokens import count_tokens


def serialize_corpus(items: List[dict]) -> str:
    parts = []
    for it in items:
        head = f"[{it.get('kind', '')}|{it.get('id', '')}|{it.get('timestamp', '')}]"
        parts.append(f"{head} {it.get('text', '')}")
    return "\n".join(parts)


def raw_once(items: List[dict], backend: str = "fallback") -> Tuple[str, int]:
    s = serialize_corpus(items)
    return s, count_tokens(s, backend=backend)


def raw_broadcast_tokens(items: List[dict], n_agents: int, backend: str = "fallback") -> int:
    _, t = raw_once(items, backend=backend)
    return t * n_agents


def generic_truncation(items: List[dict], budget_tokens: int, backend: str = "fallback") -> Tuple[str, int]:
    """Role-unaware: serialize the corpus and hard-truncate to ~budget tokens."""
    s = serialize_corpus(items)
    full = count_tokens(s, backend=backend)
    if full <= budget_tokens:
        return s, full
    # binary search on character length to land just under the token budget
    lo, hi = 0, len(s)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if count_tokens(s[:mid], backend=backend) <= budget_tokens:
            lo = mid
        else:
            hi = mid - 1
    out = s[:lo]
    return out, count_tokens(out, backend=backend)


def generic_factstore_unaware(
    facts: List[Fact], task: str, budget_tokens: int, backend: str = "fallback"
) -> Tuple[str, int]:
    """FAIR baseline: same atomized fact store as RAVEN, ranked by the task ONLY
    (no role awareness), greedily filled up to the SAME total rendered-token
    budget that RAVEN used. Proves RAVEN's win comes from recipient-awareness,
    not from having a better data structure."""
    ranked = rank_facts(facts, task, allowed_types=None)
    header = "# GENERIC (role-unaware) CONTEXT"
    chosen_lines: List[str] = []
    cur = count_tokens(header, backend=backend)
    for _, f in ranked:
        line = f"- {f.text}"
        t = count_tokens(line, backend=backend)
        if cur + t > budget_tokens:
            continue
        chosen_lines.append(line)
        cur += t
    text = header + ("\n" + "\n".join(chosen_lines) if chosen_lines else "")
    return text, count_tokens(text, backend=backend)
