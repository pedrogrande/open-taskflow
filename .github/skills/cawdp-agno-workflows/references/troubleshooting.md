# CAWDP Workflow Troubleshooting

Common issues when implementing CAWDP workflows with Agno and how to fix them.

## Loop Issues

### Loop Never Ends

**Symptom:** Write→review loop continues indefinitely, never reaches next phase.

**Causes:**
1. end_condition always returns False
2. Review format doesn't match parsing logic
3. Reviewer never produces PASS status

**Diagnosis:**
```python
def _review_passes(outputs: List[StepOutput]) -> bool:
    """Add logging to diagnose."""
    if not outputs:
        print("DEBUG: No outputs")
        return False
    
    review_text = str(outputs[-1].content)
    print(f"DEBUG: Review text length: {len(review_text)}")
    
    # Try to extract summary
    summary_section = extract_summary(review_text)
    print(f"DEBUG: Summary found: {summary_section is not None}")
    
    if summary_section:
        rows = re.findall(r"\|\s*[^|]+\s*\|\s*(PASS|FAIL|WARNING)\s*\|", summary_section)
        print(f"DEBUG: Parsed rows: {rows}")
        return "FAIL" not in rows
    
    return False
```

**Fixes:**
- Check reviewer instructions — ensure Summary table format is specified
- Verify regex patterns match actual review output
- Test end_condition with sample review text before deploying
- Set `max_iterations` as safety fallback

### Human Always Reviews (HITL Every Time)

**Symptom:** Workflow pauses for human review on every iteration, even when review passes.

**Causes:**
1. end_condition returns True too early (false positives)
2. Review parsing is too lenient
3. Reviewer instructions are unclear about what PASS means

**Fixes:**
- Tighten end_condition logic — check for explicit "PASS" in all dimensions
- Review reviewer instructions — clarify what constitutes a passing spec
- Test with known-good and known-bad specs to calibrate threshold
- Check Summary table format — ensure no typos in "PASS"

### OnReject.retry Loops Infinitely

**Symptom:** Human rejects, loop re-runs, human rejects again, repeat forever.

**Causes:**
1. max_iterations not set (or set too high)
2. Writer doesn't improve output based on feedback
3. Rejection feedback not being injected correctly

**Fixes:**
- Set `max_iterations=5` (or less) as safety limit
- Check writer instructions — ensure {{rejection_feedback}} is used
- Verify `on_reject=OnReject.retry` is set on Loop
- Test feedback injection with explicit rejection message

## State Sharing Issues

### session_state Not Shared Between Steps

**Symptom:** Writer records decisions, but reviewer doesn't see them. Or decisions aren't persisted to file.

**Causes:**
1. Different Workflow instances created for each run
2. session_state not initialized in Workflow constructor
3. DecisionToolkit not added to writer's tools

**Fixes:**
- Use singleton Workflow instance (define once, reuse for all runs)
- Initialize session_state in Workflow constructor: `session_state={"decisions": []}`
- Add DecisionToolkit to writer: `tools=[DecisionToolkit()]`
- Check that persist executor accesses `run_context.session_state`, not `step_input`

### Decisions Not Persisted to File

**Symptom:** Decisions recorded during workflow, but decisions.json doesn't update.

**Causes:**
1. Persist step missing from workflow
2. Persist executor not accessing run_context.session_state
3. File write failing silently

**Fixes:**
- Add persist step at END of workflow (after all loops)
- Use `run_context.session_state` in executor, not `step_input.previous_step_content`
- Wrap file operations in try/except, return `StepOutput(success=False, error=...)` on failure
- Check file permissions on decisions.json

## Feedback and Iteration Issues

### Writer Doesn't See Previous Output

**Symptom:** Writer produces identical output on each iteration, ignoring reviewer feedback.

**Causes:**
1. `forward_iteration_output=False` (or not set)
2. Writer instructions don't reference {{previous_step_content}}
3. Agent model doesn't follow instructions to revise

**Fixes:**
- Set `forward_iteration_output=True` on Loop
- Add to writer instructions: "Previous iteration output: {{previous_step_content}}"
- Add explicit revision instructions: "Identify issues from feedback and improve"
- Test with known bad output → feedback → check if revision addresses issues

### Rejection Feedback Not Reaching Writer

**Symptom:** Human rejects with feedback, but next iteration ignores it.

**Causes:**
1. `on_reject=OnReject.retry` not set
2. Writer instructions don't reference {{rejection_feedback}}
3. Feedback field empty in rejection

**Fixes:**
- Set `on_reject=OnReject.retry` on Loop
- Add to writer instructions: "Reviewer feedback: {{rejection_feedback}}"
- Ensure human provides feedback text when rejecting (not just clicking Reject)
- Check scripts/hitl reject command includes feedback parameter

## Output Schema Issues

### "Expected string or bytes-like object" Error

**Symptom:** Executor crashes with regex error when processing agent output.

**Causes:**
1. Agent has `output_schema` set → returns Pydantic model, not string
2. Executor tries to run regex/JSON parse on model instance

**Fixes:**
```python
# In executors, always normalize first:
def normalize_content(raw):
    """Convert any content type to string."""
    if hasattr(raw, "model_dump_json"):
        return raw.model_dump_json()
    elif isinstance(raw, dict):
        return json.dumps(raw)
    else:
        return str(raw)

def my_executor(step_input: StepInput) -> StepOutput:
    raw = step_input.previous_step_content
    normalized = normalize_content(raw)
    clean = strip_markdown_json(normalized)
    data = json.loads(clean)
    # ... process
```

### Reviewer Can't Parse Writer Output

