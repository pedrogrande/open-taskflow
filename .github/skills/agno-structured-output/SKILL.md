---
name: agno-structured-output
description: 'Configure structured input and output for Agno agents and teams — output_schema, output_model, parser_model, input_schema, use_json_mode, per-run overrides, streaming, and workflow integration. Use when an agent must return typed Pydantic objects, when a weak model needs a parser model, when you need cost-optimized output pipelines, or when workflow executors consume structured output from previous steps.'
argument-hint: 'Agent or team name and desired output shape, e.g. "design-reviewer — return ReviewReport Pydantic model"'
user-invocable: true
---

# Agno Structured Input & Output

Configure typed, validated input and output for Agno agents and teams. Covers the full output pipeline (primary model → output_model → parser_model), structured input validation, per-run overrides, streaming, and the critical gotchas when structured output flows into workflows.

## When to Use

- Agent must return typed data (not free-form text) for downstream code
- Team must synthesize member outputs into a validated object
- Weak model can't produce valid structured output — needs a parser_model
- You want a cheaper model for formatting (cost optimization)
- Workflow executor consumes `previous_step_content` from a step with `output_schema`
- API endpoint needs validated input before the agent runs
- You need different schemas for different calls to the same agent

## Decision Flow

```
Need typed output?
├── Model supports structured output natively?
│   ├── Yes → output_schema only (default behavior)
│   └── No → output_schema + use_json_mode=True
├── Need better prose/formatting?
│   └── Add output_model (secondary model for final response)
├── Primary model is weak at structured output?
│   └── Add parser_model (secondary model to parse/fix response)
└── Need different schemas per call?
    └── Pass output_schema at run time (per-run override)

Need typed input?
├── Input comes from code (you control the call site)?
│   └── Pass Pydantic model instance directly to agent.run(input=model)
└── Input comes from external source (API, config file)?
    └── Set input_schema on agent (auto-validates dicts)
```

## Procedure

### 1. Define the Pydantic Model

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class ReviewReport(BaseModel):
    """Design spec review report."""
    summary: str = Field(description="One-sentence overall assessment")
    dimensions: list[DimensionResult] = Field(description="One per review dimension")
    overall_status: Literal["PASS", "FAIL", "WARNING"]
    issues: list[Issue] = Field(default_factory=list, description="Ordered by impact")
    strengths: list[str] = Field(default_factory=list)

class DimensionResult(BaseModel):
    name: str
    status: Literal["PASS", "FAIL", "WARNING"]
    notes: str = ""

class Issue(BaseModel):
    impact: Literal["HIGH", "MEDIUM", "LOW"]
    section: str
    description: str
    suggested_fix: str = ""
```

**Schema design rules:**
- Every field gets a `description` — the model reads these to know what to generate
- Use `Literal` for constrained strings (status enums, categories)
- Use `Field(ge=, le=)` for numeric ranges — Pydantic validates after generation
- Use `Optional` / `| None` for fields the model might not have data for
- Use `default_factory=list` for list fields — avoids mutable default issues
- Nest models for complex structures (don't flatten everything into one model)

### 2. Set output_schema on Agent

```python
from agno.agent import Agent
from app.settings import default_model

review_agent = Agent(
    id="design-reviewer",
    name="Design Spec Reviewer",
    model=default_model(),
    output_schema=ReviewReport,
    instructions=REVIEWER_INSTRUCTIONS,
    db=get_surrealdb(),
)
```

**What happens:** Agno converts the Pydantic model to JSON Schema, passes it to the model's structured output API, validates the response, and returns a `ReviewReport` instance in `response.content`.

### 3. Consume the Output

```python
response = review_agent.run("Review spec D-P00-001")

# response.content is a ReviewReport instance, NOT a string
report: ReviewReport = response.content
print(report.overall_status)  # "PASS" or "FAIL"
for issue in report.issues:
    print(f"[{issue.impact}] {issue.section}: {issue.description}")
```

**Critical gotcha:** When `output_schema` is set, `response.content` is a **Pydantic model instance**, not a string. This affects:
- Workflow executors that receive it as `previous_step_content`
- Any code that does string operations on `response.content`
- Serialization for API responses

### 4. Configure the Output Pipeline

The output pipeline has three stages. Choose based on your model and quality needs:

```
Primary model → (optional) output_model → (optional) parser_model
     ↑                ↑                        ↑
  Does the           Refines prose/           Parses/fixes
  reasoning          formatting               structured output
  and tool calls     from primary             when primary can't
```

| Configuration | Use Case | Example |
|--------------|----------|---------|
| `output_schema` only | Model supports structured output natively | OpenAI, Anthropic, Google |
| `output_schema` + `use_json_mode=True` | Model doesn't support structured output | Ollama local models, older providers |
| `output_schema` + `output_model` | Need better prose from a different model | GPT-5.4 reasons → Claude formats |
| `output_schema` + `parser_model` | Primary model is weak at structured output | Ollama generates → GPT-4o parses |
| `output_schema` + `output_model` + `parser_model` | Full pipeline: weak model + formatting + parsing | DeepSeek reasons → GPT-4o parses → Claude formats |

**output_model — secondary model for final response:**

```python
from agno.models.anthropic import Claude

