"""RELAY: the SECOND compression edge -- agent -> agent handoffs.

When agent A hands off to agent B, the naive thing is to forward the whole running
context/transcript. RELAY instead compresses that handoff into a recipient-aware
passport for B's role (reusing the M1 passport machinery), so multi-agent comms cost
collapses while B still receives its action-critical facts.

Pure + offline: reuses `ingest.classify` + `compress.build_passport/render_passport`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .compress import build_passport, render_passport
from .ingest import classify, split_sentences
from .schemas import Fact
from .tokens import count_tokens


def facts_from_text(text: str, source_ref: str = "upstream", start_idx: int = 0) -> List[Fact]:
    """Atomize an upstream agent's output into typed facts (sentence split + classify)."""
    out: List[Fact] = []
    for i, s in enumerate(split_sentences(text), start=start_idx):
        out.append(Fact(fact_id=f"relay{i}", text=s, exact_span=s, source_ref=source_ref, type=classify(s)))
    return out


@dataclass
class RelayResult:
    passport_text: str
    raw_tokens: int       # forwarding the whole handoff
    relayed_tokens: int   # the compressed recipient-aware passport
    saved_tokens: int
    saved_pct: float
    fact_ids: List[str]


def build_relay_passport(
    upstream_text: str,
    task: str,
    to_role: str,
    prior_facts: Optional[List[Fact]] = None,
    backend: str = "fallback",
) -> RelayResult:
    """Compress an upstream agent's output (+ any prior context facts) into a passport
    for `to_role`. raw = the full handoff text; relayed = the rendered passport."""
    up_facts = facts_from_text(upstream_text)
    all_facts = list(prior_facts or []) + up_facts
    raw_handoff = "\n".join(f.text for f in all_facts)
    raw_tokens = count_tokens(raw_handoff, backend=backend)

    passport = build_passport(all_facts, task, to_role)
    by_id = {f.fact_id: f for f in all_facts}
    rendered = render_passport(passport, by_id)
    relayed_tokens = count_tokens(rendered, backend=backend)

    saved = raw_tokens - relayed_tokens
    pct = (saved / raw_tokens * 100.0) if raw_tokens else 0.0
    return RelayResult(rendered, raw_tokens, relayed_tokens, saved, pct, list(passport.facts))
