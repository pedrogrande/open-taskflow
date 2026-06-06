# Backcasting Output Template

> **Purpose of this document:** To work backwards from the approved output specification and determine what intermediate states, decisions, and inputs are necessary for those outputs to be produced. The Backcasting Output is a required input to Stage 2 of the Workflow Contract. It must be completed and accepted before the input specification can be finalised.

***

## Metadata

| Field | Value |
|---|---|
| **Backcasting ID** | [auto-generated] |
| **Parent Contract ID** | [Workflow Contract ID — links back to Stage 1] |
| **Workflow Name** | [From contract] |
| **Created By** | [Name / Role] |
| **Created Date** | [date] |
| **Status** | `Draft` / `In Review` / `Accepted` |
| **Accepted By** | [Name / Role] |
| **Accepted Date** | [date] |

***

## I. Outputs Being Backcast From

> List the outputs from the approved Output Specification (Section VI of the contract). These are the fixed destination points. Backcasting works backwards from each one.

| # | Output Name | Type | Description | Quality Standard |
|---|---|---|---|---|
| 1 | [From contract Section VI] | [Type] | [Description] | [Quality standard] |

***

## II. Backcasting Chains

> For each output, trace backwards: *given that this output has been produced to the required standard, what must have been true immediately before?* Continue until you reach the workflow's trigger point or a known, stable input that exists before the workflow begins.
>
> Each step backwards is either an **intermediate state** (a condition that must exist), a **decision** (a judgement that must have been made), or a **transformation** (an activity that must have occurred). Name each one. Do not design the steps yet — identify what must be true, not who does it or how.

### Output 1: [Output Name]

**Reverse chain:**

| Step | What Must Have Been True | Type | Notes / Uncertainties |
|---|---|---|---|
| Final state | [The output exists to the required standard] | Output | — |
| One step back | [Condition, decision, or transformation that immediately precedes the output] | [Intermediate state / Decision / Transformation] | [Flag uncertainties] |
| Two steps back | [What must have been true before that] | [Type] | |
| … | … | | |
| Starting point | [The earliest required condition — this becomes an input candidate] | Input candidate | |

*(Repeat for each output)*

***

## III. Intermediate States Identified

> Consolidated list of all intermediate states surfaced across the backcasting chains. These represent the internal milestones the workflow must pass through. They inform step design during decomposition.

| # | Intermediate State | Belongs To Chain(s) | Required Before Which Output(s) | Notes |
|---|---|---|---|---|
| 1 | [Description of the condition that must exist] | [Output name(s)] | [Output name(s)] | |

***

## IV. Decisions Identified

> Decisions surfaced by backcasting that must be made during the workflow. Not designed here — just identified and characterised so they can be assigned and designed during decomposition.

| # | Decision | What It Determines | Who Has Authority | Reversible? | Input Required to Make This Decision |
|---|---|---|---|---|---|
| 1 | [Description of the decision] | [What changes or proceeds depending on the outcome] | [Role] | [Yes / No] | [What must be known before this decision can be made] |

***

## V. Input Candidates

> Every starting point reached in the backcasting chains is a candidate input. This is the raw material for the Input Specification in Stage 2 of the contract.

| # | Input Candidate | Derived From (Chain) | Required Before | Likely Source | Currently Available? | Notes |
|---|---|---|---|---|---|---|
| 1 | [Name or description of the required input] | [Output name] | [Which output or intermediate state requires it] | [Where it likely comes from] | [Yes / No / Unknown] | [Uncertainties, gaps, risks] |

***

## VI. Assumptions Made During Backcasting

> Backcasting requires making assumptions about how the workflow will operate. All assumptions made during this exercise must be recorded here so they can be tested or challenged.

| Assumption | What It Affects | Confidence | Action Required |
|---|---|---|---|
| [What was assumed to be true in order to complete a chain] | [Which chain(s) or input(s) depend on this being true] | [High / Medium / Low] | [Validate / Accept risk / Flag for decomposition] |

***

## VII. Gaps & Risks Surfaced

> Backcasting often reveals that required inputs do not currently exist, or that a required intermediate state has no clear path to being achieved. Record all gaps and risks here. These become the Input Gap Analysis in Stage 2 of the contract.

| # | Gap or Risk | Type | Impact on Workflow | Proposed Resolution |
|---|---|---|---|---|
| 1 | [Description] | [Missing input / Unavailable data / Unclear decision authority / No existing upstream workflow / Other] | [What cannot proceed until this is resolved] | [What needs to happen before Stage 2 approval] |

***

## VIII. Optimisation Observations

> Backcasting frequently surfaces opportunities that would not be visible from a forward-design approach — redundant intermediate states, inputs that could be pre-computed, decisions that could be made earlier, or steps that could be parallelised. Record them here for consideration during decomposition.

| Observation | Type | Potential Benefit | Recommended Action |
|---|---|---|---|
| [What was noticed] | [Simplification / Parallelisation / Elimination / Earlier decision point / Automation candidate / Other] | [What this could improve] | [Flag for decomposition / Investigate further / Incorporate into design] |

***

## IX. Backcasting Sign-Off

> Before this artefact is submitted to Stage 2 of the workflow contract, the following must be confirmed.

| Confirmation | Status |
|---|---|
| All outputs from the Output Specification have been backcast | [Yes / Partial — note gaps] |
| All input candidates are recorded in Section V | [Yes] |
| All assumptions are recorded in Section VI | [Yes] |
| All gaps are recorded in Section VII and have a proposed resolution | [Yes / Pending — note which] |
| Optimisation observations have been recorded | [Yes / None identified] |

| Field | Value |
|---|---|
| Submitted By | [Name / Role] |
| Date | [date] |
| Accepted for Stage 2 By | [Name / Role] |
| Acceptance Date | [date] |
| Notes | [Any conditions on acceptance — or "None"] |

***

The key structural decisions made across both templates:

- **Section VI (Output Specification)** is now its own named section in Stage 1, not buried in the Completion & Quality section — it's the anchor for everything that follows
- **Section XIII (Input Specification)** explicitly references the backcasting artefact and includes an **Input Gap Analysis** table, which is the direct product of Section VII of the Backcasting Output
- The **two approval gates** are visually distinct blocks in the contract, each with explicit statements of what is and isn't being approved — removing any ambiguity about what a Stage 1 approval means
- The **Backcasting Output** is designed as a standalone artefact with its own ID and lifecycle, not a section inside the contract — it has independent status (`Draft` / `In Review` / `Accepted`) and must be formally accepted before Stage 2 opens
- **Section VIII (Optimisation Observations)** in the Backcasting Output captures the discovery value of the backcasting exercise — the questions used to populate it function as a thinking tool, surfacing opportunities that forward design cannot see
