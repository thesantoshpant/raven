"""The M1 gate, with a CONSISTENT accounting model (every condition charged for
the same N agent-sends; generic baselines built at the per-agent budget)."""

import json
import os

from raven.baselines import generic_factstore_unaware, raw_once
from raven.compress import build_passport, passport_tokens
from raven.ingest import ingest_corpus, load_corpus
from raven.store import InMemoryFactStore

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _measure():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    with open(os.path.join(DATA, "task_friday_dinner.json"), encoding="utf-8") as fh:
        task = json.load(fh)
    facts = ingest_corpus(corpus)
    store = InMemoryFactStore()
    store.add_many(facts)
    by_id = store.by_id()
    roles = task["roles"]
    n = len(roles)
    raven_total = sum(
        passport_tokens(build_passport(facts, task["request"], r), by_id, backend="fallback")
        for r in roles
    )
    _, raw_once_tok = raw_once(corpus, backend="fallback")
    return corpus, facts, task, n, raven_total, raw_once_tok


def test_ratio_gate_raven_at_most_half_of_raw_broadcast():
    _, _, _, n, raven_total, raw_once_tok = _measure()
    raw_broadcast = raw_once_tok * n
    assert raven_total > 0
    ratio = raven_total / raw_broadcast
    assert ratio <= 0.50, f"gate failed: RAVEN/raw_broadcast = {ratio:.3f}"


def test_per_send_passport_smaller_than_full_memory():
    _, _, _, n, raven_total, raw_once_tok = _measure()
    assert (raven_total / n) < raw_once_tok


def test_fair_baseline_is_equal_budget_and_consistent():
    """generic_factstore_unaware built at the per-agent budget, x N, must be ~ the
    RAVEN total (equal-budget, same N sends) — never larger, never trivially tiny."""
    _, facts, task, n, raven_total, _ = _measure()
    per_agent_budget = max(1, raven_total // n)
    _, gfs_single = generic_factstore_unaware(
        facts, task["request"], per_agent_budget, backend="fallback"
    )
    gfs_total = gfs_single * n
    assert 0 < gfs_total <= raven_total + n  # <= because of floor division on the budget
