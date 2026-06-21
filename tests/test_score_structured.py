import json
import os

from raven.score import score_structured

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def _specs():
    with open(os.path.join(DATA, "task_friday_dinner.json"), encoding="utf-8") as fh:
        return json.load(fh)["gold_constraints"]


def test_structured_all_pass():
    plan = {"dietary_ok": True, "price": 28, "time": "19:00", "quiet": True, "requires_confirmation": True}
    results, n = score_structured(plan, _specs())
    assert n == 5, results


def test_structured_all_fail():
    plan = {"dietary_ok": False, "price": 55, "time": "17:00", "quiet": False, "requires_confirmation": False}
    _, n = score_structured(plan, _specs())
    assert n == 0


def test_structured_partial():
    plan = {"dietary_ok": True, "price": 60, "time": "19:00", "quiet": False, "requires_confirmation": True}
    results, n = score_structured(plan, _specs())
    assert results["vegetarian"] and not results["budget_under_40"]
    assert results["after_6pm"] and not results["not_loud"] and results["confirm_before_pay"]
    assert n == 3


def test_fallback_to_free_form_only_for_pure_text_plans():
    plan = {"text": "Booked a vegetarian place for $30 at 7pm, nice and quiet, will confirm before paying."}
    _, n = score_structured(plan, _specs())
    assert n == 5  # no structured fields at all -> free-form fallback resolves them


def test_missing_venue_does_not_pass_vacuously():
    # Structured plan where the restaurant agent chose NO venue: dietary/price/quiet
    # are None. Those must FAIL (not vacuously pass not_loud via free-form on stub text).
    plan = {
        "venue_id": None, "price": None, "dietary_ok": None, "quiet": None,
        "time": "19:00", "requires_confirmation": True, "text": "Plan: unknown at 19:00.",
    }
    results, n = score_structured(plan, _specs())
    assert results["not_loud"] is False
    assert results["vegetarian"] is False and results["budget_under_40"] is False
    assert results["after_6pm"] is True and results["confirm_before_pay"] is True
    assert n == 2
