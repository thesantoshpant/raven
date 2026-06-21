# RAVEN — Verified Context Passports for the Agentic Web

Recipient-aware, decision-preserving context compression for multi-agent systems.
Instead of sending an agent your whole memory (expensive + over-exposed) or a
naive summary (cheap but drops the facts that matter), RAVEN gives each agent a
tiny **context passport**: only the facts that agent's role needs — at the front
door (user memory → first agent) and at every agent-to-agent handoff.

## Milestone 1 (this repo so far): the core engine + the token gate
M1 proves **context-payload (input-token) reduction** — recipient-aware selection
cuts query-time tokens ~93% vs a raw broadcast (gate threshold: ≥50%) — measured
with a tokenizer, no LLM required. (Decision-preservation / constraint satisfaction
is Milestone 2.)

### Run it
```
cd raven
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt   # just pytest; core is stdlib
.venv\Scripts\python -m pytest -q
.venv\Scripts\python bench\run_gate.py                     # prints the token table + GATE: PASS
```
The core and tests run on the **stdlib BM25 path with zero downloads**. `tiktoken`
(exact token counts) and `fastembed` (ONNX embeddings) are optional upgrades; the
gate never depends on them. `python bench\smoke_fastembed.py` exercises fastembed
if installed.

## Benchmark integrity (built in from day one)
- Four baselines incl. a **fair** one: `generic_factstore_unaware` uses the *same*
  fact store as RAVEN, role-unaware, at RAVEN's **exact** token budget.
- Two raw baselines: `raw_once` (honesty) and `raw_broadcast` (the multi-agent claim).
- Token counts are taken from the **rendered prompt text** (materialized fact text),
  never from fact IDs — enforced by `tests/test_passport_counts_actual_prompt_tokens.py`.
- Realistic corpus, **real** reported numbers, ratio-based gate.

## Layout
```
raven/        core engine (schemas, ingest, store, retrieve, compress, baselines, score, tokens, roles)
data/         synthetic messy memory + the task with JSON gold-constraint specs
bench/        run_gate.py (the gate), smoke_fastembed.py (optional)
tests/        pytest suite (stdlib path, offline)
```

## Honest notes / limitations (M1)
- **Apples-to-apples is per-send and the N-send total.** Per send, a RAVEN passport is ~93% smaller than the full memory; across the 4-agent workflow, RAVEN's total is ~93% below `raw_broadcast` (full memory to every agent). Even vs `raw_once` (an *optimistic* single shared full payload), RAVEN's total is ~74.5% lower. (Current corpus: 38 items / 127 facts; numbers from `bench/run_gate.py`, fallback tokenizer.)
- **At equal budget, RAVEN ties the fair baseline on tokens** (`generic_factstore_unaware` ≈ RAVEN). That's expected: the token win is shared by *any* equal-budget fact-store selection. RAVEN's real differentiator is **recipient-aware decision quality at that budget**, which **M2** measures — M1 does not claim it.
- The fallback tokenizer is an approximation; the gate is **ratio-based** and uses one counter across all conditions. Install `tiktoken` for exact counts (ratios stay close).
- This is a **single (now larger) hand-authored scenario**; M1's token saving is **budget-driven (scenario-independent)**. Generality needs a second scenario + the M2 quality result.
- Passport selection **drops zero-relevance facts** and **force-keeps the critical constraint types**. Sentence-level atomization can still lump a multi-topic line; finer fact subtypes (`budget_limit` vs `expense_receipt`) and multi-label classification **landed in M3**.

## Milestone 2 (done): decision preservation
Role agents (real Claude, temp 0, cached) plan the dinner under three context conditions;
the final plan is scored **deterministically** (structured-first) on the gold constraints.
Run with `.venv\Scripts\python bench\run_m2.py` (uses `ANTHROPIC_API_KEY`).

| condition | constraints | recurring agent tokens |
|---|---|---|
| raw (full memory to each agent) | 5/5 | 8308 |
| generic (role-unaware, equal budget) | 4/5 (misses *confirm before paying*) | 960 |
| **RAVEN (recipient-aware)** | **5/5** | **1030** |

RAVEN matches raw's 5/5 at **~88% lower recurring cost**; generic, at the *same* per-agent
budget, drops a constraint. The win is RAVEN's **recipient-aware guard** (learnable role
priors — not a per-scenario answer key) routing the standing "confirm before paying" rule to
the budget agent — a rule the vague request never lexically surfaces, so the role-unaware blob
misses it.

Honest notes:
- This is an **existence proof**, not broad proof. The measured gap is **exactly one
  constraint** — the standing "confirm before paying" rule, which has ~zero lexical overlap
  with the vague request, so task-only (role-unaware) ranking buries it while RAVEN routes it
  to the budget agent. A stronger role-unaware baseline (embeddings) and more scenarios are
  future work.
- The **verifier is an OPTIONAL one-time safety net** (defense-in-depth). In this scenario it
  changed no decision (the guard already kept the criticals) and amortizes vs raw by request #2.
  Reported separately; RAVEN's first run including the verifier is 9322 tok, recurring 1030 tok/task.
- Tests stay **offline** (`FakeLLM`); only `bench/run_m2.py` calls the real API. The response
  cache (`.llmcache/`) is git-ignored (it holds private-corpus responses).

## Milestone 3 (done): the agentic-web layer — RELAY + Fetch + Redis
RAVEN now runs as a real uAgent and compresses agent→agent handoffs.

- **RELAY (the second edge).** At each handoff, forward the upstream message verbatim + a
  recipient-aware compressed passport of the back-context, instead of the whole growing
  transcript. `bench/run_relay.py` compares three strategies (single scripted scenario, offline):

  | strategy | handoff tokens | keeps early back-context constraint |
  |---|---|---|
  | full_transcript (naive) | 8560 | yes, but huge |
  | last_message only | 183 | 1/3 hops (drops standing rules) |
  | **RAVEN RELAY** | 689 | **3/3 hops** |

  RELAY costs a little more than last-message-only but **preserves the standing back-context
  constraints last-message silently drops**, at ~92% below the full-transcript broadcast.
  Savings are scale-driven (a passport has ~25–30 tok of fixed structure).
- **Fetch.ai (layered).** `raven/fetch/raven_agent.py` is a Chat-Protocol uAgent
  (mailbox → Agentverse → ASI:One discovery); `raven/fetch/bureau_demo.py` runs a local
  two-agent uAgents Bureau with RAVEN RELAY on the wire — no Agentverse account; use
  `--once` for a bounded run that exits after the decision (uAgents still binds a local
  port and logs like a server, so it is not a pure offline function).
- **Redis.** `make_fact_store()` returns a `RedisFactStore` when `RAVEN_REDIS_URL` is set and
  reachable, else falls back to in-memory (default) — never breaks if Redis/Docker is absent.
- **Cleaner passports.** the `budget` type is split into `budget_limit` (caps) vs
  `expense_receipt` (money already spent), so receipts/tickets no longer leak into the budget
  passport (a cap that mentions spending, e.g. "budget is $40 but I spent $60", stays a cap).

The Fetch layer (`uagents`, `redis`) is **optional** (`requirements-fetch.txt`); the core, the
gate, M2, and the **74-test** suite stay stdlib + offline (no `uagents`/`redis`/network).

## Roadmap
- **M4** demo UI (three-pane split-screen, token/$ meters, privacy view).
- **M5** MarkItDown PDF→MD ingestion + polish.
