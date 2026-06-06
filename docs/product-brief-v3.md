# Product Brief

## Workflow Contract & Specification Artefact System

***

## Document Control

| Field | Value |
|---|---|
| **Brief ID** | PB-WCS-003 |
| **Version** | 3.0 |
| **Date** | 6 June 2026 |
| **Status** | `Ready for Planning` |
| **Supersedes** | PB-WCS-001 (1 June 2026), PB-WCS-002 (2 June 2026) |
| **Prepared By** | Zero Team |
| **Intended Recipient** | Product Manager Agent |
| **Classification** | Internal |

***

## Purpose of This Brief

This brief defines the scope, objectives, constraints, and success conditions for the implementation of the Workflow Contract and Specification Artefact System — the foundational data and workflow layer of the Zero Team AI training, consulting, and governance platform. It is the authorising document for planning to begin. It is not a specification — it frames *what* must be built and *why*, so the PM agent can produce the implementation plan, milestone structure, and task decomposition.

This document consolidates the original product brief (PB-WCS-001) and its update (PB-WCS-002) into a single authoritative brief. It is written as a greenfield specification — no implementation is assumed to exist.

***

## Background & Strategic Context

Zero Team is building a platform that enables organisations to design, govern, and improve agentic workflows. The intellectual core of the platform is the CAWDP methodology — a structured process for producing a complete design specification of any workflow.

Earlier platform design attempted to build all three layers simultaneously: the methodology, the production system, and the agent platform. This caused recursive complexity — 687 dependency links, 150 subworkflows, and an 11-phase architecture that could not be simplified without losing integrity.

The resolution identified is to build in the correct sequence:

1. **The workflow contract first** — the foundational record that anchors all downstream design
2. **The specification artefacts second** — the Output Specification, Backcasting Output, and Input Specification that populate the contract in two stages
3. **The agent layer third** — built on top of a completed, stable contract, not alongside it

This brief covers steps 1 and 2. It is the entry point for the minimum viable prototype.

***

## What Has Been Designed

The following artefacts have been designed in full and are available as templates. The PM agent should treat these as the specification of what must be implemented — they are inputs to planning, not outputs of it.

| Artefact | Template | Role in the System | Stage |
|---|---|---|---|
| **Workflow Contract (v2)** | `workflow-contract-template-v2.md` | The master record for one workflow being designed. Populated in two stages, gated by two formal approvals. | Spans Stage 1 and Stage 2 |
| **Output Specification** | `output-spec-template-v2.md` | Standalone artefact defining what the workflow must produce. Anchors the Stage 1 approval gate. | Stage 1 |
| **Backcasting Output** | `backcasting-template.md` | Standalone artefact produced between Stage 1 and Stage 2. Works backwards from outputs to surface required inputs, intermediate states, decisions, and gaps. | Between Stage 1 and Stage 2 |
| **Input Specification** | `input-spec-template-v2.md` | Standalone artefact defining what the workflow requires as inputs. Derived from backcasting. Anchors the Stage 2 approval gate. | Stage 2 |

All four documents carry their own lifecycle status, version, ID, and approval records. They are linked — not merged.

A canonical glossary (`glossary.md`) defines all terms used across these artefacts and should be treated as the authoritative vocabulary for the system.

***

## The Two-Stage Gate Logic

This is the most important structural decision in the system. The PM agent must understand it before planning begins.

**Stage 1** covers everything knowable before the workflow has been backcast: identity, current state, triggers, purpose, stakeholders, time, risk, and the output specification. Stage 1 ends with a formal approval that explicitly authorises backcasting to begin — and explicitly does *not* approve the input specification, which cannot be known yet.

**Between stages**, the Backcasting Output is produced. It works backwards from approved outputs to identify: what intermediate states must exist, what decisions must be made, what inputs are required, and what gaps currently prevent the workflow from running.

**Stage 2** uses the accepted Backcasting Output to populate the Input Specification and complete the contract. Stage 2 ends with a second formal approval that authorises decomposition to begin.

This sequencing is not bureaucratic overhead — it is the mechanism that prevents input specifications from being guessed forward from current practice rather than derived backward from required outputs.

### How the Three Artefacts Connect

