# CAWDP Workflow Patterns

Common patterns for implementing CAWDP workflows with Agno primitives.

## Pattern: Writer with Structured Output

When a writer agent needs to produce typed, structured data:

```python
from pydantic import BaseModel, Field
from agno.agent import Agent

class SpecOutput(BaseModel):
    """Output schema for the phase."""
    section_1: str = Field(..., description="First section content")
    section_2: str = Field(..., description="Second section content")
    # ... more fields

writer = Agent(
    id="spec-writer",
    output_schema=SpecOutput,  # Agent returns SpecOutput instance, not string
    # ... other config
)

# In executors that consume this agent's output:
response = writer.run(message)
if isinstance(response.content, SpecOutput):
    typed_output = response.content  # Already parsed
elif isinstance(response.content, dict):
    typed_output = SpecOutput.model_validate(response.content)
else:  # string
    typed_output = SpecOutput.model_validate_json(strip_markdown_json(response.content))
```

**Key points:**
- `output_schema` produces Pydantic instances, not JSON strings
- Executors must handle three content types: model instance, dict, string
- LLMs often wrap JSON in markdown fences — strip before parsing

## Pattern: Reviewer with Markdown Table

CAWDP reviewers produce markdown reports with Summary tables:

```python
REVIEWER_INSTRUCTIONS = """
Produce a review report with this structure:

## 1. Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| Fidelity | PASS/FAIL/WARNING | Brief note |
| Enrichment | PASS/FAIL/WARNING | Brief note |
| Cross-Cutting | PASS/FAIL/WARNING | Brief note |

## 2. Detailed Findings

For each dimension, provide:
- What was checked
- What was found
- What needs improvement (if FAIL/WARNING)

## 3. Recommendations

Prioritized list of changes needed for the next iteration.
"""

reviewer = Agent(
    id="spec-reviewer",
    instructions=REVIEWER_INSTRUCTIONS,
    # NO output_schema — produce free-form markdown
)
```

**Key points:**
- Reviewers do NOT use `output_schema` (markdown is more flexible)
- Summary table format is parsed by `end_condition` functions
- Status values: PASS, FAIL, WARNING (uppercase)

## Pattern: Accessing Previous Iteration Output

When using `forward_iteration_output=True`, the writer receives previous output:

```python
WRITER_INSTRUCTIONS = """
You are revising a previous draft.

**Previous iteration output:**
{{previous_step_content}}

**Reviewer feedback (if rejected):**
{{rejection_feedback}}

Instructions:
1. Review the previous output and feedback
2. Identify specific issues mentioned in the feedback
3. Improve the output to address those issues
4. Maintain what was working well
"""

Loop(
    steps=[write_step, review_step],
    forward_iteration_output=True,  # Enables {{previous_step_content}}
    on_reject=OnReject.retry,  # Enables {{rejection_feedback}}
)
```

**Key points:**
- `{{previous_step_content}}` is auto-injected when `forward_iteration_output=True`
- `{{rejection_feedback}}` is auto-injected when human rejects via `OnReject.retry`
- Both are string replacements in the agent's input message

## Pattern: Depth-Adaptive Workflows

CAWDP specs come in three depths (Shallow, Medium, Deep):

| Depth | Purpose | Instructions | Max Iterations |
|-------|---------|--------------|----------------|
| Shallow | Quick deterministic outputs | Short, specific criteria | 2 |
| Medium | Pre-filled with human confirmation | Moderate detail | 3 |
| Deep | Full specifications with 5 identity questions | Comprehensive criteria | 5 |

