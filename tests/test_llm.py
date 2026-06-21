from raven.llm import FakeLLM, extract_json


def test_extract_simple():
    assert extract_json('{"venue_id": "green_bowl"}') == {"venue_id": "green_bowl"}


def test_extract_with_surrounding_prose():
    assert extract_json('Sure, here you go: {"venue_id": "x"} hope that helps!') == {"venue_id": "x"}


def test_extract_brace_inside_string_value():
    # The old depth-counter broke here; raw_decode is string-aware.
    assert extract_json('{"venue_id": "a}b", "note": "cost is 28}"}') == {"venue_id": "a}b", "note": "cost is 28}"}


def test_extract_first_object_only():
    assert extract_json('{"a": 1} {"b": 2}') == {"a": 1}


def test_extract_none_when_no_json():
    assert extract_json("no json at all") is None
    assert extract_json("") is None


def test_fake_llm_counts_tokens():
    llm = FakeLLM(lambda s, u: "hello world")
    res = llm.complete("sys", "user message")
    assert res.text == "hello world"
    assert res.input_tokens > 0 and res.output_tokens > 0
