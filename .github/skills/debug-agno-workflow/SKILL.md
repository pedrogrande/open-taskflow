---
name: debug-agno-workflow
description: 'Debug and improve Agno workflows — diagnose paused runs, inspect step output, fix data flow issues, troubleshoot HITL gates, handle errors, and iterate on loop end conditions. Use when a workflow is stuck, producing wrong output, failing at a step, or needs hardening. Covers WorkflowRunOutput inspection, StepInput/StepOutput debugging, error handling, and session state troubleshooting.'
argument-hint: 'Workflow name and symptom, e.g. "design-spec-workflow — stuck in loop, review never passes"'
user-invocable: true
---

# Debug and Improve Agno Workflows

Diagnose and fix workflow issues — paused runs, wrong step output, broken data flow, HITL gates, loop end conditions, and error handling. Follows the patterns used in this project (SurrealDB persistence, AgentOS runtime, Railway deployment).

## When to Use

- Workflow is paused and won't resume
- Step output is wrong type or empty
- Loop end condition never triggers (infinite loop)
- HITL gate not working as expected
- Custom executor producing unexpected results
- Session state not flowing between steps
- Workflow errors or crashes at a specific step
- Need to add error handling or resilience to a workflow

## Architecture Context

```
AgentOS  (app/main.py)
├── agents=[web_search, code_search, design_writer, design_reviewer, impl_writer, impl_reviewer]
└── workflows=[design_spec_workflow, spec_production_workflow]
```

- **DB**: `cawdp_pipeline.db.get_pipeline_db()` — SQLite for workflow sessions
- **Hot-reload**: Edits to workflow files require container restart (unlike agent files)
- **API**: `POST /v1/workflows/{id}/runs` — form-encoded, not JSON

## Symptom → Diagnosis Map

| Symptom | Likely Cause | Where to Look |
|---------|-------------|---------------|
| Workflow pauses indefinitely | HITL gate not resolved, or `is_paused` not checked | `run_output.step_requirements` |
| Loop never terminates | `end_condition` never returns `True` | End condition function logic |
| `previous_step_content` is `None` | Previous step returned empty `StepOutput` | Previous step's agent/executor |
| `previous_step_content` is wrong type | Agent has `output_schema` → returns Pydantic model | Type normalization in executor |
| Step output is `"Error: ..."` | Executor function raised an exception | `StepOutput(success=False, error=...)` |
| Workflow runs but no output | Agent returned empty content or `None` | Agent instructions, tool availability |
| Session state not persisting | Missing `db=` on Workflow constructor | Workflow definition |
| HITL approve/reject has no effect | Resolving wrong requirement (stale entry) | Filter by `confirmed is None` |
| `continue_run` raises ValueError | Requirements not resolved, or wrong `run_id`/`session_id` | Check `is_paused` first |
| Step fails silently | `on_error` defaults to `OnError.fail` — workflow stops | Add `on_error=OnError.pause` |
| Loop iteration review always triggers | `requires_iteration_review` set to a callable (truthy in Python) | Use `True`/`False`, not a callable; use `end_condition` as conditional gate |
| HITL gate creates infinite retry loop | Passthrough executor + `on_reject=OnReject.retry` inside a Loop | Use `requires_iteration_review=True` on the Loop instead |
| Iteration review never triggers | `end_condition` returns `True` before iteration review is checked | Expected — `end_condition` is checked first; this gives conditional HITL |

## Procedure

### 1. Reproduce the Issue

Run the workflow and capture the full output:

```bash
# Non-streaming — get complete WorkflowRunOutput
curl -sS -X POST http://localhost:8006/v1/workflows/<workflow-id>/runs \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=<input>&stream=false" \
  -o /tmp/workflow-run.json

# Inspect the output
jq '.' /tmp/workflow-run.json
```

For streaming (to see step-by-step progress):

```bash
curl -sS -X POST http://localhost:8006/v1/workflows/<workflow-id>/runs \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=<input>&stream=true"
```

### 2. Inspect WorkflowRunOutput

Key properties to check:

