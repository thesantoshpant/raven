# RAVEN as an MCP server

Use RAVEN's recipient-aware context compression **inside Claude Desktop, Claude Code, or Cursor**
as a tool. RAVEN makes **no LLM calls and needs no API key** — the host model is the LLM; RAVEN
just hands back a compressed, recipient-aware **context passport**.

## Tools
- **`compress_memory(memory, task, role)`** — compress a memory/context blob into a tiny passport
  for an agent `role` (`restaurant` · `calendar` · `budget` · `writer`). Force-keeps standing
  rules (dietary / budget / permission), drops the rest — typically 80–95% fewer tokens.
- **`relay_handoff(prior_context, latest_message, role)`** — agent→agent handoff: forwards the
  latest message verbatim + a compressed passport of the prior context (~90% smaller than the
  full transcript).
- **`list_roles()`** — the roles RAVEN can compress for.

## Install
```bash
pip install -r requirements-mcp.txt
```

## Run / configure

### Claude Desktop
Add to `claude_desktop_config.json`
(`%APPDATA%\Claude\claude_desktop_config.json` on Windows, `~/Library/Application Support/Claude/`
on macOS), then restart Claude Desktop:
```json
{
  "mcpServers": {
    "raven": {
      "command": "C:\\Users\\Santosh\\desktop\\0-100\\hackathons\\AIHACKATHON\\raven\\.venv\\Scripts\\python.exe",
      "args": ["-m", "raven.mcp.server"],
      "cwd": "C:\\Users\\Santosh\\desktop\\0-100\\hackathons\\AIHACKATHON\\raven"
    }
  }
}
```

### Claude Code
```bash
claude mcp add raven -- /abs/path/.venv/Scripts/python.exe -m raven.mcp.server
```

### Cursor
Add the same `mcpServers` block to `~/.cursor/mcp.json`.

> Use the **absolute** path to the project's venv Python, and set `cwd` to the repo root so
> `raven` is importable.

## Verify without a client
```bash
python -m raven.mcp.smoke          # in-process: lists the 3 tools + runs a real compress_memory call
mcp dev raven/mcp/server.py        # optional: opens the MCP Inspector
```

## Example
> *"Use RAVEN to compress this for the budget agent: Maya is vegetarian, keep dinners under $40,
> always confirm before paying, concert tickets were $65."*

→ RAVEN returns a passport with the `$40` cap and the confirm-before-paying rule (and drops the
`$65` receipt), at a fraction of the tokens.
