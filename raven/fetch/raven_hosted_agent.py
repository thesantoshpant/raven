"""RAVEN -- single-file Agentverse hosted uAgent (recipient-aware context compressor).

The ENTIRE RAVEN engine is inlined below (pure stdlib), followed by a Chat-Protocol uAgent.
Paste this whole file into an Agentverse "Blank Agent", press Start, and chat with it:

    role: budget | memory: Maya is vegetarian. Keep dinner under $40. Always confirm before paying.

It replies with a tiny, recipient-aware context passport + the token savings. No API key needed
(pure deterministic compression). Source + tests: https://github.com/thesantoshpant/raven
"""
from __future__ import annotations

# ---------------- inlined: raven/schemas.py ----------------
"""Core data structures. Stdlib dataclasses (no pydantic) so the core has zero
install risk on Python 3.13.

NOTE on integrity: a Passport stores `facts` as fact-IDs (references into the
fact store). The string actually sent to a downstream agent is produced by
`compress.render_passport(...)`, which materialises the real fact TEXT from the
store. Token counts are always taken from that rendered string, never from IDs.
"""


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

# ---------------- inlined: raven/tokens.py ----------------
"""Token counting.

Uses tiktoken if it is installed AND its encoding loads (it downloads once, then
caches). Otherwise falls back to a deterministic, offline, stdlib approximation.

The benchmark is RATIO-based and uses the *same* counter for every condition, so
the comparison is valid regardless of which backend is active. Tests pin
backend="fallback" for determinism with zero network.
"""


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

# ---------------- inlined: raven/ingest.py ----------------
"""Ingestion: messy memory items -> atomic Facts.

M1 uses deterministic rule-based atomization (sentence split + keyword typing).
The MarkItDown PDF->Markdown hook lands in M5; for M1 every source is plain text.
"""


import json
import re
from typing import List


_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+|\s*[\r\n]+\s*")  # split on sentence ends AND newlines
_BULLET = "-*•‣◦ \t"                        # leading bullet chars to strip per line

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
        r"|\bcap(?:ped)? (?:at|of|to)\s*\$?\d|\bbudget (?:of|is|under|cap|limit|for|:)"
        r"|\bon a budget\b|\bdinner budget\b|\bkeep (?:it|dinner\w*|the bill|things?) (?:under|below|cheap|affordable|to)"
        r"|\bcheap\b|\baffordable\b)", re.I)),  # NOTE: "per person" is a price OBSERVATION, not a cap -> not budget_limit
    ("expense_receipt", re.compile(r"(\breceipt\b|\btotal:?\s*\$|\bspent\b|\bpaid\b|\bcharged?\b|\bbill\b|\bcost me\b|tickets? (?:are|were|cost)|\$\d+\.\d{2})", re.I)),
    ("availability", re.compile(
        r"\b(?:lab|class|busy|schedule|calendar|section|until|tonight|evening)\b"
        r"|\b(?:after|before|by|from)\s+\d"
        r"|\bfree\s+(?:after|before|from|until|on|all|this|next|tonight|the|\d)"
        r"|\b(?:mon|tues?|wed(?:nes)?|thurs?|fri|sat(?:ur)?|sun)(?:day)?\b"   # weekday abbr or full
        r"|\b(?:[01]?\d|2[0-3]):[0-5]\d\b"                                     # 24-hour time 19:00 / 5:30
        r"|\b\d{1,2}(?::\d{2})?\s?(?:am|pm)\b",                               # 12-hour time 7pm / 5:30pm
        re.I)),
    ("location", re.compile(r"\b(near|downtown|street|address|blvd|avenue|ave|area|neighborhood|mile|walk)\b", re.I)),
    ("preference", re.compile(r"\b(love|loves|like|likes|hate|hates|dislike|prefer|favou?rite|loud|quiet|annoy\w*|headache)\b", re.I)),
]


def classify(sentence: str) -> str:
    for fact_type, rx in _TYPE_RULES:
        if rx.search(sentence):
            return fact_type
    return "other"


