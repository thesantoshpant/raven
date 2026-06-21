"""Token counting.

Uses tiktoken if it is installed AND its encoding loads (it downloads once, then
caches). Otherwise falls back to a deterministic, offline, stdlib approximation.

The benchmark is RATIO-based and uses the *same* counter for every condition, so
the comparison is valid regardless of which backend is active. Tests pin
backend="fallback" for determinism with zero network.
"""

from __future__ import annotations

import re

_ENC = None
_BACKEND = None  # None = not yet probed; "tiktoken" or "fallback" after probe

_WORD_RE = re.compile(r"\w+|[^\w\s]")


def _probe() -> None:
    global _ENC, _BACKEND
    if _BACKEND is not None:
        return
    try:
        import tiktoken  # type: ignore

        _ENC = tiktoken.get_encoding("cl100k_base")
        _BACKEND = "tiktoken"
        return
    except Exception:
        _ENC = None
        _BACKEND = "fallback"


def _fallback_count(text: str) -> int:
    """Deterministic offline approximation of subword tokenization.

    Splits into word/punctuation pieces; long words contribute multiple tokens
    (~4 chars each), matching how BPE tokenizers behave. Monotonic in length, so
    ratios between conditions track real tokenizers closely.
    """
    n = 0
    for piece in _WORD_RE.findall(text):
        if piece.isalnum():
            n += max(1, (len(piece) + 3) // 4)
        else:
            n += 1
    return n


def count_tokens(text: str, backend: str = "auto") -> int:
    if not text:
        return 0
    if backend == "fallback":
        return _fallback_count(text)
    _probe()
    if _BACKEND == "tiktoken" and _ENC is not None:
        try:
            return len(_ENC.encode(text))
        except Exception:
            return _fallback_count(text)
    return _fallback_count(text)


def backend_name() -> str:
    _probe()
    return _BACKEND or "fallback"
