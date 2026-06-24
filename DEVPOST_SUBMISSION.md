# RAVEN — DevPost Submission

## Project name (≤60 chars)
`RAVEN: Verified Context Passports for the Agentic Web`
<sub>(53 characters)</sub>

## Elevator pitch (≤200 chars)
`RAVEN gives every AI agent a tiny, recipient-aware context passport instead of your whole memory — 80-90% fewer tokens, every standing rule preserved. Live as a Fetch.ai agent + a Claude MCP tool.`
<sub>(196 characters)</sub>

---

# Project Story

## Inspiration

Every agent demo we tried had the same dirty secret: to make an agent "smart," people dump the **entire** user memory into **every** model call, and into **every** agent in a multi-agent system. It's expensive, it's slow, and — worse — it's *unsafe*. We watched a perfectly capable model, handed 1,700 tokens of someone's notes, confidently recommend an **Italian restaurant for a vegetarian** because the dietary rule was buried in the middle and got lost.

That's the real problem we wanted to reframe. The bottleneck of the agentic web isn't model intelligence — it's **context logistics**: deciding *who needs to know what*. Humans don't brief a chef and an accountant with the same memo. So why do we hand every agent the same firehose?

RAVEN's bet: the unit of the agentic web shouldn't be "the whole memory," it should be a **context passport** — the minimal, recipient-aware slice each agent needs, with the non-negotiable rules guaranteed to survive.

## What it does

RAVEN is a **recipient-aware, decision-preserving context compressor** that sits *in front of* the expensive LLM agents. It compresses at the two edges where context explodes:

1. **Passport (user-memory → agent).** It atomizes your memory into typed facts (dietary, budget, permission, availability, location, preference…), retrieves what's relevant to *this* agent's role and task, **guards** the standing rules so they can never be dropped, dedupes, and renders a tiny passport. The calendar agent never even *sees* your budget or allergies — least-privilege by construction.

2. **RELAY (agent → agent).** On handoffs, agents forward a compressed back-context passport instead of the entire growing transcript — **~90% smaller per hop**, while the standing constraints survive **3/3 hops** (naive last-message forwarding drops them).