def classify_all(sentence: str) -> List[str]:
    """Multi-label: EVERY type whose pattern matches (in rule order, deduped).

    The corpus path uses single-label `classify` (its sentences are already atomic).
    The RELAY/agent path uses this so a combined, judge-pasted sentence stating several
    constraints ("Maya is vegetarian and keep dinner under $40 and confirm before paying")
    yields a fact per constraint instead of collapsing to a single first-match type.
    """
    out = [ftype for ftype, rx in _TYPE_RULES if rx.search(sentence)]
    return out or ["other"]


def _clean(s: str) -> str:
    return s.strip().lstrip(_BULLET).strip()


def split_sentences(text: str) -> List[str]:
    """Public sentence splitter (atomic-fact granularity). Splits on sentence ends AND
    newlines/bullets so a pasted bullet/line list becomes one fact per line. Drops <3 char
    fragments."""
    return [c for c in (_clean(s) for s in _SENT_SPLIT.split(text or "")) if len(c) >= 3]


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
        for sent in split_sentences(text):
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

# ---------------- inlined: raven/retrieve.py ----------------
"""Retrieval = BM25 over fact text (stdlib, zero-download), with an optional
type filter. This is the primary path; fastembed vectors are an optional upgrade
exercised only by bench/smoke_fastembed.py.
"""


import math
import re
from collections import Counter
from typing import List, Optional, Set, Tuple


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

# ---------------- inlined: raven/roles.py ----------------
"""Recipient (role) definitions: what each downstream agent actually needs.

This is the heart of "recipient-aware" compression: a fact is only included in a
passport if it matters to THAT agent's job. `CRITICAL_TYPES` are force-kept by the
exact-span guard (the constraints whose loss flips the decision).
"""

ROLES = {
    "restaurant": {
        "types": {"dietary", "preference", "budget_limit", "location"},
        "keywords": [
            "restaurant", "food", "dinner", "cuisine", "vegetarian", "vegan",
            "loud", "quiet", "noise", "budget", "price", "near", "location", "menu",
        ],
    },
    "calendar": {
        "types": {"availability"},
        "keywords": [
            "calendar", "free", "busy", "time", "schedule", "friday", "evening",
            "lab", "class", "until", "after", "before", "pm", "am",
        ],
    },
    "budget": {  # the budget / payment agent
        "types": {"budget_limit", "permission"},
        "keywords": [
            "budget", "price", "cost", "spend", "dollar", "confirm", "approve",
            "payment", "pay", "before", "permission",
        ],
    },
    "writer": {  # the final summarizer: needs the decisions + constraints, not receipts
        "types": {"dietary", "budget_limit", "availability", "permission", "preference", "location"},
        "keywords": [
            "summary", "plan", "recommend", "prefer", "like", "vegetarian", "budget",
            "time", "confirm", "venue", "quiet",
        ],
    },
}

# Stable order = the agent pipeline used by the benchmark (n_agents = len).
ROLE_ORDER = ["restaurant", "calendar", "budget", "writer"]

# Types the exact-span guard must always include for a role if present in the store.
CRITICAL_TYPES = {
    "restaurant": {"dietary"},
    "calendar": {"availability"},
    "budget": {"budget_limit", "permission"},
    # the writer/summarizer must retain every standing constraint, even ones BM25 scores 0
    "writer": {"dietary", "budget_limit", "availability", "permission"},
}

# ---------------- inlined: raven/compress.py ----------------
"""Recipient-aware passport construction + rendering.

Key integrity rule (enforced by tests): `render_passport` materialises the actual
fact TEXT (looked up from the store by id) into the exact string sent to the
agent. Token counts are taken from THAT string, never from bare fact IDs.
"""


from typing import Dict, List, Optional, Set


