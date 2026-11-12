# AGENTIC Non-Functional Requirement Process
## Define Non-Functional Requirements

**Lifecycle Stage:** Non-Functional Requirement  
**Status:** Proposed Baseline

## 1. Purpose

Define and approve the target system's applicable quality characteristics and constraints as explicit, measurable Non-Functional Requirements (NFRs). The NFR lifecycle stage occurs **after Data Model and before System Architecture**, as fixed by the canonical AGENTIC Engineering Lifecycle.

NFRs are authoritative system-level requirements, consolidated in this stage so architecture, technology choices, development, and testing can use one approved source.

## 2. Inputs

- Approved User Stories and UI/UX outputs, where available
- Approved Data Model
- Project context, business requirements, regulations, policies, and constraints
- Applicable Platform Knowledge, standards, and quality patterns
- NFR candidates and references discovered during earlier lifecycle stages
- Common Glossary and Project Glossary

Quality needs may be discovered earlier, including during Activity, User Story, UI/UX, and Data Model work. Earlier stages may reference an NFR or record a candidate, but this stage owns its authoritative definition. Project-specific requirements and applicable regulations take precedence over generic guidance.

## 3. Process Flow

```text
Approved Data Model + relevant project context
          +
Earlier NFR references / candidates
          ↓
Agent consolidates applicable quality needs
          ↓
Quantify each NFR and define verification evidence
          ↓
User reviews / revises ↔ Agent refines
          ↓
User approves
          ↓
Approved NFR Set
          ↓
System Architecture
```

## 4. Activities

### NFR-01 Discover and Consolidate NFRs

**Performed by:** Agent

Review project requirements, constraints, Data Model, functional artifacts, and earlier NFR references. Identify applicable quality characteristics and consolidate duplicate or overlapping candidates. Consider relevant categories such as security, privacy, performance, availability, resilience, scalability, usability, accessibility, interoperability, maintainability, and auditability. Do not create requirements for categories that have no applicable need.

**Output:** Consolidated NFR Candidate Set

### NFR-02 Quantify and Define Verification

**Performed by:** Agent

For every candidate, state a measurable target, applicable conditions or scope, and how compliance will be verified. Define units, thresholds, measurement conditions, and evidence where relevant. Identify a source or label the requirement as an inference or proposal. If a target cannot yet be quantified, expose the missing decision rather than presenting a vague statement as an approved NFR.

**Output:** Measurable, verifiable Proposed NFR Set

### NFR-03 Review / Refine NFRs

**Performed by:** User + Agent

The User reviews applicability, targets, verification methods, source, and constraints. The User may accept, modify, add, or remove NFRs. The Agent incorporates decisions, resolves duplication, and refines the set. Repeat as needed.

**Output:** Refined NFR Set

### NFR-04 Approve NFRs

**Performed by:** User

The User explicitly approves the final NFR Set. Approval establishes the authoritative quality requirement baseline for System Architecture and downstream implementation and verification.

**Output:** Approved NFR Set

## 5. NFR Structure

| Element | Description |
|---|---|
| **ID / Name** | Stable identifier and concise requirement name |
| **Quality Characteristic** | Applicable quality category, such as performance or security |
| **Requirement** | Clear statement of required system behavior or constraint |
| **Measure / Target** | Quantified threshold, range, or other objective target, with units where applicable |
| **Conditions / Scope** | Operating conditions, workload, data volume, user population, environment, or scope under which the target applies |
| **Verification Method / Evidence** | Test, inspection, analysis, measurement, or other evidence that can demonstrate compliance |
| **Source / Rationale** | Project source, regulation, approved decision, or rationale; label inference or proposal explicitly |
| **Related Requirements** | Relevant User Stories, Data Model elements, or other NFRs, by reference |

Use only applicable fields and detail. A requirement is not ready for approval if it cannot be evaluated objectively or its unresolved assumptions are hidden.

## 6. Measurability and Verification

NFRs should describe a required level of quality under stated conditions, not merely name a quality attribute. Avoid statements such as “the system must be fast,” “highly secure,” or “always available” without an agreed target and means of verification.

Example:

```text
NFR: Application search response time
Requirement: Return search results within 2 seconds for 95% of requests.
Conditions: Up to 500 concurrent users and the agreed representative data volume.
Verification: Load test; record latency distribution and test conditions.
Source: User-approved service target.
```

Numbers in examples are illustrative only and do not become project requirements without User approval. When targets depend on a decision or unavailable context, identify that dependency for review.

## 7. Earlier Discovery and Authoritative Ownership

An NFR may be discovered before this lifecycle stage. Capture the need in context and link or refer to it from the relevant Activity, User Story, UI/UX, or Data Model artifact. Do not copy a full authoritative NFR definition into those artifacts.

```text
Earlier lifecycle stage: discover and reference candidate
          ↓
NFR stage: consolidate, quantify, verify, and approve definition
          ↓
System Architecture: use approved NFR baseline
```

If a candidate is not yet approved, clearly mark it as proposed or unresolved. The NFR stage reconciles candidates and records the single authoritative approved definition.

## 8. Iteration and Clarification

Review and refinement form a repeatable loop, with no predetermined number of rounds. Ask for clarification when an unknown target, condition, source, or verification method materially prevents a measurable and implementable requirement. Otherwise proceed with a clearly labeled proposal for User review.

## 9. Core Principle

> **NFRs are discovered throughout engineering, then consolidated, quantified, made verifiable, and approved in the dedicated NFR lifecycle stage after Data Model and before System Architecture. The User remains the approval authority.**
