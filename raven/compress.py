"""Recipient-aware passport construction + rendering.

Key integrity rule (enforced by tests): `render_passport` materialises the actual
fact TEXT (looked up from the store by id) into the exact string sent to the
agent. Token counts are taken from THAT string, never from bare fact IDs.
"""

from __future__ import annotations

from typing import Dict, List

from .roles import CRITICAL_TYPES, ROLES
from .retrieve import rank_facts
from .schemas import Fact, Passport
from .tokens import count_tokens

# Grouping of fact types into passport sections (for human-legible rendering).
_HARD = {"dietary", "budget", "availability"}
_RISK = {"permission"}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def dedup_facts(facts: List[Fact]) -> List[Fact]:
    """Near-duplicate removal: keep the first occurrence of each normalized text
    (the anchor). Cheap SeCo-inspired step; order preserved."""
    seen = set()
    out: List[Fact] = []
    for f in facts:
        key = _normalize(f.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def build_passport(facts: List[Fact], task: str, role: str, top_k: int = 8) -> Passport:
    if role not in ROLES:
        raise KeyError(f"unknown role: {role}")
    spec = ROLES[role]
    query = task + " " + " ".join(spec["keywords"])
    ranked = rank_facts(facts, query, allowed_types=spec["types"])

    chosen: List[Fact] = [f for _, f in ranked[:top_k]]
    chosen_ids = {f.fact_id for f in chosen}

    # Exact-span guard: force-keep the best-ranked fact of each critical type.
    for ctype in CRITICAL_TYPES.get(role, set()):
        for _, f in ranked:
            if f.type == ctype and f.fact_id not in chosen_ids:
                chosen.append(f)
                chosen_ids.add(f.fact_id)
                break

    chosen = dedup_facts(chosen)
    passport = Passport(task=task, for_agent=f"{role}_agent")
    passport.facts = [f.fact_id for f in chosen]
    # provenance: unique source items, order-preserved
    seen_src: set = set()
    for f in chosen:
        if f.source_ref and f.source_ref not in seen_src:
            seen_src.add(f.source_ref)
            passport.source_receipts.append(f.source_ref)
    return passport


def render_passport(passport: Passport, facts_by_id: Dict[str, Fact]) -> str:
    """The exact string sent to the downstream agent. Materialises fact TEXT from
    the store via the passport's fact IDs (refs). Never emits raw IDs."""
    hard: List[str] = []
    risk: List[str] = []
    other: List[str] = []
    for fid in passport.facts:
        fact = facts_by_id.get(fid)
        if fact is None:
            continue
        if fact.type in _HARD:
            hard.append(fact.text)
        elif fact.type in _RISK:
            risk.append(fact.text)
        else:
            other.append(fact.text)

    lines = [f"# CONTEXT PASSPORT for {passport.for_agent}", f"TASK: {passport.task}"]
    if hard:
        lines.append("HARD CONSTRAINTS:")
        lines.extend(f"- {t}" for t in hard)
    if risk:
        lines.append("RISK FLAGS:")
        lines.extend(f"- {t}" for t in risk)
    if other:
        lines.append("CONTEXT:")
        lines.extend(f"- {t}" for t in other)
    return "\n".join(lines)


def passport_tokens(passport: Passport, facts_by_id: Dict[str, Fact], backend: str = "fallback") -> int:
    return count_tokens(render_passport(passport, facts_by_id), backend=backend)