| Artefact | Created | Depends On | Authorises |
|---|---|---|---|
| **Output Specification** | Stage 1 | Workflow Contract identity, purpose, and stakeholder sections | Backcasting to begin |
| **Backcasting Output** | Between Stage 1 and Stage 2 | Approved Output Specification | Input Specification to be drafted |
| **Input Specification** | Stage 2 | Accepted Backcasting Output | Stage 2 contract approval and decomposition |

- The **Output Spec** is deliberately forward-facing — it asks *what must exist*, not *how it gets produced*
- The **Input Spec** is deliberately backward-facing — it asks *what must already exist or be provided*, traced from outputs via backcasting, not assumed from current practice
- The **Input Detail block** includes a `Derived From` field linking each input back to the specific backcasting chain that surfaced it — making the reasoning traceable and the spec defensible
- Both specs carry their own approval gate and lifecycle status, so they can be versioned independently if backcasting or stakeholder review causes revisions without invalidating the entire contract

***

## Core Functional Requirements

### 1. Artefact Records

Each of the four artefact types must exist as a distinct record in the system with:

- A unique ID (auto-generated)
- A version number
- A lifecycle status with defined valid transitions
- A link to its parent Workflow Contract
- Cross-references to related artefacts (e.g. Input Spec references its parent Backcasting Output ID)
- A created-by, created-date, approved-by, and approved-date
- All template fields as structured data — not a free-text blob

Fields are **progressively populated** — not all required at creation. The system must track which fields are populated, which are empty, and which are flagged for review.

### 2. Approval Gates

The system must enforce the two-stage gate logic:

- **Stage 1 gate:** Can only be reached when all Stage 1 sections of the contract and the Output Specification are complete and submitted. Approval at this gate changes contract status to `Stage 1 Approved` and unlocks the Backcasting Output record for creation.
- **Stage 2 gate:** Can only be reached when the Backcasting Output status is `Accepted` and the Input Specification is complete and submitted. Approval at this gate changes contract status to `Approved` and unlocks decomposition.
- Neither gate can be bypassed. The system must prevent Stage 2 fields from being populated before Stage 1 is approved.

### 3. Dependency Enforcement

The system must know the dependency graph between artefacts and prevent out-of-sequence production:

- Output Specification cannot be approved before Stage 1 contract sections are complete
- Backcasting Output cannot be created before Stage 1 approval
- Input Specification cannot be created before Backcasting Output is accepted
- Stage 2 contract sections cannot be populated before Backcasting Output is accepted

The dependency resolver must support two modes:

- **Structural** — reports what depends on what, for informational use
- **Blocking** — returns a 4xx error when a prerequisite is unmet, preventing out-of-sequence API calls

The PM agent should determine whether both modes are required in the initial build or whether structural mode is sufficient for the prototype.

### 4. Progress Tracking

For any workflow contract in the system, the system must be able to report:

- Which sections are complete, incomplete, or flagged
- Which artefacts have been produced, are in progress, or not yet started
- Which gate has been passed
- What is currently blocking progress
- What the next required action is

Progress tracking must be tier-aware — Quick Start contracts should not report missing Backcasting Output or Input Specification as blockers, since those artefacts are not required at that tier.

### 5. Rigour Triage Integration

The six rigour triage questions and their scoring logic must be stored as configuration (hard-coded for the prototype). The triage result — rigour level 1–5 — must be stored per contract and must inform which fields are mandatory vs. optional.

### 6. Design Shape Routing

The seven design shape questions and their routing logic must be stored as configuration. The design shape result must be stored per contract and surfaced as a recommended first action.

***

## Progressive Tier Alignment

The system must support three tiers of rigour, routing to the appropriate tier based on the triage result. For the prototype, the **Quick Start tier** must be fully operational. The **Practitioner tier** must be implemented to the point where an end-to-end Practitioner run is possible.

| Tier | Rigour Level | Target Complexity | Artefacts Required |
|---|---|---|---|
| **Quick Start** | 1–2 | Simple, low-risk, single actor | Contract (Stage 1 only), Output Spec |
| **Practitioner** | 3 | Cross-functional, moderate risk | Contract (both stages), Output Spec, Backcasting Output, Input Spec |
| **Architect** | 4–5 | Complex, high-risk, regulated | All artefacts, full depth |

Quick Start workflows do not require a Backcasting Output or an Input Specification. The system must not require them for contracts routed to this tier.

