# Input Specification Template v2

> **When this is created:** During Stage 2 of the Workflow Contract population phase — after the Backcasting Output has been accepted. Input candidates from the backcasting exercise (Backcasting Output Section V) are the primary source material for this document. Input specs defined before backcasting is complete are provisional only and must be treated as assumptions, not facts.
>
> **Relationship to the contract:** The inputs defined here populate Section XIII of the Workflow Contract. This document provides the expanded detail; the contract holds the summary reference and the gap analysis.

***

## Metadata

| Field | Value |
|---|---|
| **Input Spec ID** | [auto-generated] |
| **Parent Contract ID** | [Workflow Contract ID] |
| **Backcasting Artefact ID** | [ID of the accepted Backcasting Output this spec is derived from] |
| **Workflow Name** | [From contract] |
| **Version** | [e.g. 1.0] |
| **Created By** | [Name / Role] |
| **Created Date** | [date] |
| **Status** | `Draft` / `In Review` / `Approved` / `Superseded` |
| **Approved By** | [Name / Role] |
| **Approved Date** | [date] |

***

## I. Input Inventory

> List every input the workflow requires. Derived from the backcasting exercise. An input is anything that must exist before the workflow can begin — or before a specific step can proceed — that originates outside the workflow itself.

| # | Input Name | Type | Required Before | Currently Available? |
|---|---|---|---|---|
| 1 | [Name] | [Data / Document / Decision / Artefact / Access / Signal / Physical item] | [Workflow start / Step name] | [Yes / No / Partially] |

***

## II. Input Detail

> Complete one block per input listed in Section I.

***

### Input [#]: [Input Name]

**Identity**

| Field | Value |
|---|---|
| Input ID | [e.g. IN-01] |
| Type | [Data / Document / Decision / Artefact / Access / Signal / Physical item] |
| Description | [What this input is and what it represents] |
| Purpose | [Why this input is required — what cannot proceed without it, and which output it ultimately enables] |
| Derived From | [Backcasting chain reference — which output's chain surfaced this input] |

**Source & Provision**

| Field | Value |
|---|---|
| Source | [Where this input comes from — system, person, upstream workflow, external party] |
| Provided By | [Role or system responsible for producing or delivering this input] |
| Trigger for Provision | [What causes this input to be produced or sent — e.g. workflow trigger, upstream workflow completion, calendar event, manual action] |
| Required Before | [Workflow start / Specific step name — when this input must be present] |

**Format & Quality**

| Field | Value |
|---|---|
| Required Format | [The form the input must arrive in — e.g. signed PDF, structured JSON, verbal confirmation, completed system record] |
| Minimum Quality Standard | [What a sufficient input looks like — the threshold required to proceed] |
| What Makes It Insufficient | [Specific conditions that mean this input cannot be accepted and the workflow cannot proceed or must be paused] |
| Quality Ownership | [Who is responsible for ensuring this input meets the required standard before it enters the workflow] |
| Escalation Path if Insufficient | [What happens and who is notified if the input does not meet standard] |

**Dependency & Sequencing**

| Field | Value |
|---|---|
| Required Before Which Output | [Which outputs from the Output Specification depend on this input existing] |
| Required Before Which Step | [If known — the specific step that first requires this input] |
| Enables | [What this input unlocks within the workflow] |
| Blocked If Missing | [What cannot proceed if this input is absent or insufficient] |

**Availability & Gap**

| Field | Value |
|---|---|
| Currently Available | [Yes / No / Partially] |
| Gap Description | [If not fully available — what is missing, unreliable, or not yet existing] |
| Gap Owner | [Who is responsible for resolving this gap] |
| Resolution Required By | [Date or milestone — when this gap must be closed for the workflow to run] |
| Interim Workaround | [If any — how the workflow can proceed in the absence of this input, and at what cost / risk] |

**Risk**

| Field | Value |
|---|---|
| Risk if Input is Poor Quality | [Consequence of proceeding with an input below minimum standard] |
| Risk if Input is Absent | [Consequence of the workflow beginning or reaching this step without this input] |
| Reversibility of Downstream Harm | [If poor input causes harm — can it be undone?] |
| Confidentiality | [Public / Internal / Restricted / Confidential] |

***

*(Repeat Input Detail block for each input)*

***

## III. Input Gap Summary

> Consolidated view of all inputs that are not currently available. This table feeds directly into the Input Gap Analysis in Section XIII of the Workflow Contract.

| # | Input | Gap Description | Resolution Required | Gap Owner | Status |
|---|---|---|---|---|---|
| 1 | [Input name] | [What is missing] | [What must happen to close this gap] | [Role] | [Open / In progress / Resolved] |

***

## IV. Input Quality Ownership Summary

> Single-view accountability table. One row per input, showing who is responsible for quality and what happens if the standard is not met.

| Input | Quality Standard (Summary) | Quality Owner | Escalation Path |
|---|---|---|---|
| [Input name] | [One-line summary of minimum standard] | [Role] | [Who and what] |

***

## V. Input Sequencing Map

> Shows the order in which inputs must be available relative to each other and to the workflow's start and key steps. Surfaces any sequencing constraints that affect workflow design.

| Input | Available At | Required By | Must Precede | Can Arrive In Parallel With |
|---|---|---|---|---|
| [Input name] | [When it becomes available] | [Deadline for availability] | [Other inputs or steps that depend on this] | [Inputs with no sequencing dependency on this one] |

***

## VI. Assumptions

| Assumption | What It Affects | Most Likely to Be Wrong? |
|---|---|---|
| [What is being taken for granted about these inputs] | [Which input or step depends on this] | [Yes / No] |

***

## VII. Open Questions

| # | Question | Blocks Which Input | Owner | Target Resolution Date |
|---|---|---|---|---|
| 1 | [The unresolved question] | [Input name] | [Who will resolve it] | [date] |

***

## VIII. Approval

> This specification must be approved before the Workflow Contract can receive Stage 2 approval and decomposition can begin.

| Field | Value |
|---|---|
| Submitted By | [Name / Role] |
| Submission Date | [date] |
| Approved By | [Name / Role] |
| Approval Date | [date] |
| Conditions / Notes | [Any conditions on this approval — or "None"] |
| Decomposition Authorised | [Yes / Pending — pending Stage 2 contract approval] |

***
