---
description: "Use when writing, modifying, or debugging code in the cawdp_contract/ sub-package. Covers CRUD patterns, router conventions, event logging, test patterns, and SurrealDB schema."
applyTo: "cawdp_contract/**"
---

# CAWDP Contract API — Conventions

## Architecture

The `cawdp_contract/` sub-package is a standalone FastAPI application that runs alongside AgentOS. It shares the same SurrealDB instance but has its own routers, models, and CRUD layer.

```
cawdp_contract/
├── app/main.py          # FastAPI app, router registration
├── config/              # Static config (fields, transitions, gates, catalogue)
├── db/
│   ├── _utils.py        # normalize() — converts SurrealDB types to JSON-safe
│   ├── session.py        # get_db() singleton, get_connection() fresh
│   ├── contract_crud.py  # workflow_contract CRUD + optimistic locking
│   ├── output_spec_crud.py # output_specification CRUD
│   ├── event_crud.py     # log_event(), get_contract_events() audit trail
│   └── crud.py           # create_workflow_and_contract()
├── models/              # Pydantic request/response models
├── routers/
│   ├── contract.py       # GET/PATCH /contracts
│   ├── output_spec.py     # CRUD + submit/approve + Stage 1 gate
│   ├── progress.py        # progress, next-action, history
│   ├── workflow.py        # POST /workflows
│   ├── triage.py          # POST /triage/evaluate
│   └── health.py          # GET /health
└── tests/
    ├── conftest.py        # Shared fixtures, MockDB, sample data
    ├── test_utils.py       # Unit tests for normalize()
    ├── test_event_logging.py # Event CRUD + router integration
    ├── test_milestone_1-5.py # Milestone test suites
    └── (integration tests marked with @pytest.mark.integration)
```

## Database Patterns

### Connection management

```python
from cawdp_contract.db.session import get_db, get_connection

# In routers (FastAPI dependency):
db: Surreal = Depends(get_db)  # cached singleton

# For one-off use (migrations, scripts):
db = get_connection()  # fresh connection, caller closes
```

**Never** pass `_connect()` as `db=` — it is a raw connection and will crash at runtime.

### CRUD functions

All CRUD functions take `db: Surreal` as the first parameter and return normalised dicts:

```python
from cawdp_contract.db.contract_crud import get_contract_by_id, update_contract_field
from cawdp_contract.db.output_spec_crud import create_output_spec, update_output_spec
from cawdp_contract.db.event_crud import log_event, get_contract_events
```

### Optimistic locking

`update_contract_field()` and `update_output_spec()` accept `expected_updated_at` for conflict detection:

```python
result = update_contract_field(db, contract_id, "status", "Stage 1 Review",
    expected_updated_at="2026-06-01T12:00:00Z")
# Returns None if the record was modified by another request
```

### Event logging

Every state-changing endpoint calls `log_event()` after the main operation:

```python
from cawdp_contract.db.event_crud import log_event

log_event(db, contract_id=full_id, event_type="section_updated",
    detail={"section": section, "updated_fields": updated_fields})
```

Event logging is **best-effort** — wrapped in `try/except` so it never blocks the main operation.

Canonical event types: `contract_created`, `section_updated`, `output_spec_created`, `output_spec_submitted`, `output_spec_approved`, `contract_submitted_stage_1`, `stage_1_approved`.

### Normalization

`_utils.normalize()` recursively converts SurrealDB types to JSON-safe values:

- `RecordID` → string
- `datetime` → ISO-8601 string (via `.isoformat()`)
- `dict`/`list` → recursively normalized
- Primitives (`str`, `int`, `float`, `bool`, `None`) → pass through

## Router Conventions

### Dependency injection

Each router defines a local `get_db()` that delegates to the session singleton:

```python
def get_db() -> Surreal:
    from cawdp_contract.db.session import get_db as _get_db
    return _get_db()
```

This allows `app.dependency_overrides[router.get_db]` in tests.

### Error handling

All database errors are caught and converted to HTTP 500:

```python
try:
    contract = get_contract_by_id(db, full_id)
except Exception as exc:
    raise HTTPException(status_code=500, detail=f"Database error: {exc}") from exc
```

404 for missing records, 422 for validation failures.

### ID resolution

Contract IDs may come with or without the `workflow_contract:` prefix. Use `_resolve_contract_id()` to normalise:

```python
full_id = _resolve_contract_id(contract_id)  # adds prefix if missing
```

## Testing

### Running tests

```bash
# Unit tests (default — skips integration tests)
python -m pytest cawdp_contract/tests/ -v

# Integration tests (requires live SurrealDB at SURREALDB_URL)
SURREALDB_URL=ws://localhost:8099 python -m pytest cawdp_contract/tests/ -v -m integration

# Run just event logging tests
python -m pytest cawdp_contract/tests/test_event_logging.py -v

# Run just utils tests
python -m pytest cawdp_contract/tests/test_utils.py -v
```

### Test patterns

Tests use `MockDB` classes that route `query()` calls by SQL verb. The shared `conftest.py` provides:

- `CONTRACT_DRAFT`, `CONTRACT_COMPLETE`, `CONTRACT_STAGE_1_APPROVED` — sample contract data
- `SPEC_DRAFT`, `SPEC_APPROVED` — sample output spec data
- `MockDB` — base mock that returns `_single_record` for SELECT/UPDATE
- `override_all_dbs(mock)` — override all three router DB dependencies
- `clear_overrides()` — clean up after tests
- `client` fixture — `TestClient(app)` with auto-cleanup

### Adding new tests

1. Import shared data from `conftest.py` instead of redefining
2. Use `@pytest.mark.integration` for tests requiring live SurrealDB
3. Mock the `contract_event` table in your `MockDB.query()` — return `[]` for SELECT queries on `contract_event` to trigger the fallback inference path

## Schema

The schema is defined in `docs/schema/current.surql`. Deploy it with:

```bash
python scripts/run_migration.py
# Or with custom connection:
python scripts/run_migration.py --url ws://localhost:8099 --namespace agno --database agentos
```

Key tables:

- `workflow_contract` — Layer 2 SCHEMALESS, the main contract record
- `output_specification` — Layer 2 SCHEMALESS, output specs
- `contract_produces` — RELATION edge (contract → output spec)
- `contract_consumes` — RELATION edge (contract → input spec)
- `contract_event` — Layer 2 SCHEMALESS, audit trail events
- `workflows` — Layer 2 SCHEMALESS, workflow records

## SurrealDB SDK (v2.0.0)

The project uses `surrealdb` Python SDK v2.0.0 targeting SurrealDB v3.0.5. Key differences from v1.x:

- `db.query('SELECT ...')` returns `list[dict]` (not first result)
- `db.update(record).merge(data)` replaces `db.merge(record, data)`
- `db.update(record).patch(data)` replaces `db.patch(record, data)`
- `db.insert(table, data, relation=True)` replaces `db.insert_relation(table, data)`
- `db.delete(Table("my-table"))` — bare strings rejected, use `Table()`
- `Surreal` is a factory function, not a class — use `Any` type annotation, not `Surreal | None`

See `.github/instructions/versions.instructions.md` for the full compatibility table.
