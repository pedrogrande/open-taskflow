# Schema Migrations

Numbered SQL files that alter the TaskFlow schema after the initial release.

## Naming convention

```
{number}_{name}.sql
```

- `number` — zero-padded 3-digit integer (001, 002, 003, …)
- `name` — lowercase, underscore-separated description (e.g. `add_cycle_number`)

## How they work

1. On startup, `_run_migrations()` reads all `*.sql` files in this directory.
2. It checks the `schema_migrations` table for already-applied versions.
3. Pending migrations are applied in version order, each inside its own transaction.
4. After applying, the version is recorded in `schema_migrations` so it never runs again.

## Rules

- **Migrations must be idempotent where possible** — use `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` patterns or guard with `SELECT` checks.
- **Never edit an existing migration file** — create a new one instead.
- **Never reorder or renumber migrations** — the version number is the identity.
- **Test against both fresh and existing databases** before committing.

## Example

```sql
-- 001_add_cycle_number.sql
ALTER TABLE features ADD COLUMN cycle_number INTEGER NOT NULL DEFAULT 1;
```