# Grouping of fact types into passport sections (for human-legible rendering).
_HARD = {"dietary", "budget_limit", "availability"}
_RISK = {"permission"}


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def dedup_facts(facts: List[Fact]) -> List[Fact]:
    """Near-duplicate removal: keep the first occurrence of each normalized text
    (the anchor). Cheap SeCo-inspired step; order preserved."""
    seen = set()
    out: List[Fact] = []
    for f in facts:
        key = _normalize(f.text)
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def build_passport(
    facts: List[Fact],
    task: str,
    role: str,
    top_k: int = 6,
    extra_keep_types: Optional[Set[str]] = None,
) -> Passport:
    if role not in ROLES:
        raise KeyError(f"unknown role: {role}")
    spec = ROLES[role]
    query = task + " " + " ".join(spec["keywords"])
    ranked = rank_facts(facts, query, allowed_types=spec["types"])

    # Only keep facts with positive query relevance (drops zero-overlap distractors
    # like a $65 concert in the budget passport), then take the top_k.
    # NOTE: sentence-level atomization can still lump a multi-topic line (e.g. a
    # digest sentence containing "free"). Finer fact subtypes (e.g. budget_limit vs
    # expense_receipt) to clean passports further are DEFERRED to M3/M4.
    ranked_pos = [(s, f) for s, f in ranked if s > 0]
    chosen: List[Fact] = [f for _, f in ranked_pos[:top_k]]
    chosen_ids = {f.fact_id for f in chosen}
    chosen_types = {f.type for f in chosen}

    # Exact-span guard: ensure AT LEAST ONE fact of each critical type is present.
    # If the passport already has one, do NOT add a second -- that would re-admit a
    # lower-relevance distractor of the same type (e.g. a $65 concert in the budget
    # passport when the $40 constraint is already present).
    # `extra_keep_types` are types LEARNED by the verifier (ACON-style guidelines).
    keep_types = set(CRITICAL_TYPES.get(role, set()))
    if extra_keep_types:
        keep_types |= set(extra_keep_types)
    for ctype in keep_types:
        if ctype in chosen_types:
            continue
        for _, f in ranked:
            if f.type == ctype:
                chosen.append(f)
                chosen_ids.add(f.fact_id)
                chosen_types.add(ctype)
                break

    chosen = dedup_facts(chosen)
    passport = Passport(task=task, for_agent=f"{role}_agent")
    passport.facts = [f.fact_id for f in chosen]
    # provenance: unique source items, order-preserved
    seen_src: set = set()
    for f in chosen:
        if f.source_ref and f.source_ref not in seen_src:
            seen_src.add(f.source_ref)
            passport.source_receipts.append(f.source_ref)
    return passport


def render_passport(passport: Passport, facts_by_id: Dict[str, Fact]) -> str:
    """The exact string sent to the downstream agent. Materialises fact TEXT from
    the store via the passport's fact IDs (refs). Never emits raw IDs."""
    hard: List[str] = []
    risk: List[str] = []
    other: List[str] = []
    for fid in passport.facts:
        fact = facts_by_id.get(fid)
        if fact is None:
            continue
        span = fact.exact_span or fact.text   # verbatim source span (never a paraphrase)
        if fact.type in _HARD:
            hard.append(span)
        elif fact.type in _RISK:
            risk.append(span)
        else:
            other.append(span)

    lines = [f"# CONTEXT PASSPORT for {passport.for_agent}", f"TASK: {passport.task}"]
    if hard:
        lines.append("HARD CONSTRAINTS:")
        lines.extend(f"- {t}" for t in hard)
    if risk:
        lines.append("RISK FLAGS:")
        lines.extend(f"- {t}" for t in risk)
    if other:
        lines.append("CONTEXT:")
        lines.extend(f"- {t}" for t in other)
    return "\n".join(lines)


def passport_tokens(passport: Passport, facts_by_id: Dict[str, Fact], backend: str = "fallback") -> int:
    return count_tokens(render_passport(passport, facts_by_id), backend=backend)

