# Agno Workflow Quick References

## Workflow Constructor

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `name` | `str` | None | Workflow display name |
| `id` | `str` | auto UUID | Workflow ID (used as API path) |
| `description` | `str` | None | Description shown in AgentOS |
| `steps` | `WorkflowSteps` | None | List of Steps, Loop, Condition, Parallel, Router |
| `db` | `BaseDb` | None | Database for session persistence (required for HITL) |
| `session_state` | `dict` | None | Initial state shared across steps |
| `session_id` | `str` | auto | Default session ID |
| `user_id` | `str` | None | Default user ID |
| `input_schema` | `BaseModel` | None | Validate workflow input against schema |
| `stream` | `bool` | None | Stream responses |
| `stream_events` | `bool` | False | Stream intermediate step events |
| `store_executor_outputs` | `bool` | True | Store agent/team responses in flattened runs |
| `debug_mode` | `bool` | False | Enable debug logging |
| `add_workflow_history_to_steps` | `bool` | False | Include workflow history in step context |
| `num_history_runs` | `int` | None | Number of past runs to include in history |

## Step Constructor

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `name` | `str` | None | Step name (used for `get_step_content()`) |
| `agent` | `Agent` | None | Agent to execute this step |
| `team` | `Team` | None | Team to execute this step |
| `executor` | `Callable` | None | Custom function `(StepInput) → StepOutput` |
| `description` | `str` | None | Instructions for agent/team steps |
| `human_review` | `HumanReview` | None | HITL configuration |
| `additional_data` | `dict` | None | Extra context passed to executor |

## HumanReview

| Parameter | Type | Purpose |
|-----------|------|---------|
| `requires_confirmation` | `bool` | Pause before step runs for approval |
| `requires_output_review` | `bool` | Pause after step runs to review output |
| `requires_user_input` | `bool` | Pause to collect user input parameters |
| `confirmation_message` | `str` | Message shown to the user |
| `user_input_fields` | `list[UserInputField]` | Fields to collect from user |
| `on_reject` | `OnReject` | What happens on rejection: `skip`, `cancel`, `retry` |
| `timeout` | `int` | Seconds before auto-resolve |
| `on_timeout` | `OnTimeout` | Auto-resolve action: `approve`, `reject`, `cancel` |

## Loop

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Loop name |
| `steps` | `list[Step]` | Steps to execute each iteration |
| `end_condition` | `Callable[[list[StepOutput]], bool]` | Return True to stop looping |
| `max_iterations` | `int` | Safety cap on iterations |
| `forward_iteration_output` | `bool` | Forward previous iteration output to next (default False) |
| `human_review` | `HumanReview` | HITL config for iteration review |

## Condition

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Condition name |
| `condition` | `str` | CEL expression (e.g. `"previous_step_content.contains('APPROVED')"`) |
| `steps` | `list[Step]` | Steps to run if condition is True |
| `else_steps` | `list[Step]` | Steps to run if condition is False |

## Parallel

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Parallel name |
| `steps` | `list[Step]` | Steps to run simultaneously |

## Router

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Router name |
| `selector` | `Agent` | Agent that returns a step name, Step, or list of Steps |
| `choices` | `dict[str, Step]` | Mapping of choice names to Step objects |
| `step_choices` | `list[Step]` | Available choices passed to selector agent context |

## Steps (Container)

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Steps container name |
| `steps` | `list[Step]` | Steps to execute sequentially |

## WorkflowFactory

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Factory name |
| `workflow_builder` | `Callable[[dict], Workflow]` | Function that builds a Workflow from request data |

## WorkflowAgent

| Parameter | Type | Purpose |
|-----------|------|---------|
| `name` | `str` | Agent name |
| `workflow` | `Workflow` | The workflow to wrap |
| `model` | `Model` | LLM model for conversation |

## StepInput

| Field | Type | Description |
|-------|------|-------------|
| `input` | `str \| dict \| list \| BaseModel` | Primary input message |
| `previous_step_content` | `Any` | Content from the last step |
| `previous_step_outputs` | `dict[str, StepOutput]` | All previous step outputs by name |
| `additional_data` | `dict[str, Any]` | Additional context data |
| `images` | `list[Image]` | Accumulated images |
| `videos` | `list[Video]` | Accumulated videos |
| `audio` | `list[Audio]` | Accumulated audio |
| `files` | `list[File]` | Accumulated files |

## StepOutput

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `content` | `str \| dict \| list \| BaseModel \| Any` | None | Primary output |
| `success` | `bool` | True | Execution success status |
| `error` | `str` | None | Error message if failed |
| `stop` | `bool` | False | Request early workflow termination |
| `images` | `list[Image]` | None | Media outputs |
| `videos` | `list[Video]` | None | Media outputs |
| `audio` | `list[Audio]` | None | Media outputs |
| `files` | `list[File]` | None | File outputs |
| `metrics` | `RunMetrics` | None | Execution metrics |
| `steps` | `list[StepOutput]` | None | Nested step outputs |

## OnReject Values

| Value | Behavior |
|-------|----------|
| `OnReject.skip` | Skip the step and continue (default for most) |
| `OnReject.cancel` | Cancel the entire workflow |
| `OnReject.retry` | Re-execute the step (pair with `reject(feedback=...)`) |
| `OnReject.else_branch` | Execute else_steps (Condition only) |

## OnTimeout Values

| Value | Behavior |
|-------|----------|
| `OnTimeout.approve` | Auto-approve after timeout |
| `OnTimeout.reject` | Auto-reject after timeout |
| `OnTimeout.cancel` | Cancel workflow after timeout |

## HITL Pause Levels

| Level | What pauses | Configured on |
|-------|-------------|---------------|
| **Step-level** | The workflow primitive (Step, Loop, etc.) | `HumanReview` on Step/Loop/Condition/Router |
| **Executor-level** | A tool call inside the agent/team | `@tool(requires_confirmation=True)` on the tool |
| **Nested** | Both step and executor gates in sequence | Both of the above |

## HITL Supported Primitives

| Primitive | Confirmation | User Input | Output Review | Iteration Review | Route Selection | Executor HITL |
|-----------|:-----------:|:----------:|:------------:|:---------------:|:--------------:|:-------------:|
| Step | ✓ | ✓ | ✓ | — | — | ✓ |
| Steps | ✓ | — | — | — | — | ✓ (via inner) |
| Condition | ✓ | — | — | — | — | ✓ (via inner) |
| Loop | ✓ | — | ✓ | ✓ | — | ✓ (via inner) |
| Parallel | — | — | — | — | — | ✓ (via inner) |
| Router | ✓ | — | ✓ | — | ✓ | ✓ (via inner) |

## Early Stopping

Return `StepOutput(stop=True)` from any executor to terminate the entire workflow immediately. Useful for guardrails and input validation.

## Async Execution

| Method | Sync | Async |
|--------|------|-------|
| Run | `workflow.run(msg)` | `await workflow.arun(msg)` |
| Continue | `workflow.continue_run(run)` | `await workflow.acontinue_run(run)` |
| Stream | `workflow.run(msg, stream=True)` | `await workflow.arun(msg, stream=True)` |

## Serialization

| Method | Purpose |
|--------|---------|
| `workflow.save(path)` | Save workflow config to JSON file |
| `Workflow.load(path)` | Load workflow from JSON file |
| `workflow.deep_copy(update=...)` | Create isolated copy with optional state overrides |
| `workflow.to_dict()` | Serialize workflow config to dict |