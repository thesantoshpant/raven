# RAVEN — Verified Context Passports for the Agentic Web

Recipient-aware, decision-preserving context compression for multi-agent systems.
Instead of sending an agent your whole memory (expensive + over-exposed) or a
naive summary (cheap but drops the facts that matter), RAVEN gives each agent a
tiny **context passport**: only the facts that agent's role needs — at the front
door (user memory → first agent) and at every agent-to-agent handoff.

## Milestone 1 (this repo so far): the core engine + the token gate
M1 proves **context-payload (input-token) reduction** — recipient-aware selection
cuts query-time tokens by ≥50% vs a raw broadcast — measured with a tokenizer, no
LLM required. (Decision-preservation / constraint satisfaction is Milestone 2.)

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
- **Apples-to-apples is per-send and the N-send total.** Per send, a RAVEN passport is ~87% smaller than the full memory; across the 4-agent workflow, RAVEN's total is ~87% below `raw_broadcast` (full memory to every agent). Even vs `raw_once` (an *optimistic* single shared full payload), RAVEN's total is ~48% lower.
- **At equal budget, RAVEN ties the fair baseline on tokens** (`generic_factstore_unaware` ≈ RAVEN). That's expected: the token win is shared by *any* equal-budget fact-store selection. RAVEN's real differentiator is **recipient-aware decision quality at that budget**, which **M2** measures — M1 does not claim it.
- The fallback tokenizer is an approximation; the gate is **ratio-based** and uses one counter across all conditions. Install `tiktoken` for exact counts (ratios stay close).
- This is a **single hand-authored scenario**; M1's token saving is **budget-driven (scenario-independent)**. Generality needs a second scenario + the M2 quality result.

## Roadmap
- **M2** decision preservation: Claude agents + deterministic gold-constraint scoring + the verifier loop + ACON-style guideline learning.
- **M3** multi-agent + Fetch (Agentverse/ASI:One) + Redis fact store.
- **M4** demo UI (three-pane split-screen, token/$ meters, privacy view).
- **M5** MarkItDown PDF→MD ingestion + polish.
