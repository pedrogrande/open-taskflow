# CAWDP Phase 2 Backcasting Specification Reference

Full specification for the backcasting engine's data models, quality gates, and gap taxonomy. Load this reference when you need the exact field definitions, quality gate checklists, or gap type details.

## InputRequirement Fields

Every `InputRequirement` discovered during backcasting has these fields:

| Field | CAWDP Ref | Type | Required | Default | Description |
|-------|-----------|------|----------|---------|-------------|
| `id` | ir-id | str (UUID) | Auto | uuid4() | Unique identifier |
| `ir_type` | ir-type | DependencyType | Yes | — | `external` or `internal` |
| `ir_criticality` | ir-criticality | Criticality | No | MEDIUM | CRITICAL / HIGH / MEDIUM / LOW |
| `ir_satisfaction_mode` | ir-satisfaction-mode | SatisfactionMode | Yes | — | DIRECT / DERIVED / PARTIAL |
| `ir_source_phase` | ir-source-phase | str | No | None | Which phase produces this (if internal) |
| `ir_derived_from_dependency` | ir-derived-from-dependency | str | No | None | Which dependency created this requirement |
| `ir_confidence` | CC-3 | float | No | 0.5 | 0.0–1.0 confidence in assessment |
| `ir_staleness_risk` | CC-5 | str | No | None | "high" / "medium" / "low" for time-sensitive inputs |
| `name` | — | str | Yes | — | Human-readable name |
| `description` | — | str | No | None | What specifically is needed |

### Criticality Levels

| Level | Meaning | When Assigned |
|-------|---------|---------------|
| CRITICAL | Pipeline cannot complete without this | Final deliverable depends on it |
| HIGH | Pipeline can complete but quality suffers | Quality gate depends on it |
| MEDIUM | Useful but not blocking | Supporting input |
| LOW | Nice to have | Optional dependency |

### Satisfaction Modes

| Mode | Meaning | When Assigned |
|------|---------|---------------|
| DIRECT | Must be provided from outside | External dependency |
| DERIVED | Produced by an earlier phase | Internal dependency on non-gate output |
| PARTIAL | Produced earlier, refined later | Internal dependency on quality gate |

### Confidence Heuristics (CC-3)

| Situation | Confidence | Reasoning |
|-----------|-----------|----------|
| Missing internal dependency | 0.1 | Very low — dependency doesn't exist in pipeline |
| CRITICAL external dependency | 0.7 | High stakes, uncertain external supply |
| Described external dependency | 0.6 | Better understood, but still external |
| Undescribed external dependency | 0.4 | Vague, risky |
| Internal dependency (existing output) | 0.8 | Under pipeline control, high certainty |

### Staleness Risk Heuristics (CC-5)

| Situation | Risk | Reasoning |
|-----------|------|----------|
| Name contains time-sensitive keywords* | "high" | Data becomes stale quickly |
| Output is a quality gate | "medium" | Gates verify current state |
| Other | None | Not time-sensitive |

\* Keywords: price, pricing, cost, rate, market, stock, exchange, forecast, trend, current, latest, real-time, live, news, weather, season, quarter, month, week, daily

## OutputSpec Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `id` | str | Yes | — | Unique identifier (e.g. "O-001") |
| `name` | str | Yes | — | Human-readable name |
| `description` | str | No | None | What this output contains |
| `is_final_deliverable` | bool | No | False | Whether this is a final deliverable |
| `is_quality_gate` | bool | No | False | Whether this is a quality gate |
| `quality_gate_references` | list[str] | No | [] | IDs this gate must verify (P2) |
| `dependencies` | list[DependencyRef] | No | [] | What this output needs to exist |

## DependencyRef Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `target_id` | str | Yes | — | ID of the dependency target |
| `type` | DependencyType | Yes | — | `external` or `internal` |
| `criticality` | Criticality | No | MEDIUM | How critical this dependency is |
| `description` | str | No | None | What specifically is needed |

## Gap Types

### 1. Missing Input (`missing_input`)

**Detection**: An output has an INTERNAL dependency whose `target_id` doesn't match any output in the pipeline.

**What it reveals**: Something needs to exist that nobody produces. The engine creates a fallback external requirement, but the structural gap remains.

**Resolution patterns**:
- Add an output spec that produces the missing target
- Reclassify the dependency as EXTERNAL with DIRECT satisfaction mode
- If the dependency was declared internal by mistake, correct the type

### 2. Circular Dependency (`circular_dependency`)

**Detection**: DFS cycle detection finds a path where an output transitively depends on itself.

**What it reveals**: Phase ordering problem — two outputs depend on each other and can't be produced sequentially.

