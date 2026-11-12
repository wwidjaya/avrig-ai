# AGENTIC Business Capability
# DMC-06 Data Model Impact Analysis

**Version:** 1.0  
**Capability ID:** DMC-06  
**Capability Name:** Data Model Impact Analysis  
**Lifecycle Stage:** Data Model  
**Status:** Proposed

---

## 1. Capability Definition

**DMC-06 Data Model Impact Analysis** determines the consequences of changing the Logical Data Model.

It analyzes a proposed or detected change and determines which business and engineering artifacts may be affected, including:

- Business Process
- Activity
- Role
- User Story
- UI/UX Design
- Data Model
- NFR
- System Architecture
- Technology Architecture
- Development
- Test
- Deployment

> **DMC-04 tells us what is connected. DMC-06 tells us what those connections mean when something changes.**

DMC-06 transforms lifecycle traceability into actionable change intelligence.

---

## 2. Purpose

DMC-06 enables the Agent to:

- understand the scope of a proposed data model change;
- identify directly and indirectly affected artifacts;
- analyze consequences across the engineering lifecycle;
- distinguish confirmed impacts from inference and uncertainty;
- assess business, data, UX, application, architecture, NFR, and engineering impacts;
- identify risks and dependencies;
- compare alternative change scenarios;
- recommend an appropriate change approach;
- provide evidence for human decision-making;
- preserve the resulting impact analysis and decision context.

DMC-06 does not approve changes. It provides the intelligence required for an authorized human to decide whether and how a change should be adopted.

---

## 3. Core Principle

> **Do not merely identify dependencies. Reason about the consequences of change.**

```text
Detect
   ↓
Trace
   ↓
Analyze
   ↓
Assess
   ↓
Compare
   ↓
Recommend
   ↓
Human Decide
```

---

## 4. Scope

DMC-06 covers:

1. Change identification
2. Dependency analysis
3. Business impact analysis
4. Data impact analysis
5. UX impact analysis
6. Application impact analysis
7. Architecture impact analysis
8. NFR impact analysis
9. Engineering impact analysis
10. Cross-lifecycle impact analysis
11. Risk and severity assessment
12. Change scenario analysis
13. Impact reporting and recommendation
14. Human review and decision support

DMC-06 does not own:

- logical data model design;
- formal data model validation;
- lifecycle traceability management;
- formal governance and approval.

Those responsibilities belong to adjacent capabilities.

---

## 5. Boundary with Other Data Model Capabilities

### 5.1 DMC-01 Data Requirement Analysis

DMC-01 determines:

> What information is needed and what does each concept mean?

DMC-06 determines:

> What is affected when the data model representing that information changes?

### 5.2 DMC-02 Logical Data Modeling

DMC-02 determines:

> What is the logical data model?

DMC-06 determines:

> What are the consequences of changing that logical model?

DMC-06 does not redesign the logical model. It may identify that redesign is required as a consequence of the change.

### 5.3 DMC-03 Data Model Validation

DMC-03 determines:

> Is the logical model complete, consistent, correct, traceable, and fit for purpose?

DMC-06 determines:

> What consequences may result from a proposed change?

DMC-03 may be invoked after proposed changes have been identified.

### 5.4 DMC-04 Data Model Traceability

DMC-04 determines:

> What is this model element connected to?

DMC-06 determines:

> What happens if this model element changes?

DMC-04 provides the traceability graph used by DMC-06. DMC-06 should not create an independent duplicate traceability mechanism.

### 5.5 DMC-05 ERD Visualization & Modeling

DMC-05 provides visual representation and modeling interaction. A change detected through the ERD may become an input to DMC-06.

### 5.6 DMC-07 Data Model Collaboration

DMC-07 provides collaborative interaction around model changes and findings. DMC-06 provides the impact intelligence used during that collaboration.

### 5.7 DMC-08 Data Model Governance & Approval

DMC-08 determines what change is formally approved and what becomes authoritative. DMC-06 provides the analysis and recommendation supporting that decision.

---

## 6. Capability Structure