It runs on **three surfaces from one engine**:
- **Fetch.ai Agentverse** — a real uAgent, reachable over the Chat Protocol and discoverable via ASI:One.
- **Inside Claude (MCP)** — the same engine ships as a **Model Context Protocol server**, so RAVEN is a tool inside Claude Desktop / Claude Code / Cursor (`compress_memory`, `relay_handoff`, `list_roles`) — no API key, no LLM calls.
- **A web dashboard** — a side-by-side **A/B** (same prompt with full memory vs. RAVEN's passport) showing the **real Claude input-token counts** and an animated pipeline of exactly what RAVEN did (atomize → rank → guard → drop → passport).

**Measured results (reproducible):**
- **A/B, live Claude usage:** 1,783 → 317 input tokens (**~82%**), and across vague, adversarial, and gibberish prompts, **82–90% fewer tokens with every standing rule preserved** — including refusing an adversarial "ignore my rules and charge my card" prompt.
- **Decision benchmark:** at an *equal* token budget, RAVEN scores **5/5** on gold constraints vs. **4/5** for generic role-unaware compression (which silently drops "confirm before paying").
- **Context-payload reduction:** **92.9%** vs. broadcasting full memory to every agent.

The honest headline isn't just "fewer tokens" — at equal budget, tokens tie. The moat is **decision quality and constraint-safety at that budget.**

## How we built it

A **stdlib-first** Python 3.13 engine, deliberately torch-free so every claim is explainable and reproducible:

`ingest → atomic typed facts → BM25 retrieval (query-aware) → recipient-aware selection → critical-fact guard → dedup → render → token count`

We grounded each stage in the literature but implemented **lightweight, deterministic** versions:
- **Query-aware extractive selection** (inspired by *LongLLMLingua*) via a custom BM25 — not a learned token classifier.
- **Inter-agent communication pruning** (*AgentPrune* / "Cut the Crap") → our **RELAY** handoff.
- **Guideline learning without fine-tuning** (*ACON*) → an optional **verifier** that learns "always keep type X" and only fires when a critical type is genuinely missing.
- **Constraint-compliance vs. accuracy separation** (*CDCT*) → deterministic decision scoring on gold constraints.
- **Near-duplicate anchoring** (*SeCo*) → dedup.

Around the engine:
- **Fetch.ai:** a uAgent (`uagents` + `uagents-core`) speaking the Chat Protocol, mailbox-connected to Agentverse, plus a local Bureau multi-agent demo.
- **Measurement:** real Claude calls (Haiku 4.5) through a thin `AnthropicLLM` wrapper that reads the API's own `usage.input_tokens` — disk-cached so the stage demo is instant and free.
- **Web:** a FastAPI backend + Next.js 14 / React frontend ("Editorial Minimal" design) with the live A/B, the animated pipeline, a token meter, the decision benchmark, and PDF/doc ingestion (`markitdown`).
- **Rigor:** **116 offline tests** (2 skipped), with a strict invariant that the test suite imports no `uagents`/`fastapi`/`markitdown`/`mcp`/network — the core stays pure.

The savings number we show is literally:
$$\text{saved}\% = \left(1 - \frac{T_{\text{RAVEN}}}{T_{\text{full}}}\right)\times 100$$
where $T$ are the model's **real** input tokens, not estimates.

## Challenges we ran into

- **Compression is lossy by math, not by mistake.** Turning $N$ tokens into $M < N$ forces a bet about what matters. Our first selector kept the dietary rule but dropped the actual restaurant suggestion *and*, in another pass, dropped "confirm before paying." The fix wasn't "compress better" — it was to make the **loss principled**: a hard guard that never drops standing rules, plus soft guards for schedule/location/preference, so the loss only ever lands on low-relevance facts.
- **Relevance has no perfect oracle.** BM25 mismatches vocabulary ("Italian place" vs. "where to eat"). We tuned a relevance floor and a recipient model rather than reaching for a heavyweight learned compressor we couldn't explain.
- **Honest measurement is hard.** It's tempting to quote a self-counted number. We forced ourselves to report the **API's own `usage.input_tokens`**, to disclose that tokens *tie* at equal budget, and to make the real win (decision quality) the headline.
- **Live latency & demo safety.** Real calls were slow under load, so we built disk caching, a "live Xs / cached" badge for transparency, and a cooldown so a demo can't accidentally burn quota.
- **Keeping the agent dependency-free.** The Agentverse agent itself makes **zero LLM calls** (pure deterministic compression), so it needs **no API key** to run — which took discipline to preserve as the codebase grew.

## Accomplishments that we're proud of

- **Three deploy surfaces from one engine** — a live Agentverse agent, an MCP server inside Claude, and a provable web A/B demo — all reusing the same pure compression core.
- A **live agent on Agentverse** that's genuinely useful infrastructure, not a toy — it makes *other* agents cheaper.
- A **provable** demo: real token counts, side-by-side, with an animation that teaches the mechanism — and it survives **adversarial prompts** (it refused to bypass the "confirm before paying" and "no steakhouse" rules).
- **Constraint-safety as a feature:** RAVEN keeps the rules a bloated full-memory model *drops*. We turned "lost in the middle" from a risk into our demo's punchline.
- **80–90% token reduction with preserved decisions**, reproducible from a clean checkout, backed by 116 tests.
- A design that's **explainable end-to-end** — every kept fact has a reason (guard vs. relevant).

## What we learned

- **More context is not safer context.** Past a point, extra tokens *hurt* — the model loses the critical rule. The relevant slice beats the whole memory on both cost *and* safety.
- **Generic compression solves a different problem than ours.** The papers optimize "shrink a prompt, keep generic answer quality." The agentic, constraint-sensitive use case needs "compress *for a recipient* without dropping the rules" — and bridging that gap (recipient-awareness + a constraint guard + a verifier) is the actual contribution.
- **The limitations are mostly the problem talking back.** Lossiness, imperfect relevance, and constraint-vs-relevance tension are fundamental; the value is in *managing* them honestly, not pretending to eliminate them.
- **Least-privilege context is a privacy story, not just a cost story.**

## What's next for RAVEN

- **Publish the MCP server to PyPI** so anyone adds RAVEN to Claude with one line (`uvx raven-mcp`), plus a persistent memory store and more tools (the MCP server already works locally inside Claude Desktop / Code / Cursor).
- **An LLM API proxy** (one-line `base_url` swap) so any existing app gets the savings with no rewrite.
- **Learned relevance as an optional upgrade** (embeddings / a small classifier) behind the same explainable interface, for users who'll trade a dependency for higher recall.
- **Cross-agent passport caching** and KV-level compression (*Cache-to-Cache*) for repeat back-context.
- **Framework adapters** (LangChain / CrewAI) so multi-agent builders get RELAY for free.

---

## Built with

**Languages:** Python 3.13 (stdlib-first), JavaScript (React/JSX), CSS.
**Frameworks & libraries:** FastAPI, Uvicorn, Next.js 14, React, pytest, a custom BM25 retriever, `markitdown` (optional doc ingestion), `fastembed` (optional vector upgrade).
**AI / models:** Anthropic Claude API (Claude Haiku 4.5 for the live demo; temperature 0, disk-cached), using the API's real `usage.input_tokens`.
**Agent platform:** Fetch.ai — `uagents` + `uagents-core` (Chat Protocol), **Agentverse** (mailbox hosting), **ASI:One** (discovery).
**MCP:** the `mcp` Python SDK (FastMCP) — RAVEN as a tool server for Claude Desktop / Claude Code / Cursor.
**Data / infra:** JSON fact corpus, optional **Redis** fact store, local disk LLM cache.
**Research grounding:** LongLLMLingua, AgentPrune / "Cut the Crap", ACON, CDCT, SeCo (implemented as lightweight, explainable variants).
**Design:** "Editorial Minimal" system (Fraunces / Inter / IBM Plex Mono).

---

## Ethical considerations (AI, social, environmental, privacy)

- **Privacy by least-privilege.** RAVEN's core design *minimizes* data exposure: each agent receives only the facts its role needs — the calendar agent never sees your budget, the budget agent never sees your allergies. This is data minimization enforced structurally, not by policy. The compression engine and the Agentverse agent run **locally and make no LLM calls**, so raw memory need never leave the user's machine to be compressed.
- **Environmental.** Fewer input tokens per call means **less compute and energy per query**, multiplied across users × agents × turns. Token reduction is a direct, measurable efficiency gain for LLM inference.
- **Safety / social.** Our **constraint guard** specifically prevents dropping standing rules (consent, budgets, dietary/medical needs), and we demonstrated it **refusing adversarial instructions** ("ignore my rules and charge my card"). Compression that silently loses a safety rule is a real social harm; RAVEN is built to prevent exactly that.
- **Honesty in claims.** We report the model's **real** token usage, disclose where the numbers tie (equal-budget tokens), and never overstate — the demo is reproducible and the tests are public. We treat misleading benchmarks as an ethical issue, not just a technical one.
- **Transparency.** Every kept fact carries a reason (guard vs. relevant) and the UI shows exactly what was sent to the model and whether a call was live or cached — so users can audit what the system did with their data.
