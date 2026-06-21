"""Local, offline-safe multi-agent demo on the real uAgents framework.

A Bureau runs two real uAgents in one process: an ORCHESTRATOR hands work to a
BUDGET specialist. Instead of forwarding the whole running context, the orchestrator
RELAYs a compressed, recipient-aware RAVEN passport on the wire, and we log the
per-hop token meter. No network, no Agentverse account needed.

    pip install -r requirements-fetch.txt
    python raven/fetch/bureau_demo.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from uagents import Agent, Bureau, Context, Model  # noqa: E402

from raven.relay import build_relay_passport  # noqa: E402

# A realistic running context (what a naive system would forward whole each hop).
RUNNING_CONTEXT = (
    "Maya is vegetarian and eats no meat. The user wants a relaxed Friday dinner. "
    "Keep dinners under $40 this month. The user dislikes loud, crowded places. "
    "Standing rule: always confirm before paying for anything. "
    "Unrelated: the library is open late, a concert has $65 tickets, and the "
    "weather has been nice. Earlier we spent $18.75 on notebooks."
)
TASK = "plan a friday dinner with maya"


class Handoff(Model):
    task: str
    to_role: str
    passport: str
    raw_tokens: int
    relayed_tokens: int


class Decision(Model):
    role: str
    summary: str


orchestrator = Agent(name="orchestrator", seed="raven-bureau-orchestrator-seed")
budget_agent = Agent(name="budget-specialist", seed="raven-bureau-budget-seed")


@orchestrator.on_event("startup")
async def kickoff(ctx: Context):
    res = build_relay_passport(RUNNING_CONTEXT, TASK, "budget")
    ctx.logger.info(
        f"RELAY orchestrator->budget: {res.raw_tokens} -> {res.relayed_tokens} tokens "
        f"({res.saved_pct:.0f}% smaller). Forwarding a passport, not the whole transcript."
    )
    await ctx.send(
        budget_agent.address,
        Handoff(task=TASK, to_role="budget", passport=res.passport_text,
                raw_tokens=res.raw_tokens, relayed_tokens=res.relayed_tokens),
    )


@budget_agent.on_message(Handoff)
async def on_handoff(ctx: Context, sender: str, msg: Handoff):
    ctx.logger.info(f"budget-specialist received a {msg.relayed_tokens}-token passport:\n{msg.passport}")
    within_rule = "$40" in msg.passport
    needs_confirm = "confirm" in msg.passport.lower()
    await ctx.send(
        sender,
        Decision(role="budget", summary=f"budget_cap_seen={within_rule}, requires_confirmation={needs_confirm}"),
    )


@orchestrator.on_message(Decision)
async def on_decision(ctx: Context, sender: str, msg: Decision):
    ctx.logger.info(f"DECISION from {msg.role}: {msg.summary}")
    ctx.logger.info("Demo complete (Ctrl-C to exit).")


bureau = Bureau()
bureau.add(orchestrator)
bureau.add(budget_agent)


if __name__ == "__main__":
    bureau.run()
