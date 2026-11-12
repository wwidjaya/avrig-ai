# AGENTIC Activity Process
## Define Activity

**Lifecycle Stage:** Activity  
**Status:** Proposed Baseline

## 1. Purpose

Decompose an approved Business Process into the business Activities that must be performed, and identify the information each Activity needs at the business entity level. For every Activity, establish **System Support**: what the target system must enable or support. System Support is the bridge from Activity to the downstream User Story stage.

An Activity describes business work, not a screen, feature, or technical implementation. Keep the definition chronological and only as detailed as needed to support Role and User Story definition.

## 2. Inputs

- Approved Business Process and its chronological steps
- Applicable Project Context and Project Knowledge
- Applicable Platform Knowledge
- Common Glossary and Project Glossary

Project-specific truth and requirements take precedence over reusable patterns. The Agent distinguishes requirements from existing practice, best practice, and inference.

## 3. Process Flow

```text
Approved Business Process
          ↓
Agent proposes Activities in process order
          ↓
Identify business information needs (entity level)
          ↓
Define System Support for each Activity
          ↓
User reviews / revises ↔ Agent refines
          ↓
User approves
          ↓
Approved Activity Set
```

## 4. Activities

### A-01 Propose Activities

**Performed by:** Agent

Decompose the approved Business Process into clear, outcome-oriented Activities, preserving the business sequence and any real branches or loops. Map each Activity to its source process step. Identify participating Role(s) when known, but detailed Role definition remains in the Role lifecycle stage.

**Output:** Proposed Activity Set

### A-02 Identify Information Requirements and System Support

**Performed by:** Agent

For each Activity, identify the business information needed or produced at the **entity level** (for example, Application, Customer, or Assessment). State the business purpose of the information and whether it is needed as input, reference, or output. Do not define attribute-level requirements here; those belong to User Stories.

Then define **System Support**: the capability the target system must provide to enable or support the Activity. State it in business terms, without prescribing a screen, visual layout, or implementation.

**Output:** Activity information requirements and System Support statements

### A-03 Review / Refine Activities

**Performed by:** User + Agent

The User reviews the proposed Activities, sequence, information needs, and System Support. The User may correct, add, remove, split, combine, or rename Activities and clarify business behavior. The Agent incorporates feedback. Repeat as needed.

**Output:** Refined Activity Set

### A-04 Approve Activities

**Performed by:** User

The User explicitly approves the Activity Set. Approval establishes it as the basis for Role and User Story definition.

**Output:** Approved Activity Set

## 5. Activity Structure

| Element | Description |
|---|---|
| **Activity ID / Name** | Stable identifier and concise business action name |
| **Sequence** | Position in the source Business Process, including branch or loop context when relevant |
| **Description** | What business work is performed and its intended result |
| **Source Process Step** | Traceable step or steps in the approved Business Process |
| **Role(s)** | Business role(s) performing or participating, when known |
| **Information Requirements** | Business entities needed or produced, with purpose and input/reference/output use |
| **System Support** | What the target system must enable or support for this Activity |
| **Business Rules / Decisions** | Applicable business conditions from the process, when needed to understand the Activity |
| **Output** | Business result or state produced, when applicable |

Only applicable information is required. Do not duplicate full process definitions or create unnecessary fields.

## 6. Entity-Level Information Requirements

Identify the business information at the entity level, not as a detailed list of attributes. The Activity answers **which business information is involved and why**. User Story later specifies the attributes needed for a particular Role and action.

Example:

```text
Activity: Review Application
Information Requirements:
- Application — review the submitted request
- Applicant — establish who submitted it
- Supporting Document — inspect evidence relevant to the review
System Support:
- Enable the reviewer to access the application and related applicant and document information and record the review outcome.
```

The Agent should identify missing or uncertain information as a question or clearly labeled inference; it must not silently promote an assumption into a project requirement.

## 7. System Support as the Bridge

System Support expresses the system-level need that follows from the business Activity. It gives the User Story stage a direct starting point:

```text
Business Process step
        ↓
Activity + entity-level information needs
        ↓
System Support
        ↓
Role-specific User Story + attribute-level information needs
```

System Support should describe the business outcome or enabled action. It must not prescribe UI/UX layout, controls, navigation, or technology. The User Story and its Acceptance Criteria become the functional reference for UI/UX design.

## 8. Iteration and Clarification

Review and refinement form a repeatable loop; there is no fixed number of rounds. Ask for clarification only when ambiguity materially affects Activity boundaries or sequence, information needs, System Support, role participation, or downstream requirements. Otherwise proceed with a reasonable, labeled interpretation.

## 9. Core Principle

> **Activity defines the chronological business work, its entity-level information requirements, and the System Support needed to enable it. The User Story stage elaborates that support for a specific Role and action.**
