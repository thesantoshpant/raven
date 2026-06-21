"""RAVEN as a uAgent on Agentverse, discoverable by ASI:One via the standard Chat
Protocol. Send it (in chat) something like:

    role: budget
    task: plan a friday dinner
    memory: Maya is vegetarian. Keep dinners under $40. Always confirm before paying.

and it replies with a compressed RAVEN context passport + the token savings.

Setup:
    pip install -r requirements-fetch.txt
    python raven/fetch/raven_agent.py
Then open the printed Agentverse Inspector URL and connect the mailbox; the agent
registers on the Almanac and becomes reachable from ASI:One.

Agent construction lives in build_agent() so importing this module has NO side effects
(no network, no key files, no log spam).
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Allow running as a plain script: put the repo root on sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from raven.handlers import handle_compress_request  # noqa: E402

SEED = os.environ.get("RAVEN_AGENT_SEED", "raven-context-passport-agent-seed-0001")


def build_agent(mailbox: bool = True, port: int = 8001):
    """Construct and wire the Chat-Protocol uAgent. Imports uagents lazily so module
    import stays side-effect-free. Pass mailbox=False, port=None for a purely-local
    (no network) instance, e.g. inside a Bureau for chat_smoke.py."""
    from uagents import Agent, Context, Protocol
    from uagents_core.contrib.protocols.chat import (
        ChatAcknowledgement,
        ChatMessage,
        EndSessionContent,
        TextContent,
        chat_protocol_spec,
    )

    kwargs = dict(name="raven-context-compressor", seed=SEED, mailbox=mailbox,
                  publish_agent_details=mailbox)
    if port is not None:
        kwargs["port"] = port
    agent = Agent(**kwargs)
    protocol = Protocol(spec=chat_protocol_spec)

    def _text_of(msg: ChatMessage) -> str:
        return "".join(item.text for item in msg.content if isinstance(item, TextContent))

    @protocol.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
        await ctx.send(sender, ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
        reply, stats = handle_compress_request(_text_of(msg))
        ctx.logger.info(f"RAVEN compress -> {stats}")
        await ctx.send(sender, ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=reply), EndSessionContent(type="end-session")],
        ))

    @protocol.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass

    agent.include(protocol, publish_manifest=True)
    return agent


if __name__ == "__main__":
    build_agent().run()
