"""Fact store. M1 = in-memory; a Redis-backed store drops in at M3 behind the
same minimal interface (add / get / all)."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from .schemas import Fact


class InMemoryFactStore:
    def __init__(self) -> None:
        self._facts: Dict[str, Fact] = {}

    def add(self, fact: Fact) -> None:
        self._facts[fact.fact_id] = fact

    def add_many(self, facts: Iterable[Fact]) -> None:
        for fact in facts:
            self.add(fact)

    def get(self, fact_id: str) -> Optional[Fact]:
        return self._facts.get(fact_id)

    def all(self) -> List[Fact]:
        return list(self._facts.values())

    def by_id(self) -> Dict[str, Fact]:
        return dict(self._facts)

    def __len__(self) -> int:
        return len(self._facts)