**Symptom:** Reviewer says "output format is invalid" or gives low scores despite correct content.

**Causes:**
1. Writer output_schema produces JSON, reviewer expects markdown
2. LLM wrapped JSON in code fences
3. Output schema fields don't match reviewer expectations

**Fixes:**
- If reviewer needs markdown, writer should NOT have output_schema
- If reviewer needs JSON, add parsing instructions to reviewer
- Strip markdown fences before reviewer sees output (use custom executor between steps)
- Align writer schema fields with reviewer evaluation criteria

## Database and Persistence Issues

### "Table does not exist" Error

**Symptom:** Workflow fails on first run with SurrealDB table error.

**Causes:**
1. Table name mismatch between agent db and workflow db
2. SurrealDB not initialized
3. Namespace/database not created

**Fixes:**
- Check `db=get_pipeline_db(table_name="...")` matches across workflow
- Run `docker compose up -d` to ensure SurrealDB is running
- Verify SURREALDB_URL, SURREALDB_NAMESPACE, SURREALDB_DATABASE in .env
- Agno auto-creates tables on first access (if namespace/database exist)

### SQLite "Database is locked" Error

**Symptom:** Pipeline workflows fail with "database is locked" when running concurrently.

**Causes:**
1. SQLite doesn't handle concurrent writes well
2. Multiple workflow runs accessing same sessions.db

**Fixes:**
- Use SurrealDB for concurrent workflows (not SQLite)
- If using SQLite, run workflows sequentially (not in parallel)
- Or switch to per-workflow database files: `get_pipeline_db(table_name=f"workflow_{workflow_id}")`

## HITL Gate Issues

### Workflow Pauses But No Pending Review Visible

**Symptom:** Workflow status is PAUSED, but AgentOS UI shows no pending review.

**Causes:**
1. step_requirements not populated correctly
2. UI filtering by wrong session_id
3. Workflow run record not persisted to database

**Diagnosis:**
```bash
# Check paused runs directly in database
python scripts/hitl list

# Show specific run details
python scripts/hitl show <run_id> <session_id>
```

**Fixes:**
- Ensure `requires_iteration_review=True` is set on Loop (not callable)
- Check that workflow is registered in app/main.py
- Verify SURREALDB_URL is correct and SurrealDB is running
- Try resuming via API: `POST /workflows/{id}/runs/{run_id}/resume`

### Approve/Reject Buttons Don't Work

**Symptom:** Clicking Approve or Reject in AgentOS UI has no effect.

**Causes:**
1. Frontend not calling correct API endpoint
2. Session ID mismatch
3. Workflow run not in PAUSED state

**Fixes:**
- Use scripts/hitl CLI as alternative: `python scripts/hitl approve <run_id> <session_id>`
- Check browser console for API errors
- Verify run status with scripts/hitl show
- Try cancel + restart if run is stuck

## Performance Issues

### Workflow Runs Very Slowly

**Symptom:** Each iteration takes 30+ seconds, workflow feels unresponsive.

**Causes:**
1. Model is slow (premium models have higher latency)
2. Agent has too many tools (increases prompt size)
3. Knowledge base queries are slow
4. agentic_memory enabled (more DB lookups)

**Fixes:**
- Use faster models for reviewers (Ollama, gpt-4o-mini)
- Limit tools to what's actually needed for the phase
- Cache knowledge base results if queries are repeated
- Disable agentic_memory for deterministic workflows: `enable_agentic_memory=False`
- Use `markdown=False` if agent doesn't need markdown formatting

### High Token Costs

**Symptom:** Workflow consumes thousands of tokens per run.

**Causes:**
1. Instructions too verbose (explain concepts model already knows)
2. Output schema has unnecessary fields
3. Reviewer sees full input history (not just latest output)
4. Multiple iterations due to low-quality initial output

**Fixes:**
- Trim instructions — assume model knows Python, Pydantic, markdown
- Remove output schema fields that aren't used downstream
- Use `num_history_runs=0` for agents that don't need history
- Improve writer quality to reduce iteration count (better instructions, examples)
- Use cheaper models for reviewers

## Debugging Workflow Execution

### Enable Step-by-Step Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("agno.workflow")

# Run workflow with debug logging
result = workflow.run("Test message", stream=False)
```

### Inspect Workflow State After Pause

```python
# Get run details via API
response = requests.get(
    f"http://localhost:8006/workflows/{workflow.id}/runs/{run_id}",
    params={"session_id": session_id}
)
data = response.json()

# Check step_requirements
for req in data["step_requirements"]:
    print(f"Requirement: {req['name']}")
    print(f"  Confirmed: {req.get('confirmed')}")
    print(f"  Output: {req.get('step_output', {}).get('content', '')[:200]}")
```

### Test end_condition Independently

```python
# Extract review output from a real run
review_text = """
## 1. Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| Fidelity | PASS | All fields present |
| Enrichment | FAIL | Missing rationale |
| Cross-Cutting | PASS | Verified independence |
"""

# Test parsing
from agno.workflow.types import StepOutput

outputs = [StepOutput(content=review_text)]
result = _review_passes(outputs)
print(f"end_condition returned: {result}")  # Should be False (FAIL present)
```

## When All Else Fails

1. **Simplify:** Remove HITL, run as pure Loop without requires_iteration_review
2. **Isolate:** Test writer and reviewer agents independently (outside workflow)
3. **Log:** Add print statements to end_condition and custom executors
4. **Restart:** Stop workflow, restart Docker containers, try again
5. **Rebuild:** Delete .venv, `./scripts/venv_setup.sh`, reinstall dependencies
6. **Ask:** Check Agno docs (https://docs.agno.com), GitHub issues, or Discord
