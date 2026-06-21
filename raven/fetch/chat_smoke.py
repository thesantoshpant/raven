"""Local chat-protocol round-trip smoke (no Agentverse, no network).

Spins up the RAVEN agent + a client uAgent in one Bureau, sends a ChatMessage, and
asserts a ChatMessage reply containing a passport. This is the EXACT path ASI:One uses
(the standard Chat Protocol) -- proving it works locally de-risks the live demo.

    pip install -r requirements-fetch.txt
    python raven/fetch/chat_smoke.py        # exits 0 on a passport reply, 1 otherwise
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from uagents import Agent, Bureau, Context, Protocol  # noqa: E402
from uagents_core.contrib.protocols.chat import (  # noqa: E402
    ChatAcknowledgement,
    ChatMessage,
    TextContent,
    chat_protocol_spec,
)

from raven.fetch.raven_agent import build_agent  # noqa: E402

QUERY = (
    "role: budget\ntask: plan a friday dinner\n"
    "memory: Maya is vegetarian. Keep dinners under $40. Always confirm before paying. "
    "The weather is nice. Concert tickets are $65."
)


def main():
    raven = build_agent(mailbox=False, port=None)  # purely local instance
    client = Agent(name="raven-chat-client", seed="raven-chat-smoke-client-seed")
    cproto = Protocol(spec=chat_protocol_spec)

    @client.on_event("startup")
    async def kickoff(ctx: Context):
        ctx.logger.info("client -> RAVEN: sending ChatMessage")
        await ctx.send(raven.address, ChatMessage(
            timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
            content=[TextContent(type="text", text=QUERY)]))

    @cproto.on_message(ChatMessage)
    async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
        text = "".join(p.text for p in msg.content if isinstance(p, TextContent))
        ctx.logger.info(f"RAVEN -> client reply:\n{text}")
        ok = ("$40" in text) and ("passport" in text.lower())
        ctx.logger.info(f"CHAT SMOKE {'PASS' if ok else 'FAIL'}")
        os._exit(0 if ok else 1)

    @cproto.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        pass

    client.include(cproto)
    bureau = Bureau()
    bureau.add(raven)
    bureau.add(client)
    bureau.run()


if __name__ == "__main__":
    main()
