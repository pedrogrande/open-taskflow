---
name: optimise-agno-workflow
description: 'Optimize Agno workflows for token cost, latency, and reliability — compress context, cache responses, parallelize steps, tune loops, reduce tool calls, and harden error handling. Use when a workflow is too expensive, too slow, hitting context limits, looping excessively, or needs production hardening. Covers token budgeting, CompressionManager, response caching, session caching, tool result caching, parallel steps, loop tuning, and agent-level optimization.'
argument-hint: 'Workflow name and optimisation goal, e.g. "design-spec-workflow — reduce token cost and loop iterations"'
user-invocable: true
---

# Optimise Agno Workflow

Reduce token cost, latency, and failure rates for Agno workflows. Applies a systematic optimisation loop: measure → diagnose → apply → verify. Works with the project's stack (SurrealDB persistence, SQLite workflow sessions, AgentOS runtime, Railway deployment).

## When to Use

- Workflow token costs are too high (especially in loops)
- Workflow latency is too slow (sequential steps that could run in parallel)
- Agent hitting context window limits during long tool-call chains
- Loop iterating too many times (end condition not converging)
- Tool calls returning verbose results that waste context
- Need production hardening (error handling, caching, session management)
- After adding new steps or agents to an existing workflow

## Optimisation Loop

```
Measure → Diagnose → Apply → Verify → (repeat)
```

Each pass targets ONE optimisation category. Don't try to optimise everything at once.

## Procedure

### 1. Measure Current Performance

Before changing anything, capture baseline metrics.

**Via API:**

```bash
# Non-streaming run with full output
curl -sS -X POST http://localhost:8006/v1/workflows/<workflow-id>/runs \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "message=<input>&stream=false" \
  -o /tmp/workflow-baseline.json

# Extract metrics
jq '.metrics' /tmp/workflow-baseline.json
```

**Via Python:**

```python
response = workflow.run("input")

# Workflow-level metrics
if response.metrics:
    print(f"Duration: {response.metrics.duration:.2f}s")
    for step_name, step_metrics in response.metrics.steps.items():
        if step_metrics.metrics:
            print(f"  {step_name}: {step_metrics.metrics.total_tokens} tokens, "
                  f"{step_metrics.metrics.duration:.2f}s")

# Session-level aggregate
session_metrics = workflow.get_session_metrics()
print(f"Total tokens across all runs: {session_metrics.total_tokens}")
```

**Record baseline in a table:**

| Metric | Before | Target | After |
|--------|--------|--------|-------|
| Total tokens | — | — | — |
| Duration (s) | — | — | — |
| Loop iterations | — | — | — |
| Tool calls per step | — | — | — |
| Context window usage | — | — | — |

### 2. Diagnose Bottlenecks

Map where tokens and time are spent.

**Token diagnosis — per step:**

```python
for step_name, sm in response.metrics.steps.items():
    if sm.metrics:
        print(f"{step_name}: {sm.metrics.total_tokens} tokens "
              f"({sm.metrics.input_tokens} in / {sm.metrics.output_tokens} out)")
```

**Common bottleneck patterns:**

| Pattern | Symptom | Root Cause |
|---------|---------|-----------|
| **Verbose tool results** | High input_tokens after tool calls | Tools return full documents instead of summaries |
| **Loop not converging** | 3/3 max_iterations used | End condition too strict or agent not improving |
| **Redundant reads** | Same file read 2-3 times per step | Agent instructions don't say "read once" |
| **Sequential bottleneck** | Long total duration, steps could run in parallel | Independent steps chained sequentially |
| **Context overflow** | Quality degrades in later loop iterations | Agent context window filling up |
| **Cold DB reads** | Slow first run, fast subsequent | No session caching enabled |

### 3. Apply Optimisations

Choose the right category based on diagnosis. Apply ONE category per pass.

---

#### Category A: Context Compression

**When:** Agent makes 3+ tool calls per step, or tool results are verbose.

**Enable automatic compression on agents:**

```python
design_writer = Agent(
    ...
    compress_tool_results=True,  # Compress after 3 tool calls (default)
)
```

**Custom compression with CompressionManager:**

```python
from agno.compression.manager import CompressionManager
from agno.models.openai import OpenAIResponses

compression = CompressionManager(
    model=OpenAIResponses(id="gpt-5.4-mini"),  # Cheaper model for compression
    compress_tool_results_limit=2,  # Compress after 2 tool calls
    compress_token_limit=8000,      # Or: compress when context exceeds 8K tokens
)

design_writer = Agent(
    ...
    compression_manager=compression,
)
```

**Token-based threshold** (better for variable-size tool results):

```python
compression = CompressionManager(
    model=OpenAIResponses(id="gpt-5.4-mini"),
    compress_token_limit=6000,  # Compress when context exceeds 6K tokens
)
```

