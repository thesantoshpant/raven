"""RELAY: the SECOND compression edge -- agent -> agent handoffs.

Two operations:
  * build_relay_passport(context, task, role)  -- compress a context blob into a
    recipient-aware passport for `role` (used by the user-facing agent / handlers).
  * build_relay_handoff(prior_context, latest_message, task, role) -- the real handoff:
    ALWAYS forward the latest upstream message verbatim (the "message floor") PLUS a
    recipient-aware compressed passport of the back-context. Used by the Bureau demo
    and the RELAY bench.

Pure + offline: reuses `ingest.classify_all/split_sentences` + the M1 passport machinery.
Fact IDs are globally unique per process so a multi-hop handoff never overwrites an
earlier fact in a by-id lookup.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import List, Optional

from .compress import build_passport, render_passport
from .ingest import classify_all, split_sentences
from .schemas import Fact
from .tokens import count_tokens

_FACT_COUNTER = itertools.count()  # process-global -> IDs never collide across hops/calls


def facts_from_text(text: str, source_ref: str = "upstream") -> List[Fact]:
    """Atomize text into typed facts. Multi-label: a sentence stating N constraints
    yields N facts (same span, one per matched type). IDs are globally unique."""
    out: List[Fact] = []
    for s in split_sentences(text):
        for ftype in classify_all(s):
            out.append(Fact(fact_id=f"relay{next(_FACT_COUNTER)}", text=s, exact_span=s,
                            source_ref=source_ref, type=ftype))
    return out


def _raw_input_text(context_text: str, prior_facts: Optional[List[Fact]]) -> str:
    """The ORIGINAL input a naive forward would send. Each unique sentence is counted
    ONCE -- multi-label atomization (one sentence -> several typed facts) must never
    inflate the raw baseline."""
    parts: List[str] = []
    seen = set()
    for f in (prior_facts or []):
        if f.text not in seen:
            seen.add(f.text)
            parts.append(f.text)
    if context_text and context_text.strip():
        parts.append(context_text.strip())
    return "\n".join(parts)


@dataclass
class RelayResult:
    passport_text: str
    raw_tokens: int       # forwarding the whole context blob (original input, deduped)
    relayed_tokens: int   # the compressed recipient-aware passport
    saved_tokens: int
    saved_pct: float
    fact_ids: List[str]


def build_relay_passport(
    context_text: str,
    task: str,
    to_role: str,
    prior_facts: Optional[List[Fact]] = None,
    backend: str = "fallback",
) -> RelayResult:
    """Compress a context blob into a recipient-aware passport for `to_role`."""
    facts = list(prior_facts or []) + facts_from_text(context_text)
    raw_tokens = count_tokens(_raw_input_text(context_text, prior_facts), backend=backend)

    passport = build_passport(facts, task, to_role)
    by_id = {f.fact_id: f for f in facts}
    rendered = render_passport(passport, by_id)
    relayed_tokens = count_tokens(rendered, backend=backend)

    saved = raw_tokens - relayed_tokens
    pct = (saved / raw_tokens * 100.0) if raw_tokens else 0.0
    return RelayResult(rendered, raw_tokens, relayed_tokens, saved, pct, list(passport.facts))


@dataclass
class HandoffResult:
    handoff_text: str          # message floor + compressed back-context passport
    raw_tokens: int            # forward the full handoff (prior + message)
    last_message_tokens: int   # forward only the upstream message
    relayed_tokens: int        # RELAY: compressed prior + verbatim message
    saved_vs_full_pct: float
    message_preserved: bool


def build_relay_handoff(
    prior_context: str,
    latest_message: str,
    task: str,
    to_role: str,
    backend: str = "fallback",
) -> HandoffResult:
    """The real agent->agent handoff: forward the latest message VERBATIM (floor) +
    a recipient-aware compressed passport of the prior back-context. Guarantees the
    latest upstream output is never dropped by role filtering."""
    msg = (latest_message or "").strip()
    prior_facts = facts_from_text(prior_context, source_ref="prior")

    # raw = the ORIGINAL prior text + the message, NOT the multi-label-expanded facts.
    raw_text = (prior_context or "").strip()
    if msg:
        raw_text = (raw_text + "\n" + msg).strip()
    raw_tokens = count_tokens(raw_text, backend=backend)
    last_message_tokens = count_tokens(msg, backend=backend)

    prior_passport = build_passport(prior_facts, task, to_role)
    by_id = {f.fact_id: f for f in prior_facts}
    prior_text = render_passport(prior_passport, by_id)
    handoff_text = prior_text + (f"\n\nLATEST FROM UPSTREAM:\n{msg}" if msg else "")
    relayed_tokens = count_tokens(handoff_text, backend=backend)

    saved = (1 - relayed_tokens / raw_tokens) * 100.0 if raw_tokens else 0.0
    message_preserved = (not msg) or (msg in handoff_text)
    return HandoffResult(handoff_text, raw_tokens, last_message_tokens, relayed_tokens, saved, message_preserved)
