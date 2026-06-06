---
description: "Agno SDK conventions for the agno-surrealdb-railway stack. Use when writing or reviewing any file that imports from agno, configures agents, teams, workflows, or registers components in AgentOS."
applyTo: "**"
---

## Model

Always use `default_model()` from `app.settings` — never hardcode model IDs:

```python
from app.settings import default_model
model=default_model()
```

## Database

Use `get_surrealdb()` for agent session storage, `create_surrealdb_knowledge()` for RAG:

```python
from db import get_surrealdb, create_surrealdb_knowledge
db=get_surrealdb()
knowledge=create_surrealdb_knowledge("Name", "collection")
```

Pipeline agents (`cawdp_development/`) use `get_surrealdb(table_name=...)` for `db=`:

```python
from db import get_surrealdb
db=get_surrealdb(table_name="cawdp_design_writer_sessions")
```

Do NOT pass `_connect()` as `db=` — it is a raw connection and will crash at runtime.
`_connect()` is only correct inside toolkit CRUD functions.

## Agent registration

New agents must be imported and added to the `agent_os` agents list in `app/main.py`.

## MCP lifecycle

In AgentOS, MCP tool lifecycle is managed automatically. Do NOT use `reload=True` with MCPTools.

## Agent defaults

```python
Agent(
    enable_agentic_memory=True,
    add_datetime_to_context=True,
    add_history_to_context=True,
    num_history_runs=5,
    markdown=True,
)
```

## Code quality

Run `./scripts/format.sh` (ruff format + import sort) and `./scripts/validate.sh` (ruff check + mypy) before committing.

## Check docs before guessing APIs

When writing code that uses SurrealDB, Agno, Pydantic, or any package in the
versions list, **check the project documentation before guessing APIs.**

- **SurrealDB Python SDK**: Read `docs/surrealdb-py-readme.md` for the current
  SDK patterns. The SDK version (2.0.0) targets SurrealDB v3.0.5 and has
  breaking changes from v1.x (return types, query syntax, builder pattern).
- **Agno SDK**: Use the `agno_docs` search tools before guessing Agno APIs.
  The framework evolves rapidly and constructor parameters change between versions.
- **Package versions**: See `.github/instructions/versions.instructions.md` for
  the pinned versions and SDK compatibility notes.

**Never assume an API from memory.** If you're unsure about a method signature,
return type, or query syntax, check the docs first. The 5 minutes spent
reading docs saves hours of debugging version-incompatible code.
