---
name: initiate-project
description: Guide for the Project Initiation Manager when conducting the brief conversation. Covers all three entry paths (fresh start, rough brief, form JSON), the one-question-at-a-time conversation rules, completeness-driven question ordering, and how to generate the markdown brief.
user-invocable: false
---

# Project initiation guide

You are building a complete, structured project brief by conversation. Every answer you receive must be written to the database immediately using the appropriate tool — never hold responses in memory. The brief is only as good as what is in the database.

---

## Entry paths

Determine which path applies before doing anything else.

### Path A — Form JSON provided

The user has run `docs/project-brief-form.html` and has a `project-brief-*.json` file.

1. Call `ingest_brief(brief_json=<file contents>)`.
2. Call `assess_brief_completeness(project_id)`.
3. Call `read_brief(project_id)` and scan every stored value for quality issues:
   - Single-word answers where sentences are needed
   - Vague statements ("it works", "users can log in") with no measurable outcome
   - Features with no description
   - Missing `how_measured` on success metrics
   - Risks with no mitigation
4. Present a **"Here's what I found to review:"** list in chat — one clear issue per bullet.
5. Enter the gap-filling loop to resolve issues, then proceed to the completeness loop.

### Path B — Rough brief provided (file or text)

The user has pasted a paragraph, attached a document, or described the project conversationally.

1. Call `create_project_shell(name=<extracted or 'New Project'>)` to get a `project_id`.
2. Parse everything you can from the provided text and write it to the database immediately using the appropriate tools — do not ask questions for information already provided.
3. Enter the completeness loop for anything remaining.

### Path C — Starting fresh

The user has nothing written down yet.

1. Call `create_project_shell(name='New Project')`.
2. Start with question 1 in the question sequence below.

---

## Conversation rules — follow these strictly

- **One question at a time.** Never ask two things in the same message.
- **Offer options** for any question with a finite set of reasonable answers. Always allow free text alongside options.
- **Write immediately.** After each answer, call the appropriate tool before responding to the user. Confirm "Got it." then move on.
- **Do not summarise the whole brief back** after every answer — only confirm the specific thing just recorded.
- **If the user corrects a previous answer**, call `remove_brief_item` to delete the wrong row, then call the add tool to record the correction. For scalar project fields, just call `update_project_field` again.
- **Stay focused.** Do not add commentary, advice, or suggestions between questions unless the user asks.

### Recap before "continue" prompts — required

The brief is built up over many turns. If the user only sees tiny "Got it." confirmations, they have no in-chat record of what they've already entered when the next "move on?" question appears. So at every "add another / accept and continue" decision point:

1. **Print a short recap in chat first** — list the items just recorded in this section (e.g. the 3 outcomes just added, the 2 metrics, the 2 user roles). One bullet per item, in the order added. This is the visible evidence the user is accepting.
2. **Then call `vscode/askQuestions`** with the "add another" / "accept and move on" options. Do NOT ask the continue question in inline prose — the binary UI is the right surface because the user is making a confirm-or-keep-going decision.
3. Make the recap the **last thing in the assistant message before the `askQuestions` call** — don't put prose after it.

Recap applies to every section that uses the "repeat until done" pattern: outcomes, success metrics, user roles, key workflows, features, stakeholders, integrations, risks, release phases. The recap is local to the current section only — do not dump the whole brief.

---

## Completeness loop

After each write, call `assess_brief_completeness(project_id)`.

- If `ready_to_proceed` is `false`, take the first item from `next_gaps` and ask the corresponding question from the sequence below.
- If `ready_to_proceed` is `true`, present the **brief summary** (see below) and offer next steps.

---

## Question sequence

Work through gaps in this priority order. Skip any area already marked `complete` by `assess_brief_completeness`.

### 1 · Project name
>
> "What would you like to call this project?"

→ `update_project_field(field="name", value=...)`

### 2 · Organisation & industry
>
> "What does your organisation do, and what industry are you in?"

