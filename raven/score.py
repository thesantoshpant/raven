"""Deterministic gold-constraint checkers.

Predicate SPECS live as JSON data in data/task_*.json; the executable checkers
live here (JSON cannot hold functions). Used to score a final agent plan in M2;
defined + unit-tested now so the benchmark is deterministic, not LLM-judged.

Semantics are EXISTENCE-based against free-form plan text (a correct plan may also
mention rejected/distractor options):
  - time_after  : satisfied if SOME trusted time in the text is >= hour.
  - within_budget: satisfied if SOME dollar amount in the text is <= value
                   (i.e. an in-budget option is present). M2 will tighten this to
                   the *chosen* item once plans are structured.

Spec shapes:
  {"id": "vegetarian",  "type": "must_include_any",     "any": ["vegetarian", "veggie"]}
  {"id": "not_loud",    "type": "must_not_include_any", "any": ["loud bar", "nightclub"]}
  {"id": "budget",      "type": "max_dollar",           "value": 40}
  {"id": "after_6pm",   "type": "time_after",           "hour": 18}
"""

from __future__ import annotations

import re
from typing import Dict, List, Tuple

_DOLLAR = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
# A TRUSTED time must have am/pm (7pm) OR HH:MM (19:00). Bare integers are rejected
# (they're usually money, counts, or ids). The lookbehind rejects $-prefixed and
# multi-digit fragments (e.g. the "52" in "$52.20", the "86" in "CS186").
_TIME = re.compile(r"(?<![\$\d])\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", re.I)


def _within_budget_ok(text: str, value: float) -> bool:
    amounts = [float(x) for x in _DOLLAR.findall(text)]
    if not amounts:
        return False  # no price shown == not verifiably within budget
    # EXISTENCE: an in-budget option is present (don't fail on distractor prices).
    return any(a <= value for a in amounts)


def _time_after_ok(text: str, hour: int) -> bool:
    ok = False
    for m in _TIME.finditer(text):
        h, mins, ap = m.group(1), m.group(2), m.group(3)
        if not ap and not mins:
            continue  # bare integer (money/count/id) -> not a trusted time
        hh = int(h)
        if ap:
            ap = ap.lower()
            if ap == "pm" and hh != 12:
                hh += 12
            elif ap == "am" and hh == 12:
                hh = 0
        if 0 <= hh <= 23 and hh >= hour:
            ok = True  # EXISTENCE: some valid time satisfies the constraint
    return ok


def check_constraint(plan_text: str, spec: dict) -> bool:
    text = plan_text or ""
    low = text.lower()
    kind = spec.get("type")
    if kind == "must_include_any":
        return any(k.lower() in low for k in spec.get("any", []))
    if kind == "must_not_include_any":
        return not any(k.lower() in low for k in spec.get("any", []))
    if kind == "max_dollar":
        if "value" not in spec:
            raise ValueError("max_dollar spec requires 'value'")
        return _within_budget_ok(text, float(spec["value"]))
    if kind == "time_after":
        if "hour" not in spec:
            raise ValueError("time_after spec requires 'hour'")
        return _time_after_ok(text, int(spec["hour"]))
    raise ValueError(f"unknown constraint spec type: {kind!r}")


def score_plan(plan_text: str, specs: List[dict]) -> Tuple[Dict[str, bool], int]:
    """Return (per-constraint results, number satisfied)."""
    results = {s["id"]: check_constraint(plan_text, s) for s in specs}
    return results, sum(1 for v in results.values() if v)


# --- Structured scoring (M2): score the chosen-plan fields first; free-form fallback ---

def _time_hour(text: str) -> "int | None":
    for m in _TIME.finditer(text or ""):
        h, mins, ap = m.group(1), m.group(2), m.group(3)
        if not ap and not mins:
            continue
        hh = int(h)
        if ap:
            ap = ap.lower()
            if ap == "pm" and hh != 12:
                hh += 12
            elif ap == "am" and hh == 12:
                hh = 0
        if 0 <= hh <= 23:
            return hh
    return None


def _structured_ok(value, rule: dict) -> bool:
    t = rule.get("type")
    if t == "is_true":
        if isinstance(value, bool):
            return value
        # tolerate stringified/numeric booleans from an LLM ("true"/"yes"/1); reject false-ish
        return str(value).strip().lower() in {"true", "yes", "y", "1"}
    if t == "max_dollar":
        try:
            return float(value) <= float(rule["value"])
        except (TypeError, ValueError, KeyError):
            return False
    if t == "time_after":
        h = _time_hour(str(value))
        return h is not None and h >= int(rule["hour"])
    raise ValueError(f"unknown structured rule type: {t!r}")


def score_structured(plan: dict, specs: List[dict]) -> Tuple[Dict[str, bool], int]:
    """Score a structured plan dict against gold specs.

    Each spec carries `field` + `structured` (the structured rule) and a `fallback`
    free-form spec. If the structured field is present (not None) we score it
    deterministically; otherwise we fall back to free-form text scoring.
    """
    # Is this a structured plan at all? (any structured field present and not None)
    has_structured = any(s.get("field") and plan.get(s["field"]) is not None for s in specs)
    results: Dict[str, bool] = {}
    for s in specs:
        field = s.get("field")
        if field and plan.get(field) is not None:
            results[s["id"]] = _structured_ok(plan[field], s["structured"])
        elif field and has_structured:
            # Structured plan, but THIS field is missing/None (e.g. no venue chosen)
            # -> genuine FAIL, never a vacuous free-form pass.
            results[s["id"]] = False
        else:
            # Purely free-form plan (no structured fields at all) -> free-form fallback.
            results[s["id"]] = check_constraint(str(plan.get("text", "")), s.get("fallback", s))
    return results, sum(1 for v in results.values() if v)
