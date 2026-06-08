# MCP Library Decision — DevFlow DB

**Brief ID:** PB-001
**Date:** 2026-06-05
**Step:** 2

## Decision

Use the **official `mcp` Python SDK** (`pip install mcp`) with its built-in `FastMCP` high-level API (`from mcp.server.fastmcp import FastMCP`).

## Evaluation

| Criterion | `mcp` (official SDK) | `fastmcp` (standalone) |
|---|---|---|
| Tool registration | `@mcp.tool()` decorator — clean, minimal boilerplate | Identical API; `fastmcp` was the prototype that inspired the official implementation |
| VS Code Copilot compatibility | ✅ Full — uses stdio transport, the standard for local MCP servers | ✅ Same transport |
| Dependencies | Minimal (`anyio`, `pydantic`, `httpx`) | Adds an extra layer on top of the official SDK |
| Maintenance | Maintained by Anthropic / MCP working group | Community-maintained; the high-level API has been upstreamed into the official SDK |
| `FastMCP` availability | ✅ Available as `mcp.server.fastmcp.FastMCP` since SDK v1.2+ | Original source; now largely redundant |
| Local execution | ✅ `mcp run server.py` or `python server.py` with stdio | Same |

## Rationale

The standalone `fastmcp` package pioneered the high-level decorator API, but that API has been merged into the official `mcp` SDK as `FastMCP`. Using the official SDK avoids a redundant dependency, follows the reference implementation, and ensures compatibility with any future MCP protocol updates. The `FastMCP` class within the official SDK provides the same ergonomics that made `fastmcp` attractive.

## Selected library

```
mcp>=1.2.0
```

Added to `servers/requirements.txt`.
