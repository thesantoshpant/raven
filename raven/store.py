"""Fact store. In-memory (default) or Redis-backed, behind the same minimal interface
(add / add_many / get / all / by_id / __len__). Use `make_fact_store()` to pick: it
returns Redis when a reachable URL is configured, else falls back to in-memory and
NEVER raises on Redis being absent."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
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


class RedisFactStore:
    """Redis-backed store (one hash, field=fact_id, value=JSON). Lazy-imports `redis`
    and pings on construction so an unreachable Redis fails fast (the factory then
    falls back). Same interface as InMemoryFactStore."""

    def __init__(self, url: str = "redis://localhost:6379/0", namespace: str = "raven:facts") -> None:
        import redis  # lazy: never imported unless Redis is actually requested

        self._r = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.5)
        self._r.ping()  # raise now if unreachable
        self._ns = namespace

    @staticmethod
    def _dump(fact: Fact) -> str:
        return json.dumps(asdict(fact))

    @staticmethod
    def _load(blob: str) -> Fact:
        return Fact(**json.loads(blob))

    def add(self, fact: Fact) -> None:
        self._r.hset(self._ns, fact.fact_id, self._dump(fact))

    def add_many(self, facts: Iterable[Fact]) -> None:
        pipe = self._r.pipeline()
        for fact in facts:
            pipe.hset(self._ns, fact.fact_id, self._dump(fact))
        pipe.execute()

    def get(self, fact_id: str) -> Optional[Fact]:
        blob = self._r.hget(self._ns, fact_id)
        return self._load(blob) if blob else None

    def all(self) -> List[Fact]:
        return [self._load(v) for v in self._r.hvals(self._ns)]

    def by_id(self) -> Dict[str, Fact]:
        return {k: self._load(v) for k, v in self._r.hgetall(self._ns).items()}

    def __len__(self) -> int:
        return int(self._r.hlen(self._ns))

    def clear(self) -> None:
        self._r.delete(self._ns)


def make_fact_store(url: Optional[str] = None, namespace: str = "raven:facts"):
    """Return a RedisFactStore if a Redis URL is set (env RAVEN_REDIS_URL) and
    reachable, else an InMemoryFactStore. Never raises on Redis being absent."""
    url = url or os.environ.get("RAVEN_REDIS_URL")
    if not url:
        return InMemoryFactStore()
    try:
        return RedisFactStore(url, namespace)
    except Exception:  # noqa: BLE001 -- any redis/connection/import error => fall back
        return InMemoryFactStore()
