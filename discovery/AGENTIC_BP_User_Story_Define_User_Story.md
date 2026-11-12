# AGENTIC User Story Process
## Define User Story

**Lifecycle Stage:** User Story  
**Status:** Proposed Baseline

## 1. Purpose

Define what each business Role needs the target system to enable or support while performing an approved Activity. User Stories and their Acceptance Criteria are AGENTIC's primary functional requirement structure.

A User Story is a direct functional reference for UI/UX design: it explains the Role's goal, the information and rules involved, and the observable outcomes. It does not prescribe visual layout, screen composition, or interaction styling; those are defined in UI/UX Design.

## 2. Inputs

- Approved Activity Set, including System Support and entity-level information needs
- Approved Role Set and Role-to-Activity mapping
- Approved Business Process and relevant steps, decisions, and outputs
- Applicable Project Context, Project Knowledge, Platform Knowledge, and Glossaries
- NFR references or constraints already discovered upstream, if applicable

NFRs may be identified while defining a story. Reference the relevant NFR or record it as a candidate for the NFR stage; do not create a competing authoritative NFR definition here.

## 3. Process Flow

```text
Approved Activity + System Support
          +
Approved Role
          ↓
Agent proposes Role-specific User Stories
          ↓
Define chronological Capability / Action
          ↓
Specify attribute-level Information Requirements,
Business Rules, and testable Acceptance Criteria
          ↓
User reviews / revises ↔ Agent refines
          ↓
User approves
          ↓
Approved User Stories
          ↓
Direct functional input to UI/UX Design
```

## 4. Activities

### US-01 Propose User Stories

**Performed by:** Agent

Derive stories from the Activity's System Support and the Role's responsibility, authority, and information needs. Create a story for a distinct Role goal or system-supported action. Keep its Capability / Action chronological with the underlying business work. Avoid splitting stories into implementation tasks or prescribing visual design.

**Output:** Proposed User Story Set

### US-02 Elaborate Functional Requirements

**Performed by:** Agent

For each story, specify the attributes the Role needs to view, create, update, validate, or otherwise use; relevant business rules; and Acceptance Criteria that describe verifiable outcomes, including applicable alternate or error paths. Maintain traceability to the Activity and identify the source of rules or constraints.

**Output:** Elaborated User Stories with testable Acceptance Criteria

### US-03 Review / Refine User Stories

**Performed by:** User + Agent

The User reviews, corrects, adds, removes, splits, combines, or clarifies stories and their requirements. The Agent refines the set and identifies unresolved assumptions or conflicts. Repeat until the User considers it ready.

**Output:** Refined User Story Set

### US-04 Approve User Stories

**Performed by:** User

The User explicitly approves the User Story Set. Approval establishes the functional requirement baseline for UI/UX Design and subsequent lifecycle work.

**Output:** Approved User Story Set

## 5. User Story Structure

Each story should contain enough information to express the functional need and verify it.

| Element | Description |
|---|---|
| **ID / Title** | Stable identifier and concise goal-oriented title |
| **Role** | Business Role that needs the system support |
| **Capability / Action** | Chronological business action the system enables or supports |
| **Information Requirements** | Required business entities and specific attributes, including their use (view, create, update, validate, etc.) |
| **Business Rules** | Conditions, calculations, permissions, decisions, or constraints governing the behavior, with source where known |
| **Acceptance Criteria** | Observable, testable conditions that establish when the story is satisfied |
| **Business Value** | Why the support matters to the Role or business |
| **Source Activity** | Approved Activity and its System Support from which the story derives |
| **Related NFRs** | References to applicable NFRs or clearly marked candidates for later NFR-stage review |

### Recommended expression

> As a **[Role]**, I need to **[Capability / Action]** so that **[Business Value]**.

The sentence is a concise summary, not a substitute for the structured requirements above.

## 6. Chronological Capability / Action

Describe the system-supported action in the order the Role performs the work. A story may include a meaningful sequence of actions, but separate distinct outcomes when doing so improves clarity or verification.

Example:

```text
Activity: Review Application
Role: Loan Officer
Capability / Action:
1. Access an assigned application.
2. Review applicant and supporting-document information.
3. Record a review outcome and comments.
```

Do not turn this into a screen sequence or prescribe where elements appear. UI/UX Design determines the appropriate user flows and presentation.

## 7. Attribute-Level Information Requirements

Specify the individual attributes needed for the story, grounded in the Activity's entity-level requirements. Identify why each attribute is needed and how the Role uses it. Avoid collecting data without a stated business purpose.

Example:

| Entity | Attribute | Use |
|---|---|---|
| Application | Application number | Identify the assigned application |
| Application | Submission date | Assess timeliness |
| Applicant | Legal name | Confirm applicant identity |
| Supporting Document | Document type and status | Determine whether required evidence is present |
| Review | Outcome and comments | Record the result of the review |

This is a functional information requirement, not a visual layout specification or final physical data model.

## 8. Business Rules and Acceptance Criteria

Capture rules that govern the behavior of the story. Use authoritative Project Knowledge where available; label inferences and surface conflicts for User decision. Avoid duplicating long rule definitions when a stable source can be referenced.

Acceptance Criteria must be observable and testable. Use specific conditions and outcomes, including relevant permissions, validation, and alternate paths. Avoid vague terms such as “easy,” “fast,” or “user-friendly” unless they are made measurable and are owned by an approved NFR.

Example:

```text
Given an application assigned to the Loan Officer
When the Officer records an outcome and submits the review
Then the system saves the outcome against that application
And the review is available to the authorized next Role.
```

## 9. UI/UX Relationship and NFR References

Approved User Stories, attribute-level information needs, and Acceptance Criteria are direct functional inputs to UI/UX Design. They tell designers **who needs to accomplish what, with which information and rules, and how success is verified**. UI/UX Design decides flows, screens, and interaction details without altering approved business intent without review.

Quality needs can be discovered at any point. User Stories may point to applicable NFRs, but the authoritative NFR definitions are consolidated, quantified, verified, and approved in the Non-Functional Requirement lifecycle stage after Data Model and before System Architecture. Do not duplicate their authoritative definitions in stories.

## 10. Iteration and Clarification

Review and refinement may repeat as needed; approval is an explicit User action. Ask only when ambiguity materially affects the Role's goal, behavior, information, rules, Acceptance Criteria, business value, or downstream design. Otherwise proceed with a reasonable, clearly labeled interpretation.

## 11. Core Principle

> **A User Story expresses a Role-specific system need through chronological Capability / Action, attribute-level Information Requirements, Business Rules, testable Acceptance Criteria, Business Value, and traceability to its Source Activity. It guides UI/UX function without prescribing visual layout.**
