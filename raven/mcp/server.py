"""RAVEN as an MCP server -- the ONLY module that imports `mcp` (mirrors web/api.py for fastapi,
so the offline test suite never pulls in the MCP SDK).

RAVEN makes NO LLM calls and needs NO API key: the host model (Claude) is the LLM; RAVEN just
returns a compressed, recipient-aware "context passport".

Run (stdio transport, for Claude Desktop / Claude Code / Cursor):
    python -m raven.mcp.server
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import _logic

mcp = FastMCP("raven")


@mcp.tool()
def compress_memory(memory: str, task: str = "general task", role: str = "writer") -> str:
    """Compress a memory/context blob into a tiny, recipient-aware RAVEN 'context passport' for a
    downstream agent role. Keeps only what that role needs, force-keeps standing rules
    (dietary / budget / permission), and drops the rest -- typically 80-95% fewer tokens.
    Deterministic, no LLM, no API key. `role` is one of: restaurant, calendar, budget, writer."""
    return _logic.compress_response(memory, task, role)


@mcp.tool()
def relay_handoff(prior_context: str, latest_message: str, role: str = "writer") -> str:
    """Compress an agent->agent handoff: forward `latest_message` VERBATIM plus a compressed
    recipient-aware passport of `prior_context` -- ~90% smaller than forwarding the whole
    transcript, while standing constraints survive. Deterministic, no LLM."""
    return _logic.relay_response(prior_context, latest_message, role)


@mcp.tool()
def list_roles() -> list:
    """List the recipient roles RAVEN can compress for (restaurant, calendar, budget, writer)."""
    return _logic.roles_list()


def main() -> None:
    mcp.run()  # stdio transport by default


if __name__ == "__main__":
    main()