# ---------------- inlined: raven/relay.py ----------------
"""RELAY: the SECOND compression edge -- agent -> agent handoffs.

Two operations:
  * build_relay_passport(context, task, role)  -- compress a context blob into a
    recipient-aware passport for `role` (used by the user-facing agent / handlers).
  * build_relay_handoff(prior_context, latest_message, task, role) -- the real handoff:
    ALWAYS forward the latest upstream message verbatim (the "message floor") PLUS a
    recipient-aware compressed passport of the back-context. Used by the Bureau demo
    and the RELAY bench.

Pure + offline: reuses `ingest.classify_all/split_sentences` + the M1 passport machinery.
Fact IDs are globally unique per process so a multi-hop handoff never overwrites an
earlier fact in a by-id lookup.
"""


import itertools
from dataclasses import dataclass
from typing import List, Optional


_FACT_COUNTER = itertools.count()  # process-global -> IDs never collide across hops/calls


def facts_from_text(text: str, source_ref: str = "upstream") -> List[Fact]:
    """Atomize text into typed facts. Multi-label: a sentence stating N constraints
    yields N facts (same span, one per matched type). IDs are globally unique."""
    out: List[Fact] = []
    for s in split_sentences(text):
        for ftype in classify_all(s):
            out.append(Fact(fact_id=f"relay{next(_FACT_COUNTER)}", text=s, exact_span=s,
                            source_ref=source_ref, type=ftype))
    return out


def _raw_input_text(context_text: str, prior_facts: Optional[List[Fact]]) -> str:
    """The ORIGINAL input a naive forward would send. Each unique sentence is counted
    ONCE -- multi-label atomization (one sentence -> several typed facts) must never
    inflate the raw baseline."""
    parts: List[str] = []
    seen = set()
    for f in (prior_facts or []):
        if f.text not in seen:
            seen.add(f.text)
            parts.append(f.text)
    if context_text and context_text.strip():
        parts.append(context_text.strip())
    return "\n".join(parts)


@dataclass
class RelayResult:
    passport_text: str
    raw_tokens: int       # forwarding the whole context blob (original input, deduped)
    relayed_tokens: int   # the compressed recipient-aware passport
    saved_tokens: int
    saved_pct: float
    fact_ids: List[str]


def build_relay_passport(
    context_text: str,
    task: str,
    to_role: str,
    prior_facts: Optional[List[Fact]] = None,
    backend: str = "fallback",
) -> RelayResult:
    """Compress a context blob into a recipient-aware passport for `to_role`."""
    facts = list(prior_facts or []) + facts_from_text(context_text)
    raw_tokens = count_tokens(_raw_input_text(context_text, prior_facts), backend=backend)

    passport = build_passport(facts, task, to_role)
    by_id = {f.fact_id: f for f in facts}
    rendered = render_passport(passport, by_id)
    relayed_tokens = count_tokens(rendered, backend=backend)

    saved = raw_tokens - relayed_tokens
    pct = (saved / raw_tokens * 100.0) if raw_tokens else 0.0
    return RelayResult(rendered, raw_tokens, relayed_tokens, saved, pct, list(passport.facts))


@dataclass
class HandoffResult:
    handoff_text: str          # message floor + compressed back-context passport
    raw_tokens: int            # forward the full handoff (prior + message)
    last_message_tokens: int   # forward only the upstream message
    relayed_tokens: int        # RELAY: compressed prior + verbatim message
    saved_vs_full_pct: float
    message_preserved: bool


