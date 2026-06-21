"""Per-role compression guidelines (ACON-style, learned at runtime).

A guideline is the set of fact TYPES a role must always keep, on top of the
static CRITICAL_TYPES. When the verifier catches a dropped action-critical fact
for a role, it adds that type here, so the compressor stops dropping that class
next time -- failure-driven guideline optimization, no fine-tuning.
"""

from __future__ import annotations

from typing import Dict, Set


class GuidelineStore:
    def __init__(self) -> None:
        self._keep_types: Dict[str, Set[str]] = {}

    def keep_types(self, role: str) -> Set[str]:
        return set(self._keep_types.get(role, set()))

    def add_keep_type(self, role: str, fact_type: str) -> bool:
        """Returns True if this is a newly-learned rule."""
        cur = self._keep_types.setdefault(role, set())
        if fact_type in cur:
            return False
        cur.add(fact_type)
        return True

    def as_dict(self) -> Dict[str, list]:
        return {r: sorted(t) for r, t in self._keep_types.items()}
