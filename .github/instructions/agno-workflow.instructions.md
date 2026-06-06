---
applyTo: "**/workflows/*.py"
description: Agno workflow guardrails — HITL patterns, Loop iteration review, anti-patterns, and executor conventions. Auto-loads when editing any workflow file.
---

# Agno Workflow Guardrails

These rules apply to ALL workflow files in this project. They capture hard-won lessons from debugging real workflow issues.

## Loop HITL: Use `requires_iteration_review`, NOT HumanReview Steps

For write→review loops, use `requires_iteration_review=True` on the Loop constructor. Do NOT create a separate Step with `HumanReview(requires_output_review=True)` inside the Loop.

```python
# ✅ Correct — iteration review on the Loop
Loop(
    name="Write-Review Loop",
    steps=[write_step, review_step],
    end_condition=review_passes,
    max_iterations=3,
    forward_iteration_output=True,
    human_review=HumanReview(
        requires_iteration_review=True,
        iteration_review_message="Review this iteration.",
        on_reject=OnReject.retry,
    ),
)

# ❌ Wrong — HumanReview Step inside a Loop (passthrough executor anti-pattern)
Loop(
    steps=[write_step, review_step, approve_step],  # approve_step is the anti-pattern
    end_condition=review_passes,
)
```

## Conditional HITL via `end_condition`

Agno checks `end_condition` BEFORE `requires_iteration_review`. If `end_condition` returns `True`, the loop ends immediately without pausing for human review. This gives conditional HITL for free:

- Review passes → `end_condition` stops loop → no human needed
- Review fails → `end_condition` doesn't stop → iteration review pauses for human

This is the correct way to implement "auto-approve on pass, human review on fail" without needing a callable predicate.

## `requires_iteration_review` is `bool`-only

Do NOT pass a callable to `requires_iteration_review`. It's typed as `bool`. A callable is truthy in Python, so iteration review will ALWAYS trigger. Use `end_condition` as the conditional gate instead.

## Passthrough Executor Anti-Pattern

Never create a Step with a passthrough executor (one that just forwards `previous_step_content`) for HITL gates. Combined with `on_reject=OnReject.retry`, this creates an infinite loop:

1. Passthrough executor runs → forwards content → HITL pauses
2. Human rejects → `OnReject.retry` re-executes the passthrough
3. Passthrough forwards same content → HITL pauses again
4. Repeat forever

Use `requires_iteration_review=True` on the Loop instead.

## `forward_iteration_output=True`

Set on Loops where the next iteration should receive the previous iteration's output (not the original step input). Essential for write→review→revise loops — without it, each iteration starts from scratch.

## `OnReject.retry` on Loop Iteration Review

Works correctly — when a human rejects an iteration review, the rejection feedback is auto-injected into the agent's message on the next iteration. This is the correct pattern for quality loops.

## Custom Executor Signatures

Agno introspects executor function signatures. If your executor accepts `run_context` or `session_state` as parameters, Agno will pass them automatically:

```python
# ✅ Both signatures work — Agno detects parameters via introspection
def my_executor(step_input: StepInput) -> StepOutput: ...
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput: ...
def my_executor(step_input: StepInput, run_context: RunContext, session_state: dict) -> StepOutput: ...
```

Note: mypy may flag the 2-arg signature as a type error because `StepExecutor` is typed as `Callable[[StepInput], ...]`. Use `# type: ignore[arg-type]` to suppress.

## `previous_step_content` Type Normalization

`step_input.previous_step_content` can be a string, dict, or Pydantic model depending on the previous step's agent. Always normalize before string operations:

```python
raw = step_input.previous_step_content
if hasattr(raw, "model_dump_json"):
    raw = raw.model_dump_json()
elif isinstance(raw, dict):
    raw = json.dumps(raw)
elif raw is None:
    raw = ""
```

## HITL Requirement Filtering

`step_requirements` is an accumulating list — it includes resolved requirements from earlier gates. Always filter by `confirmed is None` to find the CURRENT pending requirement:

```python
# ❌ Wrong — returns first match, may be a resolved earlier gate
req = run_output.step_requirements[0]

# ✅ Correct — find the active (unresolved) requirement
active_reqs = [r for r in (run_output.step_requirements or []) if not r.is_resolved]
```

## HITL via AgentOS (no /hitl/ router)

There is NO `/hitl/` router in this codebase. HITL interaction goes through AgentOS's built-in workflow run API.

**Easiest: use the AgentOS UI** at http://localhost:8006 → Workflows → paused run → Approve/Reject/Edit buttons.

**Or use `scripts/hitl` CLI:**

```bash
python scripts/hitl start "message"          # Start a run and watch for pauses
python scripts/hitl list                      # List known runs and their status
python scripts/hitl show <run_id> <sid>      # Show pending requirement details
python scripts/hitl approve <run_id> <sid>    # Approve the pending gate
python scripts/hitl reject <run_id> <sid> "feedback"  # Reject with feedback
python scripts/hitl cancel <run_id> <sid>     # Cancel a running or paused run
python scripts/hitl edit <run_id> <sid> <file> # Approve with edited output
python scripts/hitl watch <run_id> <sid>      # Poll until paused or completed
```

**Or use curl directly (form-encoded, not JSON):**

```bash
# Find pending requirement
curl -s "http://localhost:8006/workflows/{workflow_id}/runs/{run_id}?session_id={session_id}" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for req in data.get('step_requirements', []):
    if req.get('confirmed') is None and req.get('requires_output_review'):
        print(f'step_id: {req[\"step_id\"]}')
        print(f'step_name: {req.get(\"step_name\")}')
"

# Approve
curl -X POST "http://localhost:8006/workflows/{workflow_id}/runs/{run_id}/continue" \
  -F 'step_requirements=[{"step_id":"<STEP_ID>","requires_output_review":true,"confirmed":true}]' \
  -F "session_id={session_id}" -F "stream=false"

# Reject with feedback (triggers retry with on_reject=OnReject.retry)
curl -X POST "http://localhost:8006/workflows/{workflow_id}/runs/{run_id}/continue" \
  -F 'step_requirements=[{"step_id":"<STEP_ID>","requires_output_review":true,"confirmed":false,"rejection_feedback":"Fix X"}]' \
  -F "session_id={session_id}" -F "stream=false"

# Edit output and approve
curl -X POST "http://localhost:8006/workflows/{workflow_id}/runs/{run_id}/continue" \
  -F 'step_requirements=[{"step_id":"<STEP_ID>","requires_output_review":true,"confirmed":true,"edited_output":"<corrected>"}]' \
  -F "session_id={session_id}" -F "stream=false"
```