```python
run_output = workflow.run("input")

# Is the workflow paused?
run_output.is_paused          # True = waiting for HITL resolution
run_output.pause_kind         # "step" or "executor"
run_output.paused_step_name   # Which step paused
run_output.paused_step_index  # Which step index paused

# What are the requirements?
run_output.step_requirements  # ALL requirements (including resolved ones)
run_output.steps_requiring_confirmation  # Filtered: needs confirm/reject
run_output.steps_requiring_output_review # Filtered: needs output review
run_output.steps_requiring_user_input    # Filtered: needs user input
run_output.steps_requiring_route         # Filtered: needs route selection
run_output.steps_with_errors             # Filtered: steps that failed

# Step results
run_output.step_results      # List of StepOutput objects
run_output.content           # Final workflow output
run_output.status            # RunStatus enum
```

### 3. Debug Paused Workflows (HITL)

**Find the CURRENT pending requirement** — always filter by `confirmed is None`:

```python
# WRONG — returns first match, may be a resolved earlier gate
req = run_output.step_requirements[0]

# CORRECT — find the active (unresolved) requirement
active_reqs = [r for r in (run_output.step_requirements or []) if not r.is_resolved]
if active_reqs:
    req = active_reqs[-1]  # Last entry is the current pause
```

**Resolve and resume:**

```python
# Confirmation gate
req.confirm()                    # Approve
req.reject(feedback="Fix X")     # Reject with feedback

# Output review gate
req.confirm()                    # Approve as-is
req.edit(new_output="...")       # Approve with edits
req.reject(feedback="Redo")     # Reject and retry

# User input gate
req.set_user_input(environment="staging", region="us-east-1")

# Route selection
req.select("tech_specialist")   # Pick one route

# Then resume
run_output = workflow.continue_run(run_output)
```

**Error handling pause** — when a step fails with `on_error=OnError.pause`:

```python
for req in run_output.steps_with_errors:
    print(f"Step '{req.step_name}' failed: {req.error_message}")
    print(f"Error type: {req.error_type}")
    print(f"Retry count: {req.retry_count}")

    if "timeout" in req.error_message.lower():
        req.retry() if req.retry_count < 3 else req.skip()
    else:
        req.skip()  # Unknown error, skip
```

### 4. Debug Loop End Conditions

The `end_condition` function receives a **list of StepOutputs from the current iteration** (not all iterations):

```python
def review_passes(outputs: list[StepOutput]) -> bool:
    """Return True to STOP the loop."""
    if not outputs:
        return False

    # The last step's output is the reviewer's output
    review_output = outputs[-1].content
    if not review_output:
        return False

    # CRITICAL: Convert to string if agent has output_schema
    review_text = str(review_output)

    # Check for pass/fail conditions
    return "PASS" in review_text and "FAIL" not in review_text
```

**Common loop bugs:**

| Bug | Symptom | Fix |
|-----|---------|-----|
| `end_condition` never returns `True` | Infinite loop (stopped by `max_iterations`) | Add logging, check string matching |
| `end_condition` returns `True` too early | Loop exits after first iteration | Check that you're matching the right section of output |
| `previous_step_content` is `None` in loop | Previous step returned empty content | Check agent instructions, add fallback |
| Agent output is Pydantic model, not string | `str.contains()` fails | Normalize: `str(review_output)` or `review_output.model_dump_json()` |
| `max_iterations` too low | Loop stops before quality threshold | Increase `max_iterations` or improve agent instructions |
| Iteration review always triggers | `requires_iteration_review` set to a callable | Use `True`/`False` only — callables are truthy, not evaluated |
| HITL gate infinite retry | Passthrough executor + `on_reject=OnReject.retry` | Replace with `requires_iteration_review=True` on the Loop |
| `forward_iteration_output` not set | Each iteration starts from original input, not previous output | Set `forward_iteration_output=True` on the Loop |

### 5. Debug Loop Iteration Review

Agno's Loop checks `end_condition` BEFORE `requires_iteration_review`. This execution order gives **conditional HITL** — if the review passes, the loop ends without pausing for human review.