| ID | Capability | Purpose |
|---|---|---|
| DMC-06.01 | Change Identification | Define precisely what changed |
| DMC-06.02 | Dependency Analysis | Identify affected and dependent elements |
| DMC-06.03 | Business Impact Analysis | Analyze business-level consequences |
| DMC-06.04 | Data Impact Analysis | Analyze consequences within the data model |
| DMC-06.05 | UX Impact Analysis | Identify affected UI/UX behavior |
| DMC-06.06 | Application Impact Analysis | Identify affected application functionality |
| DMC-06.07 | Architecture Impact Analysis | Identify affected system and technology architecture |
| DMC-06.08 | NFR Impact Analysis | Determine potential NFR consequences |
| DMC-06.09 | Engineering Impact Analysis | Analyze development, testing, and deployment consequences |
| DMC-06.10 | Cross-Lifecycle Impact Analysis | Propagate impact across the engineering lifecycle |
| DMC-06.11 | Risk & Severity Assessment | Assess significance and risk |
| DMC-06.12 | Change Scenario Analysis | Compare alternative change approaches |
| DMC-06.13 | Impact Report & Recommendation | Produce actionable impact assessment |
| DMC-06.14 | Human Review & Decision Support | Support human decision on the proposed change |

---

## 7. Inputs

DMC-06 consumes:

### 7.1 Proposed or Detected Change

Sources may include:

- DMC-02 Logical Data Modeling;
- DMC-05 ERD Visualization & Modeling;
- new requirements;
- changed business rules;
- user requests;
- regulatory changes;
- architecture changes;
- discovered data issues;
- DMC-03 validation findings.

### 7.2 Authoritative Logical Data Model

The Agent requires the current authoritative logical data model, including:

- entities;
- attributes;
- relationships;
- identifiers;
- keys;
- cardinalities;
- optionality;
- constraints;
- definitions;
- model versions.

### 7.3 Traceability Graph

DMC-04 provides the primary dependency graph connecting the changed model element to, where applicable:

- Information Requirements;
- User Stories;
- Activities;
- Business Processes;
- Roles;
- UI/UX artifacts;
- NFRs;
- System Architecture;
- Technology Architecture;
- Development artifacts;
- Test artifacts;
- Deployment artifacts.

### 7.4 Project Knowledge

Project-specific requirements, standards, decisions, regulations, policies, and approved practices provide authoritative context.

### 7.5 Platform Knowledge

Platform Knowledge may provide:

- impact-analysis patterns;
- risk assessment patterns;
- engineering best practices;
- change-management patterns;
- reusable analysis techniques.

Project-specific authoritative knowledge takes precedence where applicable.

---

## 8. Change Definition

Impact analysis begins with a structured **Change Definition**.

| Field | Description |
|---|---|
| Change ID | Unique change identifier |
| Source | Origin of the change |
| Model Version | Current authoritative model |
| Element | Affected model element |
| Change Type | Add, remove, modify, rename, relationship change, constraint change |
| Current State | Existing definition |
| Proposed State | New definition |
| Reason | Why the change is proposed |
| Source Requirement | Requirement motivating the change |
| Requester | Person or Agent initiating change |
| Status | Proposed, under analysis, accepted, rejected, deferred, etc. |

---

## 9. Change Types

DMC-06 should recognize at least:

- Entity addition;
- Entity removal;
- Entity modification;
- Entity rename;
- Attribute addition;
- Attribute removal;
- Attribute modification;
- Attribute rename;
- Relationship addition;
- Relationship removal;
- Relationship modification;
- Cardinality change;
- Optionality change;
- Identifier/key change;
- Constraint change;
- Semantic definition change.

The Agent must determine whether a rename is merely presentational or changes semantic identity.

---

## 10. Change and Dependency Analysis

The Agent should:

1. identify the authoritative model version;
2. identify the changed element;
3. identify current and proposed state;
4. classify the change;
5. identify source and reason;
6. identify related requirements;
7. establish change scope;
8. retrieve traceability dependencies;
9. distinguish direct, indirect, potential, unknown, and conflicting findings;
10. identify unresolved ambiguity.

### Dependency Classification

| Classification | Meaning |
|---|---|
| Direct | Explicit dependency exists |
| Indirect | Dependency exists through another artifact |
| Potential | Agent inference indicates possible impact |
| No Impact | Analysis confirms no material impact |
| Unknown | Evidence is insufficient |
| Conflict | Authoritative sources disagree |

A traceability relationship identifies a candidate dependency. It does not automatically prove material impact.

---

## 11. Business Impact Analysis

The Agent determines whether the change affects:

- Vision;
- Mission;
- Strategy;
- Business Capability;
- Business Process;
- Activity;
- Role;
- Business Rule;
- User Story.

Example:

```text
Business Process
    ↓
Collect Participant Information
    ↓
Activity
    ↓
Register Participant
    ↓
User Story
    ↓
Capture Date of Birth
```

