# AGENTIC Platform System Architecture: Unified System Design Baseline

**Status:** Approved Master Design Document  
**Project:** AGENTIC — Virtual AI Autonomous Engineering Organization & Agentic SDLC Platform  
**Scope:** Unified system architecture integrating the Agentic SDLC Engineering Lifecycle, Office Operating System, Organizational Hierarchy, Persistent AI Employee Runtime, and 3D Virtual Operational Environment.

---

## 1. Executive Summary & Product Vision

The **AGENTIC** platform is not merely an AI coding assistant, an LLM chatbot, or a superficial dashboard. It is a **virtual AI company and autonomous engineering organization** operated by a human Founder.

```text
Human Founder (Ultimate Authority)
      │
      ▼
   PET AI / CEO (AI Employee #001)
      │
      ├── Corporate / Shared Departments
      │     └── Department Heads (VP / Director AI)
      │            └── Employees (Specialist AIs)
      │
      └── Projects (Execution Contexts)
             └── Project Teams
                    └── Team Leads + Members
```

The system pairs a real **Rust Office Service** operating system with an **Agentic SDLC Engine**, enabling the CEO AI to run the company, propose initiatives, recruit AI workforce, delegate work packages, coordinate cross-functional teams, conduct formal meetings, and drive engineering projects across the canonical lifecycle under strict human governance.

---

## 2. Core Architectural Principles

1. **Structured Models are Authoritative; Visualizations are Representations.**  
   - Relational and graph stores maintain authoritative truth.
   - Diagrams (ERDs, architecture diagrams) and the 3D Virtual Office are visual projections of operational state, never the source of truth.
2. **Intelligence Does Not Equal Authority.**  
   - Agents analyze, synthesize, recommend, plan, draft, and execute within permitted boundaries.
   - Authority is governed by explicit roles, organization hierarchy, capabilities, and cross-cutting human approval policies.
3. **Decoupled Identity vs. Execution Runtime.**  
   - An AI Employee is a persistent organizational identity with memory, skills, history, and relationships.
   - An Agent Runtime is an ephemeral execution instance that can spin up, execute, pause, sleep, or terminate without destroying the employee identity.
4. **Canonical Engineering Lifecycle is Invariant.**  
   - The platform preserves the approved sequence from project intent through test and optional deployment. Agent maturity accelerates execution, but never alters or skips lifecycle stages.
5. **Engineering Before Technology.**  
   - Business intent, user needs, information models, and logical boundaries precede concrete technology selections and code generation.
6. **Strict Security Boundaries.**  
   - Autonomous actors never directly interact with host operating systems or external systems without passing through typed, governed, audited policy enforcement layers.

---

## 3. Organizational & Identity Model

### 3.1 Role Distinctions

```text
Founder (Human Owner)
├── Personal Assistant (Serves Founder directly: calendar, personal tasks, reminders)
└── CEO / PET (Runs the AI company: operations, projects, departments)
     ├── Executive Officers (CTO, CPO, etc.)
     ├── Department Heads
     └── Engineering & Operations Workforce
```

- **Founder / Owner:** The human user who holds sovereign authority over the organization, budgets, recruitment approvals, policy baselines, and final baselines.
- **CEO (PET):** AI Employee #001. A first-class organizational actor responsible for managing departments, initiating projects, and recruiting workforce.
- **Personal Assistant (PA):** A distinct AI position reporting directly to the Founder, keeping administrative and personal tasks decoupled from corporate executive operations.

### 3.2 Four-Tier Actor-Runtime Hierarchy

To prevent equating an AI employee with a transient LLM context window:

```text
Position (Job Definition / Requirements / Permissions)
   │
   ▼
Employee (Persistent Organizational Identity & History)
   │
   ▼
Actor (Unified Participant Identity: Human or AI)
   │
   ▼
Agent Runtime (Ephemeral Execution Process / Worker)
   │
   ▼
LLM / Model Adapters & Tool Execution
```

- **Position:** Defines functional scope, organizational expectations, default policies, and authority boundaries (e.g., Lead Architect, Senior Backend Engineer, QA Specialist).
- **Employee:** Persistent entity containing employee ID, display name, biography, long-term memory, career audit trail, and department membership.
- **Actor:** Polymorphic identity abstraction enabling humans and AI agents to participate interchangeably in tasks, meetings, approvals, and audits.
- **Agent Runtime:** The transient execution state executing LLM prompts, holding working memory, calling tools, and emitting telemetry.

