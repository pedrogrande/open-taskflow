# Canonical Glossary

*Terms as defined for this design system only*

***

## The Core Hierarchy

Everything in this system is either a **Workflow** or something that belongs to, describes, or governs a workflow.

```
ORGANISATION
└── Process (a named collection of related workflows)
    └── Workflow (a repeatable transformation from inputs to outputs)
        ├── Subworkflow (a workflow nested inside another)
        └── Task (a single unit of work within a workflow)
                └── Cognitive Operation (a single agent turn or human judgment — the floor)
```

***

## Term Definitions

### Workflow

A repeatable, triggered sequence of tasks that transforms inputs into outputs in service of a defined purpose. A workflow has a definite start condition, a definition of done, and at least one actor. It is the primary unit of design in this system.

### Process

A named collection of workflows that together serve a larger organisational purpose. A process is the parent container. It is not designed directly — its constituent workflows are designed. Example: *Procure-to-Pay* is a process; *Submit Purchase Order for Approval* is a workflow within it.

### Subworkflow

A workflow that is triggered by and nested inside a parent workflow. It is a complete workflow in its own right — it has its own contract, inputs, and outputs — but its purpose is subordinate to the parent. Example: *Validate Supplier Details* may be a subworkflow within *Submit Purchase Order for Approval*.

### Task

The smallest meaningful unit of work within a workflow. Performed by one actor in one sitting without interruption. A task takes an input and produces an output — even if that output is just a decision or a confirmation. Tasks are not designed at the workflow level; they are identified during task decomposition.

### Cognitive Operation

The floor of the hierarchy. A single agent turn or human judgment that cannot be further decomposed. You do not design a cognitive operation — you perform it. The recursion stops here.

***

### Input

Anything consumed or referenced by a workflow or task in order to produce its outputs.

**Required Input**
Must exist before the workflow can begin or a specific step can proceed. Its absence blocks execution.

**Optional Input**
Improves the quality or completeness of the output if present, but its absence does not block execution. The workflow proceeds and the output is produced — potentially at a lower quality standard.

**Conditional Input**
Required only when a specific condition is true. Example: a credit check input is only required when the order exceeds a certain value.

### Output

Anything produced by a workflow or task as a direct result of its execution. An output changes the state of the world. Its existence is what "done" means.

**Required Output**
Must be produced for the workflow to be considered complete.

**Optional Output**
Produced when conditions allow or when a specific path is taken. Its absence does not constitute failure.

**Artefact**
A persistent, examinable output — a document, file, record, or physical item that exists after execution and can be stored, transferred, or audited. All artefacts are outputs. Not all outputs are artefacts.

**Signal**
A non-persistent output — a notification, event, or trigger that causes something else to happen. A signal is consumed immediately on receipt. It leaves a trace only if recorded.

**State Change**
An output that modifies the status of something — a record updated, a flag set, a status changed. A state change is an output but only becomes an artefact if the change is logged.

***

### Contract

A formal record of a commitment about a workflow or task — what will be produced, by whom, to what standard, under what conditions, with what consequences for non-performance. A contract governs relationships and accountability.

**Workflow Contract**
The commitment the organisation makes about a workflow as a whole — its purpose, stakeholders, inputs, outputs, risks, and governance.

**Task Contract**
The commitment between a requester and a performer for a specific task — its scope, definition of done, compensation, and verification method.

**Input Specification**
A standalone record describing one input — its format, quality standard, source, ownership, and what happens if it is missing or insufficient. Referenced by workflow contracts; not owned by them.

**Output Specification**
A standalone record describing one output — its format, quality standard, recipient, verification method, and downstream dependencies. Referenced by workflow contracts; not owned by them.

### Specification

A detailed technical description of what something must be or do. More prescriptive than a contract. A specification defines requirements; a contract defines commitments. A contract may reference a specification.

### Manifest

The organisation-wide inventory of all input and output specifications. A manifest is shared infrastructure — inputs and outputs are defined once and referenced by multiple workflow contracts. It is the map of what flows between workflows.