**Debug iteration review issues:**

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Iteration review ALWAYS triggers | `requires_iteration_review` set to a callable (truthy) | Use `True`/`False` only; use `end_condition` as conditional gate |
| Iteration review NEVER triggers | `end_condition` returns `True` first | Expected if review passes — this is conditional HITL working correctly |
| Human rejects but loop doesn't revise | `on_reject` defaults to `OnReject.skip` | Set `on_reject=OnReject.retry` to re-run iteration with feedback |
| Next iteration starts from original input | `forward_iteration_output` not set | Add `forward_iteration_output=True` to the Loop |
| Passthrough executor creates infinite loop | `on_reject=OnReject.retry` re-executes passthrough → same HITL pause | Remove passthrough step; use `requires_iteration_review=True` on Loop |

**Correct Loop HITL pattern:**

```python
Loop(
    name="Write-Review Loop",
    steps=[write_step, review_step],
    end_condition=review_passes,  # Checked FIRST — if True, loop ends
    max_iterations=3,
    forward_iteration_output=True,  # Next iteration gets previous output
    human_review=HumanReview(
        requires_iteration_review=True,  # Only reached if end_condition is False
        iteration_review_message="Review this iteration.",
        on_reject=OnReject.retry,  # Re-runs with feedback injected into agent
    ),
)
```

**Wrong pattern (anti-pattern):**

```python
# ❌ NEVER do this — passthrough executor for HITL gate inside a Loop
def _hitl_passthrough(step_input: StepInput) -> StepOutput:
    return StepOutput(content=step_input.previous_step_content)

approve_step = Step(
    name="Approve",
    executor=_hitl_passthrough,
    human_review=HumanReview(requires_output_review=True, on_reject=OnReject.retry),
)
# This creates an infinite loop: retry → passthrough → same HITL pause → retry → ...
```

### 6. Debug Custom Executors

**Type normalization** — `previous_step_content` can be string, dict, or Pydantic model:

```python
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    raw = step_input.previous_step_content

    # Normalize to string
    if hasattr(raw, "model_dump_json"):
        # Agent with output_schema returned a Pydantic model
        raw = raw.model_dump_json()
    elif isinstance(raw, dict):
        raw = json.dumps(raw)
    elif raw is None:
        raw = ""

    # Now safe to do string operations
    if "PASS" in raw:
        ...
```

**Debugging executor logic** — add print/logging inside executors:

```python
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    print(f"[DEBUG] input: {step_input.input[:100]}")
    print(f"[DEBUG] previous_step_content type: {type(step_input.previous_step_content)}")
    print(f"[DEBUG] session_state: {run_context.session_state}")

    # ... executor logic ...

    return StepOutput(content=result)
```

**Early stopping** — return `StepOutput(stop=True)` to halt the entire workflow:

```python
def security_gate(step_input: StepInput) -> StepOutput:
    if "VULNERABLE" in str(step_input.previous_step_content).upper():
        return StepOutput(
            content="Security check failed. Deployment blocked.",
            stop=True,  # Halts the entire workflow
        )
    return StepOutput(content="Security check passed.")
```

### 7. Debug Session State

Session state is shared across all steps and persisted to the database:

```python
# Read state in an executor
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    decisions = run_context.session_state.get("decisions", [])
    review_feedback = run_context.session_state.get("review_feedback")

    # Update state
    run_context.session_state["decisions"] = decisions + [new_decision]
    run_context.session_state["review_feedback"] = None  # Clear after use

    return StepOutput(content="Done")
```

**Common state bugs:**

| Bug | Symptom | Fix |
|-----|---------|-----|
| State not persisting across runs | Missing `db=` on Workflow | Add `db=get_pipeline_db(table_name="workflow_session")` |
| State not flowing to agent | Agent doesn't see state | Set `add_session_state_to_context=True` on the agent |
| State overwritten each run | Using `=` instead of `.update()` | Use `run_context.session_state["key"] = value` |
| Stale state from previous run | Session ID reused | Use a new `session_id` per run, or clear state |

### 8. Debug Error Handling

**OnError options:**

