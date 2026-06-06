---
name: backcasting-analysis
description: 'Run CAWDP Phase 2 backcasting dependency analysis using the backcasting engine tool. Use when tracing dependency chains from outputs to inputs, detecting gaps (missing inputs, circular dependencies, orphan outputs, critical path gaps, quality gate gaps), reviewing resolution plans, assessing confidence and staleness risk, or validating that a pipeline has no structural gaps before implementation.'
argument-hint: 'Output specs or phase to analyse, e.g. "P0 outputs" or JSON output list'
user-invocable: true
---

# Backcasting Analysis

Run CAWDP Phase 2 backcasting dependency analysis on a set of Phase 1 outputs. The backcasting engine traces dependency chains backward from outputs to external inputs, detects five types of structural gaps, and produces actionable reports with resolution plans.

Companion skills:
- [cawdp-identity-first-design](../cawdp-identity-first-design/SKILL.md) — P0: who the agent is
- [cawdp-output-specification](../cawdp-output-specification/SKILL.md) — P1+: producing and reviewing specs
- [cawdp-task-decomposition](../cawdp-task-decomposition/SKILL.md) — P3–P4: decompose and allocate

## When to Use

- Tracing what a set of outputs depends on (dependency chain analysis)
- Detecting missing inputs — outputs that need something nobody produces
- Detecting circular dependencies — outputs that depend on each other
- Detecting orphan outputs — things produced that nobody needs
- Detecting critical path gaps — CRITICAL dependencies with no satisfaction path
- Detecting quality gate gaps — gates that reference things the pipeline doesn't produce
- Reviewing resolution plans for detected gaps
- Assessing confidence (CC-3) and staleness risk (CC-5) for input requirements
- Validating a pipeline is structurally sound before implementation begins
- Running the full backcasting workflow (parse → trace → detect → report)

## Two Modes of Use

### Mode 1: Agent Tool (Quick Analysis)

Use the `run_backcasting` tool directly for single-turn analysis. Best when you already have structured output specs or a small set of outputs to check.

```python
from cawdp_pipeline.tools.backcasting_engine.tool import create_backcasting_tool

backcasting_tool = create_backcasting_tool()
# Add to agent's tools list
```

### Mode 2: Agno Workflow (Full Pipeline)

Use the `backcasting_workflow` for multi-step analysis with natural language input. Best when the user describes outputs in prose and needs a full report.

```python
from cawdp_pipeline.tools.backcasting_engine import backcasting_workflow

result = backcasting_workflow.run(
    "Trace dependencies for: Market Analysis (O-001) needs Market Data and Customer Survey..."
)
```

## Step 1: Prepare Output Specifications

Before running backcasting, you need output specifications. These come from Phase 1 (Output Specification skill) or can be described directly.

### From Existing Specs

If the user has already produced specs (e.g. `specs/design/P00/D-P00-001.md`), extract the output specifications from them. You can use the scaffold script for this:

```bash
python .agents/skills/backcasting-analysis/scripts/scaffold_outputs.py specs/design/P00/D-P00-001.md --output outputs.json
```

Or manually structure each output:

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique identifier (e.g. "O-001") |
| `name` | Yes | Human-readable name |
| `description` | No | What this output contains |
| `is_final_deliverable` | No | Whether this is a final deliverable |
| `is_quality_gate` | No | Whether this is a quality gate |
| `quality_gate_references` | No | IDs this gate must verify (CAWDP P2) |
| `dependencies` | No | List of dependency dicts |

Each dependency dict:

| Field | Required | Description |
|-------|----------|-------------|
| `target_id` | Yes | What this output depends on |
| `type` | No | `"external"` or `"internal"` (default: external) |
| `criticality` | No | `"CRITICAL"`, `"HIGH"`, `"MEDIUM"`, `"LOW"` |
| `description` | No | What specifically is needed |

### From Natural Language

If the user describes outputs in prose, use the workflow mode or manually structure them into the dict format above.

### Quality Gate References (CAWDP P2)

When an output is a quality gate, list the IDs it must verify in `quality_gate_references`. The engine will check that every referenced ID exists in the pipeline. This catches gates that verify things nobody produces.

## Step 2: Run the Backcasting Engine

### Using the Tool