```python
def create_workflow(output_id: str, depth: str):
    """Create a workflow with depth-adaptive configuration."""
    
    # Load depth-specific instructions
    if depth == "shallow":
        writer_instructions = SHALLOW_WRITER_INSTRUCTIONS
        reviewer_instructions = SHALLOW_REVIEWER_INSTRUCTIONS
        max_iterations = 2
        quality_threshold = "moderate"
    elif depth == "medium":
        writer_instructions = MEDIUM_WRITER_INSTRUCTIONS
        reviewer_instructions = MEDIUM_REVIEWER_INSTRUCTIONS
        max_iterations = 3
        quality_threshold = "good"
    else:  # deep
        writer_instructions = DEEP_WRITER_INSTRUCTIONS
        reviewer_instructions = DEEP_REVIEWER_INSTRUCTIONS
        max_iterations = 5
        quality_threshold = "excellent"

    writer = Agent(
        instructions=writer_instructions.format(
            output_id=output_id,
            quality_threshold=quality_threshold,
        ),
        # ... other config
    )
    
    reviewer = Agent(
        instructions=reviewer_instructions.format(
            quality_threshold=quality_threshold,
        ),
        # ... other config
    )
    
    return Workflow(
        steps=[
            Loop(
                steps=[
                    Step(agent=writer),
                    Step(agent=reviewer),
                ],
                max_iterations=max_iterations,
                end_condition=_review_passes,
                requires_iteration_review=(depth != "shallow"),  # Skip HITL for shallow
            )
        ]
    )
```

**Key points:**
- Depth affects instructions, max_iterations, and HITL behavior
- Shallow specs skip HITL entirely (deterministic, low stakes)
- Medium and Deep specs use conditional HITL
- Quality threshold is injected into instructions for context

## Pattern: Decision Register Integration

CAWDP workflows share decision state via `session_state`:

```python
from cawdp_pipeline.tools.decision_tools import DecisionToolkit

# Writer agent has decision tools
writer = Agent(
    tools=[DecisionToolkit()],  # Provides record_decision, list_decisions
    instructions="""
    When making design choices, record them using record_decision:
    - decision_id: D-<phase>-<output>-<sequence> (e.g., "D-P3-O5-001")
    - phase: CAWDP phase (e.g., "P3-Task-Decomposition")
    - question: What was decided
    - answer: The decision
    - rationale: Why this decision (specific, not generic)
    - output_refs: Which outputs this affects
    """,
)

# Reviewer agent checks decision completeness
reviewer = Agent(
    instructions="""
    Check decision register:
    - Every significant design choice has a decision record
    - Decision IDs follow format D-<phase>-<output>-<sequence>
    - Rationales are specific and traceable
    - No generic "best practice" rationales
    """,
)

# Persist executor saves to file
def _persist_decisions(step_input: StepInput, run_context: RunContext) -> StepOutput:
    decisions_data = (run_context.session_state or {}).get("decisions", [])
    
    if not decisions_data:
        return StepOutput(content="No decisions to persist.")

    register = DecisionRegister.load_from_file()
    
    for dec_dict in decisions_data:
        decision = Decision(**dec_dict)
        register.add_decision(decision)
    
    register.save_to_file()
    
    return StepOutput(content=f"Persisted {len(decisions_data)} decisions")

# Workflow wires it together
workflow = Workflow(
    steps=[
        Loop(steps=[write_step, review_step], ...),
        Step(name="Persist Decisions", executor=_persist_decisions),
    ],
    session_state={"decisions": []},  # Shared across all steps
)
```

**Key points:**
- `session_state` is shared across ALL steps in the workflow
- Writer adds decisions during execution
- Reviewer validates decision completeness
- Persist executor atomically saves at workflow end
- Decisions grow over time (never deleted)

## Pattern: Multi-Phase Sequential Workflows

When multiple phases need to run in sequence (e.g., design → impl):

```python
workflow = Workflow(
    name="multi-phase-workflow",
    steps=[
        # Phase 1: Design
        Loop(
            name="Design Loop",
            steps=[
                Step(name="Write Design", agent=design_writer),
                Step(name="Review Design", agent=design_reviewer),
            ],
            end_condition=_review_passes,
            requires_iteration_review=True,
            on_reject=OnReject.retry,
            forward_iteration_output=True,
        ),
        
        # Phase 2: Implementation
        Loop(
            name="Impl Loop",
            steps=[
                Step(name="Write Impl", agent=impl_writer),
                Step(name="Review Impl", agent=impl_reviewer),
            ],
            end_condition=_review_passes,
            requires_iteration_review=True,
            on_reject=OnReject.retry,
            forward_iteration_output=True,
        ),
        
        # Phase 3: Persist
        Step(name="Persist All", executor=_persist_decisions),
    ],
    session_state={"decisions": []},  # Shared across both loops
)
```