**Resolution patterns**:
- Introduce an intermediate output that breaks the cycle
- Rephase one dependency as external (it comes from outside the pipeline)
- Split one output into two phases (initial version + refined version)

### 3. Orphan Output (`orphan_output`)

**Detection**: An output has no internal dependents (nothing in the pipeline depends on it). Quality gates and final deliverables are excluded.

**What it reveals**: Something is produced that nobody needs. Either it's genuinely unnecessary, or a downstream consumer hasn't been modelled yet.

**Resolution patterns**:
- Add a downstream consumer that depends on this output
- Remove the output from the pipeline
- Explicitly accept: document that a future process will consume it

### 4. Critical Path Gap (`critical_path_gap`)

**Detection**: A CRITICAL dependency (directly or transitively) leads to a missing input.

**What it reveals**: The pipeline cannot produce its final deliverable because something critical doesn't exist downstream. This is the most severe gap type.

**Resolution patterns**:
- Resolve the underlying missing input first
- If the critical dependency can be satisfied externally, reclassify as EXTERNAL
- If the critical path is wrong, reconsider the criticality assignment

### 5. Quality Gate Gap (`quality_gate_gap`)

**Detection**: A quality gate output has dependencies or `quality_gate_references` that point to IDs not in the pipeline.

**What it reveals**: A quality gate is supposed to verify something the pipeline doesn't produce. The gate can't do its job.

**Two sources**:
- **via dependency**: The gate's `dependencies` list references a missing target
- **via quality_gate_reference**: The gate's `quality_gate_references` list names an ID not in the pipeline

**Resolution patterns**:
- Add the referenced output to the pipeline
- Remove the reference from the gate's `quality_gate_references`
- If the gate was checking something from outside the pipeline, document it as an external check

## Quality Gate Layers

The CAWDP quality gate has three layers. Backcasting primarily validates Layer 1 (Fidelity) and Layer 3 (Cross-cutting):

### Layer 1 — Fidelity

- [ ] Every output traces to at least one external input (no dangling dependencies)
- [ ] Every internal dependency has a producing output in the pipeline
- [ ] No circular dependencies exist (or are explicitly accepted)
- [ ] Every quality gate reference resolves to an existing output
- [ ] Critical path gaps are resolved (pipeline can deliver)

### Layer 2 — Enrichment

- [ ] Confidence values (CC-3) have been reviewed and refined
- [ ] Staleness risk (CC-5) has been assessed for time-sensitive inputs
- [ ] Resolution plans exist for every detected gap
- [ ] Explicitly accepted gaps have documented rationale

### Layer 3 — Cross-cutting

- [ ] CC-1: Backcasting is performed independently from spec production
- [ ] CC-2: Every "no gap" result is reviewed — absence of gaps may indicate incomplete modelling
- [ ] CC-3: Confidence values reflect genuine assessment, not default heuristics
- [ ] CC-5: Time-sensitive inputs are flagged with staleness risk
- [ ] CC-9: Backcasting doesn't prematurely constrain the solution space

## Resolution Plan Format

Per CAWDP P2, every gap must have a resolution plan or explicit acceptance:

```
Gap: {gap_type}:{target_id}
Plan: {how to resolve}
Status: [pending | in-progress | resolved | accepted]
Rationale: [why this resolution, or why accepted]
```

### Auto-Generated Templates

The engine generates template plans for each gap type. These are starting points — refine with domain knowledge:

| Gap Type | Template |
|----------|----------|
| missing_input | "Add an output spec that produces '{target}', or change the dependency on '{output}' to EXTERNAL" |
| circular_dependency | "Break the cycle by introducing an intermediate output or rephasing one dependency as external" |
| orphan_output | "Verify that '{output}' is needed by a downstream consumer not yet modelled, or remove it" |
| critical_path_gap | "Resolve the missing critical input '{target}' — add producing output or reclassify as external" |
| quality_gate_gap | "Add the missing artefact '{target}' to the pipeline so gate '{gate}' can verify it" |

## DependencyChain Properties

| Property | Type | Description |
|----------|------|-------------|
| `outputs` | list[OutputSpec] | All Phase 1 outputs |
| `requirements` | list[InputRequirement] | All discovered input requirements |
| `adjacency` | dict[str, list[str]] | output_id → dependency target_ids |
| `reverse_adjacency` | dict[str, list[str]] | target_id → output_ids that depend on it |
| `traced_at` | str (ISO) | When the trace was performed |
| `output_count` | int | Number of outputs |
| `requirement_count` | int | Number of requirements |
| `external_inputs` | list[InputRequirement] | External requirements only |
| `internal_inputs` | list[InputRequirement] | Internal requirements only |