---
name: agent-ux
description: How to use vscode/askQuestions and vscode/memory tools correctly. Load this skill whenever you need to ask the user structured questions or persist working state across turns.
user-invocable: false
---

# Agent UX — askQuestions and memory

## askQuestions

Use `#vscode/askQuestions` any time you need structured input from the user before proceeding. It renders a compact form UI — do not ask questions in prose when this tool is available.

### When to use it

- Before recording data that the user must confirm (project name, key decisions, stack choices)
- When presenting options for the user to choose from (Yes/No, A/B/C, multi-select)
- When you need a short freeform answer in a specific format (a date, a URL, a name)

### When NOT to use it

- For simple acknowledgement ("shall I continue?") — offer a handoff button or ask inline
- When you already have enough information to proceed without ambiguity
- For long, open-ended narrative answers — ask in prose and allow the user to reply freely

### Constraints

| Field | Limit | Notes |
|---|---|---|
| `question` | 200 chars | One sentence. State the decision clearly. |
| `header` | 50 chars | Short unique identifier — shown as the question label in the UI. |
| `options[].label` | ~40 chars | Keep option labels brief and scannable. |
| Questions per call | 3–4 max | Batch related questions; never dump a full form in one call. |

### Patterns

**Binary choice with recommended default:**
```json
{
  "header": "Include auth",
  "question": "Should authentication be included in phase 1?",
  "options": [
    { "label": "Yes — include auth in phase 1", "recommended": true },
    { "label": "No — defer to phase 2" }
  ],
  "allowFreeformInput": false
}
```

**Multi-select:**
```json
{
  "header": "Target platforms",
  "question": "Which platforms should be supported?",
  "options": [
    { "label": "Web" },
    { "label": "iOS" },
    { "label": "Android" }
  ],
  "multiSelect": true,
  "allowFreeformInput": false
}
```

**Freeform short answer:**
```json
{
  "header": "Organisation name",
  "question": "What is the client's organisation name?"
}
```

---

## memory

Use `#vscode/memory` to persist working state that needs to survive across turns in this conversation.

### Scope selection

| Scope | Path prefix | Use for |
|---|---|---|
| Session | `/memories/session/` | In-progress notes for this conversation only. Cleared when the session ends. |
| Repository | `/memories/repo/` | Verified facts about this codebase. Survives across sessions in this workspace. |
| User | `/memories/` | Cross-workspace preferences. Rarely needed in TaskFlow agents. |

### What to write to repo scope

- Confirmed tech stack choices: "Uses Supabase with postgres schema in /supabase/migrations"
- Confirmed MCP servers added: "agno-docs MCP added — agents should use it for Agno API questions"
- Confirmed agent modifications: "Builder given agno/* tools — see .github/agents/builder.agent.md"

### What to write to session scope

- Intermediate decisions mid-conversation: "User confirmed Xero integration but deferred Stripe"
- Partial answers while filling multi-step forms
- "Waiting for" state: "Asked about deadline — awaiting user response"

### What NOT to write

- Credentials, API keys, passwords, or tokens
- Data that already lives in the TaskFlow database — use the DB as the source of truth
- Large blocks of text — keep notes concise (one line per fact)
