---
name: cawdp-agno-workflows
description: 'Build CAWDP multi-phase workflows using Agno primitives (Loop, requires_iteration_review, end_condition, session_state, custom executors). Use when implementing write→review→HITL cycles, decision register sharing, conditional human approval gates, or any CAWDP phase workflow that orchestrates writer and reviewer agents. Covers the conditional HITL pattern where automated review passes skip human approval.'
argument-hint: 'CAWDP phase/output ID, e.g. "P1-O5 Task Contract Schema write→review workflow"'
user-invocable: true
---

# CAWDP Agno Workflows

Build CAWDP multi-phase workflows using Agno's Loop, HITL, session_state, and executor patterns. CAWDP workflows follow a consistent write→review→human-if-needed cycle that keeps human overhead low while maintaining quality gates.

## When to Use

- Implementing any CAWDP phase workflow (P0-P10)
- Building write→review loops with conditional HITL (human reviews only when automated review fails)
- Sharing decision register or other state across workflow steps
- Persisting workflow outputs to files or databases
- Creating iterative refinement cycles (agent revises based on reviewer feedback)
- Structuring workflows where review quality determines whether human approval is needed

## Core CAWDP Workflow Pattern

Every CAWDP phase workflow follows the same structure:

```
Writer Agent (produces output)
     ↓
Reviewer Agent (evaluates against quality gate)
     ↓
end_condition checks review result
     ↓
   Pass → loop ends → proceed to next phase
   Fail → iteration_review pauses for human
     ↓
Human approves/rejects (only if automated review failed)
     ↓
Approve → next phase
Reject → writer revises with feedback
```

This pattern appears in:

- P0: Purpose & Vision specification
- P1: Output specification  
- P2: Backcasting dependency analysis
- P3: Task decomposition
- P4: Capability allocation
- P7: Agent design specs
- P8: Contract formalization

## Key Agno Primitives

| Primitive | Purpose in CAWDP | Code Pattern |
|-----------|------------------|--------------|
| **Loop** | Write→review→revise cycles | `Loop(steps=[...], end_condition=..., requires_iteration_review=True)` |
| **end_condition** | Stop loop when review passes | `def _passes(outputs): return check_review_summary(outputs[-1])` |
| **requires_iteration_review** | Pause for human ONLY when end_condition doesn't stop loop | `requires_iteration_review=True` (bool, not callable) |
| **session_state** | Share decision register across steps | `session_state={"decisions": []}` |
| **forward_iteration_output** | Feed previous iteration to next | `forward_iteration_output=True` |
| **OnReject.retry** | Re-run with rejection feedback | `on_reject=OnReject.retry` |
| **Custom executor** | Persist outputs, normalize data | `def executor(step_input: StepInput) -> StepOutput:` |

## Conditional HITL: end_condition Before iteration_review

**Critical Agno execution order:**

1. Loop runs all steps
2. **end_condition checked first** → if True, loop ends (no HITL)
3. **requires_iteration_review checked second** → if True, pause for human

This gives conditional HITL: review passes → auto-proceed, review fails → human reviews.

❌ **Wrong** (callable predicate on requires_iteration_review):

```python
Loop(
    requires_iteration_review=lambda outputs: not review_passes(outputs),  # WRONG! Always truthy (Python functions are truthy)
)
```

✅ **Right** (end_condition + requires_iteration_review bool):

```python
Loop(
    end_condition=_review_passes,  # Stops loop when review passes
    requires_iteration_review=True,  # Pauses only if end_condition didn't stop
)
```

## Procedure

### 1. Choose the CAWDP Phase Pattern

| Phase | Workflow Type | Key Features |
|-------|---------------|--------------|
| P0-P1 | Single write→review loop | One output artifact, quality gate in review |
| P2 | Dependency tracing | Backcasting engine tool, gap detection |
| P3-P4 | Multi-agent decomposition | Decompose, Type, Allocate as separate agents |
| P5 | Event storming | Adversarial review, failure mode discovery |
| P6-P8 | Sequential with validation | Each phase builds on previous, cumulative state |
| P10 | Monitoring + evolution | Runs continuously, triggers redesign |

### 2. Define the Writer Agent

CAWDP writer agents:

