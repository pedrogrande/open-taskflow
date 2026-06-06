# Output Specification Template v2

> **When this is created:** During Stage 1 of the Workflow Contract population phase — before backcasting begins. The Output Specification is the fixed destination point for the entire design process. Nothing downstream can be accurately designed until this is approved.
>
> **Relationship to the contract:** The outputs defined here populate Section VI of the Workflow Contract directly. This document provides the expanded detail; the contract holds the summary reference.

***

## Metadata

| Field | Value |
|---|---|
| **Output Spec ID** | [auto-generated] |
| **Parent Contract ID** | [Workflow Contract ID] |
| **Workflow Name** | [From contract] |
| **Version** | [e.g. 1.0] |
| **Created By** | [Name / Role] |
| **Created Date** | [date] |
| **Status** | `Draft` / `In Review` / `Approved` / `Superseded` |
| **Approved By** | [Name / Role] |
| **Approved Date** | [date] |

***

## I. Output Inventory

> List every output the workflow must produce for it to be considered complete. Include all artefacts, decisions, state changes, communications, and signals. If it must exist at the end of the workflow, it belongs here.

| # | Output Name | Type | Description |
|---|---|---|---|
| 1 | [Name] | [Document / Record / Decision / Communication / State change / Signal / Physical item] | [What this output is and what it represents in plain language] |

***

## II. Output Detail

> Complete one block per output listed in Section I.

***

### Output [#]: [Output Name]

**Identity**

| Field | Value |
|---|---|
| Output ID | [e.g. OUT-01] |
| Type | [Document / Record / Decision / Communication / State change / Signal / Physical item] |
| Description | [Full description — what this output is, what it contains, and what it represents] |
| Purpose | [Why this output must exist — what breaks or cannot proceed without it] |

**Recipient & Handoff**

| Field | Value |
|---|---|
| Primary Recipient | [Who or what receives this output] |
| Secondary Recipients | [Others who need access — or None] |
| Handoff Format | [How it must be delivered — e.g. signed PDF, system record, verbal confirmation, structured JSON] |
| Handoff Timing | [When it must be delivered — at workflow completion / at a specific step / within a defined window] |
| Handoff Ownership | [Who is responsible for ensuring this output reaches its recipient] |

**Quality Standard**

| Field | Value |
|---|---|
| Minimum Standard | [What good enough looks like — the threshold below which this output cannot be accepted] |
| Target Standard | [What excellent looks like — the ideal] |
| Quality Criteria | [Specific, independently verifiable conditions the output must meet] |
| Who Assesses Quality | [Role responsible for quality verification] |

**Verification**

| Field | Value |
|---|---|
| Verification Method | [How completion of this output is confirmed — e.g. human review against criteria, automated validation, named approver sign-off, delivery receipt] |
| Verified By | [Role] |
| Verification Triggers | [What initiates the verification — e.g. output submitted, workflow reaches a certain step] |
| Pass / Fail Criteria | [What constitutes a pass — and what triggers a rejection and rework loop] |

**Dependencies & Sequencing**

| Field | Value |
|---|---|
| Depends On | [Other outputs or intermediate states that must exist before this output can be produced] |
| Enables | [What this output unlocks — other outputs, downstream workflows, or decisions] |
| Can Be Produced in Parallel With | [Other outputs that do not depend on this one — or None] |

**Risk**

| Field | Value |
|---|---|
| Risk if Output is Poor Quality | [Consequence of producing this output below minimum standard] |
| Risk if Output is Not Produced | [Consequence of this output not existing at all] |
| Reversibility | [Reversible / Partially reversible / Irreversible — explain if irreversible] |
| Confidentiality | [Public / Internal / Restricted / Confidential] |

***

*(Repeat Output Detail block for each output)*

***

## III. Completion Conditions

> These conditions must all be true simultaneously for the workflow to be considered complete. They are derived from — but are not identical to — the individual output quality criteria. A workflow can produce all outputs but still not meet its completion conditions if the collective outcome has not been achieved.

| # | Completion Condition | Verification Method | Who Verifies |
|---|---|---|---|
| 1 | [The condition that must be true] | [How it is confirmed] | [Role] |

***

## IV. Partial Completion Assessment

| Field | Value |
|---|---|
| Can the workflow produce value if partially complete? | [Better than before / Neutral / Worse than before — explain] |
| Which outputs are highest priority if completion is at risk? | [Rank or name outputs by priority under constraint] |
| What does incomplete output leave behind? | [Description of the world state if the workflow stops before producing all outputs] |

***

## V. Downstream Dependencies

> Other workflows or processes that depend on one or more of these outputs existing. Used to assess blast radius and sequencing urgency.

| Output | Downstream Workflow or Process | Dependency Type | Impact if Output is Delayed or Poor |
|---|---|---|---|
| [Output name] | [Workflow or process name] | [Hard dependency — cannot proceed without it / Soft — can proceed with workaround] | [Consequence] |

***

## VI. Assumptions

| Assumption | What It Affects | Most Likely to Be Wrong? |
|---|---|---|
| [What is being taken for granted about these outputs] | [Which output or condition depends on this] | [Yes / No] |

***

## VII. Open Questions

> Questions that remain unresolved at the time of drafting. Each must be resolved before this specification can be approved.

| # | Question | Blocks Which Output | Owner | Target Resolution Date |
|---|---|---|---|---|
| 1 | [The unresolved question] | [Output name] | [Who will resolve it] | [date] |

***

## VIII. Approval

> This specification must be approved before backcasting begins. Approval confirms that the outputs defined here are the correct and complete definition of what this workflow must produce.

| Field | Value |
|---|---|
| Submitted By | [Name / Role] |
| Submission Date | [date] |
| Approved By | [Name / Role] |
| Approval Date | [date] |
| Conditions / Notes | [Any conditions on this approval — or "None"] |
| Backcasting Authorised | [Yes / Pending] |
