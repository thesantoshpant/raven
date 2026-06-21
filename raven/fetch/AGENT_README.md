# RAVEN — Context Passport Compressor

**Give each AI agent a tiny, recipient-aware "context passport" instead of your whole memory —
60–95% fewer tokens, decisions preserved. Free, instant, deterministic, no API key.**

Stop stuffing every agent's prompt with your entire memory. Send RAVEN your raw notes/context
plus a recipient role, and it returns only the facts that agent actually needs (hard constraints
+ risk flags), dropping the rest — and reports the token savings.

## Use me when you want to
- "Compress my memory/context for an agent before calling it"
- "Reduce tokens / cut LLM cost before an agent call"
- "Give the budget agent only what it needs — not my whole memory"
- "Hand off from one agent to another without forwarding the entire transcript"
- "Keep standing rules (dietary, budget, confirm-before-paying) from getting lost in a long context"

## What it does
- **Input:** a memory blob + a target role — one of `restaurant`, `calendar`, `budget`, `writer`.
- **Output:** a compact **passport** — that role's action-critical facts only — typically
  **60–95% fewer context tokens** on a realistic memory (tiny inputs may not net-compress; it
  says so honestly).
- **Recipient-aware + least-privilege:** the calendar agent never sees your budget or allergies.
- **Decision-preserving:** standing rules are force-kept for the agent that needs them, even when
  they don't lexically match the task.
- **Agent→agent (RELAY):** forwards the latest message verbatim + a compressed back-context,
  ~90% smaller than the full transcript.

## How to talk to me (Chat Protocol)
Send a chat message like:
```
role: budget memory: Maya is vegetarian and allergic to peanuts. Keep dinners under $40 this month. She's free Friday after 7pm but in lab until 5:30. Always confirm before paying. Concert tickets were $65. I spent $18.75 on notebooks. I prefer Thai and Italian food.
```
Change `role:` to `restaurant`, `calendar`, or `writer` to get a **different** passport from the
**same** memory. `task:` is optional; `role` defaults to `writer`; JSON
`{"role":..., "task":..., "memory":...}` also works.

## Example reply
```
RAVEN context passport for 'budget' — 46 tokens, saved 69% vs 151 raw

# CONTEXT PASSPORT for budget_agent
HARD CONSTRAINTS:
- Keep dinners under $40 this month.
RISK FLAGS:
- Always confirm before paying.
```

**Keywords:** context compression, token reduction, prompt compression, agent memory,
recipient-aware context, least-privilege context, context passport, multi-agent, agent-to-agent
handoff, RELAY, RAG alternative, LLM cost savings, context window, retrieval.

Part of **RAVEN** — verified context passports across every edge of the agentic web
(user memory → agent, and agent → agent).
