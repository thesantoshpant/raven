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
# NOTE: `budget` is split into two subtypes so passports stay clean (M3):
#   - budget_limit    = a spending cap/limit -> the real constraint the budget agent needs
#   - expense_receipt = money already spent (receipts/totals/tickets) -> NOT a constraint
# budget_limit is matched FIRST and a CAP cue is required, so a sentence that states a
# cap but also mentions spending ("my budget is $40 but I spent $60") is kept as a
# constraint instead of being swallowed as a receipt. Bare "budget" must appear in a
# cap context (budget of/is/cap/limit/...) so a receipt note ("over budget") is NOT
# promoted to a hard constraint.
_TYPE_RULES = [
    ("dietary", re.compile(r"\b(vegetarian|vegan|pescatarian|allerg\w*|gluten|no meat|dietary)\b", re.I)),
    ("permission", re.compile(r"\b(confirm|ask me|approve|permission|before (?:you )?pay|don'?t pay|never pay|auto-?charge)\b", re.I)),
    ("budget_limit", re.compile(
        r"(\bunder \$?\d+|\bbelow \$?\d+|\bno more than \$?\d+|\b(?:don'?t|do not|not|never) spend (?:over|more than)"
        r"|\bspend (?:no more than|less than|under|below|at most)|\bmax(?:imum)? \$?\d+"
        r"|\bcap(?:ped)? (?:at|of|to)?\s*\$?\d|\bbudget (?:of|is|under|cap|limit|for|:)"
        r"|\bon a budget\b|\bdinner budget\b|\bkeep (?:it|dinner\w*|the bill|things?) (?:under|below|cheap|affordable|to)"
        r"|\bcheap\b|\baffordable\b|\bper person\b)", re.I)),
    ("expense_receipt", re.compile(r"(\breceipt\b|\btotal:?\s*\$|\bspent\b|\bpaid\b|\bcharged?\b|\bbill\b|\bcost me\b|tickets? (?:are|were|cost)|\$\d+\.\d{2})", re.I)),
    ("availability", re.compile(r"\b(lab|class|until|busy|after \d|before \d|free (?:after|before|from|until|on|all|this|next|fri|sat|sun|mon|tue|wed|thu|\d)|\d{1,2}(?::\d{2})?\s?(?:am|pm)|mon|tue|wed|thu|fri|sat|sun|schedule|calendar|section)\b", re.I)),
    ("location", re.compile(r"\b(near|downtown|street|address|blvd|avenue|ave|area|neighborhood|mile|walk)\b", re.I)),
    ("preference", re.compile(r"\b(love|loves|like|likes|hate|hates|dislike|prefer|favou?rite|loud|quiet|annoy\w*|headache)\b", re.I)),
]


def classify(sentence: str) -> str:
    for fact_type, rx in _TYPE_RULES:
        if rx.search(sentence):
            return fact_type
    return "other"


def split_sentences(text: str) -> List[str]:
    """Public sentence splitter (atomic-fact granularity). Drops <3 char fragments."""
    return [s.strip() for s in _SENT_SPLIT.split(text or "") if len(s.strip()) >= 3]


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
