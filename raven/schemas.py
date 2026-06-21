"""Core data structures. Stdlib dataclasses (no pydantic) so the core has zero
install risk on Python 3.13.

NOTE on integrity: a Passport stores `facts` as fact-IDs (references into the
fact store). The string actually sent to a downstream agent is produced by
`compress.render_passport(...)`, which materialises the real fact TEXT from the
store. Token counts are always taken from that rendered string, never from IDs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class Fact:
    fact_id: str
    text: str            # the atomic fact (verbatim sentence in M1)
    exact_span: str      # verbatim source substring (never paraphrased)
    source_ref: str      # which memory item this came from
    type: str            # dietary|budget|availability|permission|location|preference|other
    timestamp: str = ""
    salience: float = 0.0


@dataclass
class Passport:
    task: str
    for_agent: str
    facts: List[str] = field(default_factory=list)            # fact IDs (references)
    source_receipts: List[str] = field(default_factory=list)  # source item IDs (provenance)
