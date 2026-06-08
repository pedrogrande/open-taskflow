"""
TaskFlow — shared database operations.

Used by both the MCP server (mcp_server.py) and the dashboard (dashboard.py).
All write operations that both servers need live here so validation logic is
not duplicated.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RETRY_LIMIT = 3

# Reviewer step numbers (their job is to approve/reject the preceding worker)
REVIEWER_STEPS = {2, 4, 6, 11, 13}

# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------


def get_conn(db_path: str) -> sqlite3.Connection:
    """Return a connection with Row factory, FK enforcement, and WAL mode."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    return [row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Task operations
# ---------------------------------------------------------------------------


def claim_task(db_path: str, task_id: int) -> dict[str, Any]:
    """Mark a task as in_progress. Raises ValueError if not claimable."""
    conn = get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        if row["status"] != "pending":
            raise ValueError(
                f"Task {task_id} cannot be claimed: status is '{row['status']}'"
            )
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


def approve_task(
    db_path: str, task_id: int, notes: str | None = None
) -> dict[str, Any]:
    """Approve a task and cascade next step(s). Returns result dict."""
    conn = get_conn(db_path)
    try:
        task = conn.execute(
            """
            SELECT t.*, ps.step_number, ps.on_approval_spawn, ps.requires_approval
            FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        if task["status"] not in ("in_progress", "pending"):
            raise ValueError(
                f"Task {task_id} cannot be approved: status is '{task['status']}'"
            )

        project_id = task["project_id"]
        spawn_spec = task["on_approval_spawn"]
        new_ids: list[int] = []

        if spawn_spec:
            if spawn_spec == "per_feature":
                features = conn.execute(
                    "SELECT id FROM features WHERE project_id = ?", (project_id,)
                ).fetchall()
                step = conn.execute(
                    "SELECT * FROM pipeline_steps WHERE step_number = 5"
                ).fetchone()
                for feat in features:
                    cur = conn.execute(
                        """
                        INSERT INTO tasks (project_id, feature_id, step_id, agent_role, status)
                        VALUES (?, ?, ?, ?, 'pending')
                        """,
                        (project_id, feat["id"], step["id"], step["agent_role"]),
                    )
                    new_ids.append(cur.lastrowid)
            else:
                step_numbers = json.loads(spawn_spec)
                new_ids = _spawn_tasks(
                    conn, project_id, step_numbers, feature_id=task["feature_id"]
                )

        conn.execute(
            """
            UPDATE tasks
            SET status = 'done', rejection_notes = ?, completed_at = datetime('now','utc')
            WHERE id = ?
            """,
            (notes, task_id),
        )
        conn.commit()

        return {
            "approved_task_id": task_id,
            "step_number": task["step_number"],
            "spawned_task_ids": new_ids,
            "notes": notes,
        }
    finally:
        conn.close()


def reject_task(db_path: str, task_id: int, notes: str) -> dict[str, Any]:
    """Reject a task and re-create the appropriate worker task. Returns result dict."""
    conn = get_conn(db_path)
    try:
        task = conn.execute(
            """
            SELECT t.*, ps.step_number, ps.requires_approval
            FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
            WHERE t.id = ?
            """,
            (task_id,),
        ).fetchone()
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        if task["status"] not in ("in_progress", "pending"):
            raise ValueError(
                f"Task {task_id} cannot be rejected: status is '{task['status']}'"
            )

        project_id = task["project_id"]
        current_step = task["step_number"]
        feature_id = task["feature_id"]

        is_reviewer_step = current_step in REVIEWER_STEPS
        worker_step_number = (current_step - 1) if is_reviewer_step else current_step
        new_retry = task["retry_count"] + 1

        conn.execute(
            """
            UPDATE tasks
            SET status = 'rejected', rejection_notes = ?, completed_at = datetime('now','utc')
            WHERE id = ?
            """,
            (notes, task_id),
        )

        if new_retry >= RETRY_LIMIT:
            worker_step = conn.execute(
                "SELECT * FROM pipeline_steps WHERE step_number = ?",
                (worker_step_number,),
            ).fetchone()
            conn.execute(
                """
                INSERT INTO tasks
                    (project_id, feature_id, step_id, agent_role, status, rejection_notes, retry_count)
                VALUES (?, ?, ?, ?, 'blocked', ?, ?)
                """,
                (
                    project_id,
                    feature_id,
                    worker_step["id"],
                    worker_step["agent_role"],
                    notes,
                    new_retry,
                ),
            )
            conn.commit()
            return {
                "rejected_task_id": task_id,
                "result": "blocked",
                "retry_count": new_retry,
                "notes": notes,
            }
        else:
            worker_step = conn.execute(
                "SELECT * FROM pipeline_steps WHERE step_number = ?",
                (worker_step_number,),
            ).fetchone()
            cur = conn.execute(
                """
                INSERT INTO tasks
                    (project_id, feature_id, step_id, agent_role, status, rejection_notes, retry_count)
                VALUES (?, ?, ?, ?, 'pending', ?, ?)
                """,
                (
                    project_id,
                    feature_id,
                    worker_step["id"],
                    worker_step["agent_role"],
                    notes,
                    new_retry,
                ),
            )
            new_task_id = cur.lastrowid
            conn.commit()
            return {
                "rejected_task_id": task_id,
                "result": "retrying",
                "new_task_id": new_task_id,
                "retry_count": new_retry,
                "notes": notes,
            }
    finally:
        conn.close()


def pause_task(db_path: str, task_id: int) -> dict[str, Any]:
    """Pause a pending or in_progress task. Returns updated task."""
    conn = get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        if row["status"] not in ("pending", "in_progress"):
            raise ValueError(
                f"Task {task_id} cannot be paused: status is '{row['status']}'"
            )
        conn.execute("UPDATE tasks SET status = 'paused' WHERE id = ?", (task_id,))
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


def resume_task(db_path: str, task_id: int) -> dict[str, Any]:
    """Resume a paused task back to pending. Returns updated task."""
    conn = get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        if row["status"] != "paused":
            raise ValueError(
                f"Task {task_id} cannot be resumed: status is '{row['status']}'"
            )
        conn.execute("UPDATE tasks SET status = 'pending' WHERE id = ?", (task_id,))
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


def reset_task(db_path: str, task_id: int) -> dict[str, Any]:
    """Reset a blocked task: set retry_count=0, status=pending. Returns updated task."""
    conn = get_conn(db_path)
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Task {task_id} not found")
        if row["status"] != "blocked":
            raise ValueError(
                f"Task {task_id} cannot be reset: status is '{row['status']}' (only blocked tasks can be reset)"
            )
        conn.execute(
            "UPDATE tasks SET status = 'pending', retry_count = 0 WHERE id = ?",
            (task_id,),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------


def pause_project(db_path: str, project_id: int) -> dict[str, Any]:
    """Pause a project. No new tasks will be claimed while paused."""
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Project {project_id} not found")
        if row["status"] != "active":
            raise ValueError(
                f"Project {project_id} cannot be paused: status is '{row['status']}'"
            )
        conn.execute(
            "UPDATE projects SET status = 'paused' WHERE id = ?", (project_id,)
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


def resume_project(db_path: str, project_id: int) -> dict[str, Any]:
    """Resume a paused project back to active."""
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Project {project_id} not found")
        if row["status"] != "paused":
            raise ValueError(
                f"Project {project_id} cannot be resumed: status is '{row['status']}'"
            )
        conn.execute(
            "UPDATE projects SET status = 'active' WHERE id = ?", (project_id,)
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


def finalise_brief(
    db_path: str, project_id: int, force: bool = False
) -> dict[str, Any]:
    """Finalise a project brief and spawn step-3 task.

    Returns dict with status 'finalised' on success, or 'incomplete' if
    the brief has gaps and force=False.
    """
    conn = get_conn(db_path)
    try:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if project is None:
            raise ValueError(f"Project {project_id} not found")

        # Completeness guard — check if brief has enough content
        if not force:
            has_name = bool(project["name"] and project["name"] != "New Project")
            has_problem = bool(project["problem"])
            has_brief_text = bool(project["brief_text"])
            outcomes = conn.execute(
                "SELECT COUNT(*) FROM project_outcomes WHERE project_id=?",
                (project_id,),
            ).fetchone()[0]
            features = conn.execute(
                "SELECT COUNT(*) FROM brief_features WHERE project_id=?", (project_id,)
            ).fetchone()[0]

            gaps = []
            if not has_name:
                gaps.append("Project name is missing")
            if not has_problem and not has_brief_text:
                gaps.append("Problem statement or brief text is missing")
            if outcomes == 0 and features == 0:
                gaps.append("No outcomes or features defined")

            if gaps:
                return {
                    "status": "incomplete",
                    "message": "Brief is not yet complete. Resolve the gaps or use force=True.",
                    "gaps": gaps,
                }

        # Only spawn step-3 if one doesn't already exist
        step3_row = conn.execute(
            """
            SELECT t.id FROM tasks t
            JOIN pipeline_steps ps ON ps.id = t.step_id
            WHERE t.project_id = ? AND ps.step_number = 3
              AND t.status IN ('pending', 'in_progress')
            """,
            (project_id,),
        ).fetchone()

        spawned_ids: list[int] = []
        if step3_row is None:
            spawned_ids = _spawn_tasks(conn, project_id, [3])

        conn.commit()

        return {
            "status": "finalised",
            "project_id": project_id,
            "project_name": project["name"],
            "spawned_task_ids": spawned_ids,
            "step3_already_existed": step3_row is not None,
            "message": "Brief finalised. Product Manager step-3 task is ready.",
        }
    finally:
        conn.close()


def ingest_brief(db_path: str, brief_json: str) -> dict[str, Any]:
    """Parse project brief JSON and store all structured data. Returns result dict."""
    try:
        data = json.loads(brief_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}") from e

    identity = data.get("project_identity", {})
    goals = data.get("goals", {})
    users = data.get("users", {})
    nfr = data.get("non_functional", {})
    platforms = data.get("platforms", {})
    design = data.get("design", {})
    timeline = data.get("timeline", {})
    deadline = timeline.get("deadline", {})
    dm = users.get("decision_maker", {})

    name = (identity.get("name") or "").strip() or "Untitled Project"

    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO projects (
                name, brief_text,
                organisation, industry, problem, success_definition, out_of_scope,
                decision_maker_name, decision_maker_contact, acceptance_testers,
                hosting, design_source, design_references, brand, maintenance,
                deadline_date, deadline_type, deadline_reason, platforms
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                name,
                json.dumps(data, ensure_ascii=False),
                identity.get("organisation"),
                identity.get("industry"),
                identity.get("problem"),
                identity.get("success_definition"),
                identity.get("out_of_scope"),
                dm.get("name"),
                dm.get("contact"),
                users.get("acceptance_testers"),
                platforms.get("hosting"),
                design.get("source"),
                design.get("references"),
                design.get("brand"),
                design.get("maintenance"),
                deadline.get("date") or None,
                deadline.get("type") or None,
                deadline.get("reason"),
                json.dumps(platforms.get("targets", [])),
            ),
        )
        project_id = cur.lastrowid

        # project_outcomes
        for i, outcome in enumerate(goals.get("outcomes", [])):
            if outcome:
                conn.execute(
                    "INSERT INTO project_outcomes (project_id, outcome, order_index) VALUES (?,?,?)",
                    (project_id, outcome, i),
                )

        # success_metrics
        for m in goals.get("metrics", []):
            if any(m.get(k) for k in ("metric", "target")):
                conn.execute(
                    "INSERT INTO success_metrics (project_id, metric, current_state, target, how_measured) VALUES (?,?,?,?,?)",
                    (
                        project_id,
                        m.get("metric"),
                        m.get("current_state"),
                        m.get("target"),
                        m.get("how_measured"),
                    ),
                )

        # user_roles
        for r in users.get("roles", []):
            if r.get("role"):
                conn.execute(
                    "INSERT INTO user_roles (project_id, role, description, primary_workflow) VALUES (?,?,?,?)",
                    (
                        project_id,
                        r.get("role"),
                        r.get("description"),
                        r.get("primary_workflow"),
                    ),
                )

        # stakeholders
        for s in users.get("stakeholders", []):
            if s.get("name"):
                conn.execute(
                    "INSERT INTO stakeholders (project_id, name, title, authority) VALUES (?,?,?,?)",
                    (project_id, s.get("name"), s.get("title"), s.get("authority")),
                )

        # key_workflows
        for i, w in enumerate(data.get("workflows", [])):
            if w.get("actor") or w.get("steps"):
                conn.execute(
                    "INSERT INTO key_workflows (project_id, actor, trigger, steps, outcome, order_index) VALUES (?,?,?,?,?,?)",
                    (
                        project_id,
                        w.get("actor"),
                        w.get("trigger"),
                        w.get("steps"),
                        w.get("outcome"),
                        i,
                    ),
                )

        # non_functional_requirements
        for nfr_type, val in nfr.items():
            if isinstance(val, dict) and val.get("required"):
                conn.execute(
                    "INSERT INTO non_functional_requirements (project_id, nfr_type, notes) VALUES (?,?,?)",
                    (project_id, nfr_type, val.get("notes")),
                )

        # integrations
        for integ in data.get("integrations", {}).get("systems", []):
            if integ.get("system"):
                conn.execute(
                    "INSERT INTO integrations (project_id, system, purpose, direction, auth_method, phase_1_required) VALUES (?,?,?,?,?,?)",
                    (
                        project_id,
                        integ.get("system"),
                        integ.get("purpose"),
                        integ.get("direction"),
                        integ.get("auth_method"),
                        1 if integ.get("phase_1_required") == "yes" else 0,
                    ),
                )

        # project_risks
        for risk in data.get("risks", []):
            if risk.get("description"):
                conn.execute(
                    "INSERT INTO project_risks (project_id, description, likelihood, impact, mitigation) VALUES (?,?,?,?,?)",
                    (
                        project_id,
                        risk.get("description"),
                        risk.get("likelihood"),
                        risk.get("impact"),
                        risk.get("mitigation"),
                    ),
                )

        # release_phases
        for phase in timeline.get("release_phases", []):
            if phase.get("description") or phase.get("phase"):
                conn.execute(
                    "INSERT INTO release_phases (project_id, phase_number, description, target_date) VALUES (?,?,?,?)",
                    (
                        project_id,
                        phase.get("phase"),
                        phase.get("description"),
                        phase.get("target_date") or None,
                    ),
                )

        # brief_features
        for feat in data.get("features", []):
            if feat.get("name"):
                conn.execute(
                    "INSERT INTO brief_features (project_id, name, description, priority, phase) VALUES (?,?,?,?,?)",
                    (
                        project_id,
                        feat.get("name"),
                        feat.get("description"),
                        feat.get("priority"),
                        feat.get("phase"),
                    ),
                )

        # existing_project: completed features & tech debt
        existing = data.get("existing_project", {})
        if existing:
            for cf in existing.get("completed_features", []):
                feature_name = cf.get("feature", "").strip()
                if feature_name:
                    status = cf.get("status", "working")
                    notes = cf.get("notes", "")
                    desc = f"[Already built — {status}]"
                    if notes:
                        desc += f" {notes}"
                    conn.execute(
                        "INSERT INTO brief_features (project_id, name, description, priority, phase) VALUES (?,?,?,?,?)",
                        (project_id, feature_name, desc, "Must", "1"),
                    )

            priority_map = {
                "must_fix": "Must",
                "should_fix": "Should",
                "nice_to_fix": "Could",
            }
            for td in existing.get("tech_debt", []):
                issue = td.get("issue", "").strip()
                if issue:
                    priority = priority_map.get(
                        td.get("priority", "should_fix"), "Should"
                    )
                    notes = td.get("notes", "")
                    desc = f"[Tech debt] {issue}"
                    if notes:
                        desc += f" — {notes}"
                    conn.execute(
                        "INSERT INTO brief_features (project_id, name, description, priority, phase) VALUES (?,?,?,?,?)",
                        (project_id, issue, desc, priority, "1"),
                    )

        # Spawn step-3 task
        new_ids = _spawn_tasks(conn, project_id, [3])
        conn.commit()

        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return {
            "project": row_to_dict(project),
            "spawned_task_ids": new_ids,
            "message": f"Project '{name}' created from brief JSON. Step-3 task seeded.",
        }
    finally:
        conn.close()


def promote_backlog_item(
    db_path: str,
    backlog_id: int,
    title: str,
    description: str,
    source_requirement_text: str | None = None,
    order_index: int = 0,
) -> dict[str, Any]:
    """Promote a backlog item to a feature. Returns result dict."""
    conn = get_conn(db_path)
    try:
        item = conn.execute(
            "SELECT * FROM feature_backlog WHERE id = ?", (backlog_id,)
        ).fetchone()
        if item is None:
            raise ValueError(f"Backlog item {backlog_id} not found")
        if item["status"] != "pending":
            raise ValueError(
                f"Backlog item {backlog_id} has status '{item['status']}'; only 'pending' items can be promoted"
            )

        cur = conn.execute(
            "INSERT INTO features (project_id, title, description, source_requirement_text, order_index) VALUES (?, ?, ?, ?, ?)",
            (
                item["project_id"],
                title,
                description,
                source_requirement_text,
                order_index,
            ),
        )
        feature_id = cur.lastrowid

        conn.execute(
            "UPDATE feature_backlog SET status = 'promoted' WHERE id = ?", (backlog_id,)
        )
        conn.commit()

        feature = conn.execute(
            "SELECT * FROM features WHERE id = ?", (feature_id,)
        ).fetchone()
        return {"feature": row_to_dict(feature), "backlog_item_status": "promoted"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Agent questions
# ---------------------------------------------------------------------------


def ask_human(
    db_path: str,
    project_id: int,
    question: str,
    options: list[str] | None = None,
    context: str | None = None,
    task_id: int | None = None,
    agent_role: str = "unknown",
) -> dict[str, Any]:
    """Post a question for the human. Returns question record."""
    conn = get_conn(db_path)
    try:
        cur = conn.execute(
            """
            INSERT INTO agent_questions (project_id, task_id, agent_role, question, options, context)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                project_id,
                task_id,
                agent_role,
                question,
                json.dumps(options) if options else None,
                context,
            ),
        )
        question_id = cur.lastrowid
        conn.commit()

        row = conn.execute(
            "SELECT * FROM agent_questions WHERE id = ?", (question_id,)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


def read_answer(db_path: str, question_id: int) -> dict[str, Any] | None:
    """Check if a human has answered the question. Returns answer or None."""
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM agent_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Question {question_id} not found")
        return row_to_dict(row)
    finally:
        conn.close()


def answer_question(db_path: str, question_id: int, answer: str) -> dict[str, Any]:
    """Record a human answer to an agent question. Returns updated question."""
    conn = get_conn(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM agent_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Question {question_id} not found")
        if row["answer"] is not None:
            raise ValueError(f"Question {question_id} has already been answered")
        conn.execute(
            "UPDATE agent_questions SET answer = ?, answered_at = datetime('now','utc') WHERE id = ?",
            (answer, question_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM agent_questions WHERE id = ?", (question_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _spawn_tasks(
    conn: sqlite3.Connection,
    project_id: int,
    step_numbers: list[int],
    feature_id: int | None = None,
) -> list[int]:
    """Insert one pending task per step_number. Returns list of new task IDs."""
    new_ids: list[int] = []
    for sn in step_numbers:
        step = conn.execute(
            "SELECT * FROM pipeline_steps WHERE step_number = ?", (sn,)
        ).fetchone()
        if step is None:
            raise ValueError(f"pipeline_steps has no step_number={sn}")
        cur = conn.execute(
            """
            INSERT INTO tasks (project_id, feature_id, step_id, agent_role, status)
            VALUES (?, ?, ?, ?, 'pending')
            """,
            (project_id, feature_id, step["id"], step["agent_role"]),
        )
        new_ids.append(cur.lastrowid)
    return new_ids