### 3.3 Employee Lifecycle

```text
Active ──(idle timeout)──► Idle ──(shutdown runtime)──► Offline / On Leave
  ▲                          │                                │
  └────────(wake/assign)─────┴────────(wake/assign)───────────┘
  │
  ├──► Suspended (policy lock / audit review)
  │
  └──► Released ──► Archived
```

- **Active:** Runtime currently running, executing or waiting on immediate events.
- **Idle:** No active task, runtime kept warm or scheduled for sleep.
- **Offline / On Leave:** Runtime terminated; identity, state, and permissions remain intact.
- **Suspended:** Execution locked due to security check, policy violation, or human hold.
- **Released:** Formal departure requiring Founder approval. Belongings packed, access revoked.
- **Archived:** Historical record preserved indefinitely for audit, traceability, and organizational learning.

### 3.4 CEO Recruitment Flow

```text
CEO identifies organizational need / capacity deficit
       ↓
CEO drafts Position & Job Description (skills, policies, tooling)
       ↓
Founder reviews & approves recruitment request
       ↓
CEO creates Employee entity (assigning name & avatar personality)
       ↓
Employee is bound to Actor & assigned to Department / Project Team
       ↓
Agent Runtime is instantiated upon initial task assignment
```

---

## 4. Organizational Structure: Two Orthogonal Dimensions

The organization intentionally decouples organizational home from execution context:

```text
┌────────────────────────────────────────────────────────┐
│             DEPARTMENTS (Organizational Home)          │
│  - Engineering, Product, QA, Architecture, Infra       │
│  - Department Head + Members                           │
│  - Dedicated Floor, Private Offices, Lab Workspaces    │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ Employees matrix-assigned
                            ▼
┌────────────────────────────────────────────────────────┐
│             PROJECTS (Execution Context)               │
│  - Project A, Project B, Project C                     │
│  - Project Lead / Team Lead                            │
│  - Cross-functional Project Teams                      │
│  - Canonical Lifecycle Deliverables                    │
└────────────────────────────────────────────────────────┘
```

An employee belongs to exactly one home Department while simultaneously being assigned to one or more Project Teams.

---

## 5. Dual Engine Architecture

The platform operates as a cohesive system driven by two complementary engines running on top of a unified persistence and event layer:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                         AGENTIC PLATFORM                               │
├───────────────────────────────────┬────────────────────────────────────┤
│       OFFICE OPERATING SYSTEM     │        AGENTIC SDLC ENGINE         │
│  - Organization & Hierarchy       │  - Canonical Lifecycle Sequence    │
│  - Workforce & Recruitment        │  - Stage Baseline Verification     │
│  - Meetings & Rooms Management    │  - 9 Engineering SDLC Modules      │
│  - 3D Projection & Spatial State  │  - Cross-Cutting Artifact Trace    │
│  - Computer / Tool Gateways       │  - Candidate vs. Baseline State    │
├───────────────────────────────────┴────────────────────────────────────┤
│                  SHARED CROSS-CUTTING AGENT HARNESS                    │
│  - Context Engine     - Memory & Knowledge     - Dynamic Skills        │
│  - Tool Registry      - Human Approvals        - Policy & Guardrails   │
│  - Event Bus (PubSub) - Observability & Audit  - Traceability Graph    │
├────────────────────────────────────────────────────────────────────────┤
│                       AUTHORITATIVE STORAGE                            │
│    PostgreSQL (System of Record) + Apache AGE (Relationship Graph)     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. The Canonical Engineering SDLC

The platform enforces the strict, canonical engineering sequence across every project:

```text
PROJECT
  → VISION
  → MISSION
  → STRATEGY
  → BUSINESS CAPABILITY
  → BUSINESS PROCESS
  → ACTIVITY
  → ROLE
  → USER STORY
  → UI/UX DESIGN
  → DATA MODEL
  → NON-FUNCTIONAL REQUIREMENT (NFR)
  → SYSTEM ARCHITECTURE
  → TECHNOLOGY ARCHITECTURE
  → DEVELOPMENT
  → TEST (Mandatory Engineering Baseline)
  → DEPLOYMENT (Optional: cardinality 0..1)
```

### 6.1 SDLC Modules & Responsibilities

