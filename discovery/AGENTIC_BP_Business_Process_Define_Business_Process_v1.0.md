# AGENTIC Business Process
## Define Business Process

**Version:** 1.0  
**Status:** Proposed Baseline

## 1. Purpose

The Business Process stage defines how an approved Business Capability is performed from beginning to end.

A Business Process must be **chronological** and contain sufficient operational information to support the downstream definition of **Activity, Role, and User Story**.

The process should remain as simple as possible while containing the information necessary to understand how the business work is performed.

## 2. Input

- Approved Business Capability
- Applicable Project Context
- Applicable Common Glossary and Project Glossary

The Glossary ensures that business terms and their definitions are applied consistently.

## 3. Process Flow

```text
Approved Business Capability
          ↓
Agent proposes Business Process
          ↓
Define chronological process steps
          ↓
For each step:
  • Information Required
  • Process / Action
  • Role
  • Decision / Rule
  • Output
          ↓
Review / Revise
          ↕
Agent refines
          ↓
Approval / Signatory, where applicable
          ↓
User approves
          ↓
Approved Business Process
```

A Business Process may contain branches or loops where required by actual business behavior.

## 4. Business Process Definition Activities

### BP-01 Propose Business Process

**Performed by:** Agent

The Agent analyzes the approved Business Capability and applicable Project Context and proposes one or more Business Processes.

Each proposed Business Process describes the business work chronologically and identifies the information, actions, roles, decisions, reviews, approvals, signatories, and outputs required to understand the process.

**Output:**
- Proposed Business Process Set

### BP-02 Review / Revise Business Process

**Performed by:** User + Agent

The User reviews the proposed Business Process and may revise or clarify process steps, roles, information requirements, decisions, rules, reviews, approvals, signatories, or outputs.

The Agent incorporates the User's revisions and refines the Business Process.

This activity may repeat until the User considers the Business Process sufficiently accurate.

**Output:**
- Refined Business Process Set

### BP-03 Approve Business Process

**Performed by:** User

The User explicitly approves the final Business Process.

Approval establishes the Business Process as the basis for the next stage, Activity.

Where the business process requires formal business approval or signatory action, those activities are represented chronologically within the Business Process.

**Output:**
- Approved Business Process Set

## 5. Business Process Step Structure

Each Business Process is represented as a chronological sequence of steps.

| Element | Description |
|---|---|
| **Sequence** | Position of the step in the process |
| **Process / Action** | What business work is performed |
| **Role** | Business role that performs or participates |
| **Information Required** | Information needed to perform the step |
| **Decision / Rule** | Condition or business rule determining what happens next, when applicable |
| **Review** | Review performed on the work or result, when applicable |
| **Approval** | Formal approval required at the step, when applicable |
| **Signatory** | Person or business role that formally signs or authorizes, when applicable |
| **Output** | Information, decision, document, status, or other result produced |

Not every step requires every element. Only applicable information should be included.

## 6. Chronological Process

The Business Process must describe the actual sequence of business work.

Example:

```text
1. Submit Application
        ↓
2. Validate Application
        ↓
3. Review Application
        ↓
4. Request Correction
        ↓
5. Re-submit Application
        ↓
6. Approve Application
        ↓
7. Sign Application
        ↓
8. Issue Approved Application
```

Branches and loops should be represented where they are part of the actual business behavior.

The process should not introduce unnecessary decomposition or formal process notation unless needed to make the business behavior implementable.

## 7. Information Required

Information Required identifies the information a business role needs to perform a process step.

Examples include:

- Business data
- Applicant information
- Supporting documents
- Reference information
- Previous process results
- Business rules or criteria
- Decisions or approvals from preceding steps

Information Required is particularly important because it provides an input for deriving User Stories.

Example:

```text
Process Step:
Review Application

Role:
Loan Officer

Information Required:
- Applicant information
- Supporting documents
- Eligibility criteria

Action:
Review application completeness and eligibility

Output:
- Review result
- Review comments
```

This can support a downstream User Story such as:

> As a Loan Officer, I want to view the applicant information, supporting documents, and eligibility criteria so that I can review the application.

## 8. Review, Approval, and Signatory

Review, approval, and signatory are explicit process activities when they form part of the business process.

They should not be represented only as general metadata attached to the Business Process.

The chronological process should identify:

- What is being reviewed
- Who performs the review
- What information is reviewed
- What decision or result is produced
- What requires approval
- Who approves
- What requires formal signature
- Who signs
- What output is produced after approval or signing

Example:

```text
Review Application
      ↓
Approval Required
      ↓
Manager Approves
      ↓
Authorized Signatory Signs
      ↓
Approved Application
```

Where approval or signatory is not required by the business process, it should not be artificially introduced.

## 9. Iterative Refinement

Business Process refinement is iterative.

```text
Round 1:
Agent → User → Agent

Round 2:
Agent → User → Agent

Round N:
Agent → User

Final:
User Approves
```

Iterations are loops within BP-02, not separate lifecycle stages.

## 10. Conditional Clarification

The Agent should ask for clarification only when ambiguity materially affects:

- Process sequence
- Business behavior
- Role
- Information required
- Decision or rule
- Review or approval
- Signatory responsibility
- Output
- Downstream engineering

If ambiguity does not materially affect the resulting Business Process, the Agent should use a reasonable interpretation and continue.

## 11. Relationship to Downstream Lifecycle

```text
BUSINESS PROCESS
      ↓
Chronological Steps
      ↓
ACTIVITY
      ↓
ROLE
      ↓
USER STORY
```

The Business Process must contain enough information to identify:

- What activities are performed
- Which business roles perform or participate
- What information each role needs
- What the role needs the target system to support
- What outputs and decisions result from the work

The Business Process does not define the User Story directly. It provides the business context from which User Stories can be derived.

## 12. Core Principle

> **A Business Process is a chronological sequence of business activities that specifies the information required, action performed, responsible role, decision or rule, review, approval/signatory, and resulting output at each applicable step, sufficient to derive Activities, Roles, and User Stories.**

The process should remain simple and implementable. Only information necessary to understand the business behavior and produce downstream engineering outputs should be introduced.
