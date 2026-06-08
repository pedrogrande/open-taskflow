---
name: write-features
description: Guide for the product_manager agent when writing feature records and definitions of done in step 3. Auto-loaded when a step-3 task is in progress.
user-invocable: false
---

# Writing features and definitions of done (Step 3)

You are defining the feature set for this project cycle. Your output feeds directly into test writing — every criterion you write must be testable.

## Before you start

- Read `project.brief_text` carefully — extract every distinct capability.
- Call `read_backlog(project_id)` and review pending backlog items. Promote any that are appropriate for this cycle with `promote_backlog_item`.
- Check `rejection_notes` on your task if present — the previous submission was rejected for specific reasons.

## Risk-informed feature ordering — required

Read the `project_risks` from the brief context before defining features. Risks often imply that certain work must happen early to avoid costly rework later. Use risks to determine feature `order_index`:

1. **Identify risk-mitigation features.** For each risk with High impact, check whether any feature directly mitigates it. If so, that feature should be ordered early (low `order_index`).
2. **Flag dependency risks.** If a risk says "verify X early" or "test Y before building on it", the verification feature must come before features that depend on X or Y.
3. **Do not bury risk mitigations.** A feature that verifies a critical dependency (e.g. "Agno version verification") must not be the last feature in the list — it should be first or second, because if it fails, everything built on top of it must change.

**Example:** If the brief has a risk "Agno version may not support Learning Suite" with High impact and mitigation "Verify agno version early", then a feature like "Agno Version Verification" must have `order_index: 0` or `1` — not `order_index: 3` (last). The PM should flag this to the user if the brief_features suggest a different order.

If the `brief_features` from the form suggest an ordering that contradicts risk priorities, use `vscode/askQuestions` to present the conflict and ask the user which ordering to use.

## Feature record quality

Each feature must have:

- **title**: Short, noun-phrase label (e.g. "User authentication", "CSV export")
- **description**: 2–4 sentences describing the feature's purpose, scope, and expected behaviour
- **source_requirement_text**: Copy the exact requirement text from the brief that this feature addresses
- **definitions_of_done**: 2–5 criteria, each independently verifiable

## Definition of done criteria

Each criterion must be:

- **Specific**: "Returns HTTP 200 with a JSON body" not "works correctly"
- **Verifiable**: testable by an automated test, not by human judgement
- **Atomic**: one thing, not "works and is fast and is documented"

### Good examples

- "POST /api/users returns 201 with `{id, email}` when given a valid payload"
- "Unauthenticated requests to /api/orders return 401"
- "CSV export includes all columns defined in the schema"

### Bad examples

- "Feature works as expected" ← too vague
- "Code is clean and well-tested" ← not verifiable by a test
- "Authentication and authorisation work" ← two things

## Calling submit_features

```
submit_features(
  task_id=<your task id>,
  features=[
    {
      "title": "...",
      "description": "...",
      "source_requirement_text": "...",
      "order_index": 0,
      "definitions_of_done": [
        {"criterion": "...", "verifiable": 1},
        ...
      ]
    },
    ...
  ]
)
```
