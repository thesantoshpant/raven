"""In-process smoke for the RAVEN MCP server -- proves the tools work without needing a live
stdio client. Imports `mcp`; NOT run by pytest.

Run:  python -m raven.mcp.smoke
"""

from __future__ import annotations

import asyncio

from .server import mcp

_MEM = ("Maya is vegetarian and allergic to peanuts. Keep dinners under $40. "
        "She's free Friday after 7pm. Always confirm before paying. The concert tickets are $65.")


def _value(ret):
    """call_tool's return shape varies by tool return type: (content, structured) tuple,
    a bare structured dict, or a sequence of content blocks. Dig out the real value."""
    structured, content = None, ret
    if isinstance(ret, tuple):
        for part in ret:
            if isinstance(part, dict):
                structured = part
            else:
                content = part
    elif isinstance(ret, dict):
        structured = ret
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    try:
        return "".join(getattr(b, "text", "") for b in content)
    except TypeError:
        return ret


async def _main() -> None:
    tools = await mcp.list_tools()
    names = {t.name for t in tools}
    print("tools:", sorted(names))
    assert {"compress_memory", "relay_handoff", "list_roles"} <= names, "missing a tool"

    text = _value(await mcp.call_tool("compress_memory",
                                      {"memory": _MEM, "task": "plan dinner", "role": "budget"}))
    print("\n--- compress_memory(role=budget) ---\n" + str(text))
    assert "$40" in text and "confirm" in text.lower(), "budget passport lost a standing rule"

    htext = _value(await mcp.call_tool("relay_handoff",
                                       {"prior_context": _MEM, "latest_message": "Booked Green Bowl at 7pm.", "role": "writer"}))
    print("\n--- relay_handoff ---\n" + str(htext))
    assert "Green Bowl at 7pm" in htext, "RELAY dropped the latest message"

    roles = _value(await mcp.call_tool("list_roles", {}))
    print("\nlist_roles ->", roles)
    assert "budget" in roles and "writer" in roles, "roles list wrong"
    print("\nSMOKE OK")


if __name__ == "__main__":
    asyncio.run(_main())
