---
name: create-agno-workflow
description: 'Use when creating Agno workflows, adding HITL gates, configuring session state, writing custom executors, composing Loop/Condition/Parallel/Router steps, or registering workflows in AgentOS. Covers StepInput/StepOutput, HumanReview, and best practices for the agno-surrealdb-railway stack.'
argument-hint: 'Workflow name and purpose, e.g. "design-review — write and review specs in a loop"'
user-invocable: true
---

# Create Agno Workflow

Build production-grade Agno workflows — deterministic pipelines that orchestrate agents, teams, and custom functions through defined steps. Follows the patterns used in this project (SurrealDB persistence, AgentOS runtime, Railway deployment).

## When to Use

- Creating a new workflow from scratch
- Adding steps (agent, team, function, nested workflow) to an existing workflow
- Configuring HITL (human-in-the-loop) gates for approval or review
- Setting up Loop, Condition, Parallel, or Router step types
- Writing custom executor functions with `StepInput`/`StepOutput`
- Managing workflow session state across steps
- Registering a workflow in `app/main.py`
- Debugging workflow pause/resume issues

## Architecture Context

```
AgentOS  (app/main.py)
├── agents=[web_search, code_search, design_writer, design_reviewer, impl_writer, impl_reviewer]
└── workflows=[design_spec_workflow, spec_production_workflow]
```

- **Model**: `app.settings.default_model()` — single place to bump
- **DB**: `db.get_surrealdb()` for agent sessions, `cawdp_pipeline.db.get_pipeline_db()` for workflow sessions
- **AgentOS**: `app/main.py` registers all agents, teams, workflows, interfaces

## Key Concepts

| Concept | What | When to Use |
|---------|------|-------------|
| **Workflow** | Orchestrates agents/teams/functions as steps | Predictable, repeatable pipelines |
| **Step** | Single execution unit (agent, team, function, or nested workflow) | Building blocks of a workflow |
| **StepInput** | Input to a custom executor: `input`, `previous_step_content`, `previous_step_outputs`, `additional_data` | Custom function executors |
| **StepOutput** | Output from a step: `content`, `success`, `error`, `stop`, `images`, `files` | Returning data from executors |
| **Loop** | Repeat steps until `end_condition` returns True | Iterative refinement, quality gates |
| **Condition** | Branch based on `condition` expression | If/else logic |
| **Parallel** | Run steps simultaneously | Independent tasks |
| **Router** | Route to one of several steps based on input | Topic-based specialist routing |
| **Steps** | Group multiple steps into a single unit | HITL on grouped steps, Condition else_steps |
| **HumanReview** | Pause for human confirmation/input/review | Approval gates, quality checks |
| **WorkflowFactory** | Build a Workflow per request with dynamic config | Per-tenant workflows, runtime step selection |
| **WorkflowAgent** | Agent that decides when to run workflow steps vs answer from history | Conversational workflows |

## Procedure

### 1. Choose the Workflow Pattern

| Pattern | When | Example |
|---------|------|---------|
| **Sequential** | Linear pipeline, each step depends on previous | Research → Write → Edit |
| **Loop** | Iterate until quality threshold met | Write → Review → Revise loop |
| **Condition** | Branch based on intermediate results | If approved → deploy, else → revise |
| **Parallel** | Independent tasks that can run simultaneously | Research A + Research B → Merge |
| **Router** | Route to specialist based on input type | Classify → Route to expert |
| **HITL** | Need human approval or input between steps | Review gate before deployment |

### 2. Create the Workflow File

Create `cawdp_pipeline/workflows/<slug>.py` following this template:

```python
"""<WorkflowName> Workflow
==========================
<One-line purpose>
"""

from agno.workflow import Workflow, Step
from agno.workflow.types import StepInput, StepOutput

from cawdp_pipeline.db import get_pipeline_db

# Import agents used by this workflow
from cawdp_pipeline.agents.some_agent import some_agent

# Define custom executors (see Step 4)
def my_executor(step_input: StepInput) -> StepOutput:
    ...

my_workflow = Workflow(
    name="my-workflow",
    description="What this workflow does.",
    steps=[
        Step(name="Step One", agent=some_agent),
        # Add more steps...
    ],
    session_state={},  # Initial state shared across steps
    db=get_pipeline_db(table_name="workflow_session"),
)
```

