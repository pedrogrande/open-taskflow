# TaskFlow

A **database-driven agentic pipeline** for software development. Clone this repo into any project and VS Code automatically wires up the MCP server, agents, and skills. Every agent action is authorised and scoped by a task record. The database is the single source of truth for pipeline state, permissions, and context.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh | sh`
- VS Code 1.99+ with GitHub Copilot (agent mode enabled)

---

## Setup

### 1. Clone into your project

If you are starting a new project from scratch:

```bash
git clone https://github.com/pedrogrande/open-taskflow.git my-project
cd my-project
```

If you want to add TaskFlow to an **existing** project, copy the following directories and files into your workspace root:

```
.github/
.taskflow/
.vscode/mcp.json
.vscode/settings.json
.vscode/hooks.json   # merge with your existing hooks if you have one
.gitignore           # add the .taskflow/ entries to your existing .gitignore
```

### 2. Open the workspace in VS Code

VS Code detects `.vscode/mcp.json` and starts the TaskFlow MCP server automatically via `uv`. On first run, `uv` downloads the `mcp` dependency — no manual `pip install` required.

You should see **taskflow** appear in **Configure Tools** (gear icon in the Chat view).

### 3. Add `.taskflow/` to your project's `.gitignore`

The database and audit log are runtime files and should not be committed:

```
.taskflow/taskflow.db
.taskflow/audit.log
.taskflow/server/__pycache__/
```

These are already in the `.gitignore` included with this repo. If you merged TaskFlow into an existing project, add these lines to your own `.gitignore`.

---

## Quick start

There are two ways to initiate a project. Use **Path A** for a thorough brief; use **Path B** conversationally.

### Path A — Project brief form (recommended)

1. Open `.taskflow/project-brief-form.html` in any browser — it runs fully offline, no server needed.
2. Complete all sections: identity, goals, features, workflows, NFRs, integrations, risks, timeline.
3. Click **Generate brief** — a `project-brief-<name>.json` file downloads.
4. In VS Code Copilot chat, invoke the **TaskFlow Project Initiation Manager**:

   ```
   @TaskFlow Project Initiation Manager
   ```

   Tell it you have a brief JSON file and provide the path or paste the contents. The agent calls `ingest_brief`, which parses all structured data into the database and seeds the first pipeline task.
5. Proceed to [Working the pipeline](#working-the-pipeline).

### Path B — Conversational brief

1. Open your project workspace in VS Code.
2. Invoke the **TaskFlow Project Initiation Manager** in chat:

   ```
   @TaskFlow Project Initiation Manager I want to start a new project
   ```

   The agent guides you through the brief one question at a time, recording each answer directly into the database, then hands off to the Product Manager when the brief is complete.
3. Proceed to [Working the pipeline](#working-the-pipeline).

### Working the pipeline

1. Use `/my-tasks` to see what each agent needs to do next.
2. Invoke the appropriate agent (e.g. **@TaskFlow Product Manager**) to work the next task.
3. Use `/pipeline-status` at any time to see the full pipeline state.

---

## Slash commands

| Command | Description |
|---|---|
| `/start-project` | Start a project from free-text or a brief file (Path B) |
| `/my-tasks` | Show pending tasks for a chosen agent role |
| `/pipeline-status` | Show the full pipeline state for a project |

For the form-based path, use `ingest_brief` directly via the **TaskFlow Product Manager** agent rather than `/start-project`.

---

## Agents

| Agent | Role in pipeline |
|---|---|
| **TaskFlow Project Initiation Manager** | Builds the project brief conversationally or ingests a brief form JSON (pre-pipeline) |
| **TaskFlow Dev Manager** | Reviews the brief, identifies relevant MCP servers and skills, enriches the agent team (pre-pipeline) |
| **TaskFlow Product Manager** | Defines features, decisions, and decision artefacts (steps 3, 10, 12) |
| **TaskFlow PM Reviewer** | Reviews and approves PM outputs (steps 2, 4, 11, 13) |
| **TaskFlow Tester** | Writes test specs and runs tests (steps 5, 8) |
| **TaskFlow Test Reviewer** | Reviews test specs (step 6) |
| **TaskFlow Builder** | Implements features (step 7) |
| **TaskFlow Documenter** | Writes retrospective and recommendations (step 9) |

---

## Project brief form

The brief form (`.taskflow/project-brief-form.html`) is a single offline HTML file — no install, no server, no dependencies.

**Sections captured:**

| Section | What agents use it for |
|---|---|
| Project identity & problem | All agents — project scope and context |
| Goals & success metrics | PM (step 3 feature alignment); PM Reviewer (step 13 final verification) |
| User roles & workflows | PM (step 3 user-centric features); Tester (step 5 test scenario design) |
| Features (Must / Should / Could) | PM (step 3 starting point — promote Must features first) |
| Non-functional requirements | Builder (step 7 implementation constraints); Tester (step 8 verification) |
| Integrations | Builder (step 7 — system, direction, auth method, phase 1 flag) |
| Risks | PM (steps 10/12 — seeded as initial decision artefacts) |
| Release phases | PM (step 3 — assigns features to cycles) |
| Timeline & deadline | All reviewers — context for prioritisation |

**Form features:**

- Dynamic add/remove rows for features, roles, workflows, integrations, risks
- Toggle rows for NFRs — only enabled constraints are stored; disabled ones produce no noise in the DB
- Client-side validation before download (required fields, at least one Must feature, at least one platform)
- Auto-saves to `localStorage` every 2 seconds — reload the page and it offers to restore the draft
- Downloads as `project-brief-<slug>.json` — the file is the pipeline entry artefact

---

## Pipeline overview

```
.taskflow/project-brief-form.html  →  project-brief.json  →  ingest_brief
          OR