- Have `output_schema` set to the Pydantic model for the phase output
- Access `session_state` for decision register via `tools=[DecisionToolkit()]`
- Receive `instructions` with the phase-specific quality criteria
- Use markdown formatting for structured output

```python
from agno.agent import Agent
from pydantic import BaseModel, Field

from app.settings import default_model
from cawdp_pipeline.db import get_pipeline_db
from cawdp_pipeline.tools.decision_tools import DecisionToolkit

class TaskContract(BaseModel):
    """Output schema for P3 Task Decomposition."""
    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="What this task does")
    cognitive_type: str = Field(..., description="Mechanical/Analytical/Generative/Evaluative/Intuitive")
    # ... more fields

design_writer = Agent(
    id="design-writer",
    name="Design Spec Writer",
    model=default_model(),
    db=get_pipeline_db(table_name="design_sessions"),
    tools=[DecisionToolkit()],  # Access to record_decision, list_decisions
    instructions=INSTRUCTIONS,
    output_schema=TaskContract,  # Structured output
    enable_agentic_memory=True,
    markdown=True,
)
```

### 3. Define the Reviewer Agent

CAWDP reviewer agents:

- Review against the phase-specific quality gate (Fidelity, Enrichment, Cross-Cutting)
- Produce a Summary table with PASS/FAIL/WARNING per dimension
- DO NOT have `output_schema` (produce markdown review reports)
- Often use Ollama for cost optimization (reviews are cheaper than generation)

```python
from agno.models.ollama import Ollama

design_reviewer = Agent(
    id="design-reviewer",
    name="Design Spec Reviewer",
    model=Ollama(id="glm-5.1:cloud", host="https://ollama.com"),
    db=get_pipeline_db(table_name="review_sessions"),
    instructions=REVIEWER_INSTRUCTIONS,
    markdown=True,
)
```

#### L-033 — Add `output_schema` + `parser_model` for defense-in-depth (optional)

If the reviewer silently skips sections (L-026, L-028), the workflow executor can
cross-check its final response against DB verdicts using a structured summary.
`output_schema` constrains the **final response** only — the reviewer still calls
`write_verdict` tool calls for each section. `parser_model` (OpenAI) parses the
free-form Ollama response into the typed model.

```python
from pydantic import BaseModel

class ReviewSummary(BaseModel):
    sections_reviewed: list[str]   # cross-check against expected section keys
    all_passed: bool               # cross-check against DB query
    failing_sections: list[str]    # cross-check against list_failing_sections()

design_reviewer = Agent(
    ...
    output_schema=ReviewSummary,
    parser_model=OpenAIChat(id="gpt-4o"),  # Ollama doesn't support structured output
    parser_model_prompt="Extract the review summary from the agent's response.",
)
```

The executor cross-checks after the step runs:

```python
summary: ReviewSummary = step_output.content  # Pydantic model
db_fails = list_failing_sections(output_id, run_id)
if set(db_fails) != set(summary.failing_sections):
    log.warning("Reviewer summary disagrees with DB — trusting DB verdicts")
```

Cost: one additional OpenAI call per reviewer run. Only add when reviewer reliability
is a concern.

### 4. Write the end_condition Function

The end_condition parses the reviewer's Summary table to determine pass/fail:

```python
from typing import List
import re
from agno.workflow.types import StepOutput

def _review_passes(outputs: List[StepOutput]) -> bool:
    """Return True to stop loop (review passed), False to continue."""
    if not outputs:
        return False

    review_output = outputs[-1].content
    if not review_output:
        return False

    review_text = str(review_output)

    # Extract Summary section (try multiple heading patterns)
    summary_section = None
    for pattern in [
        r"##\s*1\.?\s*Summary(.*?)(?=\n##\s|\Z)",
        r"##\s*Summary(.*?)(?=\n##\s|\Z)",
    ]:
        match = re.search(pattern, review_text, re.DOTALL)
        if match:
            summary_section = match.group(1)
            break

    if summary_section:
        # Parse table rows for PASS/FAIL status
        rows = re.findall(r"\|\s*[^|]+\s*\|\s*(PASS|FAIL|WARNING)\s*\|", summary_section)
        if rows:
            return "FAIL" not in rows

    # Fallback: check entire review for explicit FAIL mentions
    return "FAIL" not in review_text.upper()
```