**Impact:** 40-70% reduction in input tokens for multi-tool-call agents.

> ⚠️ **L-020 — Do NOT use count-based compression on spec-writing or spec-reviewing agents.** `compress_tool_results_limit=3` fires after only 3 tool calls — typically `get_entry` + `list_sections` + `read_section(first)`. By the time the writer reaches its first `write_section` call, the design content it needed (cognitive_mode, quality_criteria, actor allocation) is already summarised and partial. Remove `CompressionManager` from writer/reviewer agents unless you are actually hitting context limits. If compression is reintroduced, use `compress_token_limit` with a threshold ≥ 12 000 tokens, and add preservation instructions for critical fields.

---

#### Category B: Response Caching

**When:** Same inputs produce same outputs (development, testing, deterministic steps).

**Enable on the model:**

```python
from agno.models.openai import OpenAIResponses

design_writer = Agent(
    model=OpenAIResponses(
        id="gpt-5.4",
        cache_response=True,   # Cache full responses locally
        cache_ttl=3600,        # Expire after 1 hour
    ),
    ...
)
```

**⚠️ Do NOT use in production for dynamic content.** Only for dev/test where
inputs repeat.

**Impact:** 100% token savings on cache hits, near-instant response.

---

#### Category C: Tool Result Caching

**When:** Tools return the same data across calls (catalogue reads, file reads).

**Enable on toolkits:**

```python
from cawdp_pipeline.tools.decision_tools import DecisionToolkit

_decision_tools = DecisionToolkit(cache_results=True)
```

**Enable on individual @tool functions:**

```python
from agno.tools import tool

@tool(cache_results=True)
def read_catalogue_entry(output_id: str) -> str:
    ...
```

**Impact:** Eliminates redundant tool calls within a session.

---

#### Category D: Session Caching

**When:** Workflow makes multiple runs against the same session (HITL resume, loops).

**Enable on the workflow's agents:**

```python
design_writer = Agent(
    ...
    cache_session=True,  # Keep hydrated session in memory
)
```

**Impact:** Eliminates DB reads on subsequent runs within the same session.

---

#### Category E: Parallel Steps

**When:** Independent steps are chained sequentially.

**Identify parallelisable steps:**

| Can Parallelise | Must Be Sequential |
|----------------|-------------------|
| Reading catalogue + reading decisions | Read catalogue → produce spec |
| Reading multiple independent docs | Read spec → review spec |
| Research from multiple sources | Write → review (reviewer needs writer output) |

**Apply:**

```python
from agno.workflow import Parallel

# Before: sequential (slow)
# steps=[read_catalogue_step, read_decisions_step, write_step]

# After: parallel reads, then write
workflow = Workflow(
    steps=[
        Parallel(
            name="Parallel Reads",
            steps=[read_catalogue_step, read_decisions_step],
        ),
        write_step,  # Runs after both reads complete
    ],
    ...
)
```

**Impact:** Duration reduced by the longest parallel step (not the sum).

---

#### Category F: Loop Tuning

**When:** Loop hits max_iterations, or converges in 1 iteration (too easy).

**Diagnose loop behaviour:**

```python
# Check how many iterations the loop used
response = workflow.run("input")
# Loop metrics show iteration count
```

**Tune end_condition:**

```python
# BEFORE: Too strict — requires perfect PASS on every dimension
def review_passes(outputs: list[StepOutput]) -> bool:
    review_text = str(outputs[-1].content)
    return "FAIL" not in review_text  # Any FAIL → continue

# AFTER: Accept WARNING as passing (more realistic)
def review_passes(outputs: list[StepOutput]) -> bool:
    review_text = str(outputs[-1].content)
    # Extract Summary section only
    summary = re.search(r"##\s*1\.\s*Summary(.*?)(?=\n##\s|\Z)", review_text, re.DOTALL)
    if summary:
        section = summary.group(1)
        return "FAIL" not in section and "PASS" in section
    return False
```

**Reduce max_iterations when agent converges quickly:**

```python
# BEFORE: Safety net too high
Loop(steps=[...], end_condition=review_passes, max_iterations=5)

# AFTER: Tighter bound based on observed convergence
Loop(steps=[...], end_condition=review_passes, max_iterations=3)
```

**Add early exit for hopeless cases:**

```python
def review_passes(outputs: list[StepOutput]) -> bool:
    if not outputs:
        return False
    review_text = str(outputs[-1].content)
    # If the reviewer says "Unable to assess", don't loop
    if "Unable to assess" in review_text:
        return True  # Exit loop — can't improve what can't be assessed
    # Normal check
    summary = re.search(r"##\s*1\.\s*Summary(.*?)(?=\n##\s|\Z)", review_text, re.DOTALL)
    if summary:
        return "FAIL" not in summary.group(1)
    return False
```