```python
from agno.workflow import OnError

# Default: fail the entire workflow
Step(name="risky", agent=risky_agent, on_error=OnError.fail)

# Skip the step and continue (previous_step_content will be None)
Step(name="risky", agent=risky_agent, on_error=OnError.skip)

# Pause for human decision (retry or skip)
Step(name="risky", agent=risky_agent, on_error=OnError.pause)
```

**Combine error handling with HITL confirmation:**

```python
Step(
    name="deploy",
    agent=deploy_agent,
    human_review=HumanReview(
        requires_confirmation=True,
        confirmation_message="Deploy to production?",
    ),
    on_error=OnError.pause,  # If confirmed but fails, pause for retry
)
```

### 9. Debug via API

**Check workflow status:**

```bash
# List all workflow sessions
curl -s http://localhost:8006/workflows | jq '.'

# Get a specific run
curl -s "http://localhost:8006/workflows/<workflow-id>/runs/<run-id>" | jq '.'
```

**Resume a paused workflow — easiest: use the AgentOS UI**

Open http://localhost:8006 → Workflows → your workflow → the paused run → Approve/Reject/Edit buttons.

**Or use the `scripts/hitl` CLI tool:**

```bash
# Start a run and watch for pauses
python scripts/hitl start "Produce design spec for D-P00-001"

# List known runs and their status
python scripts/hitl list

# Show pending requirement details
python scripts/hitl show <run_id> <session_id>

# Approve the pending gate
python scripts/hitl approve <run_id> <session_id>

# Reject with feedback (triggers retry with on_reject=OnReject.retry)
python scripts/hitl reject <run_id> <session_id> "Missing error handling section"

# Cancel a running or paused run
python scripts/hitl cancel <run_id> <session_id>

# Edit output and approve
python scripts/hitl edit <run_id> <session_id> edited_output.json

# Poll run status until paused or completed
python scripts/hitl watch <run_id> <session_id>
```

**Or use curl directly (form-encoded, not JSON):**

```bash
# Find pending requirement
curl -s "http://localhost:8006/workflows/<workflow-id>/runs/<run-id>?session_id=<session-id>" \
  | python3 -c "
import json, sys
data = json.load(sys.stdin)
for req in data.get('step_requirements', []):
    if req.get('confirmed') is None and req.get('requires_output_review'):
        print(f'step_id: {req[\"step_id\"]}')
        print(f'step_name: {req.get(\"step_name\")}')
        print(f'message: {req.get(\"output_review_message\")}')
"

# Approve
curl -X POST "http://localhost:8006/workflows/<workflow-id>/runs/<run-id>/continue" \
  -F 'step_requirements=[{"step_id":"<STEP_ID>","requires_output_review":true,"confirmed":true}]' \
  -F "session_id=<session-id>" -F "stream=false"

# Reject with feedback
curl -X POST "http://localhost:8006/workflows/<workflow-id>/runs/<run-id>/continue" \
  -F 'step_requirements=[{"step_id":"<STEP_ID>","requires_output_review":true,"confirmed":false,"rejection_feedback":"Fix X"}]' \
  -F "session_id=<session-id>" -F "stream=false"

# Edit output and approve
curl -X POST "http://localhost:8006/workflows/<workflow-id>/runs/<run-id>/continue" \
  -F 'step_requirements=[{"step_id":"<STEP_ID>","requires_output_review":true,"confirmed":true,"edited_output":"<corrected>"}]' \
  -F "session_id=<session-id>" -F "stream=false"
```

> ⚠️ The `/continue` endpoint uses **form-encoded** body (`-F` flags), not JSON.

### 10. Fix and Iterate

Apply fixes based on diagnosis:

| Fix Location | When | Disruption |
|-------------|------|-----------|
| **End condition function** | Loop never terminates or exits too early | Low — hot-reload if in separate module |
| **Agent instructions** | Wrong output format, hallucination, wrong tool | Low — hot-reload |
| **Executor type normalization** | `previous_step_content` wrong type | Low — hot-reload |
| **Workflow step definition** | Add/remove/reorder steps, add HITL | Medium — requires container restart |
| **Session state initialization** | State not flowing correctly | Medium — requires restart |
| **`on_error` handling** | Steps failing silently | Medium — requires restart |
| **`max_iterations`** | Loop hitting safety cap | Low — requires restart |

