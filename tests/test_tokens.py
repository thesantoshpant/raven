from raven.tokens import count_tokens


def test_empty_is_zero():
    assert count_tokens("", "fallback") == 0
    assert count_tokens(None, "fallback") == 0


def test_positive_and_deterministic():
    a = count_tokens("Maya is vegetarian and dislikes loud bars.", "fallback")
    b = count_tokens("Maya is vegetarian and dislikes loud bars.", "fallback")
    assert a > 0 and a == b


def test_monotonic_in_length():
    s = "the quick brown fox jumps over the lazy dog. "
    assert count_tokens(s * 4, "fallback") >= count_tokens(s, "fallback")
