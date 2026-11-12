# AGENTIC Role
## Define Role

**Version:** 1.0  
**Status:** Proposed Baseline

## 1. Purpose

The Role stage identifies the business roles that perform or participate in Activities within the target business process or system context.

Role is a **business role or actor**, not a project delivery or engineering team role.

Role definition establishes:

- Who performs or participates in Activities
- Where the Role sits in the reporting hierarchy
- What responsibilities the Role has
- What authority the Role has
- What approval or signatory authority the Role has
- What segregation-of-duties constraints apply
- What information the Role needs to perform its work

The Role definition provides an important basis for deriving User Stories.

## 2. Input

The primary input is:

- Approved Activity Set
- Approved Business Process
- Applicable Project Context
- Applicable Platform Knowledge
- Applicable Project Knowledge
- Applicable Common Glossary and Project Glossary

The Business Process provides the chronological business flow and identifies review, approval, and signatory activities.

The Activity Set identifies the specific work that needs to be performed.

## 3. Role Definition Process

```text
Approved Activity Set
        +
Approved Business Process
        ↓
Agent identifies / proposes Roles
        ↓
Build Role hierarchy
        ↓
Map Roles to Activities
        ↓
Analyze Authority and Segregation of Duties
        ↓
User reviews / revises
        ↕
Agent refines
        ↓
User approves
        ↓
Approved Role Set
```

## 4. Role Definition Activities

### R-01 Identify / Propose Roles

**Performed by:** Agent

The Agent analyzes the approved Activities and Business Process and identifies the business Roles required to perform or participate in the Activities.

The Agent should:

- Identify Roles from Activity responsibilities
- Map Roles to Activities
- Identify reporting relationships
- Build the Role hierarchy
- Identify decision and approval authority
- Identify signatory authority
- Identify potential segregation-of-duties conflicts
- Use applicable Platform Knowledge and Project Knowledge
- Avoid creating unnecessary roles

**Output:**

- Proposed Role Set
- Proposed Role Hierarchy
- Role-to-Activity Mapping
- Initial Authority and SoD Analysis

### R-02 Review / Revise Roles

**Performed by:** User + Agent

The User reviews the proposed Role Set and may:

- Add or remove Roles
- Rename Roles
- Change Role descriptions
- Change reporting relationships
- Change Activity assignments
- Change responsibilities
- Change authority
- Change approval authority
- Change signatory authority
- Accept, modify, or reject SoD findings
- Clarify information access

The Agent incorporates the User's revisions and refines the Role model.

This activity may repeat until the User considers the Role definition sufficiently accurate.

**Output:**

- Refined Role Set
- Refined Role Hierarchy
- Refined Role-to-Activity Mapping
- Refined Authority and SoD Definition

### R-03 Approve Roles

**Performed by:** User

The User explicitly approves the final Role Set.

Approval establishes the Roles as the basis for the next stage, User Story.

**Output:**

- Approved Role Set

## 5. Role Structure

Each Role should contain the minimum information necessary to understand its business responsibility, hierarchy, authority, and relationship to Activities.

| Element | Description |
|---|---|
| **Role** | Business role name |
| **Description** | Purpose of the Role |
| **Parent Role** | Role to which the Role reports |
| **Activities** | Activities performed or participated in |
| **Responsibilities** | Responsibilities within those Activities |
| **Authority** | Decisions or actions the Role is authorized to perform |
| **Approval Authority** | Approval level or scope, where applicable |
| **Signatory Authority** | Signing or authorization authority, where applicable |
| **SoD Constraints** | Activities or responsibilities that should be separated |
| **Information Access** | Information required or permitted for the Role, where relevant |

Not every Role requires every element. Only applicable information should be captured.

## 6. Role Hierarchy

The Role model should support reporting relationships.

Example:

```text
Director
   │
   ├── Division Head
   │      │
   │      ├── Manager
   │      │     ├── Officer
   │      │     └── Officer
   │      │
   │      └── Supervisor
   │
   └── Division Head
```

The hierarchy may influence:

- Supervision
- Review
- Approval
- Authorization
- Delegation
- Escalation
- Signatory authority

Hierarchy should be represented only to the level necessary to support the target business process and system behavior.

The Role model should not automatically become a complete organizational structure.

## 7. Role-to-Activity Mapping

A Role must be connected to the Activities it performs or participates in.

```text
Role
  ↓
performs / participates in
  ↓
Activity
```

Example:

```text
Loan Officer
   ├── Receive Application
   ├── Validate Application
   └── Prepare Assessment

Loan Supervisor
   ├── Review Assessment
   └── Recommend Approval

Branch Manager
   └── Approve Application
```

This mapping provides the basis for identifying the User Stories required by each Role.

