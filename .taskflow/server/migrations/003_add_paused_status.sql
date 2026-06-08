-- 003: Add 'paused' status to tasks and projects
--
-- SQLite doesn't support ALTER TABLE ALTER CONSTRAINT, so we must
-- recreate both tables with the updated CHECK constraints.

-- Recreate projects table with 'paused' in status CHECK
CREATE TABLE projects_new (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    brief_text  TEXT,
    brief_path  TEXT,
    organisation TEXT,
    industry    TEXT,
    problem     TEXT,
    success_definition TEXT,
    out_of_scope TEXT,
    decision_maker_name TEXT,
    decision_maker_contact TEXT,
    acceptance_testers TEXT,
    hosting     TEXT,
    design_source TEXT,
    design_references TEXT,
    brand       TEXT,
    maintenance TEXT,
    deadline_date TEXT,
    deadline_type TEXT,
    deadline_reason TEXT,
    platforms   TEXT,
    status      TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'complete', 'archived')),
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);

INSERT INTO projects_new SELECT * FROM projects;
DROP TABLE projects;
ALTER TABLE projects_new RENAME TO projects;

-- Recreate tasks table with 'paused' in status CHECK
CREATE TABLE tasks_new (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER REFERENCES projects(id),
    feature_id      INTEGER REFERENCES features(id),
    step_id         INTEGER NOT NULL REFERENCES pipeline_steps(id),
    agent_role      TEXT NOT NULL CHECK (agent_role IN (
                        'product_manager', 'pm_reviewer', 'tester',
                        'test_reviewer', 'builder', 'documenter')),
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'in_progress', 'done', 'rejected', 'blocked', 'paused')),
    rejection_notes TEXT,
    retry_count     INTEGER NOT NULL DEFAULT 0,
    task_data       TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now', 'utc')),
    completed_at    TEXT
);

INSERT INTO tasks_new SELECT * FROM tasks;
DROP TABLE tasks;
ALTER TABLE tasks_new RENAME TO tasks;

SELECT 1;  -- no-op placeholder