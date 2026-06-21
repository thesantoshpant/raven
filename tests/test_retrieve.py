from raven.retrieve import rank_facts
from raven.schemas import Fact


def _facts():
    return [
        Fact("f0", "Maya is vegetarian, no meat.", "Maya is vegetarian, no meat.", "c1", "dietary"),
        Fact("f1", "Keep dinner under $40.", "Keep dinner under $40.", "c2", "budget"),
        Fact("f2", "Lab runs until 5:30 on Friday.", "Lab runs until 5:30 on Friday.", "c3", "availability"),
        Fact("f3", "I dislike loud bars.", "I dislike loud bars.", "c4", "preference"),
        Fact("f4", "Confirm before paying.", "Confirm before paying.", "c5", "permission"),
    ]


def test_type_filter_only_returns_allowed_types():
    ranked = rank_facts(_facts(), "anything", allowed_types={"budget", "permission"})
    types = {f.type for _, f in ranked}
    assert types <= {"budget", "permission"}
    assert len(ranked) == 2


def test_ranking_surfaces_relevant_fact_first():
    ranked = rank_facts(_facts(), "vegetarian dinner for Maya", allowed_types=None)
    assert ranked[0][1].fact_id == "f0"


def test_no_facts_returns_empty():
    assert rank_facts([], "x", None) == []


def test_bm25_length_normalization_decides_ties():
    # Both docs contain the query term once; BM25 length-normalization must rank
    # the short doc above the spammy long one. A naive term-overlap scorer ties.
    facts = [
        Fact("long", "vegetarian " + ("filler word " * 80), "x", "c", "other"),
        Fact("short", "vegetarian option", "x", "c", "other"),
    ]
    ranked = rank_facts(facts, "vegetarian", allowed_types=None)
    assert ranked[0][1].fact_id == "short"
