# Workflow Contract Template (v2 — Two-Stage Gate)

> **How this contract works:** Population happens in two stages. **Stage 1** covers everything knowable before backcasting — identity, current state, triggers, purpose, stakeholders, time, risk, and the output specification. Stage 1 approval authorises the backcasting workflow to begin. **Stage 2** adds the input specification once backcasting is complete, and finalises the contract for decomposition approval. Sections marked `[STAGE 1]` must be complete before backcasting. Sections marked `[STAGE 2]` are populated after backcasting returns.

## How These Three Artefacts Connect

The design rationale across all three documents:

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

## Metadata

| Field | Value |
|---|---|
| **Contract ID** | [auto-generated] |
| **Created** | [date] |
| **Version** | [e.g. 1.0] |
| **Contract Status** | `Draft` / `Stage 1 Review` / `Stage 1 Approved` / `Stage 2 Review` / `Approved` / `Superseded` |
| **Rigour Level** | [1–5] — [Level name] |
| **Rigour Justification** | [One sentence explaining why this level was assigned] |
| **Workflow Categories** | [2–3 tags — e.g. Cross-functional / Ad hoc / Value-creating / Moderate risk] |
| **Stage 1 Approved By** | [Name / Role] |
| **Stage 1 Approved Date** | [date] |
| **Stage 2 Approved By** | [Name / Role] |
| **Stage 2 Approved Date** | [date] |
| **Backcasting Artefact Ref** | [Link or ID of the Backcasting Output document] |

***

## `[STAGE 1]` I. Identity

| Field | Value |
|---|---|
| Workflow Name | [Short, verb-noun format] |
| Purpose | [One or two sentences — why does this workflow exist?] |
| Human Goal Served | [The underlying human need this workflow traces back to] |
| Currently Documented | [Yes + reference / No] |

***

## `[STAGE 1]` II. Current State

| Field | Value |
|---|---|
| How does this workflow operate today? | [Description of current practice — formal or informal] |
| What is broken, missing, or causing friction? | [Known problems, pain points, failure patterns] |
| What workarounds currently exist? | [How people get around the official or intended process] |
| What is the gap between current state and desired state? | [The delta that this design must close] |

***

## `[STAGE 1]` III. Trigger & Starting Conditions

| Field | Value |
|---|---|
| Trigger Type | [Event / Time-based / Manual / Completion of another workflow / External signal] |
| Multiple Valid Triggers | [Yes — list each / No] |
| Preconditions | [Conditions that must be true before this workflow can begin] |
| Resources Required | [Time, money, access, tools, information needed to begin] |

> **Note:** Input quality requirements, input quality ownership, and the full input specification are `[STAGE 2]` fields — they are populated after backcasting reveals what inputs are truly required and what standard they must meet.

***

## `[STAGE 1]` IV. Purpose & Value

| Field | Value |
|---|---|
| Desired Outcome | [The end state that must exist for the workflow to be considered successful] |
| Value Created & For Whom | [Named beneficiaries and what they gain] |
| Serves Multiple Goals | [Yes — list all goals and note any tensions / No] |
| Value Justifies Cost | [Yes / No — brief rationale] |
| Could Be Eliminated | [Yes / No — brief rationale] |

***

## `[STAGE 1]` V. Stakeholders & Impact

| Stakeholder | Type | Impact if Successful | Impact if Workflow Fails |
|---|---|---|---|
| [Name or role] | [Direct actor / Direct beneficiary / Indirect] | [Positive outcome] | [Negative outcome] |

| Field | Value |
|---|---|
| Benefits Distributed Evenly | [Yes / No — note who bears disproportionate burden] |
| Who Bears the Most Effort | [The actor(s) who carry the greatest load] |
| Unintended Outputs | [Side effects beyond the stated purpose — positive or negative] |
| Stakeholder Tensions | [Where the needs or desired outcomes of different groups diverge] |
| Trust Erosion Risk | [Yes — describe how / No] |

***

## `[STAGE 1]` VI. Output Specification

> This section is the primary output of Stage 1 and the anchor for backcasting. It defines what the workflow must produce — not how it produces it.

**Outputs Produced:**

| # | Output Name | Type | Description | Format | Recipient | Quality Standard |
|---|---|---|---|---|---|---|
| 1 | [Name] | [Document / Record / Decision / Communication / State change / Signal] | [What this output is and what it represents] | [Format] | [Who receives it] | [Minimum standard — what good enough looks like] |

**Completion Criteria** — conditions that must all be true for the workflow to be considered finished:

| # | Criterion | Verification Method |
|---|---|---|
| 1 | [Condition] | [How it is confirmed] |

**Completion Triggers Downstream:**

| Condition | Downstream Workflow Triggered |
|---|---|
| [e.g. All outputs produced and approved] | [Workflow name or "None"] |

**Partial Completion Assessment:**

| Field | Value |
|---|---|
| May partial completion have value? | [Better than before / Neutral / Worse than before — explain] |
| What does an incomplete output leave behind? | [State of the world if the workflow stops partway] |

***

## `[STAGE 1]` VII. Time & Recurrence

