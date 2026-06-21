"""Local multi-agent demo on the real uAgents framework.

A Bureau runs two real uAgents in one process: an ORCHESTRATOR hands work to a
BUDGET specialist. Instead of forwarding the whole running context, the orchestrator
RELAYs (via build_relay_handoff) the upstream recommendation verbatim + a compressed,
recipient-aware passport of the back-context, and we log the per-hop token meter.

No Agentverse account is needed (in-process messaging). uAgents still binds a local
port and logs like a server, so use --once for a bounded smoke run that exits after the
decision:

    pip install -r requirements-fetch.txt
    python raven/fetch/bureau_demo.py --once     # bounded: exits after the decision
    python raven/fetch/bureau_demo.py            # live: runs until Ctrl-C

Agent construction happens inside main() so importing this module has no side effects.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from raven.relay import build_relay_handoff  # noqa: E402

# The user's standing back-context (what a naive system would forward whole each hop).
RUNNING_CONTEXT = (
    "Maya is vegetarian and eats no meat. The user wants a relaxed Friday dinner. "
    "Keep dinners under $40 this month. The user dislikes loud, crowded places. "
    "Standing rule: always confirm before paying for anything. "
    "Unrelated: the library is open late, a concert has $65 tickets, the weather is nice."
)
# The upstream agent's latest output (the message that must NOT be dropped).
RESTAURANT_REC = (
    "I recommend Green Bowl, a vegetarian-friendly and quiet spot at about $28 per person."
)
TASK = "plan a friday dinner with maya"


def main(once: bool = False):
    from uagents import Agent, Bureau, Context, Model

    class Handoff(Model):
        task: str
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
        h = build_relay_handoff(RUNNING_CONTEXT, RESTAURANT_REC, TASK, "budget")
        ctx.logger.info(
            f"RELAY orchestrator->budget: full={h.raw_tokens} last_msg={h.last_message_tokens} "
            f"relay={h.relayed_tokens} tok | message_preserved={h.message_preserved}"
        )
        await ctx.send(budget_agent.address,
                       Handoff(task=TASK, passport=h.handoff_text,
                               raw_tokens=h.raw_tokens, relayed_tokens=h.relayed_tokens))

    @budget_agent.on_message(Handoff)
    async def on_handoff(ctx: Context, sender: str, msg: Handoff):
        ctx.logger.info(f"budget-specialist received a {msg.relayed_tokens}-token passport:\n{msg.passport}")
        venue_seen = "green bowl" in msg.passport.lower()
        cap_seen = "$40" in msg.passport
        needs_confirm = "confirm" in msg.passport.lower()
        await ctx.send(sender, Decision(
            role="budget",
            summary=f"venue_seen={venue_seen}, cap_seen={cap_seen}, requires_confirmation={needs_confirm}",
        ))

    @orchestrator.on_message(Decision)
    async def on_decision(ctx: Context, sender: str, msg: Decision):
        ctx.logger.info(f"DECISION from {msg.role}: {msg.summary}")
        if once:
            ctx.logger.info("--once: exiting after the decision.")
            os._exit(0)
        ctx.logger.info("Demo complete (Ctrl-C to exit).")

    bureau = Bureau()
    bureau.add(orchestrator)
    bureau.add(budget_agent)
    bureau.run()


if __name__ == "__main__":
    main(once="--once" in sys.argv)