**Impact:** 33-66% token savings by eliminating unnecessary loop iterations.

**Use conditional HITL to avoid unnecessary human pauses:**

Agno checks `end_condition` BEFORE `requires_iteration_review`. If the review passes, the loop ends without pausing for human review. This means humans only review when the automated review finds issues — saving human time on 150+ outputs.

```python
# ❌ ALWAYS pauses for human review (even on PASS)
Loop(
    steps=[write_step, review_step],
    end_condition=review_passes,
    max_iterations=3,
    human_review=HumanReview(requires_iteration_review=True),  # Always triggers
)

# ✅ Only pauses when review FAILS (conditional HITL)
Loop(
    steps=[write_step, review_step],
    end_condition=review_passes,  # Checked FIRST — if True, loop ends
    max_iterations=3,
    forward_iteration_output=True,  # Next iteration gets previous output (saves re-reading)
    human_review=HumanReview(
        requires_iteration_review=True,  # Only reached if end_condition is False
        on_reject=OnReject.retry,
    ),
)
```

> ⚠️ `requires_iteration_review` does NOT support callables — it's `bool` only. A callable is truthy, so iteration review will ALWAYS trigger. Use `end_condition` as the conditional gate.

---

#### Category G: Agent-Level Optimisation

**When:** Individual agents within workflow steps are inefficient.

**Reduce tool_call_limit:**

```python
# BEFORE: Agent makes 30+ tool calls (reading files multiple times)
design_writer = Agent(..., tool_call_limit=35)

# AFTER: Tighter limit forces efficiency
design_writer = Agent(..., tool_call_limit=20)
```

**Targeted doc reading in instructions:**

```python
# BEFORE: "Read the CAWDP docs" → agent reads entire 2000-line doc
# AFTER: "Read ONLY the section for the output's phase (e.g., 'Phase 0').
#        One targeted read is sufficient. Do NOT read the entire document."
```

**Use cheaper model for reviewer:**

```python
# Writer needs strong model for generation
design_writer = Agent(model=OpenAIResponses(id="gpt-5.4"), ...)

# Reviewer measures against criteria — cheaper model sufficient
design_reviewer = Agent(model=Ollama(id="glm-5.1:cloud"), ...)
```

**Enable add_history_to_context selectively:**

```python
# Only include history when the agent needs conversation context
design_writer = Agent(
    ...
    add_history_to_context=True,
    num_history_runs=3,  # Limit to 3 previous runs, not unlimited
)
```

**Impact:** 20-50% token reduction per agent step.

---

#### Category H: Error Handling Hardening

**When:** Workflow fails silently or crashes on edge cases.

**Add on_error to risky steps:**

```python
from agno.workflow import OnError

Step(
    name="Write Spec",
    agent=design_writer,
    on_error=OnError.pause,  # Pause for human decision instead of crashing
)
```

**Add retry with backoff in executors:**

```python
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = some_agent.run(step_input.input)
            return StepOutput(content=response.content)
        except Exception as e:
            if attempt == max_retries - 1:
                return StepOutput(
                    content=f"Error after {max_retries} attempts: {e}",
                    success=False,
                )
    return StepOutput(content="Unexpected error", success=False)
```

**Impact:** Prevents workflow crashes, enables recovery without restart.

### 4. Verify Improvements

After each optimisation pass, re-run with the same input and compare:

```bash
# After fix
curl -sS -X POST http://localhost:8006/v1/workflows/<id>/runs \
  -d "message=<same-input>&stream=false" -o /tmp/workflow-optimised.json

# Compare metrics
jq '.metrics' /tmp/workflow-baseline.json > /tmp/before-metrics.json
jq '.metrics' /tmp/workflow-optimised.json > /tmp/after-metrics.json
diff /tmp/before-metrics.json /tmp/after-metrics.json
```

**Fill in the baseline table from Step 1.** If the target isn't met, run another
diagnose → apply → verify pass.

### 5. Document Optimisations

Record what was changed and why in the Decision Register:

```python
from cawdp_pipeline.tools.decision_tools import DecisionToolkit

toolkit = DecisionToolkit()
toolkit.record_decision(
    source_output="design-spec-workflow",
    phase="P10",
    decision="Enabled compress_tool_results=True on design_writer with "
             "CompressionManager (gpt-5.4-mini, limit=2). Reduces input "
             "tokens by ~55% in loop iterations.",
    propagates_to=["design-writer", "design-reviewer"],
    tags=["optimisation", "compression", "token-reduction"],
)
```

## Optimisation Priority Matrix

