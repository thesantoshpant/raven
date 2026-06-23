"""Weird/difficult conditions for the A/B 'personal assistant' selection (_raven_select).
Deterministic + offline (no LLM, no network)."""

from raven.llm import FakeLLM
from raven.web import services
from raven.web.services import _raven_select

DINNER_MEM = (
    "Maya is vegetarian, no meat for her. Always ask me to confirm before paying for anything. "
    "Keep dinners under $40 this month. Maya is free Friday night after 7pm. "
    "There's a cute Italian place near campus on Bancroft that Maya wants to try. "
    "I like quiet cozy restaurants and outdoor seating when it's nice. "
    "Return the library books before the late fee. Finish the line-following robot. "
    "Do laundry and meal prep on Sunday. Renew the bus pass."
)


def _guarded(chosen):
    return {f.type for f, r in chosen if r == "guard"}


def test_standing_rules_guarded_for_ANY_prompt():
    # The 3 standing rules must survive regardless of what is asked (even gibberish / empty).
    for prompt in ["where should we eat", "xyzzy", "", "robot project status", "9999", "🍕?"]:
        _, chosen = _raven_select(DINNER_MEM, prompt)
        assert {"dietary", "permission", "budget_limit"} <= _guarded(chosen), prompt


def test_planning_prompt_surfaces_venue_schedule_and_constraints():
    _, chosen = _raven_select(DINNER_MEM, "where and when should we book Friday dinner with Maya")
    text = " ".join(f.text.lower() for f, _ in chosen)
    assert "vegetarian" in text and "confirm" in text and "$40" in text   # guards
    assert "italian" in text                                              # the venue surfaced
    assert "after 7" in text or "friday" in text                         # the schedule surfaced


def test_empty_memory_returns_nothing_no_crash():
    facts, chosen = _raven_select("", "anything")
    assert facts == [] and chosen == []


def test_empty_and_gibberish_prompt_keep_guards():
    for prompt in ["", "qwzx plmk zzz foobar"]:
        _, chosen = _raven_select(DINNER_MEM, prompt)
        assert {"dietary", "permission", "budget_limit"} <= _guarded(chosen)


def test_memory_with_no_guard_types_does_not_crash():
    _, chosen = _raven_select("I like robots. The sky is blue. Soccer signups are open.", "robots")
    assert isinstance(chosen, list)  # no crash; guards simply absent


def test_selection_is_bounded_and_truncates_many_distinct_facts():
    # 20 DISTINCT relevant sentences -> selection must drop some (not return all 20) and stay bounded.
    mem = ". ".join(f"Option {i}: a quiet vegetarian place under ${30 + i} downtown" for i in range(20)) + "."
    _, chosen = _raven_select(mem, "where should we eat dinner")
    assert 1 <= len(chosen) <= 13     # bounded; neither empty nor everything
    assert len(chosen) < 20           # truncation actually happened


def test_dedup_no_repeated_fact_text():
    _, chosen = _raven_select(DINNER_MEM + " " + DINNER_MEM, "dinner with maya")
    texts = [f.text for f, _ in chosen]
    assert len(texts) == len(set(texts))


def test_unicode_symbols_and_long_input_no_crash():
    weird = "Maya is vegetarian 🌱. Budget ≤ $40 ‼. Confirm before paying. " + ("blah " * 4000)
    _, chosen = _raven_select(weird, "dinner 🍝")
    assert isinstance(chosen, list)


def test_run_ab_trace_is_internally_consistent_across_prompts():
    llm = FakeLLM(lambda s, u: "ok.")
    for prompt in ["where to eat friday", "when is maya free", "what is my budget", "zzz gibberish", ""]:
        out = services.run_ab(llm, prompt or "x", DINNER_MEM)
        tr = out["trace"]
        assert tr["dropped"] == tr["total_facts"] - len(tr["kept"])
        assert all(k["reason"] in {"guard", "relevant"} for k in tr["kept"])
        assert "cached" in out and "elapsed_s" in out
        assert out["without"]["answer"] and out["raven"]["answer"]