agent = Agent(
    model=default_model(),                    # Research + tool calls
    output_model=Claude(id="claude-sonnet-4-5"),  # Better prose
    output_model_prompt="Write as a concise executive summary. No fluff.",
    output_schema=ReviewReport,
    tools=[HackerNewsTools()],
)
```

**parser_model — secondary model to parse/fix response:**

```python
from agno.models.ollama import Ollama
from agno.models.openai import OpenAIChat

agent = Agent(
    model=Ollama(id="glm-5.1:cloud"),         # Primary: local model
    output_schema=ReviewReport,
    parser_model=OpenAIChat(id="gpt-4o"),     # Parser: fix/extract structured output
    parser_model_prompt="Extract review data into the schema. Fix any formatting issues.",
)
```

**Cost optimization pattern:**

```python
agent = Agent(
    model=OpenAIResponses(id="gpt-5.4"),       # Expensive: complex reasoning
    output_model=OpenAIResponses(id="gpt-5-mini"),  # Cheap: just formatting
    output_model_prompt="Summarize in 3 bullet points.",
    output_schema=AnalysisResult,
)
```

### 5. Per-Run Schema Overrides

Override `output_schema` at run time for agents that handle multiple tasks:

```python
# Agent without a fixed schema
multi_agent = Agent(model=default_model())

# Different schemas for different calls
sentiment = multi_agent.run("Analyze sentiment", output_schema=SentimentResult)
entities = multi_agent.run("Extract entities", output_schema=EntityList)
summary = multi_agent.run("Summarize", output_schema=SummaryResult)
```

This is useful when one agent handles multiple output formats depending on the request.

### 6. Configure Structured Input

**Option A: Pass Pydantic model instance directly** (when you control the call site):

```python
class ResearchRequest(BaseModel):
    topic: str
    max_sources: int = Field(ge=1, le=20, default=5)
    focus_areas: list[str] = Field(default_factory=list)

request = ResearchRequest(
    topic="AI Agents",
    max_sources=10,
    focus_areas=["multi-agent systems", "tool use"],
)

response = agent.run(input=request)  # Validated at model creation
```

**Option B: Set input_schema for auto-validation** (when input comes from external sources):

```python
agent = Agent(
    model=default_model(),
    input_schema=ResearchRequest,
)

# Dict is auto-validated against ResearchRequest
response = agent.run(input={
    "topic": "AI Agents",
    "max_sources": 10,
    "focus_areas": ["multi-agent systems"],
})
```

Invalid input raises `pydantic.ValidationError` before the agent runs.

### 7. Structured Output with Teams

Set `output_schema` on the team to constrain the final synthesized response:

```python
from agno.team import Team

class CombinedReport(BaseModel):
    summary: str
    market_sentiment: str
    stock_outlook: str
    final_recommendation: str

team = Team(
    name="Research Team",
    model=default_model(),
    members=[news_agent, finance_agent],
    output_schema=CombinedReport,
)

response = team.run("Full analysis of NVDA")
report: CombinedReport = response.content
```

**Per-member + per-team schemas:** Members can have their own `output_schema` for consistent intermediate outputs. The team schema controls the final synthesized response.

```python
news_agent = Agent(
    name="News Analyst",
    output_schema=NewsInsights,    # Member schema
)

finance_agent = Agent(
    name="Finance Analyst",
    output_schema=FinanceInsights, # Member schema
)

team = Team(
    members=[news_agent, finance_agent],
    output_schema=CombinedReport,  # Team schema (synthesizes member outputs)
)
```

### 8. Streaming with Structured Output

Structured output works with streaming, but the object is only available after the stream completes:

```python
# Streaming — object available after completion
for chunk in agent.run_stream("Analyze NVDA", output_schema=StockAnalysis):
    print(chunk, end="")  # Raw text chunks during stream

# After stream completes, response.content has the typed object
# (not available incrementally during streaming)
```

### 9. Workflow Integration

**The #1 gotcha:** When a step's agent has `output_schema`, `previous_step_content` in the next step's executor is a **Pydantic model instance**, not a string. Always normalize:

```python
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    raw = step_input.previous_step_content

    # Normalize to string for string operations
    if hasattr(raw, "model_dump_json"):
        # Agent with output_schema returned a Pydantic model
        raw = raw.model_dump_json()
    elif isinstance(raw, dict):
        raw = json.dumps(raw)
    elif raw is None:
        raw = ""

    # Now safe for string operations
    if "PASS" in raw:
        ...
