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
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

# Allow running as a plain script: put the repo root on sys.path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from uagents import Agent, Context, Protocol  # noqa: E402
from uagents_core.contrib.protocols.chat import (  # noqa: E402
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from raven.handlers import handle_compress_request  # noqa: E402

SEED = os.environ.get("RAVEN_AGENT_SEED", "raven-context-passport-agent-seed-0001")

agent = Agent(
    name="raven-context-compressor",
    seed=SEED,
    port=8001,
    mailbox=True,
    publish_agent_details=True,
)

protocol = Protocol(spec=chat_protocol_spec)


def _text_of(msg: ChatMessage) -> str:
    return "".join(item.text for item in msg.content if isinstance(item, TextContent))


@protocol.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    # 1) acknowledge (required by the chat protocol)
    await ctx.send(
        sender,
        ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id),
    )
    # 2) do the RAVEN work (pure, offline-safe logic)
    reply, stats = handle_compress_request(_text_of(msg))
    ctx.logger.info(f"RAVEN compress -> {stats}")
    # 3) respond + end the session
    await ctx.send(
        sender,
        ChatMessage(
            timestamp=datetime.now(timezone.utc),
            msg_id=uuid4(),
            content=[TextContent(type="text", text=reply), EndSessionContent(type="end-session")],
        ),
    )


@protocol.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(protocol, publish_manifest=True)


if __name__ == "__main__":
    agent.run()