```python
# In an agent's tool call:
result = run_backcasting(
    outputs=[
        {
            "id": "O-001",
            "name": "Market Analysis Report",
            "is_final_deliverable": True,
            "dependencies": [
                {"target_id": "Market Data", "type": "external", "criticality": "CRITICAL"},
                {"target_id": "O-002", "type": "internal"},
            ],
        },
        {
            "id": "O-002",
            "name": "Customer Survey Results",
            "dependencies": [
                {"target_id": "Survey Responses", "type": "external"},
            ],
        },
    ],
    detect_gaps_flag=True,
    save_artefact=True,
)
```

### Using the Workflow

```python
from cawdp_pipeline.tools.backcasting_engine import backcasting_workflow

result = backcasting_workflow.run(
    "Analyse these outputs: Market Analysis (O-001, final deliverable) "
    "depends on Market Data (external) and Customer Survey (O-002, internal). "
    "Customer Survey depends on Survey Responses (external)."
)
```

The workflow runs four steps:
1. **parse_outputs** — Extracts structured specs from natural language
2. **run_backcasting** — Traces dependency chains
3. **detect_gaps** — Detects all five gap types
4. **generate_report** — Produces formatted report

## Step 3: Interpret the Results

### Dependency Chain

The engine produces a `DependencyChain` with:

| Property | Meaning |
|----------|---------|
| `output_count` | Number of outputs traced |
| `requirement_count` | Total input requirements discovered |
| `external_inputs` | Requirements that must come from outside the pipeline |
| `internal_inputs` | Requirements produced by other outputs in the pipeline |
| `adjacency` | Map of output → what it depends on |
| `reverse_adjacency` | Map of target → what depends on it |

### Input Requirements (CAWDP P2 Fields)

Each `InputRequirement` includes:

| Field | CAWDP Ref | Meaning |
|-------|-----------|---------|
| `ir_type` | — | External or Internal |
| `ir_criticality` | — | CRITICAL / HIGH / MEDIUM / LOW |
| `ir_satisfaction_mode` | — | DIRECT / DERIVED / PARTIAL |
| `ir_confidence` | CC-3 | 0.0–1.0 confidence in the assessment |
| `ir_staleness_risk` | CC-5 | "high" / "medium" / "low" / None for time-sensitive inputs |
| `ir_source_phase` | — | Which phase produces this (if internal) |
| `ir_derived_from_dependency` | — | Which dependency created this requirement |

#### Confidence Heuristics (CC-3)

The engine infers initial confidence values. These are starting estimates — refine them based on domain knowledge:

| Situation | Confidence | Reason |
|-----------|-----------|--------|
| Missing internal dependency | 0.1 | Very low — the dependency doesn't exist |
| CRITICAL external dependency | 0.7 | High stakes, uncertain supply |
| Described external dependency | 0.6 | Better understood |
| Undescribed external dependency | 0.4 | Vague, risky |
| Internal dependency (existing output) | 0.8 | Under pipeline control |

#### Staleness Risk Heuristics (CC-5)

| Situation | Risk | Reason |
|-----------|------|--------|
| Name contains "price", "market", "forecast", "trend", etc. | "high" | Time-sensitive data |
| Output is a quality gate | "medium" | Gates verify current state |
| Other | None | Not time-sensitive |

## Step 4: Review Gap Report

The engine detects five gap types. Each gap gets an auto-generated resolution plan per CAWDP P2: "every gap has a resolution plan or explicit acceptance."

### Gap Types

| Gap Type | Icon | What It Means | Action |
|----------|------|---------------|--------|
| Missing input | 🚫 | Output depends on something nobody produces | Add a producing output or reclassify as external |
| Circular dependency | 🔄 | Two outputs depend on each other | Break the cycle with an intermediate or rephase |
| Orphan output | 👻 | Output produced but nothing depends on it | Verify downstream need or remove |
| Critical path gap | ⚠️ | CRITICAL dependency leads to a missing input | Resolve the missing input — pipeline can't deliver |
| Quality gate gap | 🏗️ | Gate references something not in the pipeline | Add the referenced output or remove the reference |

### Resolution Plans

Each gap gets a template resolution plan. These are starting points — refine them with domain knowledge:

- **Missing input**: "Add an output spec that produces '{target}', or change the dependency to EXTERNAL"
- **Circular dependency**: "Break the cycle by introducing an intermediate output or rephasing"
- **Orphan output**: "Verify downstream consumer or remove from pipeline"
- **Critical path gap**: "Resolve the missing critical input — add producing output or reclassify as external"
- **Quality gate gap**: "Add the missing artefact to the pipeline or remove the gate reference"

