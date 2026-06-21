"""M4 web services -- offline, deterministic (FakeLLM). pytest never imports fastapi."""

from raven.llm import FakeLLM
from raven.web import services


def _fake_agents():
    def responder(system, user):
        s = system.lower()
        if "restaurant" in s:
            return '{"venue_id": "green_bowl"}'
        if "calendar" in s:
            return '{"time": "19:00"}'
        if "budget" in s:
            return '{"requires_confirmation": true}'
        return "{}"
    return FakeLLM(responder)


def test_get_scenario_shape():
    s = services.get_scenario()
    assert s["counts"]["items"] == 38 and s["counts"]["facts"] > 100
    assert s["roles"] and s["candidates"] and s["highlights"]
    assert isinstance(s["memory_items"], list) and "text" in s["memory_items"][0]


def test_role_passports_budget_keeps_criticals_and_compresses():
    pp = services.role_passports()
    budget = next(r for r in pp["roles"] if r["role"] == "budget")
    assert "$40" in budget["passport_text"] and "confirm" in budget["passport_text"].lower()
    assert budget["tokens"] < pp["full_tokens"]
    assert budget["excluded_count"] > 0


def test_relay_demo_preserves_backcontext():
    r = services.relay_demo()
    assert r["totals"]["relay"] < r["totals"]["full"]
    assert r["preservation"]["relay_keeps"] == r["preservation"]["hops"]   # 3/3
    assert r["preservation"]["last_keeps"] < r["preservation"]["hops"]     # last-message drops it


def test_run_benchmark_structure_offline():
    out = services.run_benchmark(_fake_agents())
    assert set(out["conditions"]) == {"raw", "generic", "raven"}
    gold = set(services.get_scenario()["gold_constraints"])
    for cond in out["conditions"].values():
        assert 0 <= cond["constraints"] <= 5 and cond["agent_tokens"] > 0
        assert set(cond["per_constraint"]) == gold              # scores the real 5 gold ids
        assert isinstance(cond["plan"]["requires_confirmation"], bool)  # not the string "false"
        assert isinstance(cond["plan"]["dietary_ok"], bool)
    # raw forwards the FULL corpus, so its context cost must exceed the budgeted generic
    # -> catches a condition-routing regression (e.g. all conditions getting full_ctx).
    assert out["conditions"]["raw"]["agent_tokens"] > out["conditions"]["generic"]["agent_tokens"]


def test_compress_service():
    out = services.compress(
        "budget", "plan dinner",
        "Keep dinners under $40. Always confirm before paying. The weather is nice.",
    )
    assert out["stats"]["ok"] is True
    assert "$40" in out["reply"]
