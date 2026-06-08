#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
TaskFlow Dashboard — a local web UI for viewing pipeline progress.

Starts a lightweight HTTP server that serves a dashboard page and a JSON API
backed by the TaskFlow SQLite database. No external dependencies required
(uses only the Python standard library).

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

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
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
                     WHERE t.project_id = p.id AND t.status = 'rejected') AS rejected_count
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
            "schema_version": schema_version,
        }
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# HTML dashboard
# ---------------------------------------------------------------------------

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TaskFlow Dashboard</title>
<style>
  :root {
    --bg: #0d1117;
    --surface: #161b22;
    --border: #30363d;
    --text: #e6edf3;
    --text-muted: #8b949e;
    --accent: #58a6ff;
    --green: #3fb950;
    --yellow: #d29922;
    --red: #f85149;
    --purple: #bc8cff;
    --orange: #db6d28;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 24px;
  }
  h1 { font-size: 1.5rem; margin-bottom: 16px; }
  h2 { font-size: 1.2rem; margin: 24px 0 12px; color: var(--accent); }
  h3 { font-size: 1rem; margin: 16px 0 8px; }
  .header { display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }
  .header img { height: 32px; }
  .header span { color: var(--text-muted); font-size: 0.85rem; }

  /* Project selector */
  .project-selector { margin-bottom: 24px; }
  .project-selector select {
    background: var(--surface);
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 0.9rem;
    min-width: 300px;
  }

  /* Cards */
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
  }
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
    margin-bottom: 16px;
  }
  .stat-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }
  .stat-card .number { font-size: 2rem; font-weight: 700; }
  .stat-card .label { font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }

  /* Status badges */
  .badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.03em;
  }
  .badge-done { background: rgba(63,185,80,0.15); color: var(--green); }
  .badge-in_progress { background: rgba(210,153,34,0.15); color: var(--yellow); }
  .badge-pending { background: rgba(139,148,158,0.15); color: var(--text-muted); }
  .badge-blocked { background: rgba(248,81,73,0.15); color: var(--red); }
  .badge-rejected { background: rgba(248,81,73,0.15); color: var(--red); }

  /* Tables */
  table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
  th { text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--border); color: var(--text-muted); font-weight: 600; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
  tr:hover td { background: rgba(88,166,255,0.04); }

  /* Pipeline progress bar */
  .pipeline-bar { display: flex; gap: 2px; margin: 12px 0; }
  .pipeline-step {
    flex: 1;
    padding: 6px 4px;
    text-align: center;
    font-size: 0.7rem;
    border-radius: 4px;
    background: var(--border);
    color: var(--text-muted);
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .pipeline-step.done { background: rgba(63,185,80,0.25); color: var(--green); }
  .pipeline-step.in_progress { background: rgba(210,153,34,0.25); color: var(--yellow); }
  .pipeline-step.blocked { background: rgba(248,81,73,0.25); color: var(--red); }

  /* Feature cards */
  .feature-card { margin-bottom: 16px; }
  .feature-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
  .feature-title { font-weight: 600; }

  /* Tabs */
  .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--border); margin-bottom: 16px; }
  .tab {
    padding: 8px 16px;
    cursor: pointer;
    color: var(--text-muted);
    border-bottom: 2px solid transparent;
    font-size: 0.85rem;
  }
  .tab:hover { color: var(--text); }
  .tab.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab-content { display: none; }
  .tab-content.active { display: block; }

  /* Artefact types */
  .artefact-pattern { color: var(--green); }
  .artefact-gotcha { color: var(--red); }
  .artefact-note { color: var(--accent); }
  .artefact-constraint { color: var(--orange); }

  /* Empty state */
  .empty { color: var(--text-muted); font-style: italic; padding: 16px 0; }

  /* Auto-refresh */
  .refresh-info { font-size: 0.75rem; color: var(--text-muted); float: right; }

  /* Scrollable */
  .scroll-x { overflow-x: auto; }