The Agent should determine whether:

- the activity still works;
- additional information must be collected;
- a business rule changes;
- a role's responsibility changes;
- an approval decision changes.

Only evidence-supported impacts should be reported as confirmed.

---

## 12. Data Impact Analysis

The Agent analyzes:

- affected entities;
- affected attributes;
- affected relationships;
- affected identifiers;
- affected constraints;
- affected reference data;
- affected derived information;
- affected data dependencies.

Example:

```text
Participant.DateOfBirth
        │
        ├── Age
        ├── Eligibility
        ├── Pension Calculation
        └── Reporting
```

The Agent must distinguish explicit dependencies, indirect dependencies, inference, and unknowns.

---

## 13. UX Impact Analysis

Potential impacts include:

- forms;
- fields;
- required/optional indicators;
- field validation;
- display rules;
- search/filter criteria;
- tables;
- reports;
- user flows;
- error messages;
- accessibility behavior.

Example:

```text
Optional Date of Birth
        ↓
Mandatory Date of Birth
        ↓
Registration Form
        ↓
Required Field
        ↓
Validation Message
        ↓
Acceptance Criteria
        ↓
Test
```

The Agent should identify the relevant User Stories before recommending UX changes.

---

## 14. Application Impact Analysis

Potential impacts include:

- API contracts;
- request/response structures;
- service logic;
- validation;
- persistence logic;
- transformation;
- integration;
- reporting;
- batch processing;
- event processing.

Compatibility should be classified as:

| Classification | Meaning |
|---|---|
| Backward Compatible | Existing consumers can continue operating |
| Conditionally Compatible | Compatibility depends on specific conditions |
| Breaking | Existing consumers or behavior may fail |
| Unknown | Compatibility cannot yet be determined |

---

## 15. Architecture Impact Analysis

### System Architecture

Potential impacts:

- applications;
- services;
- APIs;
- integration;
- data stores;
- processing components.

### Technology Architecture

Potential impacts:

- database technology;
- messaging;
- integration technology;
- storage;
- processing;
- infrastructure;
- deployment architecture.

Architecture impact should be derived from authoritative artifacts and traceability rather than guessed.

---

## 16. NFR Impact Analysis

The Agent evaluates whether the change affects:

- performance;
- scalability;
- availability;
- security;
- privacy;
- interoperability;
- usability;
- maintainability;
- auditability;
- data quality.

Example:

```text
Data Model Change
      ↓
Query Complexity
      ↓
API Response Size
      ↓
Performance NFR
```

The Agent should identify existing relevant NFRs rather than inventing new requirements merely to justify an impact.

---

## 17. Engineering Impact Analysis

### Development

Potential impacts:

- source code;
- database migration;
- API implementation;
- configuration;
- integration logic;
- transformation logic.

### Test

Potential impacts:

- unit tests;
- integration tests;
- functional tests;
- regression tests;
- test data;
- acceptance tests.

### Deployment

Potential impacts:

- migration scripts;
- deployment sequence;
- backward compatibility;
- rollback;
- release dependencies.

---

## 18. Cross-Lifecycle Impact Analysis

The Agent analyzes the change across:

```text
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
UI/UX
  ↓
DATA MODEL ← CHANGE
  ↓
NFR
  ↓
SYSTEM ARCHITECTURE
  ↓
TECHNOLOGY ARCHITECTURE
  ↓
DEVELOPMENT
  ↓
TEST
  ↓
DEPLOY
```

The Agent must not assume every stage is affected. It determines the actual impact path using traceability, authoritative artifacts, business rules, dependencies, and explicit requirements.

---

## 19. Impact Propagation

A propagation path should identify:

- source element;
- relationship;
- affected element;
- impact type;
- evidence;
- confidence;
- required action.

Example:

```text
Data Model Change
       ↓
Information Requirement
       ↓
User Story
       ↓
UI/UX
       ↓
Application API
       ↓
Application Logic
       ↓
Test
       ↓
Deployment
```

---

## 20. Risk and Severity Assessment

Recommended severity levels:

| Severity | Meaning |
|---|---|
| Critical | Change may invalidate major business or system behavior |
| High | Significant redesign or engineering work is likely |
| Medium | Material change is required but localized |
| Low | Minor change with limited consequences |
| Informational | No substantive change, but awareness is useful |

Severity should consider:

