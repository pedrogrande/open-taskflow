# Advanced Workflow Patterns

Detailed patterns for advanced Agno workflow usage. See the main SKILL.md for core concepts.

## Table of Contents

- [WorkflowFactory — Dynamic Workflows per Request](#workflowfactory--dynamic-workflows-per-request)
- [WorkflowAgent — Conversational Workflows](#workflowagent--conversational-workflows)
- [Serialization and Testing](#serialization-and-testing)
- [RemoteWorkflow — Execute on Another AgentOS](#remoteworkflow--execute-on-another-agentos)
- [Parallel Step Outputs](#parallel-step-outputs)
- [Early Stopping](#early-stopping)
- [Nested Workflows](#nested-workflows)
- [Workflow History](#workflow-history)

## WorkflowFactory — Dynamic Workflows per Request

Use `WorkflowFactory` when the workflow's steps, agents, or model depend on the caller's input (e.g., per-tenant configuration):

```python
from agno.agent_os import WorkflowFactory

def build_workflow(body: dict) -> Workflow:
    # body contains the request data — build steps dynamically
    model_id = body.get("model", "gpt-5.4")
    return Workflow(
        name=f"dynamic-{body.get('tenant')}",
        steps=[Step(name="Process", agent=Agent(model=OpenAIResponses(id=model_id)))],
        db=get_pipeline_db(table_name="dynamic_sessions"),
    )

factory = WorkflowFactory(name="dynamic-workflow", workflow_builder=build_workflow)
# Register factory in AgentOS instead of a static Workflow
```

## WorkflowAgent — Conversational Workflows

`WorkflowAgent` wraps a workflow in an agent that decides when to execute workflow steps versus answer from history. Useful for chat interfaces where the user might ask follow-up questions between steps:

```python
from agno.workflow import WorkflowAgent

agent = WorkflowAgent(
    name="spec-assistant",
    workflow=spec_production_workflow,
    # The agent handles conversation flow, executing steps as needed
)
```

## Serialization and Testing

```python
# Save/load workflows for persistence or testing
workflow.save("my_workflow.json")
loaded = Workflow.load("my_workflow.json")

# Create isolated copies for parallel runs
copy = workflow.deep_copy(update={"session_state": {"user": "alice"}})

# Interactive CLI testing
workflow.cli_app()  # Starts an interactive terminal session
```

## RemoteWorkflow — Execute on Another AgentOS

```python
from agno.workflow import RemoteWorkflow

remote = RemoteWorkflow(
    url="https://my-agentos.example.com",
    workflow_id="spec-production",
)
result = remote.run(message="Write spec for D-P00-001")
```

## Parallel Step Outputs

When using `Parallel`, each parallel step's output is collected in `StepOutput.steps`. Access individual outputs:

```python
def merge_executor(step_input: StepInput) -> StepOutput:
    # step_input.previous_step_content contains the Parallel's merged output
    # step_input.previous_step_outputs contains each named step's output
    research_a = step_input.get_step_content("Research A")
    research_b = step_input.get_step_content("Research B")
    return StepOutput(content=f"Merged: {research_a}\n{research_b}")
```

## Early Stopping

Return `StepOutput(stop=True)` from any executor to terminate the entire workflow immediately. Useful for guardrails — if input validation fails, short-circuit without running downstream steps:

```python
def validate_executor(step_input: StepInput) -> StepOutput:
    if not step_input.input:
        return StepOutput(content="No input provided", stop=True)
    return StepOutput(content="Valid input")
```

## Nested Workflows

A `Workflow` can be used as a step inside another workflow. Pass it directly in the `steps` list — no need to wrap it in `Step()`:

```python
outer_workflow = Workflow(
    name="outer",
    steps=[
        research_step,
        inner_workflow,  # Nested workflow — auto-wrapped
        final_step,
    ],
)
```

The inner workflow's output becomes the step's `StepOutput.content`.

## Workflow History

Enable `add_workflow_history_to_steps=True` on the Workflow constructor to include previous run messages in step context. This is essential for conversational workflows where steps need to reference earlier interactions. Pair with `num_history_runs` to control how many past runs are included.

```python
workflow = Workflow(
    name="conversational-workflow",
    steps=[...],
    add_workflow_history_to_steps=True,
    num_history_runs=3,
    db=get_pipeline_db(table_name="workflow_session"),
)
```