</style>
</head>
<body>

<div class="header">
  <h1>📋 TaskFlow Dashboard</h1>
  <span class="refresh-info" id="refresh-info"></span>
</div>

<div class="project-selector">
  <label for="project-select">Project: </label>
  <select id="project-select"><option value="">Loading...</option></select>
</div>

<div id="dashboard-content">
  <p class="empty">Select a project to view its pipeline status.</p>
</div>

<script>
const API = '';
let currentProjectId = null;
let refreshTimer = null;

// --- API calls ---
async function fetchJSON(url) {
  const r = await fetch(url);
  return r.json();
}

async function loadProjects() {
  const projects = await fetchJSON(API + '/api/projects');
  const sel = document.getElementById('project-select');
  sel.innerHTML = '';
  if (projects.length === 0) {
    sel.innerHTML = '<option value="">No projects yet</option>';
    return;
  }
  projects.forEach(p => {
    const opt = document.createElement('option');
    opt.value = p.id;
    opt.textContent = p.name + ' — ' + taskSummary(p);
    sel.appendChild(opt);
  });
  // Auto-select first
  sel.value = projects[0].id;
  sel.dispatchEvent(new Event('change'));
}

function taskSummary(p) {
  const parts = [];
  if (p.done_count) parts.push(p.done_count + ' done');
  if (p.in_progress_count) parts.push(p.in_progress_count + ' active');
  if (p.pending_count) parts.push(p.pending_count + ' pending');
  if (p.blocked_count) parts.push(p.blocked_count + ' blocked');
  return parts.length ? '(' + parts.join(', ') + ')' : '(no tasks)';
}

async function loadDashboard(projectId) {
  currentProjectId = projectId;
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => loadDashboard(currentProjectId), 30000);

  const data = await fetchJSON(API + '/api/pipeline/' + projectId);
  if (data.error) {
    document.getElementById('dashboard-content').innerHTML = '<p class="empty">' + data.error + '</p>';
    return;
  }
  renderDashboard(data);
  document.getElementById('refresh-info').textContent = 'Auto-refreshes every 30s · Schema v' + data.schema_version;
}

