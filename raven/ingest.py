"""Ingestion: messy memory items -> atomic Facts.

M1 uses deterministic rule-based atomization (sentence split + keyword typing).
The MarkItDown PDF->Markdown hook lands in M5; for M1 every source is plain text.
"""

from __future__ import annotations

import json
import re
from typing import List

from .schemas import Fact

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Ordered: first match wins, so put the highest-signal constraint types first.
_TYPE_RULES = [
    ("dietary", re.compile(r"\b(vegetarian|vegan|pescatarian|allerg\w*|gluten|no meat|dietary)\b", re.I)),
    ("permission", re.compile(r"\b(confirm|ask me|approve|permission|before (?:you )?pay|don'?t pay|never pay)\b", re.I)),
    ("budget", re.compile(r"(\$\s?\d+|\bunder \$?\d+|\bbudget\b|\bspend\b|\bcheap\b|\bprice\b|\bcost\b|\bper person\b)", re.I)),
    ("availability", re.compile(r"\b(lab|class|until|free|busy|after \d|before \d|\d{1,2}(?::\d{2})?\s?(?:am|pm)|mon|tue|wed|thu|fri|sat|sun|schedule|calendar|section)\b", re.I)),
    ("location", re.compile(r"\b(near|downtown|street|address|blvd|avenue|ave|area|neighborhood|mile|walk)\b", re.I)),
    ("preference", re.compile(r"\b(love|loves|like|likes|hate|hates|dislike|prefer|favou?rite|loud|quiet|annoy\w*|headache)\b", re.I)),
]


def classify(sentence: str) -> str:
    for fact_type, rx in _TYPE_RULES:
        if rx.search(sentence):
            return fact_type
    return "other"


def ingest_corpus(items: List[dict]) -> List[Fact]:
    """Split each memory item into sentence-level atomic facts with a type tag."""
    facts: List[Fact] = []
    idx = 0
    for item in items:
        text = (item.get("text") or "").strip()
        if not text:
            continue
        src = item.get("id", "")
        ts = item.get("timestamp", "")
        for raw in _SENT_SPLIT.split(text):
            sent = raw.strip()
            if len(sent) < 3:
                continue
            facts.append(
                Fact(
                    fact_id=f"f{idx}",
                    text=sent,
                    exact_span=sent,
                    source_ref=src,
                    type=classify(sent),
                    timestamp=ts,
                )
            )
            idx += 1
    return facts


def load_corpus(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)
