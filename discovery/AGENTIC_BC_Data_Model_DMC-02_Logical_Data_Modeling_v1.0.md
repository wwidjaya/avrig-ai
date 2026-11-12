# DMC-02 Logical Data Modeling

## 1. Capability Definition

**Capability ID:** DMC-02  
**Capability Name:** Logical Data Modeling

### Purpose

Enable AGENTIC to transform the approved Data Requirement Analysis from DMC-01 into a coherent, technology-independent Logical Data Model.

The capability determines how identified information concepts should be logically structured while preserving their business meaning, relationships, constraints, and traceability to upstream requirements.

> **DMC-01 answers: “What information do we need?”**
>
> **DMC-02 answers: “How should that information be logically structured?”**

## 2. Scope

DMC-02 covers the logical structure of information, including:

- Entity definition
- Attribute definition
- Relationship definition
- Identifier and key definition
- Cardinality and optionality
- Constraint definition
- Logical model structuring

DMC-02 is technology-independent.

It shall not determine physical database implementation such as database platform, physical table implementation, physical data types, index implementation, partitioning, sharding, storage engine, replication implementation, or physical performance optimization.

These decisions belong to downstream architecture and technology stages.

## 3. Inputs

DMC-02 uses:

- Approved Data Requirement Analysis from DMC-01
- Approved User Stories
- Attribute-level Information Requirements
- Business Rules
- Activity-level information requirements
- Approved UI/UX information requirements
- Common Glossary
- Project Glossary
- Project Knowledge
- Relevant approved engineering artifacts
- Existing Logical Data Model, where applicable

## 4. Business Process

```text
DMC-01
Data Requirement Analysis
        │
        ▼
DM-02.1 Understand Modeling Requirements
        │
        ▼
DM-02.2 Design Logical Model
        │
        ▼
DM-02.3 Validate Logical Model
        │
        ▼
DM-02.4 Visualize / Synchronize ERD
        │
        ▼
DM-02.5 User Review & Refinement
        ↕
   Agent Revision
        │
        ▼
DM-02.6 Produce Logical Model Candidate
```

The process may iterate whenever review, validation, or impact analysis identifies a need for refinement.

## 5. DM-02.1 Understand Modeling Requirements

The Agent analyzes the approved Data Requirement Analysis and determines the modeling implications.

The Agent shall:

- Review all discovered information concepts.
- Review their semantic classifications.
- Review definitions and business meanings.
- Review provenance and source requirements.
- Identify dependencies between concepts.
- Identify concepts requiring logical representation.
- Identify potential duplicates.
- Identify unresolved ambiguities.
- Identify concepts requiring User decisions.
- Confirm consistency with the Common and Project Glossary.

The Agent shall not silently convert unresolved assumptions into approved model decisions.

### Output

**Logical Modeling Input Analysis**

## 6. DM-02.2 Design Logical Model

The Agent transforms the analyzed information requirements into a proposed Logical Data Model.

### 6.1 Entity Definition

The Agent determines which concepts should be represented as logical entities.

For each proposed entity, establish:

- Entity name
- Business definition
- Purpose
- Source concepts
- Source requirements
- Candidate identifiers
- Related entities
- Business rules
- Confidence
- Open questions

### 6.2 Attribute Definition

For each logical entity, identify the attributes required to describe the entity.

Each attribute should have:

- Name
- Definition
- Business meaning
- Parent entity
- Requirement source
- Required / optional status
- Business rule references
- Candidate logical representation
- Confidence

Attributes must not be invented without business justification or traceable inference.

### 6.3 Relationship Definition

Identify meaningful relationships between logical entities.

For each relationship, establish:

- Relationship name
- Participating entities
- Business meaning
- Relationship direction where relevant
- Cardinality
- Optionality
- Source requirement
- Business rules
- Confidence
- Open questions

Relationships should represent meaningful business semantics rather than merely physical database implementation.

### 6.4 Identifier and Key Definition

Identify candidate identifiers and logical keys, including:

- Business identifiers
- Candidate primary identifiers
- Candidate alternate identifiers
- Composite identifiers where justified
- Identifier uniqueness requirements
- Identifier business meaning

The Agent should distinguish business identity from implementation-specific surrogate keys.

### 6.5 Cardinality and Optionality

Determine how many instances of one concept may relate to another and whether participation is mandatory or optional.

Examples include:

```text
One-to-One
One-to-Many
Many-to-Many
Mandatory
Optional
```

Cardinality and optionality must be supported by business requirements, rules, or explicit modeling rationale.

### 6.6 Constraint Definition

Identify logical constraints required to preserve business integrity, including:

- Uniqueness
- Mandatory information
- Valid value restrictions
- Relationship constraints
- Conditional requirements
- Business rule constraints
- Referential integrity requirements

Constraints remain logical and technology-independent.

## 7. Logical Modeling Principles

### 7.1 Business Meaning First

The model shall represent business meaning before considering database implementation.

### 7.2 No Premature Physical Design

The Agent shall not introduce physical database decisions into the Logical Data Model.

### 7.3 Traceable Modeling

Every significant model element should be traceable to an upstream requirement, business concept, rule, or explicitly documented modeling rationale.

### 7.4 Avoid Unjustified Duplication

The Agent should detect and challenge duplicate entities, attributes, and relationships.

### 7.5 Preserve Semantic Distinction

Concepts that appear similar should not automatically be merged when their business meanings differ.

Conversely, concepts that use different terminology should be considered for consolidation when they represent the same business concept.

