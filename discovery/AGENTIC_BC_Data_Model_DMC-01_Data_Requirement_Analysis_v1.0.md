# DMC-01 Data Requirement Analysis

## 1. Capability Definition

**Capability ID:** DMC-01  
**Capability Name:** Data Requirement Analysis

### Purpose

Enable AGENTIC to determine what information the solution needs to understand, capture, store, reference, produce, or explain based on approved upstream engineering artifacts.

The capability identifies and classifies meaningful entities and information concepts before determining how they should be represented in the Logical Data Model.

> **DMC-01 answers: “What information do we need?”**
>
> **DMC-02 answers: “How should that information be logically structured?”**

## 2. Comprehensive Entity and Information Discovery

DMC-01 shall not equate an entity only with a conventional business object such as Customer, Account, or Product.

The Agent shall systematically identify and classify every meaningful entity or information concept required to describe, execute, record, reference, or explain the business process.

Discovery shall cover, at minimum:

| Entity / Information Category | Examples | Typical Purpose |
|---|---|---|
| **Person** | Customer, Employee, Applicant | Represents an individual |
| **Role** | Approver, Reviewer, Officer, Administrator | Represents a business responsibility or participation |
| **Organization** | Company, Branch, Agency, Department | Represents an organizational actor |
| **Location** | Office, Branch Location, Address, Region | Represents where something occurs or is associated |
| **Physical Object** | Device, Document, Vehicle, Asset | Represents a tangible object |
| **Digital Object** | File, Report, Application, Dataset | Represents a digital artifact |
| **Business Object** | Account, Policy, Contract, Application | Represents a persistent business concept |
| **Reference / Classification** | Status, Type, Category, Code | Provides controlled classification |
| **Abstract Concept** | Eligibility, Risk, Entitlement, Capability | Represents a conceptual business notion |
| **Business Event** | Registration, Submission, Approval, Payment, Claim | Represents something that happens |
| **Business Transaction** | Order, Payment, Transfer, Submission | Represents a business interaction or transaction |
| **Relationship / Association** | Employment, Ownership, Membership | Represents a meaningful association |
| **Time / Period** | Reporting Period, Effective Period, Fiscal Year | Represents temporal context |
| **Rule / Policy Concept** | Eligibility Rule, Validation Rule | Represents governing business logic where explicit representation is needed |
| **Measurement / Observation** | Amount, Score, Rate, Quantity | Represents measurable business information |

These are **semantic discovery categories**, not predetermined database entity types.

The Agent shall determine later whether a discovered concept should be represented as an entity, attribute, relationship, event, reference data concept, derived information, or another logical construct.

## 3. Discovery Principle

The Agent shall not use a simplistic:

> **Every noun = Entity**

approach.

Instead, it shall understand the business context and determine the semantic role of each concept.

For example:

```text
Officer approves application
```

may involve:

- Officer → Person / Role
- Application → Business Object
- Approval → Business Event
- Approval Date → Time
- Approval Decision → Classification / Value
- Approval Reason → Information
- Organization → Actor / Context

This prevents business events, roles, locations, relationships, and abstract concepts from being incorrectly buried as ordinary attributes.

## 4. Discovery Lens

The Agent should examine the business context through multiple complementary perspectives:

```text
                         INFORMATION / ENTITY DISCOVERY
                                      │
        ┌───────────────┬─────────────┼──────────────┬───────────────┐
        ▼               ▼             ▼              ▼               ▼
      WHO             WHERE         WHAT            WHEN            WHY / HOW
        │               │             │              │               │
        ▼               ▼             ▼              ▼               ▼
 Person / Role       Location      Object /       Event /         Rule /
 Organization                       Concept       Period          Policy
                                      │
                                      ▼
                              Business Transaction
                                      │
                                      ▼
                                Relationships
```

The Agent should ask:

- **Who** participates?
- **Where** does something exist or occur?
- **What** exists, is used, or is produced?
- **When** does something occur or become effective?
- **Why / How** is something governed, decided, measured, or performed?

## 5. Inputs

DMC-01 analyzes:

- Approved User Stories
- Attribute-level Information Requirements
- Business Rules
- UI/UX information requirements
- Activity-level entity requirements
- Project Knowledge
- Common Glossary
- Project Glossary
- Other approved upstream engineering artifacts relevant to information requirements

## 6. Agent Capabilities

### 6.1 Extract Information Requirements

Identify information that is:

- Entered
- Captured
- Displayed
- Selected
- Referenced
- Calculated
- Produced
- Validated
- Used in decisions
- Used to execute a business activity

### 6.2 Discover Entities and Information Concepts

Identify meaningful concepts across the complete semantic taxonomy defined in Section 2.

### 6.3 Consolidate Information Requirements