| Module | Lifecycle Alignment | Primary Boundary |
|---|---|---|
| **Requirements Engineering** | Project through User Story | Business intent, vision, capability mapping, processes, activities, roles, user stories, acceptance criteria. |
| **UI/UX Engineering** | UI/UX Design | User journeys, wireframes, screen contracts, design system adherence. |
| **Data Engineering** | Data Model | Conceptual, logical, and physical entity models, relationships, Azimutt ERD integration, schema migrations. |
| **NFR Engineering** | NFR | Quantifiable quality attributes: performance, availability, latency, security, compliance. |
| **System Architecture** | System Architecture | Technology-agnostic logical subsystems, bounded contexts, integration contracts, component interfaces. |
| **Technology Architecture**| Technology Architecture | Selection and validation of programming languages, frameworks, databases, and deployment platforms. |
| **Development Engineering**| Development | High-assurance code generation, test-driven implementation, PR management, static analysis. |
| **Test Engineering** | Test | Unit, integration, end-to-end, load, and security test execution. Establishes the **Test Baseline**. |
| **Deployment Engineering** | Deployment *(Optional)* | Infrastructure as code, containerization, CD pipelines, canary rollout, environment operationalization. |

### 6.2 Epistemic Status & Baselining Flow

To ensure high-assurance governance, every engineering artifact follows a strict lifecycle:

```text
[Agent Inference / Draft]
           ↓
[Candidate Artifact] ──(Validation & Simulation Engine)──► [Validation Evidence]
           ↓
[Human Review & Deliberation]
           ↓
[Human Approval via Policy Gate]
           ↓
[Authoritative Baseline] ──► Available to Downstream Stages
```

---

## 7. Operational Office Service & 3D Spatial Virtualization

### 7.1 Virtual Office Metaphor

The virtual 3D office is an active, spatial visualization driven directly by the Rust Office Service event stream:

- **Top Executive Floor:** Penthouse / CEO glass office overlooking the campus, Founder boardroom, and PA office.
- **Department Floors:** One floor per organizational department, featuring private offices for Department Heads and bullpen workstations for team members.
- **Meeting Facilities:** Shared conference rooms equipped with interactive presentation boards and transcription loggers.
- **Lounge & Common Areas:** Breakout areas where idle, off-duty, or resting agents congregate.
- **Basement / Datacenter:** Representation of model servers, local embeddings, vector stores, and automated background jobs.
- **Elevators & Vertical Circulation:** Active elevators transporting agents between floors based on cross-department meetings or collaboration.

### 7.2 Multi-Office Hierarchy

The CEO can manage multiple geographically separated or logical company offices:

```text
CEO Headquarters
   ├── Office Alpha (Core Platform Development)
   ├── Office Beta (R&D / Advanced Experiments)
   └── Office Gamma (Operations & Support)
```

The CEO and executives can navigate between offices via virtual transit/elevators, switching organizational context dynamically.

### 7.3 Event-Driven Spatial Behavior

Agent actions generate domain events that drive real-time 3D animations:

```text
Domain Event          3D Scene Manifestation
────────────────────  ──────────────────────────────────────────────────────
task.assigned         Agent walks from common area/elevator to assigned desk
task.working          Agent sits at terminal, typing/analyzing animations
approval.required     Agent stands up, walks to Department Head or CEO office
meeting.scheduled     Participants walk to scheduled conference room
meeting.in_progress   Participants seated around table, active speaker spotlight
task.completed        Agent heads to lounge area or takes next queue item
employee.released     Agent packs box, enters elevator, exits building
```

---

## 8. First-Class Meetings Engine

Meetings are formal domain entities, not simple chat channels:

```text
Meeting Lifecycle:
Draft → Called → Scheduled → Rooms Reserved → Participants Notified → In Progress → Adjourned → Minutes & Action Items Published
```

### Meeting Domain Structure
- **Metadata:** Unique Meeting ID, Subject, Objective, Agenda, Organizer.
- **Context:** Linked Department, Team, Project, or Lifecycle Stage.
- **Location:** Virtual Conference Room on designated floor.
- **Participants:** Attendees (Required / Optional), Roles (Chair, Scribe, Contributor).
- **Outputs:** Recorded transcript, extracted decisions, baseline impact items, generated tasks.
- **Governance Constraint:** Calling or speaking in a meeting does not confer decision authority; decisions must adhere to organizational policies.

---

## 9. Security, IAM, and Host Boundaries

### 9.1 IAM vs. Business Authorization Boundary

