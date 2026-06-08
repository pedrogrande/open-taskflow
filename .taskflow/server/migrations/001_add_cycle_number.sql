-- Migration 001: add cycle_number to features
-- This is a test migration to verify the migration system works.
-- It adds a cycle_number column to the features table so features can be
-- tracked across multiple pipeline cycles.

-- Guard: only add column if it doesn't already exist.
-- SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN,
-- so we check the column list first. This also makes the migration safe
-- to run on fresh databases where init.sql already includes the column.

-- Note: SQLite doesn't allow IF/ELSE in pure SQL, so we use a trick:
-- the _run_migrations() function in mcp_server.py catches OperationalError
-- for "duplicate column name" and treats it as already-applied.
-- However, the safest approach is to NOT use ALTER TABLE in migrations
-- that might conflict with init.sql. Instead, we rely on the fact that
-- _ensure_db() runs first (creating the full schema including cycle_number),
-- and _run_migrations() runs second. If the column already exists, this
-- migration is a no-op because the version is already recorded.

-- For existing databases that DON'T have cycle_number yet:
-- We can't use conditional ALTER TABLE in SQLite, so we use a workaround:
-- create a temporary trigger that silently ignores the error.

-- Actually, the simplest approach: just try the ALTER TABLE and catch the
-- error in Python. But executescript() doesn't allow that.
-- 
-- The REAL solution: make _run_migrations() handle "duplicate column" errors
-- gracefully. See the updated _run_migrations() in mcp_server.py.

ALTER TABLE features ADD COLUMN cycle_number INTEGER NOT NULL DEFAULT 1;