### 3. Define Steps

**Agent step** (most common):

```python
from agno.workflow import Step

write_step = Step(
    name="Write Spec",
    agent=design_writer,
    description="Produce a design spec for the given output ID.",
)
```

**Team step**:

```python
research_step = Step(
    name="Research",
    team=research_team,
    description="Analyze the topic from multiple angles.",
)
```

**Custom function step**:

```python
def my_executor(step_input: StepInput) -> StepOutput:
    """Custom executor with full programmatic control."""
    message = step_input.input
    previous = step_input.previous_step_content

    # Call an agent inside the executor
    response = some_agent.run(f"Process: {message}\nContext: {previous}")

    return StepOutput(content=response.content)

process_step = Step(
    name="Process Data",
    executor=my_executor,
)
```

**Class-based executor** (for stateful or configurable logic):

```python
class PersistExecutor:
    def __init__(self, output_dir: str = "specs/"):
        self.output_dir = output_dir

    def __call__(self, step_input: StepInput) -> StepOutput:
        # Stateful logic here
        ...
        return StepOutput(content=result)

persist_step = Step(
    name="Persist Results",
    executor=PersistExecutor(output_dir="specs/"),
)
```

### 4. Access Previous Step Data

```python
def my_executor(step_input: StepInput) -> StepOutput:
    # The workflow's input message
    message = step_input.input

    # Content from the immediately previous step
    previous = step_input.previous_step_content

    # Access any named step's output by name
    all_outputs = step_input.previous_step_outputs
    research_content = step_input.get_step_content("Research Step")

    # Additional data passed at run time
    extra = step_input.additional_data

    # Media accumulated from workflow input and previous steps
    images = step_input.images
    files = step_input.files

    return StepOutput(content=result)
```

> ⚠️ `previous_step_content` can be a **string, dict, or Pydantic model** depending on the previous step's agent. Always check type before string operations:
> ```python
> raw = step_input.previous_step_content
> if hasattr(raw, "model_dump_json"):
>     raw = raw.model_dump_json()
> elif isinstance(raw, dict):
>     raw = json.dumps(raw)
> ```

### 5. Compose with Control Flow

**Loop** — iterate until a condition is met:

```python
from agno.workflow import Loop

def review_passes(outputs: list[StepOutput]) -> bool:
    """Return True to stop the loop (review passed)."""
    if not outputs:
        return False
    review_text = str(outputs[-1].content)
    return "PASS" in review_text and "FAIL" not in review_text

write_review_loop = Loop(
    name="Write-Review Loop",
    steps=[write_step, review_step],
    end_condition=review_passes,
    max_iterations=3,
    forward_iteration_output=True,  # Forward previous iteration output to next
)
```

**Loop with iteration review** — pause for human review when the automated check fails:

```python
from agno.workflow import Loop, OnReject
from agno.workflow.types import HumanReview

# end_condition is checked BEFORE iteration review.
# If the review passes, the loop ends without pausing for human review.
# If the review fails, iteration review pauses for human approval.
# This gives conditional HITL without needing a callable predicate.
write_review_loop = Loop(
    name="Write-Review Loop",
    steps=[write_step, review_step],
    end_condition=review_passes,  # Checked first — if True, loop ends
    max_iterations=3,
    forward_iteration_output=True,
    human_review=HumanReview(
        requires_iteration_review=True,  # Only reached if end_condition is False
        iteration_review_message="Review this iteration. Approve to proceed, reject to revise.",
        on_reject=OnReject.retry,  # Re-runs iteration with feedback injected into agent
    ),
)
```

> ⚠️ **`requires_iteration_review` does NOT support callables.** It's a `bool` parameter. A callable will be truthy (Python functions are always truthy), so iteration review will ALWAYS trigger. Use `end_condition` as the conditional gate instead — it's checked before iteration review.

> ⚠️ **Never use a passthrough executor for HITL gates.** A passthrough executor (one that just forwards `previous_step_content`) combined with `on_reject=OnReject.retry` creates an infinite loop — retry re-executes the passthrough, which creates the same HITL pause. Use Loop `requires_iteration_review=True` instead.

