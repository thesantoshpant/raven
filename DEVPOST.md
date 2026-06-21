# RAVEN — Verified Context Passports for the Agentic Web

## Inspiration
AI is becoming everyone's daily driver, and multi-agent systems are exploding. But every
agent gets handed the *same firehose* — your entire memory — on every call. That's expensive
(tokens scale with users × agents × turns) and it's a privacy problem (each agent sees
everything, not just what it needs). Summarizing naively is worse: it silently drops the one
fact that flips the decision. We wanted to fix the **plumbing** of the agentic web.

## What it does
RAVEN gives every agent a **context passport**: only the facts that agent's role actually
needs, at **both** edges of a multi-agent system — user-memory → first agent, and agent →
agent (we call the second edge **RELAY**). It is **recipient-aware** (least privilege) and
**decision-preserving** (a verifier + learnable role priors keep the load-bearing facts).

## How it works
1. **Ingest** messy memory → atomic, typed facts (dietary, budget_limit, availability,
   permission, …; multi-label for combined sentences).
2. **Retrieve** per role with BM25 over the fact store.
3. **Compress** into a passport: positive-relevance selection + a guard that force-keeps the
   role's critical types + near-dup dedup, rendered as the exact prompt text.
4. **Verify** (optional, one-time): probe the passport vs full context; re-add + learn a
   guideline if a load-bearing fact is missing (ACON-style, no fine-tune).
5. **RELAY**: at each handoff, forward the latest message + a compressed back-context passport
   instead of the whole transcript.

## Proven results (in the repo, reproducible)
- **Context-payload reduction (M1):** ~93% fewer query-time tokens vs broadcasting full
  memory to every agent (ratio-gated, tokenizer-measured, 4 baselines incl. a fair
  equal-budget one).
- **Decision preservation (M2):** with real Claude agents, at an equal per-agent budget —
  **raw 5/5, generic compression 4/5 (drops the standing "confirm before paying" rule),
  RAVEN 5/5** — deterministic, structured gold-constraint scoring.
- **RELAY (M3):** agent→agent handoffs ~91% smaller than forwarding the transcript, and it
  preserves the standing back-context constraints last-message passing drops (3/3 vs 1/3).
- **Live demo (M4):** a three-pane dashboard — memory → passports → live benchmark → RELAY.

## Built with
Python (stdlib-first engine: dataclasses, BM25, deterministic scoring), Anthropic Claude
(role agents, temp 0, disk-cached), **Fetch.ai uAgents + Agentverse + ASI:One** (RAVEN runs
as a Chat-Protocol agent), optional **Redis** fact store, **FastAPI** + **Next.js** demo UI.
80+-test offline suite; honest, ratio-based benchmarks throughout.

## Sponsor fit
- **Fetch.ai:** RAVEN is a first-class uAgent on Agentverse, discoverable from ASI:One via the
  standard Chat Protocol — and it makes *every* multi-agent system on the network cheaper
  (RELAY cuts inter-agent comms cost).
- **The Token Company:** a measured, decision-preserving compression technique — quality held
  at a fraction of the tokens, with transparent, reproducible benchmarks.

## Challenges
Keeping the benchmarks *honest* (a fair equal-budget baseline; counting verifier tokens
separately; not letting multi-label expansion inflate raw counts) and keeping the live demo
**can't-fail** (disk-cached LLM calls, a local uAgents Bureau fallback for the network path).

## What's next
Finer atomization, embeddings retrieval, more scenarios for a quality *rate* (not just an
existence proof), KV-cache-level relay, and a hosted Agentverse deployment.