@TaskFlow Project Initiation Manager (conversational)
      │
      ▼  (recommended)
@TaskFlow Dev Manager
  Reads brief → researches MCP servers + skills → enriches agent team
      │
      ▼
  Step 3: PM defines features + DoD
      │
      ▼
  Step 4: PM Reviewer approves → spawns step 5 per feature
      │
      ▼ (per feature)
  Step 5: Tester writes test specs
  Step 6: Test Reviewer approves
  Step 7: Builder implements
  Step 8: Tester runs tests ──(fail × 3 → blocked)
      │ pass
      ▼
  Step 9: Documenter writes retro (auto-advances)
  Step 10: PM writes decisions
  Step 11: PM Reviewer approves
  Step 12: PM writes decision artefacts
  Step 13: PM Reviewer final verification
      │
      └──► Step 3 (next cycle)
```

New-feature decisions go to the **feature backlog**. The PM promotes them in step 3 of the next cycle.

---

## Schema summary

**Pipeline tables** (populated by agents during the cycle):

| Table | Purpose |
|---|---|
| `pipeline_steps` | 13-step workflow definition (seed data) |
| `projects` | Project records with scalar brief fields + raw JSON |
| `features` | Feature records per project |
| `definitions_of_done` | Verifiable DoD criteria per feature |
| `test_specs` | Test specifications per feature |
| `build_reports` | Build output per feature per cycle |
| `test_results` | Pass/fail per test spec per build |
| `retro_reports` | Retrospective summaries per feature |
| `recommendations` | Recommendations from retros |
| `decisions` | Decisions made on recommendations |
| `decision_artefacts` | Patterns, gotchas, notes from step 12 |
| `feature_backlog` | New features queued for future cycles |
| `tasks` | Pipeline task queue (the engine) |

**Brief-derived tables** (populated by `ingest_brief` from the form JSON):

| Table | Purpose |
|---|---|
| `project_outcomes` | Stated goals from the brief |
| `success_metrics` | Measurable targets for step-13 verification |
| `user_roles` | Actor descriptions and primary workflows |
| `stakeholders` | Named stakeholders and their authority |
| `key_workflows` | Actor → trigger → steps → outcome journeys |
| `non_functional_requirements` | Enabled NFR constraints only (performance, security, etc.) |
| `integrations` | External systems with direction, auth method, phase flag |
| `project_risks` | Risks with likelihood/impact/mitigation |
| `release_phases` | Phase-by-phase scope and target dates |
| `brief_features` | Feature suggestions from the form (PM refines these at step 3) |

All brief-derived tables are returned by `read_task_context` via the `brief` key — agents never need to re-read the JSON file.

---

## Project layout

```
open-taskflow/
  .github/
    agents/                          # 8 agent definition files
    skills/                          # 12 skill directories
    copilot-instructions.md          # Agent routing + tool reference
  .taskflow/
    server/
      mcp_server.py                  # FastMCP server (all tools)
      init.sql                       # Schema + pipeline seed data
    project-brief-form.html          # Offline brief form → downloads project-brief.json
    project-brief-template.md        # Reference template
    taskflow.db                      # Runtime DB (gitignored — auto-created on first use)
    audit.log                        # Tool call audit trail (gitignored)
  .vscode/
    mcp.json                         # Workspace MCP server definition
    settings.json                    # Skills + hooks locations
    hooks.json                       # SessionStart + PostToolUse hooks
  .gitignore
  README.md
```

---

## Blocked tasks

If a task reaches `retry_count = 3` it becomes `blocked`. To unblock:

```sql
-- Reset for another attempt
UPDATE tasks SET retry_count = 0, status = 'pending' WHERE id = <task_id>;
-- Or force-advance
UPDATE tasks SET status = 'done' WHERE id = <task_id>;
```

Then use `/pipeline-status` to see the updated state.
