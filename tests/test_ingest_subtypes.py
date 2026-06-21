"""M3 subtype split: budget_limit (a real cap) vs expense_receipt (money spent),
and 'free coffee' no longer leaking into availability."""

import os

from raven.compress import build_passport, render_passport
from raven.ingest import classify, ingest_corpus, load_corpus
from raven.store import InMemoryFactStore

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def test_budget_limit_vs_expense_receipt():
    assert classify("I want to keep dinners under $40 this month.") == "budget_limit"
    assert classify("Receipt: Campus Bookstore. Total $18.75 for a notebook.") == "expense_receipt"
    assert classify("The concert tickets are like $65 which is steep.") == "expense_receipt"
    assert classify("Burger Barn was $52.20 last time.") == "expense_receipt"


def test_free_coffee_not_availability_but_free_after_time_is():
    assert classify("The career fair had free coffee and snacks.") != "availability"
    assert classify("She's free after 7pm on Friday.") == "availability"


def test_budget_cap_with_spending_word_stays_a_limit():
    # A cap that also mentions spending must be kept as a constraint, not swallowed.
    assert classify("My budget is $40 but I already spent $60 this month.") == "budget_limit"
    assert classify("Don't spend over $40 on dinner.") == "budget_limit"
    assert classify("Let's not spend more than $40.") == "budget_limit"


def test_over_budget_receipt_note_is_not_a_budget_limit():
    # A receipt note must NOT be promoted to a hard budget constraint.
    assert classify("Note to self: this was over budget and honestly too loud.") != "budget_limit"


def test_auto_charge_rule_is_permission():
    assert classify("Never auto-charge my card without checking first.") == "permission"


def test_per_person_price_is_not_a_budget_limit():
    # "$28 per person" is a price OBSERVATION, not a spending cap -> must not be a hard constraint.
    assert classify("Green Bowl is $28 per person.") != "budget_limit"
    assert classify("Keep dinners under $40.") == "budget_limit"  # a real cap still is


def test_24h_times_and_weekdays_are_availability():
    assert classify("Free Friday at 19:00.") == "availability"
    assert classify("Meeting from 14:00 to 16:00.") == "availability"
    assert classify("Let's meet Tuesday.") == "availability"
    # no false positives from the weekday rule:
    assert classify("The wedding was lovely.") != "availability"


def test_budget_passport_excludes_expense_receipts():
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    facts = ingest_corpus(corpus)
    store = InMemoryFactStore()
    store.add_many(facts)
    task = "Plan a Friday dinner with Maya."
    rendered = render_passport(build_passport(facts, task, "budget"), store.by_id())
    assert "$40" in rendered          # the budget LIMIT is kept
    assert "$18.75" not in rendered   # a notebook receipt is not a budget constraint
    assert "$65" not in rendered      # concert tickets are not a budget constraint