// --- Rendering ---
function renderDashboard(data) {
  const el = document.getElementById('dashboard-content');
  const p = data.project;
  const tasks = data.tasks;

  // Stats
  const done = tasks.filter(t => t.status === 'done').length;
  const active = tasks.filter(t => t.status === 'in_progress').length;
  const pending = tasks.filter(t => t.status === 'pending').length;
  const blocked = tasks.filter(t => t.status === 'blocked').length;
  const rejected = tasks.filter(t => t.status === 'rejected').length;

  let html = '';

  // Stats cards
  html += '<div class="card-grid">';
  html += statCard(done, 'Done', '--green');
  html += statCard(active, 'In Progress', '--yellow');
  html += statCard(pending, 'Pending', '--text-muted');
  html += statCard(blocked, 'Blocked', '--red');
  html += '</div>';

  // Tabs
  html += '<div class="tabs">';
  html += tab('features', 'Features');
  html += tab('tasks', 'All Tasks');
  html += tab('retros', 'Retros & Decisions');
  html += tab('backlog', 'Backlog');
  html += '</div>';

  // Features tab
  html += '<div class="tab-content active" id="tab-features">';
  if (data.features.length === 0) {
    html += '<p class="empty">No features defined yet.</p>';
  } else {
    data.features.forEach(f => {
      const fTasks = tasks.filter(t => t.feature_id === f.id);
      const fDone = fTasks.filter(t => t.status === 'done').length;
      const fTotal = fTasks.length;
      html += '<div class="card feature-card">';
      html += '<div class="feature-header">';
      html += '<span class="feature-title">' + esc(f.title) + '</span>';
      html += '<span style="color:var(--text-muted);font-size:0.8rem;">#' + f.id + '</span>';
      html += '</div>';
      // Pipeline bar
      html += '<div class="pipeline-bar">';
      [3,4,5,6,7,8,9,10,11,12,13].forEach(step => {
        const stepTask = fTasks.find(t => t.step_number === step);
        let cls = '';
        let label = step;
        if (stepTask) {
          cls = stepTask.status === 'done' ? 'done' : stepTask.status === 'in_progress' ? 'in_progress' : stepTask.status === 'blocked' ? 'blocked' : '';
          label = stepTask.step_name || step;
        }
        html += '<div class="pipeline-step ' + cls + '" title="' + (stepTask ? stepTask.step_name + ' (' + stepTask.status + ')' : 'Step ' + step + ' (not started)') + '">' + label + '</div>';
      });
      html += '</div>';
      // Test results summary
      if (f.spec_count > 0) {
        html += '<div style="font-size:0.8rem;color:var(--text-muted);">Tests: ';
        html += '<span style="color:var(--green);">' + f.passed_count + ' passed</span>';
        if (f.failed_count > 0) html += ' · <span style="color:var(--red);">' + f.failed_count + ' failed</span>';
        html += ' / ' + f.spec_count + ' total</div>';
      }
      html += '</div>';
    });
  }
  html += '</div>';

  // Tasks tab
  html += '<div class="tab-content" id="tab-tasks">';
  if (tasks.length === 0) {
    html += '<p class="empty">No tasks yet.</p>';
  } else {
    html += '<div class="card scroll-x"><table>';
    html += '<tr><th>ID</th><th>Step</th><th>Feature</th><th>Agent</th><th>Status</th><th>Retry</th><th>Notes</th><th>Created</th></tr>';
    tasks.forEach(t => {
      const feature = data.features.find(f => f.id === t.feature_id);
      html += '<tr>';
      html += '<td>' + t.id + '</td>';
      html += '<td>' + t.step_number + '. ' + esc(t.step_name) + '</td>';
      html += '<td>' + (feature ? esc(feature.title) : '—') + '</td>';
      html += '<td>' + t.agent_role + '</td>';
      html += '<td><span class="badge badge-' + t.status + '">' + t.status + '</span></td>';
      html += '<td>' + t.retry_count + '</td>';
      html += '<td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + esc(t.rejection_notes || '') + '">' + esc(t.rejection_notes || '') + '</td>';
      html += '<td style="white-space:nowrap;">' + (t.created_at || '').slice(0, 16) + '</td>';
      html += '</tr>';
    });
    html += '</table></div>';
  }
  html += '</div>';

  // Retros & Decisions tab
  html += '<div class="tab-content" id="tab-retros">';
  if (data.retros.length === 0 && data.decisions.length === 0 && data.artefacts.length === 0) {
    html += '<p class="empty">No retros or decisions yet.</p>';
  } else {
    // Retros
    if (data.retros.length > 0) {
      html += '<h3>Retrospectives</h3>';
      data.retros.forEach(r => {
        html += '<div class="card">';
        html += '<div style="font-weight:600;margin-bottom:4px;">' + esc(r.feature_title) + '</div>';
        html += '<div style="font-size:0.85rem;white-space:pre-wrap;">' + esc(r.summary) + '</div>';
        html += '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px;">' + (r.created_at || '').slice(0, 16) + '</div>';
        html += '</div>';
      });
    }
    // Recommendations
    if (data.recommendations.length > 0) {
      html += '<h3>Recommendations</h3>';
      html += '<div class="card scroll-x"><table>';
      html += '<tr><th>ID</th><th>Feature</th><th>Type</th><th>Description</th></tr>';
      data.recommendations.forEach(r => {
        html += '<tr><td>' + r.id + '</td><td>' + esc(r.feature_title) + '</td><td>' + esc(r.recommendation_type) + '</td><td>' + esc(r.description) + '</td></tr>';
      });
      html += '</table></div>';
    }
    // Decisions
    if (data.decisions.length > 0) {
      html += '<h3>Decisions</h3>';
      html += '<div class="card scroll-x"><table>';
      html += '<tr><th>ID</th><th>Feature</th><th>Decision</th><th>Rationale</th></tr>';
      data.decisions.forEach(d => {
        html += '<tr><td>' + d.id + '</td><td>' + esc(d.feature_title) + '</td><td>' + esc(d.decision) + '</td><td>' + esc(d.rationale || '') + '</td></tr>';
      });
      html += '</table></div>';
    }
    // Decision artefacts
    if (data.artefacts.length > 0) {
      html += '<h3>Decision Artefacts</h3>';
      data.artefacts.forEach(a => {
        const typeClass = 'artefact-' + a.artefact_type;
        html += '<div class="card">';
        html += '<span class="' + typeClass + '" style="font-weight:600;text-transform:uppercase;font-size:0.75rem;">' + esc(a.artefact_type) + '</span> ';
        html += '<span style="font-weight:600;">' + esc(a.title) + '</span>';
        html += '<div style="font-size:0.85rem;margin-top:4px;white-space:pre-wrap;">' + esc(a.content) + '</div>';
        html += '<div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px;">' + esc(a.feature_title || '') + ' · ' + (a.created_at || '').slice(0, 16) + '</div>';
        html += '</div>';
      });
    }
  }
  html += '</div>';

  // Backlog tab
  html += '<div class="tab-content" id="tab-backlog">';
  if (data.backlog.length === 0) {
    html += '<p class="empty">No backlog items.</p>';
  } else {
    html += '<div class="card scroll-x"><table>';
    html += '<tr><th>ID</th><th>Title</th><th>Status</th><th>Priority</th><th>Description</th></tr>';
    data.backlog.forEach(b => {
      html += '<tr><td>' + b.id + '</td><td>' + esc(b.title) + '</td>';
      html += '<td><span class="badge badge-' + b.status + '">' + b.status + '</span></td>';
      html += '<td>' + b.priority + '</td><td>' + esc(b.description || '') + '</td></tr>';
    });
    html += '</table></div>';
  }
  html += '</div>';

  el.innerHTML = html;

  // Wire up tabs
  document.querySelectorAll('.tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      document.getElementById('tab-' + tab.dataset.tab).classList.add('active');
    });
  });
}

