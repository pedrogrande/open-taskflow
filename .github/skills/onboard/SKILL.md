---
name: onboard
description: Add TaskFlow to an existing project. Scans the workspace, detects existing agents/skills/MCP servers, and guides the user through creating a brief that captures what's already built.
user-invocable: true
---

# Onboard an existing project

Use this skill when adding TaskFlow to a project that already has code, agents, skills, or infrastructure. It ensures TaskFlow works *with* what's already there, not over it.

---

## When to use this skill

- The user says "add TaskFlow to my project" or "onboard my existing project"
- The workspace already has a codebase, README, docs, agents, or MCP servers
- The user wants to start the pipeline from where they are, not from scratch

Do NOT use this skill for greenfield projects — use `/start-project` instead.

---

## Step 1 — Scan the workspace

Read the following files (if they exist) and extract information:

| File / Pattern | What to extract |
|---|---|
| `README.md` | Project name, description, tech stack, features listed |
| `package.json` / `pyproject.toml` / `Cargo.toml` / `go.mod` | Dependencies, scripts, project name |
| `docs/` folder | Architecture decisions, API specs, user guides |
| `.github/agents/*.agent.md` | Existing agent names, roles, tool restrictions |
| `.github/skills/*/SKILL.md` | Existing skill names and purposes |
| `.github/copilot-instructions.md` / `.github/*.instructions.md` | Existing instructions |
| `.vscode/mcp.json` | Existing MCP servers |
| `.vscode/settings.json` | Copilot settings, skill locations |
| Test files (`*_test.*`, `*.test.*`, `tests/`) | Test framework, coverage hints |
| `Dockerfile` / `docker-compose.*` / `railway.json` | Deployment config |
| CI config (`.github/workflows/*`) | CI pipeline, test commands |

Summarise what you found in chat. Example:

> **Workspace scan results:**
>
> - **Project:** my-saas-app (Next.js 14 + PostgreSQL + Prisma)
> - **Existing agents:** 2 — `custom-builder.agent.md`, `custom-tester.agent.md`
> - **Existing skills:** 1 — `deploy-to-railway`
> - **Existing MCP servers:** postgres (read-only DB access)
> - **Tests:** Jest + React Testing Library, ~40 test files
> - **Deployment:** Railway (Dockerfile present)
> - **CI:** GitHub Actions (lint + test)

---

## Step 2 — Confirm what's already built

Ask the user to confirm which features are already working. Use `vscode/askQuestions` with multi-select options based on what was detected from the README, docs, and codebase.

> "I found these features mentioned in your README and docs. Which ones are already built and working?"

Options should be derived from what you scanned. Always include "Other (describe below)" for features not detected.

---

## Step 3 — Capture existing AI/agent setup

Record what already exists so the Dev Manager knows to preserve it. Ask:

> "I found [N] agents, [N] skills, and [N] MCP servers already configured. Should TaskFlow preserve all of these, or are any you want to replace?"

Options:

- **Preserve all** — TaskFlow adds its agents alongside your existing ones
- **Replace some** — tell me which ones to replace
- **Start fresh** — remove existing agents and let TaskFlow set up from scratch

Record the answer in the project's `out_of_scope` field or as a note in `brief_text`.

---

## Step 4 — Capture known issues and tech debt

Ask:

> "Are there any known bugs, TODOs, or technical debt the pipeline should address? List them or say 'none'."

For each item, add it as a brief feature with an appropriate priority and a description prefixed with the type:

- Bugs → `[Bug] Login redirect fails on expired session`
- TODOs → `[TODO] Add rate limiting to API endpoints`
- Tech debt → `[Tech debt] Refactor auth module — currently 800-line monolith`

---

## Step 5 — Hand off to the Project Initiation Manager

Now that the workspace context is captured, invoke the **TaskFlow Project Initiation Manager** agent with the scanned information as the "rough brief". The Initiation Manager will:

1. Create the project shell
2. Parse all the scanned information into the database
3. Enter the completeness loop for any remaining gaps
4. Call `finalise_brief` when the brief is complete

The key difference from a normal `/start-project` is that the Initiation Manager receives a pre-populated brief that includes:

- Existing tech stack and architecture
- Already-built features (to be marked as done)
- Existing agent/skill/MCP setup (to be preserved)
- Known issues and tech debt (to be addressed by the pipeline)

---

## What the Dev Manager does differently for existing projects

When the Dev Manager sees a `team_setup` record or `brief_text` that mentions existing agents/skills/MCP servers, it should:

1. **Read existing agent files** before modifying any — check tool restrictions, model preferences, and applyTo patterns
2. **Merge, don't replace** — add TaskFlow tools to existing agents' tool lists rather than overwriting them
3. **Preserve existing MCP servers** in `.vscode/mcp.json` — add TaskFlow's server entry alongside existing ones
4. **Note conflicts** — if an existing agent has the same role as a TaskFlow agent (e.g. both have a "builder"), flag this for the user to decide

---

## What the Product Manager does differently for existing projects

When the PM sees features marked as `[Already built]` in step 3:

1. **Create them as features with all DoD marked as met** — this gives the pipeline a complete record without re-building
2. **Focus new features on gaps** — what's missing, what needs fixing, what's next on the roadmap
3. **Use existing docs as DoD evidence** — if the README says "users can log in via Google", that's verifiable DoD
