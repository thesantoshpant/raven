"""Retrieval = BM25 over fact text (stdlib, zero-download), with an optional
type filter. This is the primary path; fastembed vectors are an optional upgrade
exercised only by bench/smoke_fastembed.py.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import List, Optional, Set, Tuple

from .schemas import Fact

_TOK = re.compile(r"\w+")


def tokenize(text: str) -> List[str]:
    return _TOK.findall(text.lower())


class BM25:
    def __init__(self, docs_tokens: List[List[str]], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.N = len(docs_tokens)
        self.dl = [len(d) for d in docs_tokens]
        self.avgdl = (sum(self.dl) / self.N) if self.N else 0.0
        self.tf = [Counter(d) for d in docs_tokens]
        self.df: Counter = Counter()
        for d in docs_tokens:
            for term in set(d):
                self.df[term] += 1

    def idf(self, term: str) -> float:
        n = self.df.get(term, 0)
        # BM25+ style non-negative idf
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def score(self, query_tokens: List[str], i: int) -> float:
        s = 0.0
        dl = self.dl[i]
        tf = self.tf[i]
        denom_dl = self.avgdl or 1.0
        for term in query_tokens:
            f = tf.get(term, 0)
            if f == 0:
                continue
            denom = f + self.k1 * (1 - self.b + self.b * dl / denom_dl)
            s += self.idf(term) * (f * (self.k1 + 1)) / denom
        return s


def rank_facts(
    facts: List[Fact],
    query: str,
    allowed_types: Optional[Set[str]] = None,
) -> List[Tuple[float, Fact]]:
    """Return [(score, fact)] sorted high->low. `allowed_types=None` = no filter
    (used by the role-UNAWARE fair baseline)."""
    pool = [f for f in facts if (allowed_types is None or f.type in allowed_types)]
    if not pool:
        return []
    bm = BM25([tokenize(f.text) for f in pool])
    q = tokenize(query)
    scored = [(bm.score(q, i), f) for i, f in enumerate(pool)]
    # stable tie-break by fact_id so results are deterministic
    scored.sort(key=lambda x: (-x[0], x[1].fact_id))
    return scored
