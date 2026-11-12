# DMC-03 Data Model Validation

## 1. Capability Definition

**Capability ID:** DMC-03  
**Capability Name:** Data Model Validation

### Purpose

Data Model Validation determines whether the Logical Data Model produced by DMC-02 is sufficiently complete, semantically correct, structurally consistent, traceable to approved requirements, and fit for its intended business purpose.

DMC-03 provides the authoritative validation of the logical data model. It produces evidence-based validation findings and feeds identified issues back to DMC-02 for refinement.

The key distinction is:

> **DMC-02 constructs the logical model. DMC-03 determines whether the model is sufficiently complete, consistent, correct, traceable, and fit for purpose.**

## 2. Scope

DMC-03 validates the Logical Data Model against:

- Information requirements
- User Stories
- Business Processes
- Activities
- Business Rules
- Roles and responsibilities
- UI/UX information requirements
- Project Knowledge
- Project Glossary
- Common Glossary
- Applicable standards and constraints
- Logical modeling principles

DMC-03 does not redesign the logical model. When validation identifies a problem requiring model changes, the issue is returned to DMC-02 for refinement.

## 3. Capability Structure

```text
DMC-03 Data Model Validation
│
├── Completeness Validation
├── Semantic Validation
├── Structural Validation
├── Relationship Validation
├── Business Rule Validation
├── Requirement Traceability Validation
├── Consistency Validation
├── Integrity Validation
├── Naming & Definition Validation
├── Model Quality Assessment
└── Validation Reporting
```

## 4. Inputs

| Input | Purpose |
|---|---|
| Logical Model Candidate | Primary object being validated |
| Data Requirement Analysis | Source of information concepts and meanings |
| User Stories | Source of functional information requirements |
| Business Processes | Business context and information usage |
| Activities | Entity-level information requirements and business actions |
| Business Rules | Rules the model must represent or support |
| UI/UX Specification | Information displayed, collected, and manipulated |
| Project Knowledge | Project-specific authoritative context |
| Project Glossary | Project-specific terminology and definitions |
| Common Glossary | Common terminology and definitions |
| Applicable Standards | External or organizational modeling requirements |
| Previous Validation Findings | Outstanding or recurring validation issues |
| Human Decisions | Adopted decisions affecting model validation |

## 5. Validation Principle

Validation must be **evidence-based**.

An Agent must not report that a model is valid merely because the model appears reasonable.

Each material validation finding should be supported by identifiable evidence such as:

- Source requirement
- Business rule
- Model element
- Related model element
- Glossary definition
- Traceability relationship
- Validation rule
- Expected condition
- Actual condition

The Agent must distinguish between:

- **Requirement**
- **Existing Practice**
- **Best Practice**
- **Agent Inference**
- **Unknown / Ambiguous**

An inference or assumption must not be presented as an authoritative requirement.

## 6. Process

```text
Logical Model Candidate
        │
        ▼
DM-03.1 Prepare Validation Context
        │
        ▼
DM-03.2 Validate Completeness
        │
        ▼
DM-03.3 Validate Semantics & Business Rules
        │
        ▼
DM-03.4 Validate Structure & Relationships
        │
        ▼
DM-03.5 Validate Traceability & Consistency
        │
        ▼
DM-03.6 Assess Model Quality
        │
        ▼
DM-03.7 Produce Validation Findings
        │
        ├── Pass
        │
        └── Issues
              │
              ▼
        DMC-02 Refinement
              │
              ▼
        Re-validation
```

## 7. DM-03.1 Prepare Validation Context

The Agent establishes the validation context before executing validation.

### Activities

1. Identify the Logical Model Candidate version.
2. Identify the applicable Data Requirement Analysis.
3. Identify applicable User Stories.
4. Identify relevant Business Processes and Activities.
5. Identify applicable Business Rules.
6. Load relevant Project Knowledge.
7. Load relevant Project and Common Glossary definitions.
8. Identify applicable modeling standards and constraints.
9. Identify previous unresolved validation findings.
10. Establish the validation scope.

### Output

A **Validation Context** containing:

- Model version
- Validation scope
- Applicable requirements
- Applicable business rules
- Applicable knowledge sources
- Applicable standards
- Validation rules
- Previous unresolved findings

## 8. DM-03.2 Validate Completeness

Completeness validation determines whether the logical model adequately represents the information required by the approved business context.

### Validate

- Required concepts are represented.
- Required business objects are represented.
- Required information needed by User Stories is represented.
- Required relationships are represented.
- Required identifiers are represented.
- Required classifications or reference concepts are represented where necessary.
- Required business events or transactions are represented where their information must be retained.
- Important concepts identified during Data Requirement Analysis are not unintentionally omitted.

A concept identified during DMC-01 does not automatically have to become an entity.

The Agent must determine whether the concept is represented appropriately as an:

- Entity
- Attribute
- Relationship
- Reference or classification
- Event
- Derived information
- Other appropriate logical construct

The validation question is:

> **Is every required business concept represented appropriately in the logical model?**

## 9. DM-03.3 Validate Semantics & Business Rules