Architect tier requires all artefacts from Practitioner tier plus additional rigour applied throughout. No Architect-specific artefacts or gate conditions are currently scoped beyond the shared data model.

***

## Production Method Integration

The three production methods established in the broader CAWDP methodology apply to how individual fields and artefacts are produced. For the prototype, the system only needs to support the **Shallow** method — but the data model must be designed to accommodate Medium and Deep without structural changes later.

| Method | How It Works | Prototype Requirement |
|---|---|---|
| **Shallow** | Auto-computed or extracted from existing contract fields | Must be implemented |
| **Medium** | Pattern pre-filled, human completes and confirms | Data model only |
| **Deep** | Structured multi-step workflow, human provides domain content | Data model only |

Each field in the contract and each artefact must carry a `production_method` attribute (`shallow` / `medium` / `deep`) so the system knows how to handle it.

***

## Data Model Requirements

The PM agent should use these as the entity map for planning the data architecture. Technology choices are deferred — these are logical requirements only.

### Core Entities

- `WorkflowContract` — one record per workflow being designed
- `TriageResult` — one per contract; stores answers and computed rigour level
- `DesignShapeResult` — one per contract; stores answers and computed design shape
- `OutputSpecification` — one per contract; stores all output detail records
- `BackcastingOutput` — one per contract (Practitioner/Architect tier only)
- `InputSpecification` — one per contract (Practitioner/Architect tier only)
- `ApprovalRecord` — one per gate event; stores approver, date, conditions
- `ProgressSnapshot` — queryable view of what is complete, in progress, blocked

### Key Relationships

- All artefacts reference their parent `WorkflowContract`
- `InputSpecification` references its parent `BackcastingOutput` (via `backcasting_artefact_id`)
- `ApprovalRecord` references its gate type (`stage_1` / `stage_2`) and parent contract
- Artefacts reference each other where one is an input to another (dependency links)

### Backcasting Output Record

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Auto-generated |
| `contract_id` | UUID | Parent workflow contract |
| `output_spec_ids` | UUID[] | Output specs this backcasting is derived from |
| `status` | Enum | `draft`, `submitted`, `accepted`, `rejected` |
| `version` | Integer | Incremented on update |
| `intermediate_states` | JSON | States that must exist between trigger and outputs |
| `required_decisions` | JSON | Decisions that must be made during the workflow |
| `identified_inputs` | JSON | Inputs surfaced by backcasting (seed for Input Specification) |
| `gaps` | JSON | Missing inputs or preconditions that currently prevent the workflow from running |
| `produced_by` | UUID | Actor who produced this artefact |
| `accepted_by` | UUID | Actor who accepted it |
| `accepted_at` | DateTime | Timestamp of acceptance |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

### Input Specification Record

| Field | Type | Notes |
|---|---|---|
| `id` | UUID | Auto-generated |
| `contract_id` | UUID | Parent workflow contract |
| `backcasting_artefact_id` | UUID | Parent Backcasting Output — **required, not optional** |
| `status` | Enum | `draft`, `submitted`, `approved`, `rejected` |
| `version` | Integer | |
| `inputs` | JSON[] | Each input: name, description, type, source, required/optional, format, quality standard, what-if-missing |
| `approved_by` | UUID | |
| `approved_at` | DateTime | |
| `created_at` | DateTime | |
| `updated_at` | DateTime | |

***

## API Endpoints Required

### Triage & Onboarding

| Method | Path | Description |
|---|---|---|
| `POST` | `/triage/evaluate` | Six rigour questions → rigour level, tier, name |
| `POST` | `/design-shape/evaluate` | Design shape questions → shape, recommended action |
| `POST` | `/onboard` | Combined triage + design shape in one call |

### Workflows & Contracts

| Method | Path | Description |
|---|---|---|
| `POST` | `/workflows` | Create workflow + initial contract |
| `GET` | `/contracts` | List contracts with completion status |
| `GET` | `/contracts/{id}` | Read a contract |
| `PATCH` | `/contracts/{id}` | Section updates |
| `GET` | `/contracts/{id}/fields` | Field catalogue with completion flags |

### Output Specifications

