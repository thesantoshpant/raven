# RAVEN — Verified Context Passports for the Agentic Web

Recipient-aware, decision-preserving context compression for multi-agent systems.
Instead of sending an agent your whole memory (expensive + over-exposed) or a
naive summary (cheap but drops the facts that matter), RAVEN gives each agent a
tiny **context passport**: only the facts that agent's role needs — at the front
door (user memory → first agent) and at every agent-to-agent handoff.

## Milestone 1: the core engine + the token gate
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
- **Apples-to-apples is per-send and the N-send total.** Per send, a RAVEN passport is ~93% smaller than the full memory; across the 4-agent workflow, RAVEN's total is ~93% below `raw_broadcast` (full memory to every agent). Even vs `raw_once` (an *optimistic* single shared full payload), RAVEN's total is ~71.5% lower. (Current corpus: 38 items / 127 facts; numbers from `bench/run_gate.py`, fallback tokenizer.)
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
| **RAVEN (recipient-aware)** | **5/5** | **1022** |

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
  adds **0 tokens** — the recipient-aware guard already keeps every action-critical fact, so it
  has nothing to repair (first-run = recurring = 1022 tok). It only fires on a genuinely missing
  type (see `tests/test_verifier.py`).
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
  | **RAVEN RELAY** | 889 | **3/3 hops** |

  RELAY costs a little more than last-message-only but **preserves the standing back-context
  constraints last-message silently drops**, at ~90% below the full-transcript broadcast.
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
gate, M2, and the **110+-test** offline suite stay stdlib + offline (no `uagents`/`fastapi`/`markitdown`/network; one fallback test lazily imports the `redis` client and makes a single refused loopback connect — no external network).

## Milestone 4 (done): the live demo UI
A two-server app — a FastAPI backend (`raven/web/`) over the M1–M3 engine + a Next.js
dashboard (`frontend/`):

- **Dashboard** — three panes: the messy **user memory** (the 5 gold facts highlighted),
  the **agents + their recipient-aware passports** (click an agent to see what it sees /
  is denied), and a **token meter + live decision benchmark** ("Run benchmark" → raw 5/5,
  generic 4/5 ✗confirm, RAVEN 5/5).
- **RELAY tab** — the agent→agent handoff table (full / last-message / RAVEN) + the
  back-context preservation check (3/3 vs 1/3).
- **Compress-anything tab** — paste a memory blob, pick a role, get its passport live.

Only `/api/benchmark` calls the real API (disk-cached → instant once warmed); every live
call has loading + error states. The backend deps (`fastapi`, `uvicorn`) are optional
(`requirements-web.txt`); `raven/web/services.py` is tested offline with `FakeLLM` and the
test suite never imports fastapi.

```
.venv\Scripts\python -m pip install -r requirements-web.txt
.venv\Scripts\python -m uvicorn raven.web.api:app --port 8000     # backend :8000
cd frontend && npm install && npm run dev                          # UI :3000  -> open it
```
Warm the cache first (click "Run benchmark" once) so the stage run is instant. `/api/benchmark`
is server-side cooldown'd to avoid accidental live spend. **Security:** Next 14.2.15 has known
advisories (incl. a critical) — this is **local-demo-only, risk accepted; do NOT deploy it
publicly as-is.** Bump Next after the event. If port 3000 is busy, run `npm run dev -- -p 3000`
(the backend's CORS allows 3000/3001).

## Milestone 5 (done): document ingestion
Upload a PDF / docx / html / md (MarkItDown → markdown → facts) and it becomes agent memory
with passports recomputed live (`POST /api/ingest`, the upload control in the Memory pane;
`raven/ingest_docs.py`). `markitdown` is optional (`requirements-docs.txt`); `.md`/`.txt`
work without it, and the test suite never imports it.

## Use it inside Claude (MCP)
RAVEN also ships as a **Model Context Protocol** server, so the same engine works as a tool inside
**Claude Desktop / Claude Code / Cursor** — no API key, no LLM calls (the host model is the LLM;
RAVEN returns a compressed passport). Tools: `compress_memory`, `relay_handoff`, `list_roles`.
```
pip install -r requirements-mcp.txt
python -m raven.mcp.smoke        # verify in-process (lists tools + a real call)
python -m raven.mcp.server       # stdio server for an MCP client
```
Config + examples: `raven/mcp/README.md`. The MCP server is the sole `mcp` importer
(`raven/mcp/server.py`); the pure logic (`raven/mcp/_logic.py`) is offline-tested and never
imports the SDK.

## What's next (post-hackathon)
- A hosted Agentverse deployment; embeddings retrieval; more scenarios for a quality *rate*
  (not just an existence proof); KV-cache-level relay; bump Next.js for public hosting.