### Accepting Gaps

Not every gap needs to be fixed. Per CAWDP P2, you can explicitly accept a gap by documenting why:

```
Gap: orphan_output:O-003
Acceptance: O-003 is a reference document consumed by a downstream
process not yet modelled in this pipeline. Will be linked when that
process is added.
```

## Step 5: Act on the Results

### If No Gaps

The pipeline is structurally sound. All dependencies trace to external inputs. Proceed to implementation planning.

### If Gaps Found

1. **Review each gap** and its resolution plan
2. **Refine confidence** values based on domain knowledge (override engine heuristics)
3. **Assess staleness risk** for time-sensitive inputs the engine may have missed
4. **Choose**: Resolve the gap OR explicitly accept it with documented rationale
5. **Re-run** backcasting after changes to verify the fix

### Common Resolution Patterns

| Gap | Resolution |
|-----|-----------|
| Missing internal dependency | Add the producing output to the pipeline |
| Missing internal dependency (external) | Reclassify as EXTERNAL with DIRECT satisfaction |
| Circular dependency | Introduce intermediate output that breaks the cycle |
| Orphan output | Add a downstream consumer or remove the output |
| Critical path gap | Fix the underlying missing input first |
| Quality gate gap (via dependency) | Add the referenced output to the pipeline |
| Quality gate gap (via reference) | Add the referenced output or remove from `quality_gate_references` |

## Step 6: Persist and Review Artefacts

Backcasting results are saved as JSON artefacts in `cawdp_pipeline/tools/backcasting_engine/outputs/`.

### Listing Artefacts

```python
from cawdp_pipeline.tools.backcasting_engine.tool import create_list_artefacts_tool

list_tool = create_list_artefacts_tool()
result = list_tool.entrypoint(limit=10)
```

### Artefact Structure

Each artefact contains:
- `type`: "backcasting_report"
- `summary`: output count, requirement count, gap count
- `outputs`: all OutputSpec objects
- `requirements`: all InputRequirement objects (with confidence and staleness risk)
- `gaps`: full GapReport with resolution plans
- `adjacency` / `reverse_adjacency`: dependency graph maps

## Quality Gate Checklist

Before accepting a backcasting analysis as complete:

- [ ] All outputs have been traced (no untraced dependencies)
- [ ] Every gap has a resolution plan OR explicit acceptance with rationale
- [ ] Confidence values have been reviewed and refined where needed
- [ ] Staleness risk has been assessed for time-sensitive inputs
- [ ] Quality gate references have been validated (all referenced IDs exist)
- [ ] Critical path gaps have been resolved (pipeline can deliver)
- [ ] Orphan outputs have been justified or removed
- [ ] Circular dependencies have been broken or explicitly accepted

## Module Reference

| Module | Purpose |
|--------|---------|
| `cawdp_pipeline.tools.backcasting_engine.engine` | Core algorithm: `trace_dependencies()` |
| `cawdp_pipeline.tools.backcasting_engine.gap_detector` | Gap detection: `detect_gaps()` |
| `cawdp_pipeline.tools.backcasting_engine.criticality` | Criticality inference: `infer_criticality()`, `propagate_criticality()` |
| `cawdp_pipeline.tools.backcasting_engine.visualizer` | Rendering: `render_report()`, `render_artefact()`, `render_mermaid_graph()` |
| `cawdp_pipeline.tools.backcasting_engine.tool` | Agno tools: `create_backcasting_tool()`, `create_list_artefacts_tool()` |
| `cawdp_pipeline.tools.backcasting_engine.workflow` | Agno Workflow: `backcasting_workflow` (4-step pipeline) |
| `cawdp_pipeline.tools.backcasting_engine.models` | Pydantic models: `OutputSpec`, `InputRequirement`, `DependencyChain`, `GapReport` |

## Reference Files

- [p2-backcasting-spec.md](./references/p2-backcasting-spec.md) — Full CAWDP P2 specification: InputRequirement fields, OutputSpec fields, gap taxonomy, quality gate layers, resolution plan format, DependencyChain properties

## Scripts

- [scaffold_outputs.py](./scripts/scaffold_outputs.py) — Extract output specifications from a CAWDP design spec markdown file. Usage: `python scripts/scaffold_outputs.py <spec.md> [--output outputs.json]`