| Method | Path | Description |
|---|---|---|
| `POST` | `/contracts/{id}/output-specs` | Create output spec |
| `GET` | `/output-specs/{id}` | Read an output spec |
| `PATCH` | `/output-specs/{id}` | Update an output spec |
| `POST` | `/contracts/{id}/output-specs/{spec_id}/submit` | Submit for review |
| `POST` | `/output-specs/{id}/approve` | Approve an output spec |

### Stage 1 Gate

| Method | Path | Description |
|---|---|---|
| `POST` | `/contracts/{id}/submit/stage-1` | Submit contract for Stage 1 review |
| `POST` | `/contracts/{id}/approve/stage-1` | Approve Stage 1 gate |
| `GET` | `/contracts/{id}/dependencies` | Dependency resolver |

### Backcasting Output

| Method | Path | Description |
|---|---|---|
| `POST` | `/contracts/{id}/backcasting` | Create a Backcasting Output for a Stage 1 approved contract |
| `GET` | `/backcasting/{id}` | Read a Backcasting Output |
| `PATCH` | `/backcasting/{id}` | Update a Backcasting Output |
| `POST` | `/contracts/{id}/backcasting/{bc_id}/submit` | Submit for acceptance |
| `POST` | `/backcasting/{id}/accept` | Accept a Backcasting Output (unlocks Input Specification creation) |

### Input Specification

| Method | Path | Description |
|---|---|---|
| `POST` | `/contracts/{id}/input-specs` | Create Input Specification (requires accepted Backcasting Output) |
| `GET` | `/input-specs/{id}` | Read an Input Specification |
| `PATCH` | `/input-specs/{id}` | Update an Input Specification |
| `POST` | `/contracts/{id}/input-specs/{spec_id}/submit` | Submit for review |
| `POST` | `/input-specs/{id}/approve` | Approve an Input Specification |

### Stage 2 Gate

| Method | Path | Description |
|---|---|---|
| `POST` | `/contracts/{id}/submit/stage-2` | Submit contract for Stage 2 review |
| `POST` | `/contracts/{id}/approve/stage-2` | Approve Stage 2 gate — transitions contract to `approved` |

### Progress & History

| Method | Path | Description |
|---|---|---|
| `GET` | `/contracts/{id}/progress` | Full progress snapshot (`?hide_locked=true` supported) |
| `GET` | `/contracts/{id}/next-action` | Recommended next step |
| `GET` | `/contracts/{id}/history` | Chronological event audit trail |

***

## Stage 2 Gate Conditions

The following must all be true before `POST /contracts/{id}/submit/stage-2` is accepted:

1. Contract status is `stage_1_approved`
2. A `backcasting_output` record exists for this contract with status `accepted`
3. All Stage 2 contract sections are complete
4. An `input_specification` record exists for this contract with status `submitted` or `approved`
5. No required Stage 2 fields are flagged as incomplete

Stage 2 approval must transition the contract status to `approved` and unlock decomposition (which is itself out of scope for this brief).

***

## Configuration (Hard-Code for Prototype)

The following must be encoded as configuration, not stored as user-editable data:

- The six rigour triage questions, answer options, and scoring logic
- The seven design shape questions, answer options, and routing logic
- The workflow contract field definitions (labels, data types, stage assignment, production method, mandatory/optional by rigour level)
- The artefact catalogue per tier (which artefacts are required at Quick Start vs. Practitioner vs. Architect)
- The gate conditions (what must be true before each gate can be passed)
- Valid lifecycle status transitions per artefact type

### Artefact Catalogue Updates

The artefact catalogue must define required artefacts per tier:

| Tier | Required Artefacts |
|---|---|
| Quick Start (1–2) | Contract (Stage 1 only), Output Specification |
| Practitioner (3) | Contract (both stages), Output Specification, Backcasting Output, Input Specification |
| Architect (4–5) | All Practitioner artefacts, with additional rigour applied throughout |

### Status Transitions

Valid lifecycle transitions must be defined for each artefact type:

- **Contract:** `draft` → `stage_1_review` → `stage_1_approved` → `stage_2_review` → `approved` → `superseded`
- **Output Specification:** `draft` → `in_review` → `approved` → `superseded`
- **Backcasting Output:** `draft` → `submitted` → `accepted` / `rejected`
- **Input Specification:** `draft` → `submitted` → `approved` / `rejected`

### Gate Conditions

