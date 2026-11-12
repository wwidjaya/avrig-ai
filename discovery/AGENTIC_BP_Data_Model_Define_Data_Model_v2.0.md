# AGENTIC Data Model Business Process v2

## 1. Purpose

Define the agentic business process for transforming approved upstream requirements and information requirements into an approved, technology-independent Logical Data Model.

The process preserves the established authority model:

- AGENTIC structured logical data-model specification is authoritative.
- Azimutt is the ERD modeling and visualization interface.
- The User remains the final authority.
- Physical database design is deferred to downstream System Architecture and Technology Architecture stages.

## 2. Process

```text
DM-01  Analyze Data Requirements
          ↓
DM-02  Discover & Propose Logical Model
          ↓
DM-03  Validate Model & Traceability
          ↓
DM-04  Generate / Synchronize Azimutt ERD
          ↓
DM-05  Impact & Change Analysis
          ↓
DM-06  User Review & Refinement
          ↕
       Agent Revision
          ↓
DM-07  User Approval
```

The process may iterate between User Review & Refinement and Agent Revision until the User is satisfied.

## 3. Activities

### DM-01 Analyze Data Requirements

The Agent analyzes:

- Approved User Stories
- Attribute-level Information Requirements
- Business Rules
- UI/UX information requirements
- Activity-level entity requirements
- Project Knowledge
- Common and Project Glossary

**Output:** Data Requirement Analysis

### DM-02 Discover & Propose Logical Model

The Agent proposes:

- Entities
- Entity definitions
- Attributes
- Logical data types
- Identifiers
- Relationships
- Cardinality
- Optionality
- Business constraints

**Output:** Draft Structured Logical Data Model

The model remains technology-independent.

### DM-03 Validate Model & Traceability

The Agent validates the proposed model against upstream requirements.

```text
User Story
    ↓
Information Requirement
    ↓
Entity
    ↓
Attribute
    ↓
Relationship / Constraint
```

The Agent checks for:

- Missing data representation
- Unsupported entities
- Unsupported attributes
- Missing identifiers
- Missing relationships
- Contradictory requirements
- Duplicate concepts
- Inconsistent terminology
- Unresolved assumptions

**Output:** Model Validation & Traceability Report

### DM-04 Generate / Synchronize Azimutt ERD

The structured model is transformed into the Azimutt representation.

```text
Structured Model
       ↓
   Synchronization
       ↓
     Azimutt
       ↓
      ERD
```

Azimutt provides the visual modeling and review experience. The AGENTIC structured model remains authoritative.

### DM-05 Impact & Change Analysis

The Agent analyzes the consequences of model changes.

```text
Data Model Change
       ↓
What requirements are affected?
       ↓
What User Stories are affected?
       ↓
What UI/UX is affected?
       ↓
What Activities are affected?
       ↓
What downstream engineering artifacts
may be affected?
```

**Output:** Model Impact Analysis

### DM-06 User Review & Refinement

The User reviews:

- Model structure
- Entity semantics
- Attributes
- Relationships
- Cardinality
- Constraints
- Traceability
- Impact analysis

The User may modify the model directly or instruct the Agent to revise it.

```text
User Change
    ↓
Agent analyzes
    ↓
Agent updates structured model
    ↓
Agent validates
    ↓
Azimutt updated
```

The loop continues until the User is satisfied.

### DM-07 User Approval

The User explicitly approves the Logical Data Model.

**Approved Logical Data Model Baseline**

The approved baseline becomes the authoritative input for downstream engineering stages.

## 4. Activity Summary

| Activity | Purpose | Primary Output |
|---|---|---|
| DM-01 | Understand what data is required | Data Requirement Analysis |
| DM-02 | Design the logical model | Draft Structured Logical Data Model |
| DM-03 | Prove the model is consistent and traceable | Model Validation & Traceability Report |
| DM-04 | Make the model visually usable | Azimutt ERD |
| DM-05 | Understand consequences of changes | Model Impact Analysis |
| DM-06 | Enable human-agent collaboration | Refined Logical Data Model |
| DM-07 | Establish authoritative baseline | Approved Logical Data Model |

## 5. Agentic Design Pattern

> **Understand → Propose → Validate → Visualize → Analyze Impact → Collaborate → Approve**

The Agent does not merely generate diagrams. It reasons about requirements, maintains traceability, identifies inconsistencies, analyzes change impact, supports User refinement, and prepares the model for explicit User approval.

## 6. Authority Model

1. AGENTIC proposes the logical data model.
2. The User reviews and refines it.
3. Azimutt provides the visual modeling and review experience.
4. AGENTIC validates consistency and traceability.
5. The User explicitly approves the model.
6. The approved model becomes the baseline for downstream engineering.

The User remains the final authority.

## 7. Scope Boundary

### Included

- Logical entities
- Entity semantics
- Logical attributes
- Logical data types
- Identifiers
- Relationships
- Cardinality
- Optionality
- Business-level constraints
- Requirement traceability
- Model validation
- Change and impact analysis
- ERD visualization
- User review and approval

### Excluded

- Physical database schema design
- Vendor-specific database features
- Index design
- Partitioning
- Storage layout
- Database deployment
- Database migration implementation

These concerns belong to downstream architecture and technology stages.

## 8. Core Principle

> **AGENTIC transforms approved requirements into a validated, traceable, technology-independent Logical Data Model. The structured specification is authoritative, Azimutt provides the visual representation and modeling interface, the Agent continuously validates and analyzes impact, and the User remains the final authority.**