**After fixing, re-run the workflow with the same input and compare:**

```bash
# Before fix
curl -sS -X POST http://localhost:8006/v1/workflows/<id>/runs \
  -d "message=<input>&stream=false" -o /tmp/before.json

# After fix (restart container if needed)
docker compose restart agentos-api

# After fix
curl -sS -X POST http://localhost:8006/v1/workflows/<id>/runs \
  -d "message=<input>&stream=false" -o /tmp/after.json

# Compare
diff <(jq '.step_results[].content' /tmp/before.json) \
     <(jq '.step_results[].content' /tmp/after.json)
```

## Key Patterns for This Project

### Database
- **Workflow sessions**: `cawdp_pipeline.db.get_pipeline_db(table_name="workflow_session")` — SQLite
- **Agent sessions**: `db.get_surrealdb()` — SurrealDB (separate from workflow sessions)

### Container Restart Scope
- `agents/<slug>.py` — hot-reloads within ~1s
- `cawdp_pipeline/workflows/*.py` — **requires** `docker compose restart agentos-api`
- `cawdp_pipeline/agents/*.py` — hot-reloads within ~1s
- `app/main.py` — **requires** restart

### API Content-Type
`POST /v1/workflows/{id}/runs` expects `application/x-www-form-urlencoded`, NOT JSON. Use `URLSearchParams` or `-d "key=value"` with curl.

### Output Schema Gotcha
When a step's agent has `output_schema`, `step_input.previous_step_content` is a **Pydantic model instance**, not a string. Always normalize before string operations.

### HITL Requirement Filtering
`step_requirements` is an **accumulating list** — it includes resolved requirements from earlier gates. Always filter by `confirmed is None` or use `is_resolved` to find the CURRENT pending requirement.

### Loop End Condition
The `end_condition` function receives outputs from the **current iteration only**, not all iterations. Return `True` to STOP the loop.

**Execution order:** `end_condition` is checked BEFORE `requires_iteration_review`. If `end_condition` returns `True`, the loop ends without pausing for human review. This gives conditional HITL — passing reviews auto-approve, failing reviews pause for human input.

### Loop Iteration Review
Use `requires_iteration_review=True` on a Loop to pause after each iteration for human review. The human can approve (stop loop) or reject with feedback (run another iteration with feedback auto-injected).

Set `forward_iteration_output=True` so the next iteration receives the previous iteration's output.

### Passthrough Executor Anti-Pattern
NEVER create a Step with a passthrough executor for HITL gates inside a Loop. Combined with `on_reject=OnReject.retry`, this creates an infinite loop. Use `requires_iteration_review=True` on the Loop instead.

### `requires_iteration_review` Does NOT Support Callables
It's typed as `bool`. A callable is truthy in Python, so iteration review will ALWAYS trigger. Use `end_condition` as the conditional gate instead.

## Related Resources

- [Agno HITL overview](https://docs.agno.com/workflows/hitl/overview) — pause/resume patterns
- [Agno pause anatomy](https://docs.agno.com/workflows/hitl/pause-anatomy) — StepRequirement, executor requirements
- [Agno error handling](https://docs.agno.com/workflows/hitl/error-handling) — OnError.pause, retry, skip
- [Agno early stopping](https://docs.agno.com/workflows/early-stop) — StepOutput(stop=True)
- [Agno session state](https://docs.agno.com/state/workflows/overview) — state across steps
- [Agno WorkflowRunOutput reference](https://docs.agno.com/reference/workflows/run-output) — all output properties
- Project: `cawdp_pipeline/workflows/design_spec_workflow.py` — design-only workflow with Loop
- Project: `cawdp_pipeline/workflows/spec_production_workflow.py` — unified workflow with conditional iteration review
- Project: `cawdp_pipeline/db.py` — pipeline database config
- Project: `create-agno-workflow` skill — building workflows from scratch
- Project: `improve-agno-agent` skill — hardening agent behavior