def build_relay_handoff(
    prior_context: str,
    latest_message: str,
    task: str,
    to_role: str,
    backend: str = "fallback",
) -> HandoffResult:
    """The real agent->agent handoff: forward the latest message VERBATIM (floor) +
    a recipient-aware compressed passport of the prior back-context. Guarantees the
    latest upstream output is never dropped by role filtering."""
    msg = (latest_message or "").strip()
    prior_facts = facts_from_text(prior_context, source_ref="prior")

    # raw = the ORIGINAL prior text + the message, NOT the multi-label-expanded facts.
    raw_text = (prior_context or "").strip()
    if msg:
        raw_text = (raw_text + "\n" + msg).strip()
    raw_tokens = count_tokens(raw_text, backend=backend)
    last_message_tokens = count_tokens(msg, backend=backend)

    prior_passport = build_passport(prior_facts, task, to_role)
    by_id = {f.fact_id: f for f in prior_facts}
    prior_text = render_passport(prior_passport, by_id)
    handoff_text = prior_text + (f"\n\nLATEST FROM UPSTREAM:\n{msg}" if msg else "")
    relayed_tokens = count_tokens(handoff_text, backend=backend)

    saved = (1 - relayed_tokens / raw_tokens) * 100.0 if raw_tokens else 0.0
    message_preserved = (not msg) or (msg in handoff_text)
    return HandoffResult(handoff_text, raw_tokens, last_message_tokens, relayed_tokens, saved, message_preserved)

# ---------------- inlined: raven/handlers.py ----------------
"""Pure message logic for the RAVEN uAgent (no uagents / no network imports here).

The Chat-Protocol agent (raven/fetch/raven_agent.py) is a thin wrapper: it parses a
ChatMessage's text, calls `handle_compress_request`, and sends the reply back. Keeping
the brains here means the behaviour is fully unit-testable offline.
"""


import json
import re
from typing import Dict, Tuple


_HELP = (
    "Send your memory/context to compress. Example:\n"
    "  role: budget | task: plan a friday dinner | memory: Maya is vegetarian. "
    "Keep dinners under $40. Always confirm before paying.\n"
    "(role/task/memory markers are optional and can appear anywhere; plain text is "
    "treated as memory for the 'writer' role.)"
)

_MAX_MEMORY_CHARS = 12_000  # cap pasted input so a huge blob can't block the agent loop
_SEP = " |,\t\r\n"          # marker separators to strip from captured values
# Markers are honored ONLY at an anchor -- start of the text, after a newline, or after a
# '|'/',' separator -- so prose that merely mentions "memory:" / "task:" mid-sentence
# ("just for your memory: ...") is NOT treated as a marker and is kept verbatim.
_MENTION = re.compile(r"^\s*@\S+\s*")
_ROLE = re.compile(r"(?:^|[|,])\s*role\b\s*[:=]?\s*([A-Za-z]+)", re.I | re.M)
_TASK = re.compile(r"(?:^|[|,])\s*task\s*[:=]\s*(.+?)(?=[|,]|\bmemory\s*[:=]|$)", re.I | re.M | re.S)
_MEMORY = re.compile(r"(?:^|[|,])\s*memory\s*[:=]\s*(.+)$", re.I | re.M | re.S)
_DANGLING = re.compile(r"(?im)(?:^|[|,])\s*(?:role|task|memory)\s*[:=]\s*$")  # a marker with no value left


def _parse(text: str) -> Tuple[str, str, str]:
    """Return (role, task, memory). Robust to how real chats arrive:
    - JSON {role,task,memory};
    - a leading @agent mention (ASI:One/Agentverse prepend it) is stripped;
    - role/task/memory markers anywhere, ':'/'=', single- or multi-line, '|'/',' separated;
    - plain text -> the whole thing is memory (role defaults to writer).
    An invalid `role:` value is left in the memory rather than excised (so prose that merely
    says 'my role: organizer ...' isn't corrupted)."""
    text = (text or "").strip()
    try:
        d = json.loads(text)
        if isinstance(d, dict):
            return (str(d.get("role") or "writer"), str(d.get("task") or "general task"),
                    str(d.get("memory") or ""))
    except (json.JSONDecodeError, ValueError):
        pass

    text = _MENTION.sub("", text)  # drop a leading "@agent1q..." mention
    role, task = "writer", "general task"

    rm = _ROLE.search(text)
    if rm and rm.group(1).lower() in ROLES:  # only consume a VALID role marker
        role = rm.group(1).lower()
        text = text[:rm.start()] + " " + text[rm.end():]

    tm = _TASK.search(text)
    if tm:
        cand = tm.group(1).strip(_SEP)
        if cand:
            task = cand
        text = text[:tm.start()] + " " + text[tm.end():]

    mm = _MEMORY.search(text)
    if mm:
        leftover = text[:mm.start()].strip(_SEP)
        memval = mm.group(1).strip(_SEP)
        memory = (leftover + " " + memval).strip() if leftover else memval
    else:
        memory = _DANGLING.sub("", text).strip(_SEP)  # drop a value-less trailing 'memory:'
    return role, task, " ".join(memory.split())