- business criticality;
- number of affected artifacts;
- dependency depth;
- implementation complexity;
- migration complexity;
- compatibility;
- regulatory impact;
- security/privacy impact;
- operational risk;
- reversibility.

For significant changes, the Agent should identify:

- risk;
- cause;
- consequence;
- likelihood;
- severity;
- mitigation;
- residual risk.

---

## 21. Change Scenario Analysis

DMC-06 should compare alternative change approaches when more than one viable option exists.

Example:

> `Participant.DateOfBirth` is missing for historical records.

Possible approaches:

### Option A
Make the attribute mandatory immediately.

### Option B
Keep it optional for historical records but mandatory for new records.

### Option C
Introduce a data remediation process.

The Agent compares:

- business impact;
- data impact;
- UX impact;
- application impact;
- architecture impact;
- NFR impact;
- implementation effort;
- migration complexity;
- risk;
- reversibility.

### Scenario Comparison

| Dimension | Option A | Option B | Option C |
|---|---|---|---|
| Business Impact | | | |
| Data Impact | | | |
| UX Impact | | | |
| Application Impact | | | |
| Architecture Impact | | | |
| NFR Impact | | | |
| Implementation Effort | | | |
| Migration Complexity | | | |
| Risk | | | |
| Reversibility | | | |
| Overall Assessment | | | |

Unknown values must remain explicitly unknown.

---

## 22. Impact Graph

DMC-06 may construct a change-specific **Impact Graph** from the DMC-04 traceability graph.

```text
                 CHANGE
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
      Business     Data      UX
       Impact      Impact    Impact
          │         │         │
          └────┬────┴────┬────┘
               ▼         ▼
          Application  NFR
             Impact    Impact
               │         │
               └────┬────┘
                    ▼
               Architecture
                  Impact
                    │
                    ▼
              Engineering
                  Impact
```

The Impact Graph is a change-specific analytical view. It is not a replacement for DMC-04 traceability.

---

## 23. Impact Depth

The Agent may identify propagation depth:

```text
Depth 0
Changed Data Model Element

Depth 1
Directly dependent User Story

Depth 2
UI/UX derived from User Story

Depth 3
Application behavior derived from UI/UX / User Story

Depth 4
Tests and deployment artifacts
```

Depth alone does not determine severity.

---

## 24. Impact Completeness

The Agent should assess whether the analysis is sufficient to support a decision.

| Status | Meaning |
|---|---|
| Complete | Relevant traceability and evidence are sufficient |
| Substantially Complete | Minor unknowns remain |
| Incomplete | Material dependencies or evidence are missing |
| Blocked | Analysis cannot proceed without additional information |

The Agent should explicitly identify missing information.

---

## 25. Impact Record

Each material finding should be represented as a structured record.

| Field | Description |
|---|---|
| Impact ID | Unique impact identifier |
| Change ID | Related change |
| Source Element | Element initiating impact |
| Affected Element | Element potentially affected |
| Lifecycle Stage | Stage containing affected element |
| Relationship | Traceability/dependency relationship |
| Impact Type | Direct, indirect, potential, etc. |
| Impact Description | What changes or may change |
| Evidence | Supporting evidence |
| Confidence | Confidence of analysis |
| Severity | Impact severity |
| Risk | Associated risk |
| Required Action | Recommended action |
| Status | Open, reviewed, accepted, rejected, etc. |

---

## 26. Impact Analysis Report

DMC-06 should produce an **Impact Analysis Report** containing:

### Change
What is changing?

### Reason
Why is it changing?

### Affected Elements
Which elements are affected?

### Impact Paths
How does the change propagate?

### Business Impact
What changes for the business?

### Data Impact
What changes in the model and data?

### UX Impact
What changes for users?

### Application Impact
What changes in applications, services, and APIs?

### Architecture Impact
What architecture elements are affected?

### NFR Impact
Which quality requirements may change?

### Engineering Impact
What development, testing, and deployment work is required?

### Risks
What can go wrong?

### Alternatives
What alternative approaches exist?

### Recommendation
What does the Agent recommend?

### Uncertainty
What is not known?

### Human Decision
What did the authorized decision maker decide?

---

## 27. Agent Recommendation

For significant changes, the Agent should provide:

- Recommendation;
- Change Type;
- Affected Elements;
- Current State;
- Proposed State;
- Rationale;
- Evidence;
- Source;
- Related Requirement;
- Related Business Rule;
- Impact;
- Risks;
- Dependencies;
- Assumptions;
- Confidence;
- Uncertainty;
- Alternatives;
- Human Decision Required.

