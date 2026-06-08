-- 004: Add agent_questions table for human-in-the-loop via dashboard

CREATE TABLE IF NOT EXISTS agent_questions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    task_id     INTEGER REFERENCES tasks(id),
    agent_role  TEXT NOT NULL,
    question    TEXT NOT NULL,
    options     TEXT,       -- JSON array of option strings
    context     TEXT,       -- additional context the agent provides
    answer      TEXT,       -- null until answered
    answered_at TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now', 'utc'))
);