Semantic validation determines whether the model accurately represents the meaning of the business concepts.

### Validate

- Entity meanings are consistent with their definitions.
- Attribute meanings are clear and unambiguous.
- Relationships represent the intended business meaning.
- Similar concepts are not incorrectly merged.
- Distinct concepts are not incorrectly treated as identical.
- Business rules are represented or supported by the model.
- Definitions are consistent with the Project Glossary.
- Terminology is consistent with approved business language.
- Derived concepts are distinguishable from stored concepts where relevant.

Where a business rule cannot be represented directly at the logical data model level, the Agent should identify the gap and indicate the likely downstream layer where the rule must be implemented.

## 10. DM-03.4 Validate Structure & Relationships

Structural validation examines the internal quality of the logical model.

### Entities

Validate:

- Entity definitions are meaningful.
- Entity boundaries are justified.
- Entities are not duplicated without justification.
- Entity specialization or consolidation is appropriate where applicable.

### Attributes

Validate:

- Attributes belong to the appropriate entity.
- Attributes represent atomic business information where appropriate.
- Attribute meanings are unambiguous.
- Repeated or duplicated attributes are identified.
- Derived attributes are identified appropriately.

### Relationships

Validate:

- Relationships have clear business meaning.
- Relationships connect the appropriate entities.
- Cardinality is appropriate.
- Optionality is appropriate.
- Relationship interpretation is clear where relevant.

### Identifiers

Validate:

- Entities have suitable logical identifiers.
- Identifier meaning is clear.
- Identifier uniqueness assumptions are justified.
- Natural and surrogate identification concerns are identified without prematurely making physical database decisions.

### Constraints

Validate:

- Required logical constraints are identified.
- Uniqueness requirements are represented where applicable.
- Mandatory relationships or attributes are represented appropriately.
- Relevant domain restrictions are identified.

## 11. DM-03.5 Validate Traceability & Consistency

### Requirement Traceability

The Agent verifies that important model elements can be traced to their business context.

Typical traceability chain:

```text
Vision / Strategy
      │
      ▼
Business Capability
      │
      ▼
Business Process
      │
      ▼
Activity
      │
      ▼
User Story
      │
      ▼
Information Requirement
      │
      ▼
Logical Data Model
```

The model should also support reverse traceability:

```text
Logical Model Element
        │
        ▼
Information Requirement
        │
        ▼
User Story / Activity
        │
        ▼
Business Context
```

### Consistency Validation

The Agent checks for contradictions or inconsistencies between:

- Entity definitions
- Attribute definitions
- Relationship definitions
- Business rules
- User Stories
- Data Requirement Analysis
- Glossary definitions
- Project Knowledge
- Previously approved decisions

Conflicts must be surfaced rather than silently resolved.

## 12. DM-03.6 Assess Model Quality

The Agent assesses the overall quality of the Logical Data Model.

| Quality Dimension | Question |
|---|---|
| Completeness | Does the model represent required information? |
| Semantic Correctness | Does the model represent the intended business meaning? |
| Structural Consistency | Is the model internally coherent? |
| Relationship Correctness | Are relationships and cardinalities appropriate? |
| Traceability | Can model elements be traced to business requirements? |
| Integrity | Can important business integrity conditions be represented? |
| Clarity | Are concepts and definitions understandable? |
| Maintainability | Can the model evolve without unnecessary complexity? |
| Reusability | Are shared concepts modeled consistently? |
| Fitness for Purpose | Is the model adequate for its intended use? |

The quality assessment should be evidence-based and identify significant limitations or uncertainty.

## 13. DM-03.7 Produce Validation Findings

Each material finding should contain:

| Field | Description |
|---|---|
| Validation ID | Unique validation finding identifier |
| Validation Rule | Rule or criterion being evaluated |
| Model Element | Affected entity, attribute, relationship, or other element |
| Expected Condition | Condition expected by the requirement or rule |
| Actual Condition | Observed condition in the model |
| Result | Pass, Fail, Warning, or Not Determined |
| Severity | Impact level of the finding |
| Evidence | Supporting evidence |
| Source Requirement | Requirement or business source |
| Rationale | Explanation of the finding |
| Recommendation | Suggested resolution |
| Resolution Status | Open, Resolved, Accepted, Deferred, or Rejected |
| Related Decision | Human decision where applicable |

## 14. Validation Result

DMC-03 should produce an overall validation result.

### Valid

The model satisfies the applicable validation criteria with no unresolved material issues.

### Conditionally Valid

The model is usable subject to explicitly documented non-material issues, accepted limitations, or conditions.

### Invalid

The model contains material issues that prevent it from being considered fit for purpose.

### Not Determined

There is insufficient information to complete validation.

The Agent must not convert uncertainty into a passing result.

## 15. Findings Severity

| Severity | Meaning |
|---|---|
| Critical | Prevents the model from satisfying a fundamental business or integrity requirement |
| High | Significant issue affecting important business requirements or model correctness |
| Medium | Material quality issue requiring resolution but not fundamentally invalidating the model |
| Low | Minor issue or improvement opportunity |
| Informational | Observation with no immediate corrective requirement |