**Condition** — branch based on a CEL expression or previous output:

```python
from agno.workflow import Condition

quality_check = Condition(
    name="Quality Gate",
    condition="previous_step_content.contains('APPROVED')",  # CEL expression
    steps=[deploy_step],       # If condition is True
    else_steps=[revise_step],  # If condition is False
)
```

> ⚠️ The `condition` parameter uses **CEL (Common Expression Language)**, not Python. Available variables include `previous_step_content`, `session_state`, `additional_data`, and `input`. String methods like `.contains()`, `.startsWith()`, and `.endsWith()` work. See [Agno CEL expressions](https://docs.agno.com/agent-os/studio/cel-expressions) for the full syntax.

**Parallel** — run independent steps simultaneously:

```python
from agno.workflow import Parallel

research_parallel = Parallel(
    name="Parallel Research",
    steps=[hackernews_step, finance_step, web_step],
)
```

**Router** — route to a specialist based on classification:

```python
from agno.workflow import Router

classify_route = Router(
    name="Topic Router",
    selector=classifier_agent,  # Agent that returns a step name or Step object
    choices={
        "tech": tech_step,
        "finance": finance_step,
        "general": general_step,
    },
)
```

The `selector` agent's response determines routing. It can return:
- A **string** matching a key in `choices`
- A **Step** object from `choices`
- A **list of Steps** (executed sequentially as a `Steps` container)

Use `step_choices` parameter to pass the choices dict to the selector agent's context.

**Steps** — group multiple steps into a single unit:

```python
from agno.workflow import Steps

research_group = Steps(
    name="Research Pipeline",
    steps=[web_search_step, analyze_step, summarize_step],
)
```

Use `Steps` when you want to apply HITL to a group of steps (confirm once for all), or when a `Condition` needs multiple steps in an `else_steps` branch.

### 6. Add HITL (Human-in-the-Loop)

HITL pauses the workflow for human action. State is persisted to the database so you can resume after the user responds.

There are **two HITL levels** — workflow-level and executor-level — which can coexist on the same step:

| Level | What pauses | Configured on |
|-------|-------------|---------------|
| **Workflow-level** | The step/loop/condition/router itself | `HumanReview` on Step, Loop, Condition, Router |
| **Executor-level** | A tool call inside the agent/team | `@tool(requires_confirmation=True)` on the tool |

When both are present, the workflow pauses **twice**: once before the step runs (workflow-level), and once when the agent calls a HITL tool (executor-level).

**Step confirmation** — approve before a step runs:

```python
from agno.workflow.types import HumanReview
from agno.workflow import OnReject

deploy_step = Step(
    name="Deploy",
    agent=deploy_agent,
    human_review=HumanReview(
        requires_confirmation=True,
        confirmation_message="Deploy to production?",
        on_reject=OnReject.cancel,  # skip | cancel | retry
    ),
)
```

**Output review** — review a step's output after it runs:

```python
review_step = Step(
    name="Review Output",
    agent=review_agent,
    human_review=HumanReview(
        requires_output_review=True,
        confirmation_message="Review the generated spec.",
        on_reject=OnReject.retry,  # Re-execute with feedback
    ),
)
```

**User input** — collect parameters before a step runs:

```python
from agno.workflow.types import UserInputField

config_step = Step(
    name="Configure",
    agent=config_agent,
    human_review=HumanReview(
        requires_user_input=True,
        user_input_fields=[
            UserInputField(name="environment", description="Target environment"),
            UserInputField(name="region", description="Deployment region"),
        ],
    ),
)
```

**Timeout** — auto-resolve if the user doesn't respond:

```python
from agno.workflow import OnTimeout

approve_step = Step(
    name="Approve",
    agent=approve_agent,
    human_review=HumanReview(
        requires_confirmation=True,
        confirmation_message="Approve deployment?",
        timeout=300,                     # 5 minutes
        on_timeout=OnTimeout.approve,    # approve | reject | cancel
    ),
)
```

**Resume a paused workflow**:

```python
# Run the workflow — it pauses at the HITL gate
run_output = workflow.run("Process data")

# Async variant
run_output = await workflow.arun("Process data")

if run_output.is_paused:
    # Find the pending requirement (last entry in step_requirements)
    for req in run_output.step_requirements:
        if req.confirmed is None:  # Pending
            req.confirm()           # Or req.reject(feedback="...")

    # Resume from where it left off
    run_output = workflow.continue_run(run_output)

    # Async variant (use in FastAPI BackgroundTasks)
    run_output = await workflow.acontinue_run(run_output)
```

> ⚠️ **Critical**: Always filter `step_requirements` by `confirmed is None` to find the CURRENT pending requirement. Using `find()` without this filter returns the FIRST requirement, which may be an already-resolved one from an earlier gate.

### 7. Validate Input and Manage Session State

**Validate workflow input** with `input_schema`:

```python
from pydantic import BaseModel

class SpecRequest(BaseModel):
    output_id: str
    depth: str = "medium"

workflow = Workflow(
    name="spec-workflow",
    input_schema=SpecRequest,  # Validates and parses input
    steps=[...],
)

# Run with validated input
workflow.run(SpecRequest(output_id="D-P00-001", depth="deep"))
```

When `input_schema` is set, the workflow validates the input message against the Pydantic model before any step runs. Invalid input raises a validation error.

**Workflow session state** is shared across all steps and persisted to the database:

```python
workflow = Workflow(
    name="my-workflow",
    session_state={"decisions": [], "review_feedback": None},
    db=get_pipeline_db(table_name="workflow_session"),
)
```

**Access state in custom executors** via `run_context`:

```python
from agno.run import RunContext

def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    # Read state
    decisions = run_context.session_state.get("decisions", [])

    # Update state
    run_context.session_state["review_feedback"] = "needs revision"

    return StepOutput(content="Done")
```

**State flows automatically** to agents and teams within steps — they receive `run_context.session_state` without manual wiring.

**Workflow history** — enable `add_workflow_history_to_steps=True` to include previous run messages in step context. This is essential for conversational workflows where steps need to reference earlier interactions. Pair with `num_history_runs` to control how many past runs are included.

### 8. Register in AgentOS

Add to `app/main.py`:

```python
from cawdp_pipeline.workflows.my_workflow import my_workflow

agent_os = AgentOS(
    ...
    workflows=[..., my_workflow],
    ...
)
```

Restart: `docker compose restart agentos-api`

### 9. Test Locally

```bash
# Ensure Docker is running
docker compose up -d --build

# Test via API (non-streaming)
curl -X POST http://localhost:8006/v1/workflows/my-workflow/runs \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=Write+spec+for+D-P00-001&stream=false"

# Test via API (streaming)
curl -X POST http://localhost:8006/v1/workflows/my-workflow/runs \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=Write+spec+for+D-P00-001&stream=true"
```

**Test HITL resume**:

```bash
# 1. Start the workflow — it pauses at the HITL gate
# 2. Get pending pauses
curl http://localhost:8006/hitl/pending

# 3. Approve and resume
curl -X POST http://localhost:8006/hitl/{run_id}/approve
```

## Quick References

Full constructor and parameter tables are in [quick-reference.md](./references/quick-reference.md):

- **Workflow constructor** — all 15 parameters
- **Step constructor** — agent, team, executor, human_review
- **HumanReview** — confirmation, output review, user input, timeout
- **Loop** — end_condition, max_iterations, forward_iteration_output, human_review
- **Condition** — CEL expression, steps, else_steps
- **Parallel** — steps
- **Router** — selector, choices, step_choices
- **Steps** — container for grouped steps
- **WorkflowFactory** — dynamic workflow creation
- **WorkflowAgent** — conversational workflow agent
- **StepInput / StepOutput** — all fields
- **OnReject / OnTimeout** — all values
- **HITL primitives matrix** — which primitives support which HITL modes
- **Async execution** — sync/async method pairs
- **Serialization** — save, load, deep_copy, to_dict

Advanced patterns are in [advanced.md](./references/advanced.md):

- **WorkflowFactory** — dynamic workflows per request
- **WorkflowAgent** — conversational workflows
- **Serialization and testing** — save/load, deep_copy, cli_app
- **RemoteWorkflow** — execute on another AgentOS
- **Parallel step outputs** — accessing individual parallel results
- **Early stopping** — `StepOutput(stop=True)`
- **Nested workflows** — workflow as a step
- **Workflow history** — `add_workflow_history_to_steps`

## Key Patterns for This Project

### Database
- **Agent sessions**: Use `db.get_surrealdb()` from `db/`
- **Workflow sessions**: Use `cawdp_pipeline.db.get_pipeline_db()` — creates a SurrealDb with a custom table name

### Custom Executor Signature
```python
def my_executor(step_input: StepInput) -> StepOutput:
    # OR with run_context:
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
```

### Output Schema Gotcha
See Step 4 — `previous_step_content` can be a Pydantic model, dict, or string. Always normalize before string operations.

### HITL in AgentOS
The project has a custom HITL API in `app/routers/hitl.py`:
- `GET /hitl/pending` — list all paused workflow runs
- `POST /hitl/{run_id}/approve` — approve and resume
- `POST /hitl/{run_id}/reject` — reject with feedback, triggers retry
- `POST /hitl/{run_id}/edit` — approve with edited output

All approve/reject/edit endpoints use `BackgroundTasks` because `workflow.acontinue_run()` can take minutes.

### Loop End Condition
The `end_condition` function receives a **list of all StepOutputs from the current iteration** (not all iterations). Return `True` to stop the loop.

**Execution order**: `end_condition` is checked BEFORE `requires_iteration_review`. This means `end_condition` acts as a conditional gate for iteration review — if the condition passes, the loop ends without pausing for human review.

### Loop Iteration Review
Use `requires_iteration_review=True` on a Loop to pause after each iteration for human review. The human can:
- **Approve** → stop the loop, proceed to next workflow step
- **Reject with feedback** → run another iteration with feedback auto-injected into the agent's message

Set `forward_iteration_output=True` so the next iteration receives the previous iteration's output as input (instead of the original step input).

### Passthrough Executor Anti-Pattern
See Step 5 — never use a passthrough executor for HITL gates. Use Loop `requires_iteration_review=True` instead.

### Early Stopping

Return `StepOutput(stop=True)` from any executor to terminate the entire workflow immediately. Useful for guardrails and input validation.

### Nested Workflows

A `Workflow` can be used as a step inside another workflow — pass it directly in the `steps` list (no `Step()` wrapper needed). The inner workflow's output becomes the step's `StepOutput.content`.

**Advanced**: See [references/advanced.md](references/advanced.md) for WorkflowFactory, WorkflowAgent, serialization, RemoteWorkflow, parallel outputs, and workflow history.

## Related Resources

- [Agno workflows overview](https://docs.agno.com/workflows/overview) — concepts and patterns
- [Agno HITL](https://docs.agno.com/workflows/hitl/overview) — human-in-the-loop details
- [Agno workflow examples](https://docs.agno.com/examples/workflows) — complete examples
- [Agno CEL expressions](https://docs.agno.com/agent-os/studio/cel-expressions) — Condition evaluator syntax
- [Agno StepInput reference](https://docs.agno.com/reference/workflows/step_input) — input schema
- [Agno StepOutput reference](https://docs.agno.com/reference/workflows/step_output) — output schema
- [Agno Workflow reference](https://docs.agno.com/reference/workflows/workflow) — full constructor
- [Agno WorkflowFactory](https://docs.agno.com/agent-os/factories/workflow-factory.md) — dynamic workflow creation
- [Agno WorkflowAgent](https://docs.agno.com/examples/workflows/advanced-concepts/workflow-agent/overview.md) — conversational workflow agent
- [Agno teams](https://docs.agno.com/teams/overview) — multi-agent routing
- [Agno context providers](https://docs.agno.com/context-providers/overview) — reduce tool surface
- Project: `cawdp_pipeline/workflows/design_spec_workflow.py` — design-only workflow example
- Project: `cawdp_pipeline/workflows/spec_production_workflow.py` — unified design+impl workflow with conditional iteration review
- Project: `app/routers/hitl.py` — HITL API endpoints