"""Tests for the deterministic gold-constraint checkers (the M2 scoring logic).

Covers the cases the bug-hunt flagged: multi-time plans (lab end + dinner time)
and distractor prices, which the original max()/early-return logic got wrong.
"""

import pytest

from raven.score import check_constraint, score_plan


def test_must_include_any():
    spec = {"id": "veg", "type": "must_include_any", "any": ["vegetarian", "veggie"]}
    assert check_constraint("We chose a vegetarian spot.", spec) is True
    assert check_constraint("We chose a steakhouse.", spec) is False


def test_must_not_include_any():
    spec = {"id": "quiet", "type": "must_not_include_any", "any": ["nightclub", "loud bar"]}
    assert check_constraint("A quiet cozy bistro.", spec) is True
    assert check_constraint("A loud bar downtown.", spec) is False


def test_within_budget_existence_not_max():
    spec = {"id": "b", "type": "max_dollar", "value": 40}
    # in-budget choice present even though a distractor price is higher
    assert check_constraint("Picked Noodle House $31.50, not Burger Barn $52.20.", spec) is True
    assert check_constraint("Only option was $52.20.", spec) is False
    assert check_constraint("No prices mentioned.", spec) is False


def test_time_after_existence_not_universal():
    spec = {"id": "t", "type": "time_after", "hour": 18}
    # lab ends 5:30pm but dinner is 7pm -> satisfied
    assert check_constraint("Lab ends 5:30pm, dinner at 7pm.", spec) is True
    assert check_constraint("Dinner at 5pm.", spec) is False
    assert check_constraint("Reserved for 19:00.", spec) is True
    # bare ambiguous low number is skipped (not trusted as 24h)
    assert check_constraint("Meet at 5:30.", spec) is False


def test_bad_specs_raise():
    with pytest.raises(ValueError):
        check_constraint("x", {"type": "nonsense"})
    with pytest.raises(ValueError):
        check_constraint("x", {"type": "max_dollar"})
    with pytest.raises(ValueError):
        check_constraint("x", {"type": "time_after"})


def test_score_plan_counts():
    specs = [
        {"id": "veg", "type": "must_include_any", "any": ["vegetarian"]},
        {"id": "b", "type": "max_dollar", "value": 40},
    ]
    results, n = score_plan("vegetarian dinner, $30 total", specs)
    assert results == {"veg": True, "b": True}
    assert n == 2