### 7.6 Explicit Inference

When a model element is inferred rather than directly specified, the Agent shall identify the inference and its rationale.

## 8. DM-02.3 Validate Logical Model

The Agent performs an initial logical-model validation before presenting the model for User review.

Validation should include:

### Completeness

- All relevant approved information concepts are represented.
- Required attributes are represented.
- Required relationships are represented.

### Consistency

- Naming is consistent.
- Definitions are consistent.
- Relationships do not contradict business meaning.
- Cardinality is consistent with requirements.
- Constraints are consistent with business rules.

### Structural Integrity

- Entities have meaningful identity where required.
- Relationships have valid participating entities.
- Attributes belong to appropriate entities.
- No obvious orphan concepts remain.
- Many-to-many relationships are explicitly understood.

### Traceability

- Model elements can be traced to requirements or modeling rationale.
- Untraced elements are flagged.

### Ambiguity

- Unresolved modeling decisions are identified.
- Conflicting requirements are surfaced.
- User decisions required for material issues are identified.

The output is:

**Logical Model Validation Findings**

## 9. DM-02.4 Visualize / Synchronize ERD

AGENTIC shall generate or synchronize a visual ERD representation from the authoritative structured Logical Data Model.

The selected ERD tool is **Azimutt**.

The authority relationship is:

```text
AGENTIC Structured Logical Model
             │
             │ authoritative
             ▼
          Azimutt
             │
             ▼
       Visual ER Diagram
```

Azimutt provides visualization and modeling support, but does not become the authoritative definition of the Logical Data Model.

The synchronization process shall preserve entities, attributes, relationships, keys, cardinality, relevant constraints, definitions where supported, and traceability metadata where supported.

Any discrepancy between the structured model and ERD representation shall be detected and surfaced.

## 10. DM-02.5 User Review & Refinement

The User reviews the proposed Logical Data Model.

The Agent should present:

- Model overview
- Entities
- Attributes
- Relationships
- Keys
- Cardinality
- Constraints
- Traceability
- Validation findings
- Modeling assumptions
- Open questions
- Alternatives where material choices exist

The User may:

- Accept
- Modify
- Reject
- Request clarification
- Request alternative modeling options

The Agent incorporates the User's direction and regenerates affected model elements.

The review process may iterate:

```text
Agent Proposal
      ↓
User Review
      ↓
User Feedback
      ↓
Agent Revision
      ↓
Validation
      ↺
```

The Agent shall not treat an unapproved model as the authoritative Logical Data Model.

## 11. DM-02.6 Produce Logical Model Candidate

After refinement, the Agent produces the Logical Model Candidate.

The candidate should include:

1. Logical entities
2. Entity definitions
3. Attributes
4. Attribute definitions
5. Relationships
6. Cardinality
7. Optionality
8. Identifiers and keys
9. Logical constraints
10. Business rules affecting the model
11. Traceability
12. Modeling assumptions
13. Open issues
14. Validation findings
15. ERD representation

The candidate becomes the input to **DMC-03 Data Model Validation**.

## 12. Agentic Reasoning

The Agent shall distinguish:

```text
Requirement
Existing Practice
Best Practice
Agent Inference
Unknown / Ambiguous
```

For every significant modeling decision, the Agent should be able to explain:

- What requirement or concept triggered the decision.
- Why the selected structure is appropriate.
- What alternatives were considered.
- What assumptions were made.
- What uncertainty remains.

The Agent shall not silently replace an approved business requirement with a preferred modeling pattern.

## 13. Example

DMC-01 identifies:

```text
Officer
Participant
Application
Approval
Regional Office
Approval Date
Approval Decision
Approval Reason
```

DMC-02 may logically structure these as:

```text
Officer
   │
   │ performs
   ▼
Approval Event
   │
   ├── applies to → Application
   ├── performed at → Regional Office
   ├── performed by → Officer
   ├── occurs at → Approval Date
   ├── has decision → Approval Decision
   └── has reason → Approval Reason

Application
   │
   └── belongs to → Participant
```

The exact representation remains subject to business semantics and User review.

The Agent must not assume that every business event automatically becomes a persistent entity. The appropriate representation is determined through logical modeling analysis.

## 14. Outputs

Primary output:

**Logical Model Candidate**

Supporting outputs:

- Logical Model Input Analysis
- Logical Entity Definitions
- Attribute Definitions
- Relationship Definitions
- Identifier and Key Definitions
- Cardinality and Optionality Definitions
- Logical Constraints
- Validation Findings
- Modeling Decisions and Rationale
- Traceability
- ERD Representation
- Open Questions

## 15. Boundary with Adjacent Capabilities

```text
DMC-01
Data Requirement Analysis
        │
        ▼
DMC-02
Logical Data Modeling
        │
        ▼
DMC-03
Data Model Validation
```

### DMC-01

Determines:

> What information do we need?

### DMC-02

Determines:

> How should that information be logically structured?

### DMC-03

Determines:

> Is the resulting model complete, consistent, correct, and fit for its intended purpose?

DMC-02 may perform preliminary validation to improve the model, but authoritative model validation belongs to DMC-03.

## 16. Core Principle

> **DMC-02 transforms approved information requirements into a coherent, technology-independent Logical Data Model. It defines entities, attributes, relationships, identifiers, cardinality, optionality, and logical constraints while preserving business meaning, provenance, and traceability. The structured AGENTIC Logical Data Model remains authoritative, while Azimutt provides the visual ERD representation.**
