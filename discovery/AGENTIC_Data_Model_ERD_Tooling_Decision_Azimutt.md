# AGENTIC Data Model ERD Tooling Decision

## 1. Decision

**ERD Tool: Azimutt**

Azimutt is selected as the ERD modeling and visualization tool for the AGENTIC Data Model stage.

The modeling scope remains the **Logical Data Model**.

The **AGENTIC structured logical data-model specification remains the authoritative representation**. Azimutt provides the visual ERD representation and modeling interface.

## 2. Tooling Principle

AGENTIC should maintain a clear separation between the authoritative engineering model and its visual representation.

- **AGENTIC structured model:** authoritative source of truth
- **Azimutt ERD:** visual representation and modeling/review interface
- **Physical database design:** deferred to downstream System Architecture and Technology Architecture stages

This prevents the ERD tool from becoming the authoritative source of business semantics and traceability.

## 3. Data Model Flow

```text
Approved User Stories
        │
        ▼
Activity / Information Requirements
        │
        ▼
AGENTIC Agent
        │
        │ proposes
        ▼
Structured Logical Data Model
        │
        │ authoritative
        ▼
Azimutt ERD
        │
        ▼
Visual Review
        │
        ▼
User Review / Refinement
        │
        └──────────────► Agent revises model
        │
        ▼
User Approval
        │
        ▼
Approved Logical Data Model
```

## 4. Separation of Concerns

| Concern | AGENTIC | Azimutt |
|---|---|---|
| Entity definitions | **Authoritative** | Visual |
| Attribute definitions | **Authoritative** | Visual |
| Relationships | **Authoritative** | Visual |
| Cardinality | **Authoritative** | Visual |
| Business constraints | **Authoritative** | Supporting |
| Traceability | **Authoritative** | No |
| Agent reasoning | **Yes** | No |
| User visual modeling | Supporting | **Yes** |
| ERD visualization | Generated/managed | **Yes** |
| Physical DB design | Later stage | Not the focus |
| Versioned engineering artifact | **Yes** | Supporting |

## 5. Proposed Model Synchronization Capability

Because AGENTIC is an agentic engineering platform, the Data Model stage should eventually include an explicit **Model Synchronization capability**.

Conceptually:

```text
AGENTIC Structured Model
          ↕
     Azimutt Model
          ↕
     ERD Visualization
```

The agent should be able to detect and reconcile changes such as:

- Entity added or removed
- Attribute added, removed, or changed
- Relationship changed
- Cardinality changed
- Naming inconsistency
- Orphan entities
- Missing identifiers
- Requirements without data representation
- Data elements without upstream justification

This becomes particularly valuable when a User edits the ERD manually.

## 6. Authority Model

The authority relationship should remain explicit:

1. AGENTIC proposes the logical data model.
2. The User reviews and refines it.
3. Azimutt provides the visual modeling and review experience.
4. AGENTIC validates consistency and traceability.
5. The User explicitly approves the model.
6. The approved model becomes the baseline for downstream engineering.

The User remains the final authority.

## 7. Final Decision Statement

**Azimutt is the selected ERD modeling and visualization tool for the AGENTIC Data Model stage. The AGENTIC structured logical data-model specification remains authoritative, while Azimutt provides the visual modeling and review interface.**

This supports the AGENTIC design principle:

> **Simple process, rich context, intelligent agent, User remains the final authority.**