## 8. Authority

Authority defines the decisions or actions a Role is authorized to perform.

Examples:

| Role | Activity | Authority |
|---|---|---|
| Officer | Prepare Assessment | Create |
| Supervisor | Review Assessment | Review |
| Manager | Approve Application | Approve |
| Director | Approve Exception | Authorize |

Authority is particularly important for Activities involving:

- Review
- Approval
- Rejection
- Authorization
- Exception handling
- Signatory

The Business Process identifies where these actions occur. Role identifies who has the authority to perform them.

## 9. Approval and Signatory Authority

Where the Business Process contains approval or signatory steps, the Role definition should identify the Role authorized to perform those actions.

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

The Role model therefore establishes:

```text
Business Process
      ↓
Approval / Signatory Activity
      ↓
Authorized Role
```

The Agent should not infer formal authority solely from a person's organizational seniority when the Project Knowledge does not establish that authority.

## 10. Segregation of Duties

Segregation of Duties (SoD) is an explicit consideration of Role design.

The Agent should analyze whether assigning multiple Activities to the same Role creates a potential conflict.

Example:

```text
Prepare Assessment
        ↓
Review Assessment
        ↓
Approve Application
```

Potentially conflicting assignment:

```text
Loan Officer
 ├── Prepare Assessment
 ├── Review Assessment
 └── Approve Application
```

The Agent should flag:

> Potential Segregation of Duties conflict: the same Role performs preparation, review, and approval.

The Agent may propose:

```text
Loan Officer
   ↓
Prepare Assessment

Supervisor
   ↓
Review Assessment

Manager
   ↓
Approve Application
```

SoD is a control consideration, not an automatic rule.

The project may have legitimate reasons for allowing a Role to perform multiple Activities.

The User remains responsible for accepting, modifying, or rejecting the proposed SoD treatment.

## 11. Information Access

Where relevant, the Role should identify the information required or permitted to perform its Activities.

This does not require creating a separate access-control model at this stage.

The information should be sufficient to support later User Story and system authorization design.

Example:

```text
Role:
Loan Officer

Activity:
Review Application

Information Access:
- Applicant information
- Application documents
- Eligibility information
```

## 12. No Unnecessary Role Hierarchy

For the initial AGENTIC lifecycle, do not introduce separate lifecycle entities such as:

- Organization Unit
- Position
- Actor
- Responsibility
- Authority

unless later engineering stages demonstrate that they are independently required.

These concepts can initially be represented as attributes or relationships of Role.

The objective is to preserve a simple lifecycle while still capturing the business information required for engineering.

## 13. Iterative Refinement

Role refinement is iterative.

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

Iterations are loops within R-02 Review / Revise Roles, not separate lifecycle stages.

## 14. Conditional Clarification

The Agent should ask for clarification only when ambiguity materially affects:

- Role identification
- Reporting hierarchy
- Activity assignment
- Responsibility
- Authority
- Approval authority
- Signatory authority
- Segregation of Duties
- Information access
- Downstream User Stories

If ambiguity does not materially affect the Role definition or downstream engineering, the Agent should use a reasonable interpretation and continue.

## 15. Knowledge Usage

The Agent should use both Platform Knowledge and Project Knowledge.

```text
Approved Activities
        +
Approved Business Process
        +
Platform Role Patterns
        +
Project Organization / Procedures
        +
Project Policies
        +
Applicable Glossary
        ↓
      Agent
        ↓
Proposed Roles
        ↓
Hierarchy + Activity Mapping
        ↓
Authority + SoD Analysis
        ↓
User Review
        ↓
Approved Roles
```

Platform Knowledge provides reusable role and SoD patterns.

Project Knowledge provides project-specific organizational, policy, and authority information.

Authoritative Project Knowledge takes precedence over generic Platform Knowledge.

## 16. Relationship to User Story

Role is the direct business-actor input to User Story.

```text
Business Process
       ↓
Activity
       ↓
Role
       ↓
What the Role needs the system to support
       ↓
User Story
```

The Role definition provides the identity, responsibility, authority, and business context needed to express a User Story from the perspective of the Role.

Example:

```text
Role:
Loan Officer

Activity:
Review Application

Responsibility:
Assess application completeness and eligibility

Information:
Applicant information and supporting documents

Authority:
Record review result

System Need:
View information and record review result
```

This provides the basis for:

> As a Loan Officer, I want to view applicant information and supporting documents and record my review result so that I can complete the application review.

## 17. Core Principle

> **Role defines who performs or participates in business Activities, where the Role sits in the reporting hierarchy, what responsibilities and authority it has, and what segregation-of-duties constraints apply.**

The Role definition should remain simple and implementable while providing enough business context to support User Story definition and later authorization design.
