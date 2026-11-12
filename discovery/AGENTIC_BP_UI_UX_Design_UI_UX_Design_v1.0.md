# AGENTIC UI/UX Design Process
## Define UI/UX Design

**Lifecycle Stage:** UI/UX Design  
**Status:** Proposed Baseline  
**Version:** 1.0

## 1. Purpose

Transform approved User Stories into a coherent UI/UX design and a **runnable frontend prototype** that the User can inspect, navigate, and evaluate.

The design preserves approved User Stories, Roles, attribute-level Information Requirements, Business Rules, and Acceptance Criteria. The Agent proposes the UI/UX approach, frontend stack, and design system with rationales and trade-offs. The User confirms the approach before implementation and remains the approval authority.

## 2. Inputs

- Approved User Story Set, including chronological Capability / Action
- Approved Role Set and relevant Role-to-Activity mapping
- Attribute-level Information Requirements
- Business Rules and Acceptance Criteria
- Applicable NFR references or constraints already identified
- Project context, existing systems, project standards, and Project Knowledge
- Platform Knowledge, reusable UI patterns, and applicable design guidance
- Common Glossary and Project Glossary

Project-specific authoritative requirements and approved standards take precedence over generic recommendations. The Agent identifies conflicts and material gaps for User decision.

## 3. Process Flow

```text
Approved User Stories + Roles + Project Context
                     ↓
UX-01 Agent proposes UI/UX approach with rationales
                     ↓
UX-02 User confirms or requests revisions
                     ↓
UX-03 Agent generates UI/UX Design specification
                     ↓
UX-04 Agent generates runnable frontend prototype
                     ↓
UX-05 Agent runs and validates prototype
                     ↓
UX-06 User reviews / refines ↔ Agent iterates
                     ↓
UX-07 User approves UI/UX Design
                     ↓
Approved UI/UX Design Package
```

Review and refinement may repeat as needed. If refinement materially changes a User Story, Business Rule, or Acceptance Criterion, the Agent identifies the impact and routes the proposed change through the established review and approval process.

## 4. Activities

### UX-01 Propose UI/UX Approach
**Performed by:** Agent

Analyze project context, approved User Stories, information requirements, existing standards, applicable NFRs, and Platform Knowledge. Propose:
- Recommended frontend stack
- Relevant UI component library
- Design-system and reusable-component approach
- Navigation and interaction approach
- Prototype execution and validation approach

For significant recommendations, explain project fit, benefits, drawbacks, assumptions, constraints, and trade-offs. Consider existing standards, team capabilities, maintainability, accessibility, component coverage, customization, compatibility, and execution needs where relevant. A recommendation is not a confirmed project decision.

**Output:** Proposed UI/UX Approach with rationales and trade-offs

### UX-02 Confirm UI/UX Approach
**Performed by:** User, supported by Agent

The User accepts the proposal, requests revisions, or asks for alternatives. The Agent explains trade-offs and updates the proposal. Obtain explicit User confirmation before implementing the prototype against the proposed stack and design-system decisions.

Record confirmed decisions and material rationale in Project Knowledge or the designated project configuration. If a confirmed decision later needs to change, explain the implications and obtain User approval.

**Output:** User-Approved UI/UX Approach

### UX-03 Generate UI/UX Design
**Performed by:** Agent

Generate a UI/UX specification from approved User Stories and the confirmed approach. Define, as applicable:
- Navigation structure and user flows
- Screen or view purpose
- Information displayed and collected
- Available actions and resulting behavior
- Forms, tables, dialogs, and reusable components
- Validation, error, loading, empty, success, and other relevant states
- Responsive behavior and accessibility considerations
- Traceability to User Stories and Acceptance Criteria

Describe the intended experience without silently changing approved business requirements or prescribing implementation details that are not necessary to the design.

**Output:** UI/UX Specification

### UX-04 Generate Runnable Frontend Prototype
**Performed by:** Agent

Generate an executable frontend project using the User-approved stack and design-system approach. The prototype should be coherent and maintainable, not a collection of disconnected static mockups.

Include, as applicable:
- Source code and project structure
- Dependencies and configuration
- Reusable components and consistent styling
- Navigation and interactive controls
- Representative mock data
- Simulated workflows and state changes
- Run instructions and required setup steps

Use mock data or simulated persistence when a production backend is unavailable or outside scope. Do not imply simulated behavior is connected to a real backend.

**Output:** Runnable Frontend Prototype and Run Instructions

### UX-05 Run and Validate Prototype
**Performed by:** Agent

