---
description: "Use when working with Python, Docker, or infrastructure configuration. Lists key package and runtime versions for the AgentOS project."
applyTo: "**"
---

# Key Versions

## Runtime

| Component | Version |
|-----------|---------|
| Python | 3.12 (Docker: `agnohq/python:3.12`) |
| SurrealDB | v3.0.5 (Docker: `surrealdb/surrealdb:latest`) |

## Core Python Packages

| Package | Version | Purpose |
|---------|---------|---------|
| agno | 2.6.9 | Agent framework (OS + Slack) |
| fastapi | 0.136.3 | API server |
| uvicorn | 0.48.0 | ASGI server |
| starlette | 1.2.0 | ASGI framework |
| pydantic | 2.13.4 | Data validation |
| surrealdb | 2.0.0 | Database (session storage + vector search) |
| openai | 2.38.0 | OpenAI SDK |
| mcp | 1.27.2 | MCP protocol |
| httpx | 0.28.1 | HTTP client |
| anyio | 4.13.0 | Async runtime |
| parallel-web | 0.6.0 | Parallel SDK |
| slack-sdk | 3.42.0 | Slack integration |
| pyjwt | 2.13.0 | JWT auth |
| sentry-sdk | 2.61.0 | Error tracking |

## Dev Tooling

| Tool | Config |
|------|--------|
| ruff | line-length=120 |
| mypy | strict with pydantic plugin |
| uv | pip sync for dependency management |

## SDK Compatibility Notes

### surrealdb.py 2.0.0 (targets SurrealDB v3.0.5)

The Python SDK version 2.0.0 targets SurrealDB v3.0.5. Key API differences from v1.x:

| v1.x (old) | v2.0.0 (current) |
|------------|-------------------|
| `db.merge(record, data)` | `db.update(record).merge(data)` |
| `db.patch(record, data)` | `db.update(record).patch(data)` |
| `db.insert_relation(table, data)` | `db.insert(table, data, relation=True)` |
| `db.query("SELECT 1; SELECT 2")` → first result | `db.query("SELECT 1; SELECT 2")` → tuple of all results |
| `db.delete("my-table")` (bare string) | `db.delete(Table("my-table"))` (bare strings rejected) |

**Return types for sync usage** (verified against installed SDK):

| Operation | Return Type | Notes |
|-----------|------------|-------|
| `db.query('RETURN 1')` | `int` | Scalar result |
| `db.query('SELECT ...')` | `list[dict]` | List of record dicts |
| `db.query('UPDATE ... RETURN AFTER')` | `list[dict]` | List of updated records |
| `db.query('DELETE FROM ...')` | `list` | Empty list |
| `db.query('INFO FOR DB')` | `dict` | With 'tables', 'accesses', etc. keys |
| `db.select(RecordID)` | `list[dict]` | List with one dict |
| `db.upsert(RecordID, data)` | `dict` | Single record dict |

**SurrealQL v3 syntax changes:**

- `SELECT 1 AS ok` → `RETURN 1` (SELECT without FROM not valid in v3)
- `INFO FOR TABLES` → `INFO FOR DB` (returns dict with 'tables' key)
- `⟨$param⟩` bracket syntax → Use `RecordID` as `$param` binding
- `STARTS WITH` → `string::starts_with(record::id(id), ...)`
- `record::id()` extracts string from RecordID

**Always check `docs/surrealdb-py-readme.md`** for the latest SDK patterns before writing SurrealDB code.