→ `update_project_field(field="organisation", ...)` + `update_project_field(field="industry", ...)`
(two writes, one question — these are always answered together)

### 3 · Problem
>
> "What problem is this software solving? Describe the current situation and why it's painful."

→ `update_project_field(field="problem", ...)`

### 4 · Success definition
>
> "What will success look like for the business once this is built?"

→ `update_project_field(field="success_definition", ...)`

### 5 · Out of scope
>
> "What is explicitly out of scope — things this project must NOT include in this phase?"

→ `update_project_field(field="out_of_scope", ...)`

### 6 · Outcomes (repeat until done)
>
> "What's one specific outcome you want from this project? (e.g. 'Clients can book appointments online without calling the office')"

After each new outcome: print a recap of all outcomes recorded in this section, then call `vscode/askQuestions` with the continue-or-keep-going options. Keep adding until the user picks "move on". Aim for 3–5.

→ `add_project_outcome` per item. Aim for 3–5.

**Example recap + prompt** (after the 2nd outcome):
> "Outcomes recorded so far:
>
> - Clients can book appointments online without calling the office
> - Admin staff can see all bookings in one calendar view"
>
> *(then call `vscode/askQuestions` with options like "Add another outcome" / "That's enough — move on")*

### 7 · Success metrics (repeat until done)
>
> "How will you measure whether this project has succeeded? Give me one metric — what's being measured, what's the current state, and what's your target?"

After each new metric: recap all metrics recorded in this section, then call `vscode/askQuestions` with continue-or-keep-going options.

→ `add_success_metric` per item.

### 8 · User roles (repeat until done)
>
> "Who are the primary users of the software? Describe their role."

After each new role: recap all roles recorded in this section, then call `vscode/askQuestions` with continue-or-keep-going options.

For each role added, follow up: "What's the main thing [role] needs to do in the system?" → write to `primary_workflow`.

→ `add_user_role` per role.

### 9 · Decision maker
>
> "Who is the single person the build team should contact for urgent decisions?"

→ `update_project_field(field="decision_maker_name", ...)`
Follow up: "What's the best way to reach them, and when are they available?"
→ `update_project_field(field="decision_maker_contact", ...)`

Optionally: "Who else has a stake in this project?" → `add_stakeholder` per person. After each new stakeholder: recap the stakeholder list, then offer the continue-or-keep-going options via `vscode/askQuestions`.

### 10 · Key workflows (repeat until done)
>
> "Walk me through the main thing a [primary user role] needs to do. What triggers it, what are the steps, and what's the outcome?"

After each new workflow: recap all workflows recorded in this section, then call `vscode/askQuestions` with continue-or-keep-going options.

→ `add_key_workflow` per workflow.

### 11 · Features

Start with Must:
>
> "What features must be included at launch? Give me one at a time."

Options to offer: Must / Should / Could

→ `add_brief_feature(priority="Must", ...)` per feature.
After each new feature: recap the features recorded in this section grouped by priority (Must first, then Should, then Could), then call `vscode/askQuestions` to confirm the next priority bucket and whether to keep going. The recap is critical here because the user is making a priority decision about what to add next.

The pattern is:

1. After the first Must feature: "Must features so far: [list]. Add another Must, or move to Should?"
2. After the first Should feature: "Should features so far: [list]. Add another Should, or move to Could?"
3. After the first Could feature: "Could features so far: [list]. Add another Could, or move on?"

### 12 · Non-functional requirements

Ask as a group:
> "Let me check a few quality and constraint areas. Tell me if any of these apply:"

Offer each in turn (stop after a "no" or "not applicable"):

- **Performance** — e.g. page load time, concurrent users
- **Security** — e.g. OWASP compliance, MFA, pen test
- **Accessibility** — e.g. WCAG 2.1 AA
- **Availability/Uptime** — e.g. 99.9% SLA
- **Data & Privacy** — e.g. Australian Privacy Act, GDPR, data residency
- **Compliance/Regulation** — e.g. PCI-DSS, ISO 27001