Gate conditions must be defined per stage:

- **Stage 1:** All Stage 1 contract sections complete, Output Specification submitted
- **Stage 2:** Backcasting Output accepted, Input Specification submitted, all Stage 2 contract sections complete

***

## Event Audit Trail

Every state-changing operation must log an event to an audit trail. Canonical event types:

**Quick Start tier:**

- `contract_created`
- `section_updated`
- `output_spec_created`
- `output_spec_submitted`
- `output_spec_approved`
- `contract_submitted_stage_1`
- `stage_1_approved`

**Practitioner tier (additional):**

- `backcasting_created`
- `backcasting_submitted`
- `backcasting_accepted`
- `backcasting_rejected`
- `input_spec_created`
- `input_spec_submitted`
- `input_spec_approved`
- `input_spec_rejected`
- `contract_submitted_stage_2`
- `stage_2_approved`

Event logging should be best-effort — the main operation succeeds even if logging fails. The history endpoint should fall back to timestamp inference for legacy or incomplete event records.

***

## Optimistic Locking

All update operations on contracts, output specs, backcasting outputs, and input specifications must support optimistic locking via an `expected_updated_at` parameter. This prevents lost updates when multiple actors modify the same record concurrently.

***

## Progress Tracker Requirements

`GET /contracts/{id}/progress` must report:

- Which sections are complete, incomplete, or flagged
- Which artefacts have been produced, are in progress, or not yet started
- Which gate has been passed
- What is currently blocking progress
- Whether Stage 2 gate conditions are met (for Practitioner-tier contracts)
- What is currently blocking Stage 2 submission (for Practitioner-tier contracts)

`GET /contracts/{id}/next-action` must return tier-specific next actions, including:

- Quick Start: "Complete Stage 1 sections", "Submit Output Specification", "Submit for Stage 1 review"
- Practitioner: "Create Backcasting Output — Stage 1 is approved and backcasting has not begun", "Submit Backcasting Output for acceptance", "Create Input Specification — Backcasting Output is accepted", "Submit for Stage 2 review — all Stage 2 conditions met"

Progress responses must be tier-aware — Quick Start contracts must not report missing Practitioner-tier artefacts as blockers.

***

## What Is Explicitly Out of Scope for This Build

The following are **future iterations** and must not be built now:

- The agent specification layer (what is built *on top of* a completed contract)
- Phase orchestrator agents (the 11-phase CAWDP pipeline)
- Deep production workflows for artefact generation (the Compiler, Analyst, Deriver agents)
- The full 150-output artefact catalogue for Practitioner and Architect tiers
- Any UI beyond what is needed to populate and review a contract record
- External integrations (notification systems, document platforms, etc.)
- Architect-specific artefacts or gate conditions beyond the shared data model
- Medium or Deep production method execution paths (data model only)

The prototype must prove one thing: **that defining the workflow contract and its specification artefacts first makes everything downstream easier, faster, and more explainable**. Anything that does not contribute to proving that must wait.

***

## Constraints & Guardrails for Planning

| Constraint | Detail |
|---|---|
| **Sequence integrity** | The PM agent must not plan the agent specification layer or phase orchestrators alongside this work. Those come after. |
| **Prototype first** | Every planning decision should ask: does this prove the foundation, or is it a later-iteration feature? If the latter, flag and defer. |
| **Template fidelity** | The designed templates are the specification. The PM agent should not redesign them — only plan their implementation. |
| **No premature UI investment** | The prototype does not need a polished interface. Functionality first; interface later. |
| **Dependency resolver before progress tracker** | The dependency resolver (what is blocking production of a given artefact) must be built before the progress tracker — the tracker depends on it. |
| **Rigour routing before field population** | The triage engine and design shape router must be operational before the contract populator is built — they determine which fields are required. |
| **Layer 1 immutability** | Configuration tables (artefact catalogue, status transitions, gate conditions, contract fields) are seeded via migration. Changes to these require a new migration script, not runtime edits. |
| **Layer 2 schemaless** | Instance tables are created on first write. New artefact types (Backcasting Output, Input Specification) follow this pattern unless a migration explicitly defines them. |
| **Event logging is best-effort** | State-changing endpoints log events after the main operation — the main operation succeeds even if logging fails. The history endpoint falls back to timestamp inference. Backcasting Output and Input Specification lifecycle events need to be designed with this failure mode in mind. |
| **Optimistic locking pattern** | `expected_updated_at` is used to prevent lost updates on contracts and output specs. The same pattern must be applied to Backcasting Output and Input Specification records. |

