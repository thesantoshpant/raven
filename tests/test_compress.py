import os

from raven.compress import build_passport, dedup_facts, render_passport
from raven.ingest import ingest_corpus, load_corpus
from raven.schemas import Fact
from raven.store import InMemoryFactStore

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _setup():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    facts = ingest_corpus(corpus)
    store = InMemoryFactStore()
    store.add_many(facts)
    task = "Plan a Friday dinner with Maya under $40, quiet, after my lab, confirm before paying."
    return facts, store.by_id(), task


def test_restaurant_passport_keeps_dietary_constraint():
    facts, by_id, task = _setup()
    p = build_passport(facts, task, "restaurant")
    rendered = render_passport(p, by_id)
    assert "vegetarian" in rendered.lower()


def test_budget_passport_keeps_budget_and_permission():
    facts, by_id, task = _setup()
    p = build_passport(facts, task, "budget")
    rendered = render_passport(p, by_id).lower()
    assert "$40" in rendered
    assert "confirm" in rendered


def test_calendar_passport_is_recipient_aware_availability_only():
    # Strong recipient-awareness check: the calendar agent receives ONLY
    # availability facts (no dietary/budget/etc leaking in).
    facts, by_id, task = _setup()
    p = build_passport(facts, task, "calendar")
    assert p.facts, "calendar passport should not be empty"
    types = {by_id[fid].type for fid in p.facts}
    assert types <= {"availability"}, f"calendar leaked non-availability facts: {types}"


def test_budget_passport_excludes_zero_relevance_priced_distractors():
    # The positive-score filter must drop priced facts with no query overlap
    # (concert tickets, a restaurant total) from the budget passport.
    facts, by_id, task = _setup()
    p = build_passport(facts, task, "budget")
    rendered = render_passport(p, by_id)
    assert "$65" not in rendered      # concert tickets
    assert "$52.20" not in rendered   # Burger Barn total
    # but the real budget constraint is still there (force-kept)
    assert "$40" in rendered


def test_unknown_role_raises():
    facts, _, task = _setup()
    try:
        build_passport(facts, task, "nope")
        assert False, "expected KeyError"
    except KeyError:
        pass


def test_extra_keep_types_force_keeps_a_learned_type():
    # A budget fact with zero query-overlap is normally dropped from the restaurant
    # passport; a learned guideline (extra_keep_types) must force-keep it.
    facts = [
        Fact("d1", "Maya is vegetarian.", "Maya is vegetarian.", "c", "dietary"),
        Fact("g1", "Keep it under $40.", "Keep it under $40.", "c", "budget_limit"),
    ]
    task = "plan dinner with maya"
    without = build_passport(facts, task, "restaurant", top_k=1)
    with_keep = build_passport(facts, task, "restaurant", top_k=1, extra_keep_types={"budget_limit"})
    assert "g1" not in without.facts        # normally dropped (zero relevance, beyond top_k)
    assert "g1" in with_keep.facts          # force-kept by the learned guideline


def test_dedup_collapses_duplicates():
    f = lambda i: Fact(f"f{i}", "Maya is vegetarian.", "Maya is vegetarian.", "c", "dietary")
    out = dedup_facts([f(0), f(1), f(2)])
    assert len(out) == 1
