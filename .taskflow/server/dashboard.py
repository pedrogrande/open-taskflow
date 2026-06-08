#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
TaskFlow Dashboard — a local control plane for the agentic development pipeline.

Serves a web UI with read/write API endpoints backed by the TaskFlow SQLite
database. Supports task/project pause/resume, approval/rejection, agent
question answering, and agent invocation via VS Code deep-links.

Usage:
    uv run .taskflow/server/dashboard.py          # uses default DB path
    DB_PATH=/path/to/taskflow.db uv run .taskflow/server/dashboard.py

Opens the dashboard in your default browser automatically.
"""

from __future__ import annotations

import json
import os
import pathlib
import sqlite3
import sys
import urllib.parse
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DB_PATH: str = os.environ.get(
    "DB_PATH",
    str(pathlib.Path(__file__).parent.parent / "taskflow.db"),
)

PORT = int(os.environ.get("DASHBOARD_PORT", "8675"))

BRIEF_FORM_PATH = str(pathlib.Path(__file__).parent.parent / "project-brief-form.html")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def _row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


def _rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [_row_to_dict(r) for r in rows]


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


def api_projects() -> list[dict]:
    """Return all projects with task counts."""
    conn = _get_conn()
    try:
        projects = _rows_to_list(conn.execute("""
                SELECT p.*,
                    (SELECT COUNT(*) FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
                     WHERE t.project_id = p.id AND t.status = 'done') AS done_count,
                    (SELECT COUNT(*) FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
                     WHERE t.project_id = p.id AND t.status = 'in_progress') AS in_progress_count,
                    (SELECT COUNT(*) FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
                     WHERE t.project_id = p.id AND t.status = 'pending') AS pending_count,
                    (SELECT COUNT(*) FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
                     WHERE t.project_id = p.id AND t.status = 'blocked') AS blocked_count,
                    (SELECT COUNT(*) FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
                     WHERE t.project_id = p.id AND t.status = 'rejected') AS rejected_count,
                    (SELECT COUNT(*) FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id
                     WHERE t.project_id = p.id AND t.status = 'paused') AS paused_count
                FROM projects p
                ORDER BY p.created_at DESC
                """).fetchall())
        return projects
    finally:
        conn.close()


def api_pipeline_status(project_id: int) -> dict:
    """Return full pipeline state for a project."""
    conn = _get_conn()
    try:
        project = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if project is None:
            return {"error": "Project not found"}

        # Features with their task status
        features = _rows_to_list(
            conn.execute(
                """
                SELECT f.*,
                    (SELECT COUNT(*) FROM definitions_of_done WHERE feature_id = f.id) AS dod_count,
                    (SELECT COUNT(*) FROM test_specs WHERE feature_id = f.id) AS spec_count,
                    (SELECT COUNT(*) FROM test_results tr
                     JOIN test_specs ts ON ts.id = tr.test_spec_id
                     WHERE ts.feature_id = f.id AND tr.passed = 1) AS passed_count,
                    (SELECT COUNT(*) FROM test_results tr
                     JOIN test_specs ts ON ts.id = tr.test_spec_id
                     WHERE ts.feature_id = f.id AND tr.passed = 0) AS failed_count
                FROM features f
                WHERE f.project_id = ?
                ORDER BY f.order_index, f.id
                """,
                (project_id,),
            ).fetchall()
        )

        # All tasks grouped by status
        tasks = _rows_to_list(
            conn.execute(
                """
                SELECT t.*, ps.step_number, ps.name AS step_name
                FROM tasks t
                JOIN pipeline_steps ps ON ps.id = t.step_id
                WHERE t.project_id = ?
                ORDER BY t.feature_id, ps.step_number, t.id
                """,
                (project_id,),
            ).fetchall()
        )

        # Retro reports
        retros = _rows_to_list(
            conn.execute(
                """
                SELECT rr.*, f.title AS feature_title
                FROM retro_reports rr
                JOIN features f ON f.id = rr.feature_id
                WHERE f.project_id = ?
                ORDER BY rr.created_at
                """,
                (project_id,),
            ).fetchall()
        )

        # Recommendations
        recommendations = _rows_to_list(
            conn.execute(
                """
                SELECT rec.*, f.title AS feature_title
                FROM recommendations rec
                JOIN retro_reports rr ON rr.id = rec.retro_report_id
                JOIN features f ON f.id = rr.feature_id
                WHERE f.project_id = ?
                ORDER BY rec.id
                """,
                (project_id,),
            ).fetchall()
        )

        # Decisions
        decisions = _rows_to_list(
            conn.execute(
                """
                SELECT d.*, f.title AS feature_title
                FROM decisions d
                JOIN recommendations rec ON rec.id = d.recommendation_id
                JOIN retro_reports rr ON rr.id = rec.retro_report_id
                JOIN features f ON f.id = rr.feature_id
                WHERE f.project_id = ?
                ORDER BY d.created_at
                """,
                (project_id,),
            ).fetchall()
        )

        # Decision artefacts
        artefacts = _rows_to_list(
            conn.execute(
                """
                SELECT da.*, d.decision AS decision_summary, f.title AS feature_title
                FROM decision_artefacts da
                JOIN decisions d ON d.id = da.decision_id
                JOIN recommendations rec ON rec.id = d.recommendation_id
                JOIN retro_reports rr ON rr.id = rec.retro_report_id
                JOIN features f ON f.id = rr.feature_id
                WHERE f.project_id = ?
                ORDER BY da.created_at
                """,
                (project_id,),
            ).fetchall()
        )

        # Feature backlog
        backlog = _rows_to_list(
            conn.execute(
                "SELECT * FROM feature_backlog WHERE project_id = ? ORDER BY priority DESC, id",
                (project_id,),
            ).fetchall()
        )

        # Build reports
        builds = _rows_to_list(
            conn.execute(
                """
                SELECT br.*, f.title AS feature_title
                FROM build_reports br
                JOIN features f ON f.id = br.feature_id
                WHERE f.project_id = ?
                ORDER BY br.created_at
                """,
                (project_id,),
            ).fetchall()
        )

        # Agent questions (may not exist if migrations not yet applied)
        try:
            questions = _rows_to_list(
                conn.execute(
                    "SELECT * FROM agent_questions WHERE project_id = ? ORDER BY created_at DESC",
                    (project_id,),
                ).fetchall()
            )
        except sqlite3.OperationalError:
            questions = []

        # Schema version
        schema_version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]

        return {
            "project": _row_to_dict(project),
            "features": features,
            "tasks": tasks,
            "retros": retros,
            "recommendations": recommendations,
            "decisions": decisions,
            "artefacts": artefacts,
            "backlog": backlog,
            "builds": builds,
            "questions": questions,
            "schema_version": schema_version,
        }
    finally:
        conn.close()


def api_questions(project_id: int) -> list[dict]:
    """Return all agent questions for a project."""
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM agent_questions WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        return _rows_to_list(rows)
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Write API endpoints
# ---------------------------------------------------------------------------


def api_claim_task(task_id: int) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return {"error": f"Task {task_id} not found"}
        if row["status"] != "pending":
            return {
                "error": f"Task {task_id} is '{row['status']}', must be 'pending' to claim"
            }
        conn.execute("UPDATE tasks SET status = 'in_progress' WHERE id = ?", (task_id,))
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


def api_approve_task(task_id: int, notes: str | None = None) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT t.*, ps.step_number, ps.on_approval_spawn FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id WHERE t.id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            return {"error": f"Task {task_id} not found"}
        if row["status"] != "in_progress":
            return {
                "error": f"Task {task_id} is '{row['status']}', must be 'in_progress' to approve"
            }

        conn.execute("UPDATE tasks SET status = 'done' WHERE id = ?", (task_id,))

        # Spawn next tasks based on on_approval_spawn
        spawn = row["on_approval_spawn"]
        if spawn:
            try:
                spawn_list = json.loads(spawn) if isinstance(spawn, str) else spawn
            except (json.JSONDecodeError, TypeError):
                spawn_list = []

            for step_id in spawn_list:
                step = conn.execute(
                    "SELECT * FROM pipeline_steps WHERE id = ?", (step_id,)
                ).fetchone()
                if step:
                    conn.execute(
                        """INSERT INTO tasks (project_id, feature_id, step_id, agent_role, status, retry_count)
                           VALUES (?, ?, ?, ?, 'pending', 0)""",
                        (
                            row["project_id"],
                            row["feature_id"],
                            step_id,
                            step["agent_role"],
                        ),
                    )
        conn.commit()
        return {"ok": True, "task_id": task_id, "notes": notes}
    finally:
        conn.close()


def api_reject_task(task_id: int, notes: str) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT t.*, ps.step_number FROM tasks t JOIN pipeline_steps ps ON ps.id = t.step_id WHERE t.id = ?",
            (task_id,),
        ).fetchone()
        if row is None:
            return {"error": f"Task {task_id} not found"}
        if row["status"] not in ("in_progress", "pending"):
            return {"error": f"Task {task_id} is '{row['status']}', cannot reject"}

        new_retry = row["retry_count"] + 1
        if new_retry >= 3:
            conn.execute("UPDATE tasks SET status = 'blocked' WHERE id = ?", (task_id,))
            conn.commit()
            return {
                "ok": True,
                "task_id": task_id,
                "status": "blocked",
                "reason": "retry limit reached",
            }

        # For reviewer steps (2,4,6,11,13), re-create the preceding worker step
        reviewer_steps = {2, 4, 6, 11, 13}
        if row["step_number"] in reviewer_steps:
            prev_step = conn.execute(
                "SELECT * FROM pipeline_steps WHERE step_number = ?",
                (row["step_number"] - 1,),
            ).fetchone()
        else:
            prev_step = conn.execute(
                "SELECT * FROM pipeline_steps WHERE id = ?", (row["step_id"],)
            ).fetchone()

        conn.execute("UPDATE tasks SET status = 'rejected' WHERE id = ?", (task_id,))

        if prev_step:
            conn.execute(
                """INSERT INTO tasks (project_id, feature_id, step_id, agent_role, status, retry_count, rejection_notes)
                   VALUES (?, ?, ?, ?, 'pending', ?, ?)""",
                (
                    row["project_id"],
                    row["feature_id"],
                    prev_step["id"],
                    prev_step["agent_role"],
                    new_retry,
                    notes,
                ),
            )

        conn.commit()
        return {"ok": True, "task_id": task_id, "retry_count": new_retry}
    finally:
        conn.close()


def api_pause_task(task_id: int) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return {"error": f"Task {task_id} not found"}
        if row["status"] not in ("pending", "in_progress"):
            return {"error": f"Task {task_id} is '{row['status']}', cannot pause"}
        conn.execute("UPDATE tasks SET status = 'paused' WHERE id = ?", (task_id,))
        conn.commit()
        return {"ok": True, "task_id": task_id, "status": "paused"}
    finally:
        conn.close()


def api_resume_task(task_id: int) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return {"error": f"Task {task_id} not found"}
        if row["status"] != "paused":
            return {
                "error": f"Task {task_id} is '{row['status']}', must be 'paused' to resume"
            }
        conn.execute("UPDATE tasks SET status = 'pending' WHERE id = ?", (task_id,))
        conn.commit()
        return {"ok": True, "task_id": task_id, "status": "pending"}
    finally:
        conn.close()


def api_reset_task(task_id: int) -> dict:
    """Reset a blocked task back to pending with retry_count = 0."""
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return {"error": f"Task {task_id} not found"}
        if row["status"] not in ("blocked", "rejected"):
            return {
                "error": f"Task {task_id} is '{row['status']}', can only reset blocked/rejected"
            }
        conn.execute(
            "UPDATE tasks SET status = 'pending', retry_count = 0, rejection_notes = NULL WHERE id = ?",
            (task_id,),
        )
        conn.commit()
        return {"ok": True, "task_id": task_id, "status": "pending"}
    finally:
        conn.close()


def api_pause_project(project_id: int) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            return {"error": f"Project {project_id} not found"}
        if row["status"] != "active":
            return {
                "error": f"Project {project_id} is '{row['status']}', must be 'active' to pause"
            }
        conn.execute(
            "UPDATE projects SET status = 'paused' WHERE id = ?", (project_id,)
        )
        conn.commit()
        return {"ok": True, "project_id": project_id, "status": "paused"}
    finally:
        conn.close()


def api_resume_project(project_id: int) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        if row is None:
            return {"error": f"Project {project_id} not found"}
        if row["status"] != "paused":
            return {
                "error": f"Project {project_id} is '{row['status']}', must be 'paused' to resume"
            }
        conn.execute(
            "UPDATE projects SET status = 'active' WHERE id = ?", (project_id,)
        )
        conn.commit()
        return {"ok": True, "project_id": project_id, "status": "active"}
    finally:
        conn.close()


def api_answer_question(question_id: int, answer: str) -> dict:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT * FROM agent_questions WHERE id = ?", (question_id,)
        ).fetchone()
        if row is None:
            return {"error": f"Question {question_id} not found"}
        if row["answer"] is not None:
            return {"error": f"Question {question_id} already answered"}
        conn.execute(
            "UPDATE agent_questions SET answer = ?, answered_at = datetime('now') WHERE id = ?",
            (answer, question_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM agent_questions WHERE id = ?", (question_id,)
        ).fetchone()
        return _row_to_dict(updated)
    finally:
        conn.close()


def api_create_project(data: dict) -> dict:
    """Create a project from brief JSON (API mode from brief form)."""
    conn = _get_conn()
    try:
        name = data.get("name", "Untitled Project")
        brief_text = data.get("brief_text", data.get("problem", ""))

        cur = conn.execute(
            "INSERT INTO projects (name, brief_text, status) VALUES (?, ?, 'active')",
            (name, brief_text),
        )
        project_id = cur.lastrowid

        # If full brief data provided, populate brief tables
        if "outcomes" in data:
            for o in data["outcomes"]:
                conn.execute(
                    "INSERT INTO project_outcomes (project_id, outcome) VALUES (?, ?)",
                    (project_id, o.get("outcome", str(o))),
                )
        if "metrics" in data:
            for m in data["metrics"]:
                conn.execute(
                    "INSERT INTO success_metrics (project_id, metric, current_state, target, how_measured) VALUES (?, ?, ?, ?, ?)",
                    (
                        project_id,
                        m.get("metric", ""),
                        m.get("current_state", ""),
                        m.get("target", ""),
                        m.get("how_measured", ""),
                    ),
                )
        if "roles" in data:
            for r in data["roles"]:
                conn.execute(
                    "INSERT INTO user_roles (project_id, role, description, primary_workflow) VALUES (?, ?, ?, ?)",
                    (
                        project_id,
                        r.get("role", ""),
                        r.get("description", ""),
                        r.get("primary_workflow", ""),
                    ),
                )
        if "features" in data:
            for f in data["features"]:
                conn.execute(
                    "INSERT INTO brief_features (project_id, name, description, priority, phase) VALUES (?, ?, ?, ?, ?)",
                    (
                        project_id,
                        f.get("name", ""),
                        f.get("description", ""),
                        f.get("priority", "could"),
                        f.get("phase", "1"),
                    ),
                )
        if "workflows" in data:
            for w in data["workflows"]:
                conn.execute(
                    "INSERT INTO key_workflows (project_id, actor, trigger, steps, outcome) VALUES (?, ?, ?, ?, ?)",
                    (
                        project_id,
                        w.get("actor", ""),
                        w.get("trigger", ""),
                        w.get("steps", ""),
                        w.get("outcome", ""),
                    ),
                )
        if "stakeholders" in data:
            for s in data["stakeholders"]:
                conn.execute(
                    "INSERT INTO stakeholders (project_id, name, title, authority) VALUES (?, ?, ?, ?)",
                    (
                        project_id,
                        s.get("name", ""),
                        s.get("title", ""),
                        s.get("authority", ""),
                    ),
                )
        if "risks" in data:
            for r in data["risks"]:
                conn.execute(
                    "INSERT INTO project_risks (project_id, description, likelihood, impact, mitigation) VALUES (?, ?, ?, ?, ?)",
                    (
                        project_id,
                        r.get("description", ""),
                        r.get("likelihood", "M"),
                        r.get("impact", "M"),
                        r.get("mitigation", ""),
                    ),
                )
        if "integrations" in data:
            for i in data["integrations"]:
                conn.execute(
                    "INSERT INTO integrations (project_id, system, purpose, direction, auth_method, phase_1_required) VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        project_id,
                        i.get("system", ""),
                        i.get("purpose", ""),
                        i.get("direction", ""),
                        i.get("auth_method", ""),
                        i.get("phase_1_required", False),
                    ),
                )
        if "phases" in data:
            for ph in data["phases"]:
                conn.execute(
                    "INSERT INTO release_phases (project_id, phase_number, description, target_date) VALUES (?, ?, ?, ?)",
                    (
                        project_id,
                        ph.get("phase_number", "1"),
                        ph.get("description", ""),
                        ph.get("target_date", ""),
                    ),
                )
        if "nfrs" in data:
            for n in data["nfrs"]:
                conn.execute(
                    "INSERT INTO non_functional_requirements (project_id, nfr_type, notes) VALUES (?, ?, ?)",
                    (project_id, n.get("nfr_type", "other"), n.get("notes", "")),
                )

        # Seed step-3 task (feature definition)
        step3 = conn.execute(
            "SELECT id FROM pipeline_steps WHERE step_number = 3"
        ).fetchone()
        if step3:
            conn.execute(
                "INSERT INTO tasks (project_id, step_id, agent_role, status, retry_count) VALUES (?, ?, 'product_manager', 'pending', 0)",
                (project_id, step3["id"]),
            )

        conn.commit()
        return {"ok": True, "project_id": project_id, "name": name}
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# HTML dashboard — loaded from external files
# ---------------------------------------------------------------------------

DASHBOARD_DIR = pathlib.Path(__file__).parent
DASHBOARD_HTML_PATH = DASHBOARD_DIR / "dashboard.html"
DOCS_DIR = DASHBOARD_DIR / "docs"


def _load_dashboard_html() -> str:
    """Load the dashboard HTML from the external file."""
    if DASHBOARD_HTML_PATH.exists():
        return DASHBOARD_HTML_PATH.read_text("utf-8")
    return "<html><body><h1>Dashboard HTML not found</h1></body></html>"


def _load_doc_page(page: str) -> str:
    """Load a documentation page HTML fragment from the docs directory."""
    doc_path = DOCS_DIR / f"{page}.html"
    if doc_path.exists():
        return doc_path.read_text("utf-8")
    return "<p>Page not found</p>"


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self._html_response(_load_dashboard_html())

        elif self.path in ("/about", "/quick-start", "/using"):
            self._html_response(_load_dashboard_html())

        elif self.path == "/brief" or self.path.startswith("/brief?"):
            self._serve_brief_form()

        elif self.path.startswith("/api/docs/"):
            page = self.path.split("/")[-1]
            html = _load_doc_page(page)
            if html == "<p>Page not found</p>":
                self._json_response(
                    {"error": "Page not found", "html": html}, status=404
                )
            else:
                self._json_response({"html": html})

        elif self.path == "/api/projects":
            self._json_response(api_projects())

        elif self.path.startswith("/api/pipeline/"):
            try:
                project_id = int(self.path.split("/")[-1])
                self._json_response(api_pipeline_status(project_id))
            except (ValueError, IndexError):
                self._json_response({"error": "Invalid project ID"}, status=400)

        elif self.path.startswith("/api/questions/"):
            try:
                project_id = int(self.path.split("/")[-1])
                self._json_response(api_questions(project_id))
            except (ValueError, IndexError):
                self._json_response({"error": "Invalid project ID"}, status=400)

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length else ""

        # Parse body based on content type
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._json_response({"error": "Invalid JSON"}, status=400)
                return
        elif "application/x-www-form-urlencoded" in content_type:
            data = dict(urllib.parse.parse_qs(body))
            # Flatten single-value params
            data = {k: v[0] if len(v) == 1 else v for k, v in data.items()}
        else:
            data = {}

        # Route POST endpoints
        path = self.path

        # Task actions
        if path.startswith("/api/tasks/") and path.endswith("/claim"):
            task_id = self._extract_task_id(path, "/claim")
            if task_id is None:
                self._json_response({"error": "Invalid task ID"}, status=400)
                return
            self._json_response(api_claim_task(task_id))

        elif path.startswith("/api/tasks/") and path.endswith("/approve"):
            task_id = self._extract_task_id(path, "/approve")
            if task_id is None:
                self._json_response({"error": "Invalid task ID"}, status=400)
                return
            notes = data.get("notes", "")
            self._json_response(api_approve_task(task_id, notes))

        elif path.startswith("/api/tasks/") and path.endswith("/reject"):
            task_id = self._extract_task_id(path, "/reject")
            if task_id is None:
                self._json_response({"error": "Invalid task ID"}, status=400)
                return
            notes = data.get("notes", "")
            if not notes:
                self._json_response({"error": "Rejection notes required"}, status=400)
                return
            self._json_response(api_reject_task(task_id, notes))

        elif path.startswith("/api/tasks/") and path.endswith("/pause"):
            task_id = self._extract_task_id(path, "/pause")
            if task_id is None:
                self._json_response({"error": "Invalid task ID"}, status=400)
                return
            self._json_response(api_pause_task(task_id))

        elif path.startswith("/api/tasks/") and path.endswith("/resume"):
            task_id = self._extract_task_id(path, "/resume")
            if task_id is None:
                self._json_response({"error": "Invalid task ID"}, status=400)
                return
            self._json_response(api_resume_task(task_id))

        elif path.startswith("/api/tasks/") and path.endswith("/reset"):
            task_id = self._extract_task_id(path, "/reset")
            if task_id is None:
                self._json_response({"error": "Invalid task ID"}, status=400)
                return
            self._json_response(api_reset_task(task_id))

        # Project actions
        elif path.startswith("/api/projects/") and path.endswith("/pause"):
            project_id = self._extract_id(path, "/api/projects/", "/pause")
            if project_id is None:
                self._json_response({"error": "Invalid project ID"}, status=400)
                return
            self._json_response(api_pause_project(project_id))

        elif path.startswith("/api/projects/") and path.endswith("/resume"):
            project_id = self._extract_id(path, "/api/projects/", "/resume")
            if project_id is None:
                self._json_response({"error": "Invalid project ID"}, status=400)
                return
            self._json_response(api_resume_project(project_id))

        # Create project (from brief form API mode)
        elif path == "/api/projects":
            self._json_response(api_create_project(data))

        # Answer question
        elif path.startswith("/api/questions/") and path.endswith("/answer"):
            question_id = self._extract_id(path, "/api/questions/", "/answer")
            if question_id is None:
                self._json_response({"error": "Invalid question ID"}, status=400)
                return
            answer = data.get("answer", "")
            if not answer:
                self._json_response({"error": "Answer required"}, status=400)
                return
            self._json_response(api_answer_question(question_id, answer))

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

    def _extract_task_id(self, path: str, suffix: str) -> int | None:
        """Extract task ID from paths like /api/tasks/42/claim"""
        try:
            prefix = "/api/tasks/"
            stripped = path[len(prefix) :]
            id_str = stripped[: stripped.index("/")]
            return int(id_str)
        except (ValueError, IndexError):
            return None

    def _extract_id(self, path: str, prefix: str, suffix: str) -> int | None:
        """Extract integer ID from paths like /api/projects/5/pause"""
        try:
            stripped = path[len(prefix) :]
            id_str = stripped[: stripped.index("/")]
            return int(id_str)
        except (ValueError, IndexError):
            return None

    def _serve_brief_form(self):
        """Serve the project brief form HTML."""
        form_path = pathlib.Path(BRIEF_FORM_PATH)
        if not form_path.exists():
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Brief form not found at " + BRIEF_FORM_PATH.encode())
            return
        html = form_path.read_text("utf-8")
        self._html_response(html)

    def _html_response(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def log_message(self, format, *args):
        pass


def _run_migrations():
    """Apply any pending schema migrations (same logic as mcp_server.py)."""
    migrations_dir = pathlib.Path(__file__).parent / "migrations"
    if not migrations_dir.is_dir():
        return

    conn = _get_conn()
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, "
            "name TEXT NOT NULL, "
            "applied_at TEXT NOT NULL DEFAULT (datetime('now', 'utc'))"
            ")"
        )
        conn.commit()
        applied = {
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }

        for path in sorted(migrations_dir.glob("*.sql")):
            version = int(path.stem.split("_", 1)[0])
            if version in applied:
                continue
            sql = path.read_text("utf-8")
            try:
                conn.executescript(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                    (version, path.stem),
                )
                conn.commit()
                print(f"  Applied migration {path.stem}")
            except sqlite3.OperationalError as e:
                # If the migration fails because the object already exists
                # (fresh DB created with init.sql), record it and continue.
                if "already exists" in str(e):
                    conn.execute(
                        "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                        (version, path.stem),
                    )
                    conn.commit()
                else:
                    raise
    finally:
        conn.close()


def main():
    if not pathlib.Path(DB_PATH).exists():
        print(f"⚠  Database not found at {DB_PATH}")
        print("   Start TaskFlow first to create the database, then run the dashboard.")
        return

    # Apply any pending migrations
    _run_migrations()

    server = HTTPServer(("127.0.0.1", PORT), DashboardHandler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"✓ TaskFlow Dashboard running at {url}")
    print(f"  Database: {DB_PATH}")
    print(f"  Brief form: {url}/brief")
    print(f"  Press Ctrl+C to stop")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