Example:

```text
Recommendation

Option B is recommended.

Rationale:
- New participant registration requires Date of Birth.
- Existing historical records may not contain the information.
- Making the attribute globally mandatory would require historical
  data remediation before deployment.
- Option B limits the immediate business and migration impact.

Affected:
- Registration User Story
- Registration UI
- Participant API
- Validation rules
- Test cases

Risk:
Medium

Open Question:
Whether historical records are subject to the same completeness rule.
```

---

## 28. Evidence and Confidence

Every material impact should identify its basis.

Possible evidence categories:

- Authoritative requirement;
- Approved User Story;
- Approved Business Process;
- Approved Activity;
- Approved Data Model;
- Approved UI/UX Design;
- Approved NFR;
- Approved Architecture;
- Existing traceability;
- Project Knowledge;
- Platform Knowledge;
- Agent inference.

The Agent must distinguish:

```text
Evidence
   versus
Inference
   versus
Unknown
```

A high-confidence inference is still an inference.

---

## 29. Human Review and Decision Support

DMC-06 does not approve the change.

```text
Impact Analysis
      ↓
Agent Recommendation
      ↓
Human Review
      ↓
┌─────┼────────┬────────┐
▼     ▼        ▼        ▼
Adopt Modify  Defer   Reject
```

The human may also request revision.

### Decision Outcomes

| Decision | Meaning |
|---|---|
| Adopt | Proposed change is accepted |
| Modify | Change is accepted with modifications |
| Reject | Proposed change is not accepted |
| Defer | Decision is postponed |
| Request Revision | Agent must revise the proposed change or analysis |

The decision does not automatically mean that every downstream artifact has already been updated. Accepted changes initiate the applicable change process.

---

## 30. Process

### DM-06.1 Identify Change

Establish the exact change and its source.

**Output:** Change Definition.

### DM-06.2 Determine Baseline

Identify authoritative model and relevant artifact versions.

**Output:** Analysis Baseline.

### DM-06.3 Retrieve Dependencies

Use DMC-04 traceability to identify candidate affected artifacts.

**Output:** Dependency Set.

### DM-06.4 Analyze Business Impact

Analyze Business Process, Activity, Role, User Story, and business rules.

**Output:** Business Impact Findings.

### DM-06.5 Analyze Data Impact

Analyze model dependencies and data consequences.

**Output:** Data Impact Findings.

### DM-06.6 Analyze UX Impact

Analyze affected screens, interactions, validation, and user flows.

**Output:** UX Impact Findings.

### DM-06.7 Analyze Application Impact

Analyze APIs, services, logic, integrations, and processing.

**Output:** Application Impact Findings.

### DM-06.8 Analyze Architecture Impact

Analyze system and technology architecture.

**Output:** Architecture Impact Findings.

### DM-06.9 Analyze NFR Impact

Analyze affected quality requirements.

**Output:** NFR Impact Findings.

### DM-06.10 Analyze Engineering Impact

Analyze Development, Test, and Deploy.

**Output:** Engineering Impact Findings.

### DM-06.11 Assess Risk

Assess severity, likelihood, consequence, and mitigation.

**Output:** Risk Assessment.

### DM-06.12 Compare Scenarios

Analyze alternative change approaches.

**Output:** Scenario Comparison.

### DM-06.13 Generate Recommendation

Produce the Agent's recommended approach.

**Output:** Impact Analysis Report.

### DM-06.14 Human Review

Present findings and recommendation to the authorized human.

**Output:** Human Decision.

### DM-06.15 Record Outcome

Record the decision and associated impact analysis.

**Output:** Decision-Linked Impact Record.

---

## 31. Relationship with DMC-04

The fundamental distinction is:

```text
DMC-04
Data Model Traceability

"Where is this element connected?"

             ↓

        Traceability Graph

             ↓

DMC-06
Data Model Impact Analysis

"What happens if this element changes?"
```

DMC-04 maintains the relationship graph.

DMC-06 interprets that graph for a specific change scenario.

DMC-06 must not create an independent duplicate traceability system.

---

## 32. Relationship with Human Decision & Approval

```text
Change Proposal
      ↓
DMC-06 Impact Analysis
      ↓
Impact Findings
      ↓
Risk Assessment
      ↓
Scenario Analysis
      ↓
Agent Recommendation
      ↓
Human Review
      ↓
Approved / Modified / Rejected / Deferred
```

