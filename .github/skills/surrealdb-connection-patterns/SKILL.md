---
name: surrealdb-connection-patterns
description: 'SurrealDB Python SDK connection management patterns for this project — caching the connection singleton to prevent file descriptor exhaustion on bulk operations, and annotating the connection as Any to work around incomplete surrealdb stubs. Use when writing db CRUD modules, seeding scripts, migration tools, or any code that calls _connect() in a loop.'
argument-hint: 'What you are building, e.g. "seed script" or "db CRUD module"'
user-invocable: true
---

# SurrealDB Connection Patterns

Two hard lessons from this codebase, encoded as rules.

## When to Use

- Writing or reviewing anything in `cawdp_development/db/`
- Writing bulk operations, seeding scripts, or migration tools
- Hitting `OSError: [Errno 24] Too many open files` during seeds
- Hitting mypy errors: `Function "surrealdb.Surreal" is not valid as a type`

## Rule 1 — Cache the connection (L-001)

**Never open a new SurrealDB connection per CRUD call.**

Opening a new `Surreal()` WebSocket per call means 410 seed records = 410 open file descriptors. macOS hits the default limit (~256) at ~record 100, causing all subsequent DNS lookups to fail.

### Pattern: module-level singleton

There are two implementations of this pattern in the codebase:

**AgentOS (parent project)** — `db/session.py`:

```python
# db/session.py
from typing import Any
from surrealdb import Surreal

_cached_connection: Any = None

def get_surrealdb() -> Any:
    global _cached_connection
    if _cached_connection is not None:
        return _cached_connection
    db = Surreal(SURREALDB_URL)
    db.signin(_CREDENTIALS)
    db.use(_NAMESPACE, _DATABASE)
    _cached_connection = db
    return _cached_connection
```

**CAWDP Contract API** — `cawdp_contract/db/session.py`:

```python
# cawdp_contract/db/session.py
from typing import Any
from surrealdb import Surreal

_cached_connection: Any = None

def get_db() -> Any:
    """FastAPI dependency — returns cached singleton."""
    global _cached_connection
    if _cached_connection is not None:
        return _cached_connection
    db = Surreal(_URL)
    db.signin(_CREDENTIALS)
    db.use(_NAMESPACE, _DATABASE)
    _cached_connection = db
    return _cached_connection

def get_connection() -> Any:
    """Fresh connection for one-off use (migrations, scripts)."""
    db = Surreal(_URL)
    db.signin(_CREDENTIALS)
    db.use(_NAMESPACE, _DATABASE)
    return db
```

### Usage in CRUD modules

```python
# In routers (FastAPI dependency injection):
from cawdp_contract.db.session import get_db

def get_db_dependency() -> Any:
    from cawdp_contract.db.session import get_db as _get_db
    return _get_db()

# In CRUD functions (called with db parameter):
from cawdp_contract.db.contract_crud import get_contract_by_id

contract = get_contract_by_id(db, contract_id)
```

### Migration runner teardown

```python
# scripts/run_migration.py
from surrealdb import Surreal

db = Surreal(url)
db.signin({"username": user, "password": password})
db.use(namespace, database)
# Execute statements...
# No explicit close needed — script exits
```

## Rule 2 — Annotate the connection as `Any` (L-004)

**Use `Any` for the `_db` singleton and `_connect()` return type.**

`surrealdb` ships incomplete stubs. mypy finds the package but the stubs don't declare methods like `query`, `upsert`, `select`. Using `Surreal` as a type annotation produces 20+ errors across all CRUD modules:

```
error: Function "surrealdb.Surreal" is not valid as a type
error: Surreal? has no attribute "query"
error: Surreal? has no attribute "upsert"
```

`ignore_missing_imports = true` in `pyproject.toml` does NOT suppress these — it only suppresses "cannot find module" errors, not errors from stubs that exist but are wrong.

### Fix

```python
from typing import Any
from surrealdb import Surreal  # noqa: F401

_db: Any = None          # not: _db: Surreal | None

def _connect() -> Any:   # not: def _connect() -> Surreal
    ...
    db = Surreal(SURREALDB_URL)   # runtime instantiation still works
    ...
```

Since `_connect()` returns `Any`, all downstream calls (`db.query(...)`, `db.upsert(...)`) inherit `Any` and mypy stops complaining.

## Checklist for new CRUD modules

```
- [ ] Imports _connect from ._connection, not from surrealdb directly
- [ ] Calls _connect() once per function (not once per loop iteration)
- [ ] Does NOT store the result as Surreal type — only calls methods on it
- [ ] Seed runner calls close_connection() in a finally block
```