Detect when different User Stories, Activities, or UI/UX elements refer to the same conceptual information.

The Agent should avoid creating duplicate concepts without justification.

### 6.4 Classify Information

The Agent should classify discovered concepts into appropriate semantic categories and distinguish between business concepts and their potential logical representations.

### 6.5 Analyze Semantics

The Agent should:

- Determine the business meaning of each concept.
- Use the Common and Project Glossary.
- Detect potentially conflicting definitions.
- Identify terminology variations.
- Identify concepts that appear equivalent but may have different meanings.

### 6.6 Identify Information Dependencies

Determine:

- Which information depends on other information.
- Which information is required before another concept can exist.
- Which information is derived from other information.
- Which concepts participate in business events or transactions.

### 6.7 Detect Gaps and Ambiguity

Identify:

- Missing information definitions
- Undefined terminology
- Conflicting requirements
- Information referenced but never defined
- Information collected without an apparent business purpose
- Concepts whose semantic classification is uncertain
- Missing context needed to determine meaning

### 6.8 Maintain Provenance

Every identified concept or information requirement should maintain traceability to its source.

Possible sources include:

- User Story
- Activity
- Business Rule
- UI/UX Design
- Project Knowledge
- Glossary
- Other approved engineering artifact

## 7. Concept Analysis Structure

For each discovered concept, DMC-01 should capture:

| Field | Description |
|---|---|
| **Concept** | Name of the discovered concept |
| **Definition** | Business meaning |
| **Semantic Category** | Person, Role, Location, Event, Object, Abstract Concept, etc. |
| **Business Meaning** | Why the concept matters |
| **Source / Provenance** | Upstream artifact and reference |
| **Used By** | Activities, User Stories, Roles, or UI/UX elements using it |
| **Purpose** | Why the information is needed |
| **Dependencies** | Related prerequisite or dependent concepts |
| **Related Concepts** | Semantically related concepts |
| **Potential Logical Representation** | Candidate representation for DMC-02 |
| **Confidence** | Agent confidence in the analysis |
| **Open Questions** | Issues requiring clarification or User decision |

The **Potential Logical Representation** is deliberately not authoritative at this stage. It is an input to DMC-02.

## 8. Semantic Classification

After discovering concepts, the Agent should classify each concept into an appropriate logical direction:

```text
Discovered Concept
       │
       ▼
Semantic Classification
       │
       ├── Entity
       ├── Attribute
       ├── Relationship
       ├── Event
       ├── Reference Data
       ├── Derived Information
       └── Other / Requires Decision
```

Classification is an analytical result, not an automatic modeling decision.

## 9. Agentic Reasoning Rules

The Agent shall distinguish between:

```text
Requirement
Existing Practice
Best Practice
Agent Inference
Unknown / Ambiguous
```

If the Agent infers that two concepts should be combined, separated, renamed, or reclassified, it shall make the reasoning visible.

The Agent shall not silently convert an inference into an approved requirement.

Where ambiguity materially affects the resulting model, the Agent shall surface the issue for User decision.

## 10. Output

The primary output is:

**Data Requirement Analysis**

It should provide:

1. Comprehensive discovered concepts
2. Semantic classification
3. Business definitions
4. Information usage
5. Dependencies
6. Provenance and traceability
7. Gaps and ambiguities
8. Candidate logical representations
9. Confidence
10. Open questions and decisions required

The output becomes an input to:

**DMC-02 Logical Data Modeling**

## 11. Boundary with DMC-02

The boundary must remain explicit:

```text
DMC-01
What information do we need?
          │
          ▼
Data Requirement Analysis
          │
          ▼
DMC-02
How should that information be logically structured?
          │
          ▼
Logical Data Model
```

DMC-01 discovers and analyzes the business information landscape.

DMC-02 decides how the approved information requirements should be structured into the Logical Data Model.

## 12. Example

Input:

> “The Officer approves the participant application at the regional office.”

DMC-01 should identify at least:

| Concept | Category |
|---|---|
| Officer | Person / Role |
| Participant | Person / Business Object |
| Application | Business Object |
| Approval | Business Event |
| Regional Office | Organization / Location |
| Approval Date | Time |
| Approval Decision | Classification |
| Approval Reason | Information |

DMC-01 does not yet decide whether `Approval` becomes an entity, event structure, relationship, or another logical construct.

That decision belongs to DMC-02.

## 13. Core Principle

> **DMC-01 comprehensively discovers and analyzes the information landscape of the solution. It identifies persons, roles, organizations, locations, physical and digital objects, business objects, abstract concepts, events, transactions, relationships, time, rules, measurements, and other meaningful information concepts. It preserves provenance and uncertainty, and provides the semantic foundation from which DMC-02 derives the Logical Data Model.**