The Agent's recommendation remains non-authoritative until the applicable human decision is made.

---

## 33. Outputs

| Output | Description |
|---|---|
| Change Definition | Structured description of the analyzed change |
| Analysis Baseline | Versions of authoritative artifacts used |
| Dependency Set | Candidate affected artifacts |
| Impact Graph | Change-specific dependency and propagation view |
| Impact Records | Structured individual impact findings |
| Business Impact Findings | Business-level consequences |
| Data Impact Findings | Data-model consequences |
| UX Impact Findings | User experience consequences |
| Application Impact Findings | Application and API consequences |
| Architecture Impact Findings | Architecture consequences |
| NFR Impact Findings | Quality requirement consequences |
| Engineering Impact Findings | Development, test, and deployment consequences |
| Risk Assessment | Risks, severity, likelihood, and mitigation |
| Scenario Comparison | Comparison of alternative approaches |
| Impact Analysis Report | Consolidated analysis |
| Agent Recommendation | Recommended change approach |
| Human Decision Reference | Decision associated with the analysis |
| Open Questions | Unresolved information required for decision |

---

## 34. Boundary Summary

| Concern | Primary Owner | DMC-06 Role |
|---|---|---|
| Information discovery | DMC-01 | Analyze consequences |
| Logical model design | DMC-02 | Analyze consequences |
| Model validation | DMC-03 | Consume validation findings |
| Lifecycle traceability | DMC-04 | Consume traceability |
| ERD visualization | DMC-05 | Consume proposed visual changes |
| Impact analysis | DMC-06 | Own |
| Collaboration | DMC-07 | Provide impact intelligence |
| Governance and approval | DMC-08 | Provide decision support |

---

## 35. Core Principles

### Principle 1: Impact Is Change-Specific

The same dependency may produce different impacts depending on the nature of the change.

### Principle 2: Traceability Is Evidence, Not Impact

A traceability relationship identifies a candidate dependency. It does not automatically prove material impact.

### Principle 3: Evidence and Inference Must Be Distinguished

The Agent must clearly distinguish confirmed facts, inference, and unknown information.

### Principle 4: Analyze the Whole Lifecycle

Data model changes can affect business and engineering artifacts upstream and downstream.

### Principle 5: Do Not Overstate Impact

The Agent must not report every connected artifact as materially affected.

### Principle 6: Alternatives Matter

When multiple approaches are viable, the Agent should compare them.

### Principle 7: Recommendation Is Not Approval

The Agent recommends. The authorized human decides.

### Principle 8: Preserve Provenance

Every significant impact finding should be traceable to its evidence.

### Principle 9: Uncertainty Must Be Explicit

Missing information should result in Unknown or Potential findings, not fabricated certainty.

### Principle 10: Impact Analysis Should Be Actionable

The purpose is not merely to identify affected artifacts. It is to determine what should happen next.

---

## 36. Expected Agentic Behavior

The Agent should operate as an intelligent **change impact analyst**.

For example:

```text
User:
"Make Participant.DateOfBirth mandatory."

Agent:
1. Identify the current authoritative model.
2. Identify the current definition of DateOfBirth.
3. Identify all authoritative dependencies.
4. Trace affected User Stories and Activities.
5. Analyze UX consequences.
6. Analyze application and API consequences.
7. Analyze data migration consequences.
8. Analyze test and deployment consequences.
9. Identify NFR and architecture implications.
10. Identify uncertainty around historical records.
11. Generate alternative approaches.
12. Compare risks and effort.
13. Recommend an approach.
14. Present the analysis to the human.
15. Wait for the human decision.
```

The Agent does not silently implement the change merely because it identified the impact.

---

## 37. Capability Outcome

When DMC-06 is successfully executed, the project has:

- a precise definition of the proposed change;
- identified dependencies;
- a change-specific impact graph;
- business impact analysis;
- data impact analysis;
- UX impact analysis;
- application impact analysis;
- architecture impact analysis;
- NFR impact analysis;
- engineering impact analysis;
- risk and severity assessment;
- alternative change scenarios;
- evidence-backed recommendation;
- explicit uncertainty;
- human decision support;
- traceable decision context.

The resulting capability transforms the AGENTIC Data Model from a static design artifact into a **change-aware engineering knowledge structure**.

> **DMC-04 tells AGENTIC what is connected. DMC-06 enables AGENTIC to reason about what happens when something changes.**