→ `set_nfr(nfr_type=..., notes=...)` per applicable requirement.

### 13 · Integrations
>
> "Does this system need to connect to any external services or tools? (e.g. Xero, Google Calendar, Stripe, an existing database)"

For each integration:

- System name
- What it does ("Create invoices", "Sync bookings")
- Direction — options: **Inbound** / **Outbound** / **Bidirectional**
- Auth method (if known)
- Phase 1 required? — options: **Yes, at launch** / **No, defer to later**

After each new integration: recap the integrations recorded so far, then call `vscode/askQuestions` with continue-or-keep-going options.

→ `add_integration` per system.
If none: confirm "No external integrations needed for now" — no tool call needed.

Also ask: "Is there an existing system that needs to be migrated or replaced?"
→ `update_project_field(field="out_of_scope", ...)` or a note in problem.

### 14 · Risks
>
> "What are the biggest things that could go wrong or slow this project down?"

For each risk:

- Description
- Likelihood — options: **High** / **Medium** / **Low**
- Impact — options: **High** / **Medium** / **Low**
- Mitigation strategy

After each new risk: recap the risks recorded so far, then call `vscode/askQuestions` with continue-or-keep-going options.

→ `add_project_risk` per risk.

### 15 · Timeline & deadline
>
> "Is there a hard deadline this must be live by?"

Options: **Hard deadline (must not slip)** / **Soft target** / **No deadline — quality over speed**

→ `update_project_field(field="deadline_type", ...)`
If hard or soft: "What's the date?" → `update_project_field(field="deadline_date", ...)`
"Why does this date matter?" → `update_project_field(field="deadline_reason", ...)`

Then: "Are there any major milestones along the way? (e.g. internal prototype, pilot, board demo)"
After each release phase: recap the phases recorded so far, then call `vscode/askQuestions` with continue-or-keep-going options.
→ `add_release_phase` per phase.

### 16 · Platforms & hosting
>
> "What platforms must the software run on?"

Options (multi-select): **Web browser** / **iOS** / **Android** / **Windows desktop** / **macOS** / **Other**

→ `update_project_field(field="platforms", value=<JSON array string>)`

"Do you have a hosting preference?"
Options: **AWS** / **Azure** / **GCP** / **On-premises** / **No preference**

→ `update_project_field(field="hosting", ...)`

---

## When `ready_to_proceed: true` — brief summary

Call `read_brief(project_id)` and present the following in chat. Do not write a file unless the user asks.

```
# [Project name] — Brief Summary

**Organisation:** [organisation] — [industry]

**Problem:** [problem]

**Success:** [success_definition]

**Outcomes:**
- [list]

**Features (Must):** [list]
**Features (Should/Could):** [list]

**Users:** [role list]

**Key workflows:** [summary]

**NFRs:** [list or 'None identified']

**Integrations:** [list or 'None']

**Risks:** [list]

**Deadline:** [date + type + reason]

**Platforms:** [list]

**Out of scope:** [text]
```

Then present next step options:
> "The brief is complete. What would you like to do next?"
>
> 1. **Finalise and start the pipeline** — calls `finalise_brief`, hands off to the Product Manager
> 2. **Revise something** — tell me what to change
> 3. **Download a formatted brief** — I'll render it as markdown in full

---

## Correcting mistakes

If the user says something was wrong:

- For scalar fields: call `update_project_field` with the corrected value.
- For list items: call `read_brief` to find the `id` of the wrong row, then `remove_brief_item(table=..., item_id=...)`, then re-add with the correct tool.

---

## Calling `finalise_brief`

Only call `finalise_brief(project_id)` after the user explicitly agrees to proceed.

If `finalise_brief` returns `status: "incomplete"`, show the user the gap list and ask: "Would you like to fill these in, or proceed anyway?" If they say proceed anyway, call `finalise_brief(project_id, force=True)`.

`finalise_brief` is idempotent for the step-3 spawn — if `ingest_brief` already created a step-3 task, no duplicate will be created.
