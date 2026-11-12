# AGENTIC Lifecycle Decision: Deployment as an Optional Stage

## Status

**Approved**

Deployment is an **optional lifecycle stage** in the AGENTIC Canonical Engineering Lifecycle.

The existing Deploy domain and its DPC-01 through DPC-10 capability structures remain approved and frozen. This decision changes the lifecycle cardinality of Deployment, not the internal structure of the Deploy domain.

## 1. Canonical Engineering Lifecycle

```text
PROJECT
   ↓
VISION
   ↓
MISSION
   ↓
STRATEGY
   ↓
BUSINESS CAPABILITY
   ↓
BUSINESS PROCESS
   ↓
ACTIVITY
   ↓
ROLE
   ↓
USER STORY
   ↓
UI/UX DESIGN
   ↓
DATA MODEL
   ↓
NON-FUNCTIONAL REQUIREMENT
   ↓
SYSTEM ARCHITECTURE
   ↓
TECHNOLOGY ARCHITECTURE
   ↓
DEVELOPMENT
   ↓
TEST
   ↓
┌─────────────────────────────┐
│       DEPLOYMENT            │
│          OPTIONAL           │
└─────────────────────────────┘
   ↓
OPERATIONAL SYSTEM
```

Deployment is not mandatory for every AGENTIC engineering project.

## 2. Lifecycle Semantics

> **Development → Test is the engineering completion path.**

> **Test → Deploy is an optional transition depending on project scope and deployment responsibility.**

The Test stage establishes an approved **Test Baseline**. From there, the project may either complete engineering delivery or proceed to Deployment when AGENTIC is responsible for establishing the operational system state.

```text
                         ┌──→ DEPLOY → OPERATIONAL SYSTEM
                         │
TEST BASELINE ───────────┤
                         │
                         └──→ HANDOFF / RELEASE ARTIFACT
```

## 3. Why Deployment Is Optional

AGENTIC may be used for:

- Software development where AGENTIC also performs deployment
- Development projects where deployment is performed by another platform or team
- Library or component development
- Prototype development
- SDK or package development
- Source-code delivery
- CI/CD pipelines external to AGENTIC
- Systems where deployment is governed outside AGENTIC
- Architecture or engineering work that does not result in immediate deployment

Therefore, forcing Deployment into every project would incorrectly constrain the platform's applicability.

## 4. Lifecycle Completion States

The lifecycle supports two valid paths after Test:

```text
TEST
  ↓
TEST BASELINE
  │
  ├──→ ENGINEERING COMPLETE
  │
  └──→ DEPLOY
          ↓
      DEPLOYMENT BASELINE
          ↓
      OPERATIONAL SYSTEM
```

### Engineering Complete

The project may be considered engineering-complete when the approved Test Baseline is established and no AGENTIC deployment is required.

### Operationalized

When Deployment is required and performed through AGENTIC, the project proceeds through the Deploy domain and establishes an authorized Deployment Baseline representing the operational system state.

## 5. Deployment Cardinality

Deployment has the following lifecycle cardinality:

> **Deploy = 0..1 occurrence in the lifecycle**

rather than:

> **Deploy = 1..1 occurrence in the lifecycle**

This means:

- `0` = Deployment is not required or is handled outside AGENTIC.
- `1` = Deployment is performed through the AGENTIC Deploy domain.

The Deploy domain itself remains fully defined when selected.

## 6. Deploy Domain Remains Authoritative

The approved Deploy capabilities remain:

| ID | Capability |
|---|---|
| **DPC-01** | Deployment Requirement Analysis |
| **DPC-02** | Deployment Planning & Design |
| **DPC-03** | Release & Deployment Package Preparation |
| **DPC-04** | Deployment Environment & Configuration Preparation |
| **DPC-05** | Deployment Execution & Automation |
| **DPC-06** | Deployment Validation & Evidence Analysis |
| **DPC-07** | Deployment Traceability |
| **DPC-08** | Deployment Impact Analysis |
| **DPC-09** | Deployment Collaboration |
| **DPC-10** | Deployment Governance & Approval |

These capabilities apply whenever the Deployment stage is selected.

## 7. Definition of Deployment

The canonical definition is:

> **Deployment is an optional lifecycle stage performed when the project requires AGENTIC to establish an authorized operational system state.**

Deployment therefore transforms an approved engineering/test state into an authorized operational state.

```text
TEST BASELINE
      ↓
DEPLOYMENT
      ↓
DEPLOYMENT BASELINE
      ↓
OPERATIONAL SYSTEM
```

## 8. Relationship to Test

```text
TEST
    │
    │ "Does the system satisfy the approved
    │ requirements and quality objectives?"
    ▼
TEST BASELINE
    │
    │ Optional transition
    ▼
DEPLOY
    │
    │ "Can the approved release be established
    │ as an authorized operational state?"
    ▼
DEPLOYMENT BASELINE
```

Test establishes evidence that the system is sufficiently verified and validated.

Deploy establishes the authorized operational system state.

## 9. Relationship to Handoff

When Deployment is not performed by AGENTIC, the project may produce an engineering delivery or release artifact for another party or platform.

```text
TEST BASELINE
      ↓
ENGINEERING DELIVERY
      ↓
External Deployment Responsibility
```

AGENTIC should preserve the distinction between:

- **Engineering completion**
- **Release/package delivery**
- **Deployment**
- **Operationalization**

A project should not be considered deployed merely because a release package exists.

## 10. Architectural Principle

> **AGENTIC should support engineering delivery independently from operational deployment, while providing a complete Deploy domain when operationalization is within scope.**

This allows the platform to serve both:

1. **Engineering-centric projects**, where the output is an approved engineering baseline or release artifact.
2. **End-to-end engineering projects**, where AGENTIC continues through deployment and establishes the operational system.

## 11. Final Decision

The AGENTIC Canonical Engineering Lifecycle therefore recognizes:

- **Test** as the final mandatory engineering stage.
- **Deploy** as an optional operationalization stage.
- **Deployment Baseline** as the authoritative output when Deploy is performed.
- **Operational System** as the resulting state when deployment is successfully authorized.
- External deployment as a valid path when deployment responsibility lies outside AGENTIC.

### Canonical Principle

> **Deployment is optional. Engineering completion does not require deployment, but when AGENTIC is responsible for operationalization, Deployment provides the governed path from Test Baseline to an authorized Operational System state.**