Severity should be justified by impact and evidence.

## 16. Validation Feedback Loop

DMC-03 does not directly redesign the model.

When a validation finding requires a model change:

```text
DMC-03 Validation
       │
       ▼
Validation Finding
       │
       ▼
DMC-02 Logical Model Refinement
       │
       ▼
New Logical Model Candidate
       │
       ▼
DMC-03 Re-validation
```

This maintains a clear boundary:

- **DMC-02 creates and refines the model.**
- **DMC-03 validates the model.**

## 17. Human Decision & Approval

DMC-03 validation findings may result in Agent recommendations, but the Agent does not have authority to accept its own findings as approved decisions.

Where human judgment is required:

```text
Agent Validation / Recommendation
             │
             ▼
       Human Review
             │
             ▼
       Human Decision
       ┌─────┼─────┬──────┐
       ▼     ▼     ▼      ▼
     Adopt Modify Reject  Defer
```

The Human Decision & Approval capability is cross-cutting across AGENTIC. The principle is:

> **Agent recommends. Human decides.**

Human decisions should be recorded and remain traceable to the validation finding and resulting model change.

## 18. Relationship with DMC-01

DMC-01 **Data Requirement Analysis** determines what information is required and what the concepts mean.

DMC-03 validates whether the Logical Data Model represents those requirements appropriately.

```text
DMC-01
Data Requirement Analysis
        │
        │ requirements
        ▼
DMC-02
Logical Data Modeling
        │
        │ logical model candidate
        ▼
DMC-03
Data Model Validation
```

DMC-03 may identify that an information requirement itself is ambiguous or incomplete. Such a finding should be traced back to DMC-01 rather than being silently resolved in the model.

## 19. Relationship with DMC-02

DMC-02 may perform preliminary validation while constructing the model.

This does not replace DMC-03.

| DMC-02 | DMC-03 |
|---|---|
| Construct the model | Validate the model |
| Identify obvious modeling problems during design | Perform formal validation |
| Refine entities, attributes, relationships and constraints | Produce authoritative validation findings |
| Internal design feedback | Independent validation perspective |
| Candidate model creation | Validation result |

DMC-02 may iterate based on its own preliminary checks. DMC-03 provides the formal validation checkpoint.

## 20. Relationship with DMC-04

DMC-03 validates whether required traceability exists and is correct.

DMC-04 is responsible for maintaining the traceability relationships as an ongoing capability.

Therefore:

- **DMC-03:** Is traceability sufficient and correct?
- **DMC-04:** Maintain and manage traceability.

## 21. Relationship with DMC-08

DMC-03 determines the validation status of the model.

DMC-08 Data Model Governance & Approval controls formal baseline, approval, versioning, and change governance.

```text
DMC-03
Validation
    │
    ▼
Validation Result
    │
    ▼
DMC-08
Governance & Approval
    │
    ▼
Authoritative Baseline
```

A model being technically validated does not automatically mean that it is formally approved.

## 22. Agentic Reasoning Requirements

The Agent should be able to:

- Determine applicable validation criteria.
- Select relevant requirements and business rules.
- Compare the logical model against requirements.
- Detect omissions.
- Detect semantic inconsistencies.
- Detect structural problems.
- Detect relationship inconsistencies.
- Detect traceability gaps.
- Identify contradictions between sources.
- Explain findings.
- Distinguish evidence from inference.
- Assess uncertainty.
- Recommend corrective actions.
- Track findings through resolution.
- Revalidate changed models.

The Agent must not:

- Silently change the logical model during validation.
- Treat an inference as a requirement.
- Suppress conflicting evidence.
- Mark an unresolved material issue as passed without justification.
- Treat its own recommendation as human approval.
- Convert a validation result into formal approval without the applicable governance process.

## 23. Outputs

DMC-03 produces:

1. **Validation Context**
2. **Validation Rules**
3. **Validation Findings**
4. **Traceability Validation Results**
5. **Model Quality Assessment**
6. **Validation Report**
7. **Validation Status**
8. **Recommended Corrective Actions**
9. **Open Questions and Uncertainties**
10. **Re-validation Results**, where applicable

## 24. Boundary Summary

```text
DMC-01 Data Requirement Analysis
    |
    | What information is required?
    | What does it mean?
    v
DMC-02 Logical Data Modeling
    |
    | How should the information be represented logically?
    v
DMC-03 Data Model Validation
    |
    | Is the model complete, correct, consistent,
    | traceable, and fit for purpose?
    v
DMC-04 Data Model Traceability
    |
    | How is traceability maintained?
    v
DMC-08 Data Model Governance & Approval
    |
    | How is the model formally approved,
    | baselined, versioned, and controlled?
```

## 25. Core Principle

> **DMC-03 does not design the data model. It provides evidence that the data model adequately represents the approved business information requirements and identifies where it does not.**

Validation is therefore a distinct capability from modeling, while remaining tightly connected through an iterative feedback loop.
