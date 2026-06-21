"""Baseline token-accounting (the gate's measurement model)."""

import os

from raven.baselines import (
    generic_factstore_unaware,
    generic_truncation,
    raw_broadcast_tokens,
    raw_once,
)
from raven.ingest import ingest_corpus, load_corpus

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _corpus():
    return load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))


def test_raw_broadcast_is_raw_once_times_n():
    c = _corpus()
    once = raw_once(c)[1]
    assert once > 0
    assert raw_broadcast_tokens(c, 4) == once * 4


def test_generic_truncation_respects_budget():
    text, toks = generic_truncation(_corpus(), 200)
    assert toks <= 200 and len(text) > 0


def test_generic_factstore_unaware_within_budget():
    facts = ingest_corpus(_corpus())
    text, toks = generic_factstore_unaware(facts, "plan a friday dinner", 200)
    assert toks <= 200 and "GENERIC" in text
