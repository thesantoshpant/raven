"""Store factory: defaults to in-memory and falls back gracefully when Redis is
unset or unreachable. The real Redis path is only exercised if a server is reachable."""

import os

import pytest

from raven.schemas import Fact
from raven.store import InMemoryFactStore, make_fact_store


def test_factory_defaults_to_in_memory(monkeypatch):
    monkeypatch.delenv("RAVEN_REDIS_URL", raising=False)
    assert isinstance(make_fact_store(), InMemoryFactStore)


def test_factory_falls_back_when_redis_unreachable():
    # Dead port (or redis not installed) -> must fall back, never raise.
    store = make_fact_store(url="redis://127.0.0.1:6390/0")
    assert isinstance(store, InMemoryFactStore)


def test_in_memory_roundtrip():
    s = InMemoryFactStore()
    s.add_many([Fact("f1", "hello", "hello", "src", "other"), Fact("f2", "world", "world", "src", "other")])
    assert s.get("f1").text == "hello"
    assert len(s) == 2
    assert set(s.by_id()) == {"f1", "f2"}


def test_redis_serialization_roundtrip_no_server():
    # Exercises the JSON (de)serialization the Redis path relies on, WITHOUT a server:
    # all 7 Fact fields (incl. timestamp + salience) must survive.
    from raven.store import RedisFactStore

    f = Fact("f1", "t", "span", "src", "dietary", timestamp="2026-01-01", salience=0.9)
    assert RedisFactStore._load(RedisFactStore._dump(f)) == f


@pytest.mark.skipif(not os.environ.get("RAVEN_REDIS_URL"), reason="no live Redis configured")
def test_redis_roundtrip_if_available():
    from raven.store import RedisFactStore

    try:
        store = RedisFactStore(os.environ["RAVEN_REDIS_URL"], namespace="raven:test")
    except Exception as exc:  # configured but server down -> skip, don't fail
        pytest.skip(f"Redis configured but unreachable: {exc}")
    store.clear()
    store.add(Fact("rf1", "redis fact", "redis fact", "src", "other"))
    assert store.get("rf1").text == "redis fact"
    assert len(store) == 1
    store.clear()