### Template

A reusable structure for producing a contract or specification. A template defines the fields; a completed template is the contract or specification.

### Register

A maintained list of instances of a category — risks, assumptions, decisions, anomalies. A register is a living document updated over time.

***

### Handoff

The transfer of an output from one actor, step, or workflow to the next. Defined by: what is transferred, in what form, to whom, by when, and how receipt is confirmed. Handoffs are the most fragile points in any workflow.

### Dependency

A relationship in which one thing cannot proceed without another.

- **Hard** — blocks execution entirely if unmet
- **Soft** — creates risk or reduced quality but does not block
- **Informational** — benefits from but does not require

### Definition of Done

The set of conditions that must all be true for a workflow or task to be considered complete. Answers: *is it finished?*

### Quality Standard

The level of quality an output must meet. Defined at two thresholds: minimum (acceptable) and target (excellent). Answers: *is it good enough?*

### Acceptance Criterion

A specific, independently verifiable condition used to assess whether an output meets its quality standard.

### Verification

Confirming an output meets its acceptance criteria. Performed by someone independent of the producer. Answers: *does it meet the specification?*

### Validation

Confirming the output serves its intended purpose. Answers: *did we build the right thing?*

***

### Rigour Level

A classification (1–5) determining how thoroughly a workflow must be designed and governed. Assigned by triage before design begins.

### Design Shape

The category of work required before or instead of standard workflow design. One of: Discovery / Document Only / Mapping / Automation Design / Facilitated Design / Iterative Design / Full Design.

### Happy Path

The execution sequence when all inputs are present, all steps succeed, and no exceptions occur. Designed first.

### Exception Path

The execution sequence when something deviates from the happy path. Designed after the happy path is understood.

### Blast Radius

The scope of harm if a workflow fails. Classified as: Isolated / Team / Organisation / External.

### Assumption

Something taken to be true without verification. Must be named to be tested.

### Hypothesis

A specific, testable belief about what a workflow will produce or how it will behave.

***

### Actors

| Term | Definition |
|---|---|
| **Owner** | Accountable for a workflow's design, performance, and improvement. Does not necessarily perform it |
| **Performer** | Executes a task or workflow. May be human, agent, system, or hybrid |
| **Requester** | Initiates a task or workflow and defines what is needed |
| **Reviewer** | Assesses an output for quality or correctness. Exercises general judgement |
| **Verifier** | Confirms specific acceptance criteria are met. More formal than a reviewer |
| **Stakeholder** | Anyone affected by a workflow — directly or indirectly — whether or not they participate |

***

## Concept Map

```
                        ORGANISATION
                             │
                         PROCESS
                             │
                ┌────────────┴────────────┐
           WORKFLOW ◄──────────────── SUBWORKFLOW
                │
        ┌───────┴────────┐
      TASK            TASK
        │
  COGNITIVE OPERATION (floor)


WORKFLOW is governed by
        │
        ├── WORKFLOW CONTRACT
        │       ├── references ──► INPUT SPECIFICATION(s)
        │       └── references ──► OUTPUT SPECIFICATION(s)
        │
        └── TASK CONTRACT(s) (one per task where needed)


INPUT SPECIFICATION ──────────────────────────────────────────┐
OUTPUT SPECIFICATION ─────────────────────────────────────────┤
                                                    live in the MANIFEST


OUTPUT types:          INPUT types:
├── Artefact           ├── Required
├── Signal             ├── Optional
└── State Change       └── Conditional


HANDOFF connects OUTPUT ──────────────► INPUT
                    (across a boundary)


DEFINITION OF DONE ──── answers: is it finished?
QUALITY STANDARD ─────── answers: is it good enough?
ACCEPTANCE CRITERION ─── answers: does it meet the spec?
VERIFICATION ─────────── answers: does it meet the spec? (independently confirmed)
VALIDATION ───────────── answers: did we build the right thing?
```