```text
┌─────────────────────────────────┐      ┌─────────────────────────────────┐
│        IAM LAYER (Rauthy)       │      │      OFFICE SERVICE DOMAIN      │
│  - Identity & Credentials       │      │  - Actor Identity Mapping       │
│  - Passkeys / WebAuthn / TOTP   │ OIDC │  - Founder / Employee Roles     │
│  - OIDC / OAuth 2.0 Tokens      │─────►│  - Department / Team Membership │
│  - User Authentication Audit    │      │  - Task / Project Permissions   │
└─────────────────────────────────┘      └─────────────────────────────────┘
```

Authentication is strictly isolated from business authorization:
- External IAM (Rauthy, with Kanidm fallback) handles user credentials, passkeys, sessions, and token issuance.
- The Office Service maps authenticated subjects to `HumanUser` and `Actor` records, managing business authorization and role assignments.
- The domain database never stores passwords or raw authentication credentials.

### 9.2 First-User Atomic Bootstrap

```text
1. Fresh Installation: Database empty, Office Service starts in UNREGISTERED state.
2. Founder connects via Web/PET UI and authenticates through Rauthy OIDC.
3. System checks: If no Owner exists:
   a. Atomically registers current user as Owner / Founder.
   b. Creates HumanUser and Actor record with sovereign authority.
   c. Initializes Root Organization and Headquarters Office.
   d. Instantiates CEO AI Employee (PET) with Position #001.
   e. Binds CEO Agent Runtime and enters OPERATIONAL state.
```

### 9.3 Host & OS Execution Boundary (Windows Tooling Gateway)

Agents never issue raw system calls or unrestricted terminal commands to the host environment:

```text
Agent Runtime
      │ (Typed Tool Invocation)
      ▼
Host Tool Gateway (Rust Core)
      │
      ├── Policy Engine & Permission Evaluator
      │     └── Requires Founder Approval for Sensitive Operations
      │
      ├── Secure Sandboxing & Audit Logging
      │
      ▼
Operating System Interop Layer (Windows API / CLI / Process)
      ├── Screen Capture / OCR
      ├── Window Management
      ├── Keyboard / Mouse (Restricted & Supervised)
      └── File System / Workspace Sandbox
```

---

## 10. Avatar & PET Presentation Architecture

PET's visual presentation is strictly decoupled from its core cognitive engine:

```text
CEO Agent Runtime (Cognitive / Reasoning)
      │
      ▼ (Emits Semantic State Events)
Semantic State Engine (idle, thinking, working, meeting, approval_required, etc.)
      │
      ▼
Animation & Expression Controller (Blends, IK, Gestures)
      │
      ▼
Avatar 3D Presentation Layer (Wardrobe, Mesh, Shading)
```

- **Semantic State Mapping:** The LLM does not manage raw bones or animation frames. It updates high-level semantic states (e.g., `listening`, `deliberating`, `presenting`, `error`).
- **Wardrobe as Semantic Signal:** Attire communicates connection status (e.g., casual attire during offline/disconnected states; formal blazer/jacket when connected and operational).
- **Multi-Avatar Roster:** 20 distinct avatar personas (Bulb, Nova, Draco, Sage, Foxy, Lumi, Bamboo, Orbit, Leafy, Cloudy, Pixel, Aura, Rocky, Spark, Aqua, Byte, Zen, Comet, Ivy, Neo) sharing a unified bone, expression, and semantic animation interface.

---

## 11. Authoritative Persistence Architecture

The storage tier combines relational integrity with graph traversal capabilities:

```text
┌────────────────────────────────────────────────────────┐
│             POSTGRESQL (Authoritative Store)           │
├───────────────────────────┬────────────────────────────┤
│     RELATIONAL TABLES     │      APACHE AGE GRAPH      │
│  - Organizations & Offices│  - Employee Reporting Tree │
│  - Departments & Teams    │  - Matrix Project Links    │
│  - Employees & Positions  │  - Meeting Attendance Graph│
│  - SDLC Stage Artifacts   │  - Artifact Provenance     │
│  - Policies & Audit Logs  │  - Impact & Dependency Net │
└───────────────────────────┴────────────────────────────┘
```

- **Relational Tables:** Authoritative system of record for transactions, state transitions, domain entities, and formal baselines.
- **Apache AGE:** Graph extension embedded directly within PostgreSQL, supporting fast Cypher queries for complex organizational traversals, cross-functional project teams, and end-to-end SDLC traceability graphs.