| Priority | Category | Typical Savings | Risk |
|----------|----------|----------------|------|
| 🔴 1st | F: Loop tuning | 33-66% tokens | Low — just changes thresholds |
| 🔴 2nd | A: Context compression | 40-70% input tokens | Low — Agno handles automatically |
| 🟡 3rd | G: Agent-level | 20-50% per step | Medium — may affect output quality |
| 🟡 4th | E: Parallel steps | Duration reduction | Medium — requires step independence |
| 🟢 5th | C: Tool caching | Eliminates redundant calls | Low — cache invalidation rare |
| 🟢 6th | D: Session caching | Faster DB reads | Low — memory overhead minimal |
| ⚪ Dev only | B: Response caching | 100% on cache hits | High — stale results in prod |
| ⚪ As needed | H: Error handling | Reliability | Low — adds resilience |

## Key Patterns for This Project

### Database

- **Agent sessions**: `db.get_surrealdb()` — SurrealDB
- **Workflow sessions**: `cawdp_pipeline.db.get_pipeline_db()` — SQLite
- **Session caching**: Add `cache_session=True` to agents in workflow steps

### Models

- **Writer**: `OpenAIResponses(id="gpt-5.4")` — strong model for generation
- **Reviewer**: `Ollama(id="glm-5.1:cloud")` — cheaper model for measurement
- **Compression model**: Use `OpenAIResponses(id="gpt-5.4-mini")` or similar cheap model

### Loop End Condition

The `end_condition` function receives outputs from the **current iteration only**.
Return `True` to STOP the loop. Check the Summary section, not the full review.

### Telemetry — `WorkflowRunOutput.metrics` (L-021)

`wf.run()` returns a `WorkflowRunOutput` with a `metrics` attribute. No Step refactoring needed to capture per-agent token usage.

```python
result = wf.run(message)

# Total workflow duration
result.metrics.duration  # float, seconds

# Per-step metrics — keyed by step name (e.g. 'design_writer', 'design_reviewer')
step = result.metrics.steps['design_writer']
step.metrics.input_tokens    # int
step.metrics.output_tokens   # int
step.metrics.total_tokens    # int
step.metrics.duration        # float, seconds

# Separate main-model from compression-model calls
step.metrics.details['model'][0].input_tokens   # main model only
step.metrics.details.get('compression_model')   # present if CompressionManager used
```

Extract telemetry from `result.metrics.steps` after `wf.run()`. Do NOT convert `Step(agent=agent)` to executor functions just to intercept `RunResponse`.

### Container Restart Scope

- `agents/<slug>.py` — hot-reloads within ~1s
- `cawdp_pipeline/workflows/*.py` — **requires** `docker compose restart agentos-api`
- Optimisation changes to agent constructors (compression, caching) — **requires restart**

### API Content-Type

`POST /v1/workflows/{id}/runs` expects `application/x-www-form-urlencoded`, NOT JSON.

## Anti-Patterns

| Anti-Pattern | Why It's Wrong | Fix |
|--------------|---------------|-----|
| Enable response caching in production | Returns stale results for dynamic content | Only use `cache_response=True` in dev/test |
| Compress too aggressively (limit=1) | Loses critical detail from first tool call | Start with limit=2-3, measure, then tune |
| Parallelise dependent steps | Race conditions, missing data | Only parallelise truly independent steps |
| Reduce max_iterations to 1 | No chance for quality improvement | Minimum 2 iterations for write-review loops |
| Use passthrough executor for HITL in Loop | Infinite retry loop with `on_reject=OnReject.retry` | Use `requires_iteration_review=True` on Loop |
| Set `requires_iteration_review` to a callable | Callable is truthy → iteration review always triggers | Use `True`/`False` only; use `end_condition` as conditional gate |
| Skip measurement before optimising | Can't verify improvement | Always capture baseline first |
| Optimise all categories at once | Can't isolate which change helped | One category per pass |

## Related Resources

- [Agno context compression](https://docs.agno.com/compression/overview) — CompressionManager, token limits
- [Agno response caching](https://docs.agno.com/models/cache-response) — cache_response, cache_ttl
- [Agno tool caching](https://docs.agno.com/tools/caching) — cache_results on toolkits and @tool
- [Agno session caching](https://docs.agno.com/sessions/session-management) — cache_session
- [Agno parallel steps](https://docs.agno.com/workflows/usage/parallel-steps-workflow) — Parallel step type
- [Agno workflow metrics](https://docs.agno.com/sessions/metrics/workflow) — token and duration metrics
- [Agno loop patterns](https://docs.agno.com/workflows/usage/loop-steps-workflow) — end_condition, max_iterations
- Project: `cawdp_pipeline/workflows/design_spec_workflow.py` — existing workflow
- Project: `debug-agno-workflow` skill — diagnose workflow issues
- Project: `create-agno-workflow` skill — build workflows from scratch
- Project: `improve-agno-agent` skill — harden agent behavior