function statCard(n, label, colorVar) {
  return '<div class="stat-card"><div class="number" style="color:var(' + colorVar + ')">' + n + '</div><div class="label">' + label + '</div></div>';
}

function tab(id, label) {
  return '<div class="tab' + (id === 'features' ? ' active' : '') + '" data-tab="' + id + '">' + label + '</div>';
}

function esc(s) {
  if (!s) return '';
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// --- Init ---
document.getElementById('project-select').addEventListener('change', e => {
  const id = parseInt(e.target.value);
  if (id) loadDashboard(id);
});

loadProjects();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# HTTP server
# ---------------------------------------------------------------------------


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif self.path == "/api/projects":
            self._json_response(api_projects())

        elif self.path.startswith("/api/pipeline/"):
            try:
                project_id = int(self.path.split("/")[-1])
                self._json_response(api_pipeline_status(project_id))
            except (ValueError, IndexError):
                self._json_response({"error": "Invalid project ID"}, status=400)

        else:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Not found")

    def _json_response(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress per-request logs for cleanliness
        pass


def main():
    if not pathlib.Path(DB_PATH).exists():
        print(f"⚠  Database not found at {DB_PATH}")
        print("   Start TaskFlow first to create the database, then run the dashboard.")
        return

    server = HTTPServer(("127.0.0.1", PORT), DashboardHandler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"✓ TaskFlow Dashboard running at {url}")
    print(f"  Database: {DB_PATH}")
    print(f"  Press Ctrl+C to stop")
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")


if __name__ == "__main__":
    main()
