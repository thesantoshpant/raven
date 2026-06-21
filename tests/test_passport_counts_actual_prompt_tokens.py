"""Integrity guard (the review's required addition): token counts MUST be computed
from the exact rendered string sent to the agent — the materialized fact TEXT —
NOT from internal fact IDs / refs. This prevents artificially tiny token counts.
"""

import os
import re

from raven.compress import build_passport, passport_tokens, render_passport
from raven.ingest import ingest_corpus, load_corpus
from raven.store import InMemoryFactStore
from raven.tokens import count_tokens

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _setup():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    facts = ingest_corpus(corpus)
    store = InMemoryFactStore()
    store.add_many(facts)
    task = "Plan a Friday dinner with Maya under $40, quiet, after lab, confirm before paying."
    p = build_passport(facts, task, "restaurant")
    return p, store.by_id()


def test_count_is_taken_from_rendered_string():
    p, by_id = _setup()
    rendered = render_passport(p, by_id)
    assert passport_tokens(p, by_id, backend="fallback") == count_tokens(rendered, "fallback")


def test_rendered_string_contains_real_fact_text_not_ids():
    p, by_id = _setup()
    rendered = render_passport(p, by_id)
    # real materialized text is present
    assert "vegetarian" in rendered.lower()
    # the passport references facts by id, but the rendered prompt must NOT be the ids
    assert p.facts, "passport should reference facts by id internally"
    for fid in p.facts:
        assert f"- {fid}\n" not in (rendered + "\n"), "rendered a bare fact ID instead of text"
    # rendered is not just a list of ids like 'f0\nf1\n...'
    body_lines = [ln[2:] for ln in rendered.splitlines() if ln.startswith("- ")]
    assert body_lines, "expected materialized bullet lines"
    assert not all(re.fullmatch(r"f\d+", ln) for ln in body_lines)


def test_counting_ids_would_be_smaller_proving_we_dont_cheat():
    # Sanity: counting bare IDs would understate tokens vs the real rendered text.
    p, by_id = _setup()
    rendered_tok = passport_tokens(p, by_id, backend="fallback")
    ids_only_tok = count_tokens("\n".join(p.facts), "fallback")
    assert rendered_tok > ids_only_tok