def handle_compress_request(text: str, backend: str = "fallback") -> Tuple[str, Dict]:
    """Core of the RAVEN agent: compress a memory blob into a recipient-aware passport
    for the requested role. Returns (reply_text, stats)."""
    role, task, memory = _parse(text)
    if role not in ROLES:
        role = "writer"
    memory = memory[:_MAX_MEMORY_CHARS]  # bound work so a huge paste can't stall the agent
    if not memory.strip():
        return _HELP, {"ok": False, "reason": "no memory supplied"}

    res = build_relay_passport(memory, task, role, backend=backend)
    if not res.fact_ids:
        return (
            f"No facts in your memory were relevant to the '{role}' agent. "
            f"Try a different role, or include {role}-relevant details.",
            {"ok": True, "role": role, "facts": 0, "raw_tokens": res.raw_tokens,
             "relayed_tokens": 0, "saved_tokens": 0, "saved_pct": 0.0},
        )
    if res.saved_tokens > 0:
        tokens_line = f"{res.relayed_tokens} tokens, saved {res.saved_pct:.0f}% vs raw {res.raw_tokens}"
    else:
        tokens_line = (
            f"{res.relayed_tokens} tokens (raw was {res.raw_tokens}; input too small "
            f"for net compression -- the passport adds structure)"
        )
    reply = (
        f"RAVEN context passport for '{role}' (task: {task})\n"
        f"Tokens: {tokens_line}\n\n"
        f"{res.passport_text}"
    )
    stats = {
        "ok": True,
        "role": role,
        "facts": len(res.fact_ids),
        "raw_tokens": res.raw_tokens,
        "relayed_tokens": res.relayed_tokens,
        "saved_tokens": res.saved_tokens,
        "saved_pct": round(res.saved_pct, 1),
    }
    return reply, stats


# ============================ Agentverse Chat-Protocol uAgent ============================
from datetime import datetime, timezone  # noqa: E402
from uuid import uuid4  # noqa: E402

from uagents import Agent, Context, Protocol  # noqa: E402
from uagents_core.contrib.protocols.chat import (  # noqa: E402
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

agent = Agent()  # Agentverse hosting provides the identity + runtime

chat_proto = Protocol(spec=chat_protocol_spec)


def _text_of(msg: ChatMessage) -> str:
    return "".join(i.text for i in msg.content if isinstance(i, TextContent))


@chat_proto.on_message(ChatMessage)
async def _on_chat(ctx: Context, sender: str, msg: ChatMessage):
    try:  # a failed ack must not skip the reply
        await ctx.send(sender, ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    except Exception as exc:  # noqa: BLE001
        ctx.logger.error(f"ack failed: {exc}")
    try:
        reply, stats = handle_compress_request(_text_of(msg))
        ctx.logger.info(f"RAVEN compress -> {stats}")
    except Exception as exc:  # noqa: BLE001
        ctx.logger.error(f"RAVEN error: {exc}")
        reply = "Sorry -- I couldn't compress that. Try:  role: budget | memory: <your notes>"
    await ctx.send(sender, ChatMessage(
        timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
        content=[TextContent(type="text", text=reply), EndSessionContent(type="end-session")]))


@chat_proto.on_message(ChatAcknowledgement)
async def _on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat_proto, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