***

## Recommended Build Sequence

This is a suggested order for the PM agent to validate and refine during planning. It is sequenced to enable the earliest possible end-to-end test.

### Quick Start Tier (Steps 1–6)

1. **Triage engine** — accepts answers, returns rigour level
2. **Design shape router** — accepts answers, returns design shape and recommended action
3. **Contract record** — all Stage 1 fields, progressive population, status tracking
4. **Output Specification record** — all fields, lifecycle status, link to contract
5. **Stage 1 gate logic** — conditions, approval record, status transition
6. **Progress tracker** — what is complete, what is blocked, what is next

### Practitioner Tier (Steps 7–11)

1. **Backcasting Output record** — all fields, lifecycle status, link to contract and output spec
2. **Input Specification record** — all fields, lifecycle status, link to backcasting output
3. **Stage 2 gate logic** — conditions, approval record, status transition
4. **Shallow production method** — auto-computation of derivable fields from existing contract data
5. **Dependency resolver** — prevents out-of-sequence artefact production

Steps 1–6 constitute the **Quick Start tier** minimum viable loop. Steps 7–11 complete the **Practitioner tier**.

***

## Test Coverage Required

Following a milestone test structure:

- **Milestone 1** — Schema, configuration, health check
- **Milestone 2** — Workflow creation, triage, design shape
- **Milestone 3** — Contract CRUD, section updates, fields
- **Milestone 4** — Output specs, submit/approve, Stage 1 gate
- **Milestone 5** — Progress, next-action, history, `hide_locked`
- **Milestone 6** — Backcasting Output CRUD, submit, accept, reject
- **Milestone 7** — Input Specification CRUD, submit, approve, Stage 2 gate
- **Event logging tests** — Event CRUD, router integration, new event types
- **Utility tests** — `normalize()` edge cases

Milestones 1–5 validate the Quick Start tier. Milestones 6–7 validate the Practitioner tier.

***

## Success Conditions

### Quick Start Tier

The prototype is successful when a user can complete the following end-to-end loop without external assistance:

1. Describe a workflow they want to design (name, purpose, rough description)
2. Answer the six rigour triage questions and receive a rigour level
3. Answer the seven design shape questions and receive a design shape and recommended first action
4. Begin populating the workflow contract — Stage 1 sections
5. Complete and submit the Output Specification
6. Pass the Stage 1 gate
7. View a progress report showing what is complete, what is pending, and what the next action is

A successful Quick Start run must be achievable in **under 2 hours** for a simple, well-understood workflow.

### Practitioner Tier

This phase is successful when a user can complete the following Practitioner-tier loop end-to-end without external assistance:

1. Complete the Quick Start loop (steps 1–7 above)
2. For a contract routed to Practitioner tier: create a Backcasting Output after Stage 1 approval
3. Submit the Backcasting Output and have it accepted
4. Create an Input Specification referencing the accepted Backcasting Output
5. Complete Stage 2 contract sections
6. Submit for Stage 2 review and receive Stage 2 approval
7. See contract status transition to `approved`
8. Receive accurate progress and next-action responses at every step

A successful Practitioner tier run must be completable in **under 24 hours** for a cross-functional, moderately complex workflow.

***

## MCP server tools for VS Code Copilot custom agents

These have already been added to the mcp.json file.

```
"agno-docs": {
   "type": "http",
   "url": "https://docs.agno.com/mcp"
  },
  "railway": {
   "type": "http",
   "url": "https://mcp.railway.com"
  },
  "surrealdb.py Docs": {
   "type": "sse",
   "url": "https://gitmcp.io/surrealdb/surrealdb.py"
  },
  "SurrealDB Docs": {
   "type": "sse",
   "url": "https://gitmcp.io/surrealdb/docs.surrealdb.com"
  },
  "fastapi-docs": {
   "command": "uv",
   "args": [
    "run",
    "--directory",
    "/Users/peteargent/edgeos/fastapi-docs-mcp",
    "python",
    "main.py"
   ]
  }
```
