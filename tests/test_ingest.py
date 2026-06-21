import os

from raven.ingest import ingest_corpus, load_corpus

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _facts():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    return ingest_corpus(corpus)


def test_produces_facts():
    facts = _facts()
    assert len(facts) > 20
    # exact_span is verbatim (never paraphrased)
    for f in facts:
        assert f.exact_span == f.text


def test_gold_constraints_are_present_and_typed():
    facts = _facts()

    def find(substr, ftype):
        return [f for f in facts if substr.lower() in f.text.lower() and f.type == ftype]

    assert find("vegetarian", "dietary"), "missing buried vegetarian/dietary fact"
    assert find("$40", "budget"), "missing buried budget fact"
    assert find("5:30", "availability"), "missing buried lab/availability fact"
    assert find("confirm", "permission"), "missing buried confirm/permission fact"
    assert find("loud", "preference"), "missing buried loud/preference fact"
