# RAVEN — Demo Runbook

A rehearsable, can't-fail script for judging. ~3 minutes.

## 0. Pre-flight (do this BEFORE you present)
```
# terminal 1 — backend (requirements-docs is needed for PDF/docx/html upload; .md/.txt work without it)
.venv\Scripts\python -m pip install -r requirements-web.txt -r requirements-docs.txt
.venv\Scripts\python -m uvicorn raven.web.api:app --port 8000

# terminal 2 — warm the live cache so the on-stage benchmark is instant
.venv\Scripts\python bench\warm_cache.py

# terminal 3 — frontend
cd frontend && npm install && npm run dev -- -p 3000
```
Open http://localhost:3000. Click **Run benchmark** once now (it's cached after) so it's snappy live.

Optional (the Fetch/ASI:One live moment — see §4): start the agent and connect its mailbox.

## 1. The hook (20s)
"AI is becoming everyone's daily driver, and every agent gets handed your *entire* memory —
expensive and over-exposed. RAVEN gives each agent a **context passport**: only the facts
that agent's role needs, at every edge of a multi-agent system."

## 2. Dashboard — three panes (70s)
- **Left (User memory):** "38 messy items — chats, notes, receipts. Five decision-critical
  facts are buried in here (highlighted): Maya's vegetarian, the $40 cap, the lab schedule,
  'no loud places', and a standing 'confirm before paying' rule."
- **Middle (Agents · passports):** click **budget** → "Instead of all 127 facts, the budget
  agent gets a 3-line passport: the $40 cap + the confirm rule. It's *denied* the rest —
  least privilege by construction." Click **restaurant** → "different agent, different slice."
- **Right (Token meter + live benchmark):** "Across the workflow that's ~94% fewer context
  tokens." Click **Run benchmark** → "Now the punchline — does compression hurt the decision?
  **raw** (full memory) gets 5/5 but is expensive. **generic** compression at the same budget
  drops to **4/5** — it loses the payment rule. **RAVEN** keeps **5/5** at a fraction of the
  cost. Same budget, better decision."

## 3. RELAY tab (30s)
"Compression isn't just at the front door — it's every agent-to-agent handoff. Naively you
forward the whole growing transcript. RELAY forwards the latest message + a compressed
back-context passport: **~90% smaller** than broadcasting the transcript, and it *keeps* the
standing constraints that last-message-passing silently drops (3/3 hops vs 1/3)."

## 4. Fetch / ASI:One — "it's live on the agentic web" (30s)
"RAVEN runs as a real **uAgent** on **Agentverse**, discoverable from **ASI:One** over the
standard Chat Protocol." Then EITHER:
- **(best) live:** in ASI:One chat, message the RAVEN agent with a memory blob → it returns a
  passport. (Have this pre-tested; see mailbox steps below.)
- **(fallback) local:** `python raven/fetch/bureau_demo.py --once` — two real uAgents hand off
  with RAVEN compressing the wire; or `python raven/fetch/chat_smoke.py` for the chat round-trip.

## 5. Close (10s)
"RAVEN: verified context passports for the agentic web. ~94% fewer tokens, decisions
preserved, and a real agent on Fetch's network today."

---

## Agentverse mailbox + ASI:One setup (one-time, your account)
1. Set a **private** identity seed (required for mailbox runs; keep it secret, reuse the
   same value to keep the same agent address):
   `$env:RAVEN_AGENT_SEED = "your-own-secret-phrase"`
   then `python raven/fetch/raven_agent.py` — it prints an **Agentverse Inspector** URL.
2. Open that URL (log into Agentverse), click **Connect** → **Mailbox** to link the agent.
3. In the agent's Agentverse page, paste the contents of `raven/fetch/AGENT_README.md` as the
   README (ASI:One matches agents on this text — keep the keywords).
4. In **ASI:One** chat, ask for context compression / find the RAVEN agent, then send:
   `role: budget` / `task: plan a friday dinner` / `memory: <your notes>`.
5. **Record** a successful exchange (screenshot/screen-cap) as the can't-fail fallback.

## Fallback ladder (if something breaks live)
- Wifi flaky → the benchmark is cached (warmed in §0), so it still runs instantly.
- Agentverse/ASI:One not cooperating → run the **local Bureau** (`bureau_demo.py --once`) or
  `chat_smoke.py` — same Chat Protocol, no Agentverse mailbox required (uAgents may log a few
  harmless network warnings before the local round-trip succeeds).
- Backend down → restart `uvicorn`; the UI shows a clear "backend not reachable" banner.
- Port 3000 busy → `npm run dev -- -p 3000` (CORS also allows 3001).