#### L-026 — Guard against empty verdict set in `end_condition`

When the reviewer did not write ANY verdicts (e.g. it failed to call `write_verdict`
on any section), `list_verdicts_for_run()` returns `[]`. An empty fails list would
incorrectly make `len(fails) == 0 → True` → loop ends with no spec written.

```python
# ❌ WRONG — empty list passes as "all good"
def _end_condition(outputs):
    verdicts = list_verdicts_for_run(output_id, run_id)
    fails = [v for v in verdicts if v.verdict == "FAIL"]
    return len(fails) == 0  # True when verdicts=[] !

# ✅ CORRECT — guard against empty before counting fails
def _end_condition(outputs):
    verdicts = list_verdicts_for_run(output_id, run_id)
    if len(verdicts) == 0:
        return False  # reviewer didn't complete tool calls — iterate
    fails = [v for v in verdicts if v.verdict == "FAIL"]
    return len(fails) == 0
```

#### L-030 — `already_passing` requires two-part update when all sections pre-pass

When a workflow run writes `already_passing` (sections that passed in a prior run) to
`session_state` before the loop, the `end_condition` closure must combine both sources:

```python
# Factory: capture pre-passing sections at construction time
def make_end_condition(output_id: str, already_passing: frozenset[str]) -> Callable:
    def _end_condition(outputs: list[StepOutput]) -> bool:
        verdicts = list_verdicts_for_run(output_id, current_run_id())
        if len(verdicts) == 0:
            # Special case: if EVERY expected section was already passing,
            # the reviewer has nothing to review — treat as done.
            expected = get_expected_sections(output_id)
            return expected.issubset(already_passing)
        fails = [v for v in verdicts if v.verdict == "FAIL"]
        current_pass = frozenset(v.section_key for v in verdicts if v.verdict == "PASS")
        expected = get_expected_sections(output_id)
        return expected.issubset(current_pass | already_passing)
    return _end_condition
```

Key points:

- Compute `already_passing` **before** building the Loop (not inside the executor).
- The empty-verdict guard from L-026 must have the `already_passing` bypass, otherwise
  a run where all sections already pass would never terminate.
- `expected.issubset(current_pass | already_passing)` — union the two pass sources.

### 5. Build the Loop with Conditional HITL

```python
from agno.workflow import Loop, OnReject, Step, Workflow

write_review_loop = Loop(
    name="Write→Review Loop",
    steps=[
        Step(
            name="Write Spec",
            agent=design_writer,
            description="Produce the design spec for the given output.",
        ),
        Step(
            name="Review Spec",
            agent=design_reviewer,
            description="Evaluate the spec against quality gates.",
        ),
    ],
    end_condition=_review_passes,  # Checked BEFORE iteration_review
    requires_iteration_review=True,  # Pauses ONLY if end_condition didn't stop
    on_reject=OnReject.retry,  # Rejection feedback injected into writer
    forward_iteration_output=True,  # Writer sees previous iteration's output
    max_iterations=5,
)
```

**Execution flow:**

1. Writer produces spec
2. Reviewer evaluates spec
3. end_condition checks review → if PASS, loop ends (no human)
4. If FAIL, iteration_review pauses → human approves/rejects
5. If human rejects, OnReject.retry runs another iteration with feedback
6. Writer receives: original message + previous output + rejection feedback

### 6. Add Decision Register Sharing via session_state

CAWDP workflows share the decision register across steps using `session_state`:

```python
from cawdp_pipeline.models.decisions import Decision, DecisionRegister

workflow = Workflow(
    name="design-spec-workflow",
    steps=[write_review_loop, persist_step],
    session_state={
        "decisions": [],  # Writer adds, reviewer validates, persist saves
    },
    db=get_pipeline_db(table_name="workflow_sessions"),
)
```

**In the writer agent's instructions:**

```markdown
Record decisions using the record_decision tool:
- decision_id: unique ID (e.g., "D-P1-O5-001")
- phase: CAWDP phase (e.g., "P1-Output-Specification")
- question: What was decided
- answer: The decision
- rationale: Why this decision
- output_refs: Which outputs this affects
```

