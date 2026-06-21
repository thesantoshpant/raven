"""Decision-preserving verifier (the research teeth) + ACON-style guideline learning.

For each role's action-critical probe: answer it from the FULL context and from the
compressed passport. If the answers diverge, the passport lost a load-bearing fact
-> re-add the best fact of the probe's type AND learn a guideline (so future builds
keep that type). Verifier token cost is returned and reported SEPARATELY as a
one-time, amortizable cost -- it is NOT folded into RAVEN's recurring per-task total.

Runs once per role passport (not per agent run), so its cost is one-time.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .compress import render_passport
from .guidelines import GuidelineStore
from .llm import BaseLLM
from .schemas import Fact, Passport

ANSWER_SYS = (
    "Answer the question using ONLY the context. Reply with a short value or yes/no. "
    "If the context does not contain the answer, reply exactly UNKNOWN."
)

# Action-critical probes per role: each maps to the fact TYPE that answers it.
ROLE_PROBES = {
    "restaurant": [{"question": "Does Maya have a dietary restriction? If so, what?", "type": "dietary"}],
    "calendar": [{"question": "Is the user busy until a certain time on Friday?", "type": "availability"}],
    "budget": [
        {"question": "What is the user's dinner budget limit?", "type": "budget"},
        {"question": "Does the user require confirmation before paying?", "type": "permission"},
    ],
}


def _answer(llm: BaseLLM, question: str, context: str, max_tokens: int = 60) -> Tuple[str, int]:
    res = llm.complete(ANSWER_SYS, f"CONTEXT:\n{context}\n\nQUESTION: {question}", max_tokens)
    return res.text.strip(), res.input_tokens + res.output_tokens


def _norm(ans: str) -> str:
    a = (ans or "").strip().lower().rstrip(".")
    if a in ("", "unknown", "n/a", "none", "i don't know", "i do not know"):
        return "unknown"
    return a


def verify_and_repair(
    llm: BaseLLM,
    role: str,
    passport: Passport,
    facts_by_id: Dict[str, Fact],
    all_facts: List[Fact],
    guidelines: Optional[GuidelineStore] = None,
) -> Tuple[Passport, List[str], int]:
    """Returns (possibly-repaired passport, list of newly-learned types, verifier tokens)."""
    tokens = 0
    learned: List[str] = []
    full_ctx = "\n".join(f.text for f in all_facts)

    for probe in ROLE_PROBES.get(role, []):
        passport_ctx = render_passport(passport, facts_by_id)
        a_full, t1 = _answer(llm, probe["question"], full_ctx)
        a_pass, t2 = _answer(llm, probe["question"], passport_ctx)
        tokens += t1 + t2
        # Divergence = the passport lost the answer that the full context has.
        if _norm(a_full) != "unknown" and _norm(a_pass) != _norm(a_full):
            # The passport diverges from full context. Re-add a missing fact of the
            # probe's type. Only count a "repair"/"learn" if a fact was ACTUALLY
            # added -- if the fact is already present (e.g. the static guard kept it,
            # or only the phrasing drifted), this is a no-op and must not claim a win.
            added = False
            for f in all_facts:
                if f.type == probe["type"] and f.fact_id not in passport.facts:
                    passport.facts.append(f.fact_id)
                    if f.source_ref and f.source_ref not in passport.source_receipts:
                        passport.source_receipts.append(f.source_ref)
                    added = True
                    break
            if added and guidelines is not None and guidelines.add_keep_type(role, probe["type"]):
                learned.append(probe["type"])

    return passport, learned, tokens
