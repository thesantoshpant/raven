# RAVEN — Verified Context Passports for the Agentic Web

![tests](https://img.shields.io/badge/tests-116%20passing-brightgreen)
![python](https://img.shields.io/badge/python-3.10%2B-blue)
![MCP](https://img.shields.io/badge/MCP-ready-7c3aed)
![Fetch.ai](https://img.shields.io/badge/Fetch.ai-Agentverse-000)
![license](https://img.shields.io/badge/license-MIT-green)

**RAVEN gives each AI agent a tiny, recipient-aware "context passport" instead of your whole memory — ~80–93% fewer context tokens, with every standing rule guaranteed to survive.**

Most agent stacks make agents "smart" by dumping the **entire** user memory into **every** model call and **every** agent in a multi-agent system. It's expensive, slow, and unsafe: hand a capable model 1,700 tokens of notes and it will confidently recommend an *Italian restaurant for a vegetarian* — because the dietary rule was buried in the middle and got lost.

The bottleneck of the agentic web isn't model intelligence — it's **context logistics**: deciding *who needs to know what*. You don't brief a chef and an accountant with the same memo. RAVEN is the layer that gives each agent only the slice it needs, with the non-negotiable rules force-kept.

> *Same memory, two agents:* the **budget** agent gets `under $40` + `confirm before paying`; the **calendar** agent gets only `free Friday after 7pm`. Neither sees the other's facts. That's recipient-aware, least-privilege context — by construction.

---

## Try it 3 ways

### 1. Inside Claude (MCP) — one line, no clone
Add this to your Claude Desktop config (`%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/` on macOS), then restart Claude:
```json
{
  "mcpServers": {
    "raven": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/thesantoshpant/raven", "raven-mcp"]
    }
  }
}
```
Then ask Claude: *"Use raven to compress this for the budget agent: Maya is vegetarian, keep dinner under $40, free Friday after 7pm, always confirm before paying."*
Tools exposed: `compress_memory`, `relay_handoff`, `list_roles`. No API key — RAVEN does pure, deterministic compression; the host model is the LLM. (Details: [`raven/mcp/README.md`](raven/mcp/README.md).)

### 2. On Fetch.ai Agentverse — a live uAgent
RAVEN runs as a Chat-Protocol uAgent discoverable from ASI:One.
- **Hosted (24/7):** paste [`raven/fetch/raven_hosted_agent.py`](raven/fetch/raven_hosted_agent.py) (a single self-contained file) into an Agentverse *Blank Agent* and press Start.
- **Local (mailbox):** `pip install -r requirements-fetch.txt`, set `RAVEN_AGENT_SEED`, run `python raven/fetch/raven_agent.py`, connect the mailbox.

Then chat it: `role: budget | memory: Maya is vegetarian. Keep dinner under $40. Confirm before paying.`

### 3. Locally — the visual demo dashboard
A side-by-side **A/B** (same prompt with full memory vs. RAVEN's passport) showing the model's **real input-token usage** and an animated pipeline of exactly what RAVEN did.
```bash
git clone https://github.com/thesantoshpant/raven && cd raven
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements-web.txt
.venv/Scripts/python -m uvicorn raven.web.api:app --port 8000      # backend
cd frontend && npm install && npm run dev                          # UI -> http://localhost:3000
```
> ⚠️ The dashboard's live A/B calls the Claude API (needs `ANTHROPIC_API_KEY`) and Next 14 has known advisories — it's **local-demo-only; don't deploy as-is**. The engine, gate, and tests need none of this.

---

## What it does

RAVEN compresses at the **two edges** where context explodes:

1. **Passport (user memory → agent).** Atomize memory into typed facts (dietary, budget, permission, availability, location, preference…), retrieve what *this* role needs, **guard** the standing rules so they're never dropped, dedup, and render a tiny passport.
2. **RELAY (agent → agent).** On handoffs, forward the latest message verbatim + a compressed back-context passport instead of the whole growing transcript — **~90% smaller per hop**, while standing constraints survive **3/3 hops** (naive last-message forwarding drops them).

## Results (reproducible from a clean checkout)

| Measure | Result |
|---|---|
| **Context-payload reduction** (vs broadcasting full memory to every agent) | **92.9%** |
| **A/B, real Claude input tokens** (one prompt) | **1,783 → 317 (~82%)** |
| **Decision benchmark** at an *equal* token budget | **RAVEN 5/5** vs generic role-unaware **4/5** (drops "confirm before paying") |
| **RELAY** handoff vs full transcript | **8,560 → 889 (~90%)**, constraints kept 3/3 hops |
| **Offline test suite** | **116 passing** (stdlib, no network) |

*Corpus: 38 memory items / 127 facts. Model: Claude Haiku 4.5, temperature 0, disk-cached. Numbers from `bench/run_gate.py`, `bench/run_m2.py`, `bench/run_relay.py`.*

**The honest headline:** at an *equal* token budget RAVEN ties a generic fact-store baseline on raw token count — that part isn't the moat. The moat is **decision quality and constraint-safety at that budget**: the guard routes "confirm before paying" to the budget agent even though the request never lexically mentions it, so RAVEN scores 5/5 where the role-unaware blob drops to 4/5.

## How it works

Deterministic, **stdlib-first**, torch-free — so every claim is explainable and reproducible:
```
raw memory → split into atomic typed facts → BM25 retrieval (query-aware)
           → recipient-aware selection (keep the role's types)
           → critical-fact GUARD (force-keep standing-rule types, even at score 0)
           → dedup → render passport → count tokens
```
The **guard** is the key idea: a constraint can be lexically *irrelevant* to a query ("vegetarian" vs "where to eat") yet decision-critical. Pure relevance compression drops it — exactly the "lost in the middle" failure. The guard force-keeps standing-rule *types*, so the loss only ever lands on low-relevance facts, never a rule. Every kept fact carries a reason (`guard` vs `relevant`), so the output is fully auditable — no black-box compressor.

## Architecture

One pure engine, three surfaces:
- **Engine** (`raven/`): a custom BM25 retriever + typed-fact compression + the critical guard + an optional ACON-style verifier. Pure stdlib; no ML downloads.
- **MCP server** (`raven/mcp/`): the engine as a tool for Claude Desktop / Code / Cursor.
- **Fetch.ai uAgent** (`raven/fetch/`): Chat-Protocol agent for Agentverse / ASI:One + a single-file hosted build.
- **Web** (`raven/web/` + `frontend/`): FastAPI + Next.js dashboard with the live A/B and animated pipeline.

**Engineering discipline:** 116 offline tests with a strict isolation invariant — the test suite imports no `uagents`/`fastapi`/`markitdown`/`mcp`/network; the heavy transports are the *sole* importers of their SDKs, and the pure logic is tested separately.

### Research grounding (lightweight, explainable variants)
| Implemented | Grounded in |
|---|---|
| Query-aware extractive selection (custom BM25, not a learned classifier) | LongLLMLingua |
| Inter-agent comms pruning (RELAY) | AgentPrune / "Cut the Crap" |
| Guideline learning without fine-tuning (the verifier) | ACON |
| Constraint-compliance vs. accuracy separation (deterministic gold scoring) | CDCT |
| Near-duplicate anchoring (dedup) | SeCo |

Deliberately **not** used: a learned token classifier (LLMLingua-2) or KV-cache compression (Cache-to-Cache) — extractive + deterministic is *why* RAVEN can **prove** decision-preservation (it can point at the exact kept fact and its reason).

## Honest limitations
- **Compression is lossy by definition** — RAVEN bounds the loss to low-relevance facts and never to standing rules (the guard).
- **BM25 has vocabulary-mismatch failures**; mitigated by the recipient model + guard. Learned relevance is an optional future upgrade behind the same interface.
- **Single hand-authored scenario** for the decision benchmark — an *existence proof* of the recipient-aware win, not a broad rate. More scenarios + a stronger (embedding) baseline are future work.
- **ASI:One auto-discovery is best-effort** (the host model routes by description).

## Repo layout
```
raven/raven/      engine: ingest, retrieve, compress, relay, roles, score, verifier, tokens, schemas
raven/raven/mcp/  MCP server (compress_memory / relay_handoff / list_roles)
raven/raven/fetch/  Fetch.ai uAgent + single-file hosted build + Bureau demo
raven/raven/web/  FastAPI backend over the engine
frontend/         Next.js dashboard (A/B, animated pipeline, token meter)
bench/            run_gate.py · run_m2.py · run_relay.py
tests/            116-test offline suite
```

## What's next
Publish the MCP server to PyPI (`uvx raven-mcp`); an LLM API proxy (one-line `base_url` swap); learned relevance as an optional upgrade; cross-agent passport caching; LangChain / CrewAI adapters.

## License
MIT — see [LICENSE](LICENSE).