**In the reviewer agent's instructions:**

```markdown
Check decision register completeness:
- Every significant design choice has a decision record
- Decision rationales are specific, not generic
- Decision IDs follow the format D-<phase>-<output>-<sequence>
```

### 7. Persist Outputs with Custom Executor

CAWDP workflows persist outputs to files (specs/, data/) using custom executors:

```python
from pathlib import Path
from agno.run import RunContext
from agno.workflow.types import StepInput, StepOutput

def _persist_decisions(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Persist decisions from session_state to decisions.json.
    
    This executor is called at the END of the workflow, after all loops complete.
    It atomically writes all decisions accumulated in session_state during the
    writer/reviewer cycles.
    """
    decisions_data = (run_context.session_state or {}).get("decisions", [])
    
    if not decisions_data:
        return StepOutput(content="No decisions to persist.")

    try:
        # Load current file state
        register = DecisionRegister.load_from_file()
        
        # Merge session decisions (deduplication handled by DecisionRegister)
        for dec_dict in decisions_data:
            decision = Decision(**dec_dict)
            register.add_decision(decision)
        
        # Atomic write
        register.save_to_file()
        
        return StepOutput(
            content=f"Persisted {len(decisions_data)} decisions to decisions.json"
        )
    except Exception as e:
        return StepOutput(
            content=f"Error persisting decisions: {e}",
            success=False,
            error=str(e),
        )
```

Add to workflow:

```python
workflow = Workflow(
    steps=[
        write_review_loop,
        Step(name="Persist Decisions", executor=_persist_decisions),
    ],
    session_state={"decisions": []},
)
```

### 8. Handle Multi-Phase Workflows

For workflows with multiple phases (e.g., design + impl):

```python
workflow = Workflow(
    name="spec-production-workflow",
    steps=[
        Loop(
            name="Design Loop",
            steps=[write_design_step, review_design_step],
            end_condition=_review_passes,
            requires_iteration_review=True,
            on_reject=OnReject.retry,
            forward_iteration_output=True,
        ),
        Loop(
            name="Impl Loop",
            steps=[write_impl_step, review_impl_step],
            end_condition=_review_passes,
            requires_iteration_review=True,
            on_reject=OnReject.retry,
            forward_iteration_output=True,
        ),
        Step(name="Persist", executor=_persist_decisions),
    ],
    session_state={"decisions": []},
)
```

Each loop has independent iteration review, but they share session_state.

## Advanced Patterns

Common implementation patterns are in [references/patterns.md](references/patterns.md):

- Writer with structured output (Pydantic models)
- Reviewer with markdown tables
- Accessing previous iteration output
- Depth-adaptive workflows
- Decision register integration
- Multi-phase sequential workflows
- Conditional HITL based on review scores
- Cost optimization with reviewer models
- Handling LLM markdown wrappers
- Workflow-level error handling

## Troubleshooting

Common issues and fixes are in [references/troubleshooting.md](references/troubleshooting.md):

- Loop issues (never ends, always pauses for human, infinite retry)
- State sharing issues (session_state not shared, decisions not persisted)
- Feedback and iteration issues (writer doesn't see previous output/feedback)
- Output schema issues (Pydantic model vs string errors)
- Database and persistence issues
- HITL gate issues (no pending review visible, approve/reject don't work)
- Performance issues (slow execution, high token costs)
- Debugging techniques

## Cross-References

- **create-agno-workflow**: Low-level Agno workflow primitives
- **cawdp-phase-guide**: Which CAWDP phase to use when
- **cawdp-identity-first-design**: P0-P1 methodology (5 identity questions)
- **cawdp-output-specification**: P1 output schemas and dependencies
- **cawdp-task-decomposition**: P3-P4 decompose→type→allocate pattern
- **improve-agno-agent**: Fix agents that drift from spec
- **debug-agno-workflow**: Diagnose paused/stuck workflows

## Examples

See working CAWDP workflows in the codebase:

- `cawdp_pipeline/workflows/design_spec_workflow.py` — single-phase write→review
- `cawdp_pipeline/workflows/spec_production_workflow.py` — multi-phase (design + impl)