```

**Or normalize to the expected model:**

```python
def my_executor(step_input: StepInput, run_context: RunContext) -> StepOutput:
    raw = step_input.previous_step_content

    if isinstance(raw, ReviewReport):
        report = raw  # Already the right type
    elif isinstance(raw, dict):
        report = ReviewReport.model_validate(raw)
    elif isinstance(raw, str):
        report = ReviewReport.model_validate_json(raw)
    else:
        report = ReviewReport()  # Fallback

    # Use typed report
    if report.overall_status == "PASS":
        return StepOutput(content="Review passed", stop=True)
```

**Loop end conditions with structured output:**

```python
def review_passes(outputs: list[StepOutput]) -> bool:
    """Return True to STOP the loop."""
    if not outputs:
        return False

    review_output = outputs[-1].content
    if not review_output:
        return False

    # If agent has output_schema, content is a Pydantic model
    if isinstance(review_output, ReviewReport):
        return review_output.overall_status == "PASS"

    # If agent has no output_schema, content is a string
    review_text = str(review_output)
    return "PASS" in review_text and "FAIL" not in review_text
```

### 10. JSON Mode Fallback

For models that don't support structured output natively:

```python
agent = Agent(
    model=Ollama(id="glm-5.1:cloud"),
    output_schema=ReviewReport,
    use_json_mode=True,  # Injects schema into system prompt instead
)
```

**When to use JSON mode:**
- Model doesn't support structured output (most local/Ollama models)
- Model doesn't support tools with structured outputs
- You need broader compatibility but are okay with manual validation

**Key difference:** JSON mode injects the schema description into the system prompt. The model *tries* to follow it, but the API doesn't enforce it. You may get malformed JSON. Structured output (default) enforces the schema at the API level.

## Common Patterns for This Project

### Model Selection

| Agent Type | Model | Structured Output? | Notes |
|-----------|-------|--------------------|-------|
| Reasoning-heavy | `OpenAIResponses(id="gpt-5.4")` | ✅ Native | Default for most agents |
| Local / cost-optimized | `Ollama(id="glm-5.1:cloud")` | ❌ Use JSON mode | Add `use_json_mode=True` |
| Review / measurement | `Ollama(id="glm-5.1:cloud")` | ❌ Use JSON mode | Or add `parser_model` |

### Output Schema Checklist

Before adding `output_schema` to an agent, verify:

- [ ] Every field has a `description` (guides the model)
- [ ] Constrained strings use `Literal` (not free-form `str`)
- [ ] Optional fields use `| None` or `Optional`
- [ ] List fields use `default_factory=list`
- [ ] Nested models for complex structures (not flat dicts)
- [ ] Downstream consumers handle Pydantic model (not string)
- [ ] Workflow executors normalize `previous_step_content` type
- [ ] Loop end conditions handle both Pydantic model and string

### API Serialization

When returning structured output from API endpoints:

```python
from fastapi.responses import JSONResponse

response = agent.run("Analyze", output_schema=AnalysisResult)

# Pydantic model → dict for JSON response
if isinstance(response.content, BaseModel):
    return JSONResponse(content=response.content.model_dump())
else:
    return JSONResponse(content={"result": str(response.content)})
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `response.content` is a string, not a model | Model doesn't support structured output | Add `use_json_mode=True` or switch model |
| `ValidationError` on response | Model returned invalid data | Add `parser_model` to fix/extract, or simplify schema |
| Missing fields in output | Model skipped optional fields | Add `description` to guide the model, or make required |
| Wrong enum values | Model ignored `Literal` constraint | Use `description` to list valid values explicitly |
| `previous_step_content` crashes executor | String operation on Pydantic model | Add type normalization (see Section 9) |
| Loop end condition never triggers | Checking string on Pydantic model | `str(model)` may not contain expected text; check typed fields |
| JSON mode returns malformed JSON | Model can't follow schema reliably | Add `parser_model` to fix output |
| Streaming doesn't return typed object | Object only available after stream completes | Access `response.content` after stream ends |
| `output_model` changes the content | Secondary model rewrites the response | Set `output_model_prompt` to control formatting |

## Related Resources

- [Agno structured output for agents](https://docs.agno.com/input-output/structured-output/agent) — basic usage, per-run overrides
- [Agno structured output for teams](https://docs.agno.com/input-output/structured-output/team) — team-level schemas, per-member schemas
- [Agno output model](https://docs.agno.com/input-output/output-model) — output_model, parser_model, cost optimization
- [Agno structured input for agents](https://docs.agno.com/input-output/structured-input/agent) — input_schema, Pydantic input
- [Agno structured input for teams](https://docs.agno.com/input-output/structured-input/team) — team-level input validation
- [Agno structured outputs FAQ](https://docs.agno.com/faq/structured-outputs) — structured output vs JSON mode
- Project: `create-agno-agent` skill — agent constructor quick reference (includes output_schema params)
- Project: `create-agno-workflow` skill — StepInput/StepOutput, previous_step_content type handling
- Project: `debug-agno-workflow` skill — diagnosing type mismatch in workflow data flow