---

## 12. Rust Workspace & Implementation Structure

The platform is engineered as a high-performance, memory-safe Rust workspace:

```text
agentic/
├── Cargo.toml                      # Workspace definition
├── crates/
│   ├── domain/                     # Pure domain entities, value objects, invariants
│   ├── actor/                      # Actor abstraction (Human vs. AI) & identity
│   ├── agent-runtime/              # LLM adapters, memory runners, loop orchestrator
│   ├── office-core/                # Departments, teams, rooms, meetings, spatial logic
│   ├── office-api/                 # REST, WebSocket, and gRPC endpoints
│   ├── sdlc-engine/                # 9 SDLC modules & canonical lifecycle verification
│   ├── event-bus/                  # PubSub event router, typed domain events
│   ├── memory/                     # Episodic, working, and semantic vector memory
│   ├── policy/                     # Authorization, guardrails, approval gates
│   ├── tools/                      # Tool definitions, host boundary & sandbox
│   ├── repository/                 # PostgreSQL relational data access layer
│   ├── graph/                      # Apache AGE Cypher graph queries & sync
│   └── iam/                        # Rauthy OIDC integration & token verification
├── office/                         # Virtual office spatial schemas & assets
├── avatar/                         # Avatar definitions, semantic mappings, rig configs
├── migrations/                     # SQL & Apache AGE graph migration scripts
├── docs/                           # Architecture, guides, and lifecycle specs
└── tests/                          # Integration, end-to-end, and scenario test suites
```

---

## 13. System Integration Architecture

```text
                               ┌───────────────────────────┐
                               │   FOUNDER / HUMAN USER    │
                               └─────────────┬─────────────┘
                                             │ Web / 3D Client / PET
                                             ▼
                               ┌───────────────────────────┐
                               │      IAM (Rauthy OIDC)    │
                               └─────────────┬─────────────┘
                                             │ Authenticated Token
                                             ▼
                               ┌───────────────────────────┐
                               │   OFFICE API & GATEWAY    │
                               └──────┬─────────────┬──────┘
                                      │             │
                 ┌────────────────────┘             └────────────────────┐
                 ▼                                                       ▼
  ┌──────────────────────────────┐                        ┌──────────────────────────────┐
  │     OFFICE SERVICE CORE      │                        │     AGENTIC SDLC ENGINE      │
  │ - Organization / Depts       │◄─── Shared Events ───►│ - Canonical 16-Stage Cycle   │
  │ - Employees & Positions      │      & Trace Graph     │ - 9 Engineering Modules      │
  │ - Meetings & Physical Floors │                        │ - Artifact Baselining        │
  └──────────────┬───────────────┘                        └──────────────┬───────────────┘
                 │                                                       │
                 └────────────────────┬──────────────────────────────────┘
                                      ▼
                       ┌──────────────────────────────┐
                       │     AGENT HARNESS RUNTIME    │
                       │ - Actor Execution Loops      │
                       │ - Memory, Context, Skills    │
                       │ - Policy & Approval Guards   │
                       └──────────────┬───────────────┘
                                      │
                 ┌────────────────────┴────────────────────┐
                 ▼                                         ▼
  ┌──────────────────────────────┐          ┌──────────────────────────────┐
  │    PERSISTENCE LAYER         │          │   EXTERNAL & HOST GATEWAY    │
  │ - PostgreSQL (Authoritative) │          │ - Governed Windows OS Tools  │
  │ - Apache AGE (Graph Network) │          │ - LLM Providers / Sandboxes  │
  └──────────────────────────────┘          └──────────────────────────────┘
```

---

## 14. Document History & Baseline References

This unified system design supersedes isolated partial drafts and is based upon:
- `sources/AGENTIC_Canonical_Engineering_Lifecycle_v1.0.md`
- `sources/AGENTIC_Lifecycle_Deployment_Optional_Stage.md`
- `sources/AGENTIC_BP_System_Architecture_System_Architecture_v1.0.md`
- `sources/AGENTIC_System_Architecture_Domain_Model_v1.0.md`
- `sources/AGENTIC_Cross_Cutting_Human_Decision_Approval_v1.0.md`
- `sources/AGENTIC_Design_Knowledge_Architecture_v1.0.md`
- The Consolidated Autonomous Organization & Virtual Office Design Decision Baseline (Sections 1–29).
