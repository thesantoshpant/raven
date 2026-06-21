"""M1 gate: prove RAVEN cuts the context payload (input tokens) vs a raw broadcast,
with a CONSISTENT, defensible table. NO LLM needed — measured with a tokenizer.

Accounting model = "total input tokens delivered across all N agents":
  - RAVEN            : N different tailored passports (sum).
  - raw_broadcast    : full memory delivered to each of N agents (raw_once x N).
  - generic_*        : ONE role-unaware shared payload, built at the per-agent
                       budget (raven_total // N), delivered to all N agents (x N).
                       => same TOTAL budget as RAVEN, charged for the same N sends.
  - raw_once         : full memory delivered ONCE (optimistic single-shared ref).

Honesty note baked into the output: at equal budget RAVEN ~= generic_factstore on
TOKENS; RAVEN's differentiator is recipient-aware DECISION quality, measured in M2.

Run from anywhere:  python bench/run_gate.py
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from raven.baselines import (  # noqa: E402
    generic_factstore_unaware,
    generic_truncation,
    raw_once,
)
from raven.compress import build_passport, passport_tokens  # noqa: E402
from raven.ingest import ingest_corpus, load_corpus  # noqa: E402
from raven.store import InMemoryFactStore  # noqa: E402
from raven.tokens import backend_name  # noqa: E402

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
GATE_RATIO = 0.50  # RAVEN total must be <= 50% of raw_broadcast


def run(backend: str = "auto"):
    corpus = load_corpus(os.path.join(DATA, "corpus_friday_dinner.json"))
    with open(os.path.join(DATA, "task_friday_dinner.json"), encoding="utf-8") as fh:
        task = json.load(fh)

    request = task["request"]
    roles = task["roles"]
    n = len(roles)

    facts = ingest_corpus(corpus)
    store = InMemoryFactStore()
    store.add_many(facts)
    by_id = store.by_id()

    # --- RAVEN: one recipient-aware passport per agent (N tailored payloads) ---
    per_role = []
    raven_total = 0
    for role in roles:
        p = build_passport(facts, request, role)
        t = passport_tokens(p, by_id, backend=backend)
        per_role.append((role, len(p.facts), t))
        raven_total += t
    raven_per_send = raven_total / n if n else 0

    # --- Baselines, charged for the SAME N sends, at the SAME total budget ---
    per_agent_budget = max(1, raven_total // n)
    _, raw_once_tok = raw_once(corpus, backend=backend)
    raw_broadcast_tok = raw_once_tok * n
    _, gtrunc_single = generic_truncation(corpus, per_agent_budget, backend=backend)
    _, gfs_single = generic_factstore_unaware(facts, request, per_agent_budget, backend=backend)
    gtrunc_total = gtrunc_single * n
    gfs_total = gfs_single * n

    used_backend = backend_name() if backend == "auto" else backend

    # --- Report ---
    print(f"Token backend: {used_backend}")
    print(f"Corpus items: {len(corpus)} | atomic facts: {len(facts)} | agents: {n}\n")

    print("PER SEND (one agent):")
    print(f"  full memory (raw)          {raw_once_tok:>6}")
    print(f"  RAVEN passport (avg)       {raven_per_send:>6.0f}   "
          f"({(1 - raven_per_send / raw_once_tok) * 100:.1f}% smaller)" if raw_once_tok else "")

    print("\nACROSS THE WORKFLOW (total input tokens delivered to all agents):")
    print(f"  {'condition':<30}{'tokens':>8}{'vs raw_broadcast':>20}")
    print("  " + "-" * 56)

    def row(name, tok):
        pct = (1 - tok / raw_broadcast_tok) * 100 if raw_broadcast_tok else 0.0
        print(f"  {name:<30}{tok:>8}{pct:>19.1f}%")

    row("raw_broadcast (full x N)", raw_broadcast_tok)
    row("generic_truncation (x N)", gtrunc_total)
    row("generic_factstore_unaware (xN)", gfs_total)
    row("RAVEN (N tailored passports)", raven_total)
    print(f"  {'[ref] raw_once (full x1, optim.)':<30}{raw_once_tok:>8}{'(single-shared)':>19}")
    print("  " + "-" * 56)

    print("\n  RAVEN per-role passports:")
    for role, nf, tok in per_role:
        print(f"    {role:<14} facts={nf:<3} tokens={tok}")

    ratio = raven_total / raw_broadcast_tok if raw_broadcast_tok else 1.0
    red_bc = (1 - ratio) * 100
    red_once = (1 - raven_total / raw_once_tok) * 100 if raw_once_tok else 0.0
    passed = ratio <= GATE_RATIO

    print(f"\nRAVEN context-payload reduction: {red_bc:.1f}% vs raw_broadcast "
          f"(naive: full memory to every agent).")
    print(f"  Even vs raw_once (optimistic single shared full payload), RAVEN's "
          f"total is {red_once:.1f}% lower.")
    print(f"  At equal budget RAVEN ({raven_total}) ~= generic_factstore_unaware "
          f"({gfs_total}) on TOKENS by design;")
    print(f"  the token win is shared by any equal-budget fact-store selection. "
          f"RAVEN's edge is recipient-aware")
    print(f"  DECISION quality at that budget -> measured in M2 (not here).")
    print(f"NOTE: M1 measures context-payload (input tokens) only; full cost is M2. "
          f"Single scenario; savings are budget-driven.")
    print(f"\nGATE (RAVEN <= {int(GATE_RATIO * 100)}% of raw_broadcast): "
          f"{'PASS' if passed else 'FAIL'} (ratio={ratio:.3f})")
    return passed


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
