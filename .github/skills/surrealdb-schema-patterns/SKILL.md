---
name: surrealdb-schema-patterns
description: 'SurrealDB v3.0.5 SCHEMAFULL DDL patterns for this project — no FLEXIBLE in DEFINE FIELD, explicit sub-field definitions for nested array objects, using model_dump() not json.loads(model_dump_json()) to preserve Python datetime objects, and storing datetime.now(UTC) not .isoformat() in Pydantic models. Use when writing DEFINE TABLE/FIELD DDL, defining schema for tables with nested arrays, or writing Pydantic model data to SurrealDB via the Python SDK.'
argument-hint: 'Table or field type you are defining, e.g. "array of issue objects" or "datetime field"'
user-invocable: true
---

# SurrealDB SCHEMAFULL Schema Patterns

Three DDL / serialisation pitfalls confirmed during Plan 02 Step 6 validation.

## When to Use

- Writing or reviewing `DEFINE TABLE` / `DEFINE FIELD` DDL in `cawdp_development/db/schema.py`
- Defining SCHEMAFULL tables that contain nested object arrays (e.g. `issues`, `findings`)
- Writing Pydantic models to SurrealDB with `datetime` fields
- Hitting `InternalError: Found field 'X', but no such field exists for table 'Y'`
- Hitting `InternalError: Couldn't coerce value for field: Expected datetime but found '2026-...'`

## Rule 1 — No `FLEXIBLE` in `DEFINE FIELD` (L-005 Finding 1)

`FLEXIBLE` is a **table-level** modifier, not a field-level modifier. Both placements fail:

```sql
-- ❌ WRONG: "FLEXIBLE must be specified after TYPE"
DEFINE FIELD issues[*] ON t FLEXIBLE TYPE object;

-- ❌ WRONG: "Unexpected token FLEXIBLE, expected a kind name"
DEFINE FIELD issues[*] ON t TYPE FLEXIBLE object;

-- ✅ Table-level only — valid use of FLEXIBLE
DEFINE TABLE my_table FLEXIBLE SCHEMAFULL;
```

For SCHEMAFULL tables with object arrays, use sub-field definitions (see Rule 2).

## Rule 2 — Define sub-fields for nested array objects (L-005 Finding 2)

In SCHEMAFULL tables, **every field written to the DB must be defined** — including fields inside array items. Writing `{section_key: "x", description: "y"}` to `issues[*]` without sub-field definitions produces:

```
InternalError: Found field 'issues[0].description', but no such field exists for table 'design_spec_reviews'
```

**Pattern**: define the array field, then each sub-field with `[*].` prefix:

```sql
DEFINE FIELD IF NOT EXISTS issues ON design_spec_reviews TYPE array DEFAULT [];
DEFINE FIELD IF NOT EXISTS issues[*].section_key  ON design_spec_reviews TYPE string;
DEFINE FIELD IF NOT EXISTS issues[*].description  ON design_spec_reviews TYPE string;
DEFINE FIELD IF NOT EXISTS issues[*].suggestion   ON design_spec_reviews TYPE option<string>;
```

Use `option<string>` for nullable sub-fields; `string` for required sub-fields.

## Rule 3 — Use `model_dump()`, not `json.loads(model_dump_json())` (L-005 Finding 3)

SurrealDB rejects ISO strings for `datetime` fields:

```
InternalError: Couldn't coerce value for field `updated_at`: Expected `datetime` but found '2026-...'
```

`json.loads(model_dump_json())` converts Python `datetime` to an ISO string. The SurrealDB Python SDK serialises Python `datetime` objects to the correct SurrealDB datetime type — but only if they arrive as native `datetime`, not as strings.

```python
# ❌ WRONG — datetime becomes ISO string "2026-05-25T..."
data = json.loads(section.model_dump_json())

# ✅ CORRECT — datetime stays as Python datetime object
data = section.model_dump()
data.pop("id", None)  # strip id if present; let SurrealDB manage it
db.upsert(record_id).content(data)
```

## Rule 4 — Store `datetime.now(UTC)`, not `.isoformat()` (L-006)

Store native Python `datetime` objects in Pydantic models. Do NOT call `.isoformat()` at the model level — the SurrealDB SDK handles datetime serialisation.

```python
from datetime import UTC, datetime
from pydantic import BaseModel, Field

class MyModel(BaseModel):
    # ✅ CORRECT — Python datetime preserved through model_dump()
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    # ❌ WRONG — ISO string loses sortability and timezone semantics in SurrealDB
    # created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
```

Combined with Rule 3: `model_dump()` keeps `created_at` as a `datetime` object, which the SDK converts correctly. `json.loads(model_dump_json())` first converts it to a string, making Rule 4 irrelevant — both are wrong.

## Checklist for new SCHEMAFULL tables

```
- [ ] No FLEXIBLE keyword in any DEFINE FIELD statement
- [ ] Every nested object array (e.g. issues[*], findings[*]) has sub-field definitions
- [ ] All optional sub-fields use option<string> / option<int> / etc.
- [ ] All datetime fields use datetime = Field(default_factory=lambda: datetime.now(UTC))
- [ ] All write paths use model_dump(), not json.loads(model_dump_json())
- [ ] id is stripped from data dict before upsert (data.pop("id", None))
```