**Key points:**
- Each Loop has independent iteration review
- session_state is shared across all loops
- Impl writer can access design decisions from session_state
- Persist step runs once at the end (atomic write)
- Each loop can have different max_iterations and end_condition

## Pattern: Conditional HITL Based on Review Score

Standard CAWDP pattern uses binary pass/fail. For nuanced scoring:

```python
def _review_score_high(outputs: List[StepOutput]) -> bool:
    """End condition: stop loop when review score ≥ 8/10."""
    if not outputs:
        return False
    
    review_text = str(outputs[-1].content)
    
    # Parse score from review (assumes reviewer includes "Overall Score: X/10")
    match = re.search(r"Overall Score:\s*(\d+)/10", review_text)
    if match:
        score = int(match.group(1))
        return score >= 8
    
    return False  # No score found, continue loop

Loop(
    steps=[write_step, review_step],
    end_condition=_review_score_high,  # Score ≥ 8 → auto-proceed
    requires_iteration_review=True,  # Score < 8 → human reviews
    max_iterations=5,
)
```

**Key points:**
- end_condition can parse any review format (not just PASS/FAIL tables)
- Reviewer must include parseable score/status in consistent format
- Score thresholds can vary by depth (shallow: 6/10, deep: 9/10)

## Pattern: Cost Optimization with Reviewer Models

CAWDP reviewers often use cheaper models than writers:

```python
from agno.models.ollama import Ollama
from app.settings import default_model

# Writer uses premium model (generation is expensive)
writer = Agent(
    model=default_model(),  # OpenAI GPT-4.5
    # ... writer config
)

# Reviewer uses cheaper model (evaluation is cheaper than generation)
reviewer = Agent(
    model=Ollama(id="glm-5.1:cloud", host="https://ollama.com"),
    # ... reviewer config
)
```

**Key points:**
- Writers need creativity/generation → premium models
- Reviewers need pattern matching/evaluation → cheaper models work well
- Ollama offers cloud-hosted models with competitive quality
- Test reviewer quality before deployment (bad reviews → more human overhead)

## Pattern: Handling LLM Markdown Wrappers

LLMs often wrap JSON in markdown code fences:

```python
def strip_markdown_json(text: str) -> str:
    """Remove markdown code fences from JSON strings."""
    # Remove ```json ... ``` wrappers
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()

# Use in executors that parse agent output:
def my_executor(step_input: StepInput) -> StepOutput:
    raw = step_input.previous_step_content
    
    # Handle Pydantic models
    if hasattr(raw, "model_dump_json"):
        raw = raw.model_dump_json()
    elif isinstance(raw, dict):
        raw = json.dumps(raw)
    
    # Strip markdown before parsing
    clean = strip_markdown_json(raw)
    data = json.loads(clean)
    
    # ... process data
```

**Key points:**
- ALWAYS strip markdown before JSON parsing
- Check for Pydantic models first (they have `model_dump_json()`)
- Check for dicts second (convert to JSON string)
- Only then strip + parse

## Pattern: Workflow-Level Error Handling

Custom executors can catch and report errors gracefully:

```python
def safe_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    """Executor with comprehensive error handling."""
    try:
        # Main logic here
        result = do_work(step_input)
        
        return StepOutput(
            content=result,
            success=True,
        )
    
    except ValidationError as e:
        # Pydantic validation failed
        return StepOutput(
            content=f"Validation error: {e}",
            success=False,
            error=str(e),
        )
    
    except FileNotFoundError as e:
        # File operation failed
        return StepOutput(
            content=f"File not found: {e}",
            success=False,
            error=str(e),
        )
    
    except Exception as e:
        # Unexpected error
        return StepOutput(
            content=f"Unexpected error: {type(e).__name__}: {e}",
            success=False,
            error=str(e),
        )
```

**Key points:**
- Always return `StepOutput`, even on error
- Set `success=False` and populate `error` field
- Provide user-friendly `content` messages
- Catch specific exceptions before generic `Exception`
- Workflow continues (doesn't crash) on executor errors
