# /dashboard

Opens the TaskFlow Dashboard in your browser to view project progress, tasks, features, retros, and decisions.

## What it does

Starts a local web server that reads from the TaskFlow SQLite database and serves an interactive dashboard at `http://127.0.0.1:8675`.

The dashboard shows:

- **Project overview** — task counts (done, in-progress, pending, blocked)
- **Features** — pipeline progress bar per feature, test pass/fail counts
- **All tasks** — filterable table with step, agent, status, retry count, rejection notes
- **Retros & Decisions** — retrospective summaries, recommendations, decisions, and decision artefacts (patterns, gotchas, notes, constraints)
- **Backlog** — pending feature backlog items with priority

Auto-refreshes every 30 seconds.

## Usage

```
/dashboard
```

## How to run manually

```bash
uv run .taskflow/server/dashboard.py
```

Or with a custom DB path:

```bash
DB_PATH=/path/to/taskflow.db uv run .taskflow/server/dashboard.py
```

The server uses only the Python standard library — no extra dependencies required.