| Field | Value |
|---|---|
| Expected Duration | [Elapsed time from trigger to completion] |
| Deadline | [Date, duration, or condition — if applicable] |
| Deadline Type | [Hard / Soft] |
| Consequence of Missing Deadline | [What happens if the deadline is not met] |
| Value Decays if Delayed | [Yes — describe how quickly and severely / No] |
| Recurrence | [Once / Scheduled / Ad hoc / Continuous] |
| Recurrence Pattern | [If scheduled — frequency and timing] |
| Can Be Paused | [Yes — what causes a pause and what allows resumption / No] |

***

## `[STAGE 1]` VIII. Failure, Abortion & Risk

**How It Fails:**

| Failure Mode | Likely Cause | Response |
|---|---|---|
| [Description] | [What causes this] | [What happens next] |

**How It Stops Legitimately:**

| Abortion Trigger | Condition | Who Can Abort |
|---|---|---|
| [Description] | [When this applies] | [Role] |

**What Non-Completion Costs:**

| Stakeholder | Cost of Non-Completion |
|---|---|
| [Role or group] | [Consequence] |

**Risk Profile:**

| Field | Value |
|---|---|
| Blast Radius | [Isolated / Team / Organisation / External stakeholders] |
| Safety Risks | [Physical / Psychological / Legal / Reputational — describe or None] |
| Irreversible Outputs | [Yes — identify what cannot be undone / No] |
| External Constraints | [Legal, regulatory, or contractual obligations governing this workflow] |

***

## `[STAGE 1]` IX. Visibility & Governance

| Field | Value |
|---|---|
| Progress Visible To | [Who can see workflow status, and at what level of detail] |
| How Incompleteness Is Made Visible | [The mechanism that signals the workflow is stalled, blocked, or incomplete] |
| Status Signals During Execution | [What indicates normal progress vs. at-risk progress] |
| Notifications | [Who is notified, of what, and when] |
| Audit Trail Required | [Yes — what must be recorded / No] |
| Quality Standard for Outputs | [What does good enough look like at the workflow level] |

***

## `[STAGE 1]` X. Relationships to Other Workflows

| Field | Value |
|---|---|
| Part of Larger Process | [Yes — name the parent process / No] |
| Depends On | [Upstream workflows whose completion or output this workflow requires] |
| Triggers Downstream | [Workflows triggered by completion of this workflow — and under what condition] |
| Can Run Simultaneously | [Yes — note any resource contention / No] |
| Conflicts With Other Workflows | [Yes — identify which and what the conflict involves / No] |

***

## `[STAGE 1]` XI. Assumptions

| Assumption | Why It Matters | Most Likely to Be Wrong? |
|---|---|---|
| [What we are taking for granted] | [What breaks if this assumption is false] | [Yes / No] |

***

## `[STAGE 1]` XII. Knowledge & Learning

| Field | Value |
|---|---|
| Knowledge Generated by Completing This Workflow | [What running this workflow reveals — time, quality, patterns, exceptions] |
| Reusable Knowledge Assets Produced | [Templates, decision records, process discoveries — or None] |
| Retrospective Triggers | [Conditions that prompt a formal review] |
| Retrospective Questions | [What will be asked after completion to improve future runs] |

***

## ⬛ STAGE 1 APPROVAL GATE

> **What is being approved:** The output specification, workflow identity, purpose, stakeholders, risk profile, and all Stage 1 sections above. Approval at this gate authorises the backcasting workflow to begin.
>
> **What is not yet approved:** Input specification. This cannot be finalised until backcasting is complete.

| Field | Value |
|---|---|
| Approved By | [Name / Role] |
| Date | [date] |
| Conditions / Notes | [Any conditions attached to this approval — or "None"] |
| Backcasting Authorised | [Yes / Pending] |

***

## `[STAGE 2]` XIII. Input Specification

> Populated after the Backcasting Output (see linked artefact) is complete and reviewed. Backcasting determines what inputs are truly required, where they come from, and what standard they must meet.

**Backcasting Artefact:** `[Link or ID]` — reviewed and accepted on `[date]` by `[name/role]`

**Inputs Required:**

| # | Input Name | Type | Description | Source | Provided By | Required Before | Format | Quality Standard | What Makes It Insufficient |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [Name] | [Data / Document / Decision / Artefact / Access / Signal / Physical item] | [What this input is and what it represents] | [System, person, upstream workflow, external party] | [Role or system responsible] | [Workflow start / Specific step] | [Format] | [Minimum standard to proceed] | [Conditions under which this input cannot be accepted] |

**Input Quality Ownership:**

| Input | Owner | Escalation Path if Insufficient |
|---|---|---|
| [Input name] | [Role responsible for ensuring quality] | [What happens if input does not meet standard] |

**Input Gap Analysis:**

> Surfaced by backcasting — identifies inputs that are required but currently unavailable, unreliable, or not yet existing.

| Input | Currently Available? | Gap Description | Resolution Required Before Workflow Can Run |
|---|---|---|---|
| [Input name] | [Yes / No / Partially] | [What is missing or insufficient] | [What must be done to close this gap] |

***

## ⬛ STAGE 2 APPROVAL GATE

> **What is being approved:** The completed contract including the input specification, validated against backcasting findings. Approval at this gate authorises decomposition to begin.

| Field | Value |
|---|---|
| Approved By | [Name / Role] |
| Date | [date] |
| Conditions / Notes | [Any conditions attached to this approval — or "None"] |
| Decomposition Authorised | [Yes / Pending] |