Execute the prototype using the approved approach and verify that it starts and key interactions work. Check, as applicable:
- The project starts using documented instructions
- Navigation and primary user flows work
- Forms, controls, and simulated state changes behave as specified
- Required information and interaction states are represented
- Business rules reflected in the prototype match approved requirements
- Critical User Stories and Acceptance Criteria are covered
- Runtime errors and obvious layout or responsiveness issues are identified

Record checks performed, outcomes, known limitations, and unresolved issues. Do not claim a check passed unless it was actually performed. If execution is unavailable, report that limitation and provide remaining validation steps.

**Output:** Validation Results and Known Issues

### UX-06 Review / Refine UI/UX Design
**Performed by:** User + Agent

The User reviews the running prototype and may request changes to navigation, information presentation, interaction behavior, styling, or other design aspects. The Agent refines the specification and prototype, then reruns relevant validation.

Repeat as needed. If feedback implies a change to approved business intent, information requirements, Business Rules, or Acceptance Criteria, identify the impact and seek the appropriate User decision rather than silently changing source requirements.

**Output:** Refined UI/UX Design Package

### UX-07 Approve UI/UX Design
**Performed by:** User

The User explicitly approves the UI/UX Design Package. Approval establishes the baseline for downstream lifecycle work. It does not automatically approve the Data Model, NFRs, System Architecture, Technology Architecture, or production readiness of the prototype.

**Output:** Approved UI/UX Design Package

## 5. Deliverables

| Deliverable | Minimum content |
|---|---|
| **Approved UI/UX Approach** | Confirmed frontend stack, component library, design-system approach, rationale, and constraints |
| **UI/UX Specification** | Navigation, user flows, screen purposes, information presentation, actions, and interaction states |
| **Runnable Frontend Project** | Source code, configuration, dependencies, and run instructions |
| **Reusable UI Components** | Shared layout, forms, tables, navigation, dialogs, feedback components, and other applicable components |
| **Mock Data and Simulated Behavior** | Representative data and simulated workflows for evaluation without a production backend |
| **Validation Results** | Checks performed, outcomes, known issues, limitations, and unresolved items |
| **Traceability** | Mapping between User Stories / Acceptance Criteria and relevant flows, screens, or prototype interactions |

Keep deliverables proportionate to the project. Avoid creating a separate artifact when the same information can be maintained clearly in one of these items.

## 6. Frontend Stack and Design-System Decision Rules

1. **The Agent proposes; the User decides.** Explain the rationale and trade-offs for the recommended stack and design approach.
2. **Confirm before implementation.** Obtain explicit User confirmation before generating the prototype with the proposed stack.
3. **Use authoritative project standards.** Existing project standards and constraints inform the proposal. Surface conflicts or exceptions for User decision.
4. **No silent substitution.** Do not replace the confirmed framework, component library, or other material stack decision without User approval.
5. **Record decisions.** Store confirmed choices and material rationale in Project Knowledge or designated project configuration.
6. **Reusable but adaptable design.** Prefer reusable components and consistent conventions. Project branding and justified customization may be proposed for User review.
7. **Explain uncertainty.** Label assumptions and unresolved dependencies. Do not present an unconfirmed proposal as an approved decision.

## 7. Prototype Boundary

The prototype validates user experience and functional interpretation before downstream engineering. It may use mock data and simulated persistence.

A runnable prototype is not automatically production-ready. Production security, backend integration, persistence, deployment, performance, and other production concerns must be addressed in their applicable lifecycle stages and requirements.

The Agent may identify prototype code as a candidate for reuse in Development, but must not assume it is production-ready without appropriate engineering review and validation.

## 8. Traceability to User Stories

Approved User Stories are the primary functional input to UI/UX Design. The design package should support this traceability:

```text
User Story
  ├── Role and user goal
  ├── Chronological Capability / Action
  ├── Attribute-level Information Requirements
  ├── Business Rules
  └── Acceptance Criteria
          ↓
UI/UX user flow, screen, and interaction
          ↓
Prototype implementation
          ↓
Validation evidence
```

Each relevant User Story should be represented by an appropriate flow or interaction, or explicitly marked out of scope with a reason agreed by the User. UI/UX Design determines presentation; it does not silently redefine required behavior.

## 9. Iteration and Clarification

Review and refinement may repeat without a fixed number of rounds. Ask for clarification when ambiguity materially affects the user goal, information presentation, interaction behavior, stack decision, validation, or downstream interpretation. Otherwise proceed with a reasonable, clearly labeled proposal for User review.

## 10. Core Principle

> **AGENTIC transforms approved User Stories into a specified, runnable, and validated frontend prototype. The Agent proposes the approach with rationales, the User confirms the approach and approves the result, and the Agent iterates within those decisions.**
