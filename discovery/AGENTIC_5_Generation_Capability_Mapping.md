# Agentic Engineering 5-Generation Capability Mapping

## 1. Purpose and status

This document maps the approved five-generation Agentic Engineering maturity model against the ten cross-cutting capability domains. It identifies capabilities required at each generation, autonomy and human-control expectations, architectural implications, and progression gates.

The mapping is a design baseline for review. It preserves the project authority rule: Agent-generated outcomes are non-authoritative by default, and an Agent cannot approve its own recommendation or baseline. The named L1 through L5 autonomy labels are retained from the approved maturity model; this document does not define numeric thresholds for them.

The ten domains are a shared control fabric across the lifecycle, not new lifecycle stages. The canonical lifecycle remains unchanged. Lifecycle Orchestration determines what happens next; Agentic Autonomy & Control determines how much the Agent may decide and act, within which boundaries, and when control returns to a human.

## 2. Generation summary

| Generation | Name | Agent role | Autonomy | Human role | Control pattern |
|---|---|---|---|---|---|
| G1 | AI-Assisted Engineering | Assistant | L1 | Engineer | Human directs and performs work; Agent assists on request. |
| G2 | AI-Augmented Engineering | Proactive Advisor | L2 | Decision Maker | Agent analyzes and recommends; human decides. |
| G3 | AI-Executed Engineering | Engineering Executor | L3 | Approver | Agent plans; human approves; Agent executes approved work. |
| G4 | AI-Supervised Engineering | Autonomous Operator | L4 | Supervisor | Agent executes within authority and supervises; human handles exceptions and consequential decisions. |
| G5 | Autonomous Engineering | Autonomous Engineering System | L5 | Strategic Authority | System pursues objectives across lifecycle within delegated boundaries; human governs strategy and authority. |

## 3. Cross-cutting capability progression

| Capability domain | G1: AI-Assisted | G2: AI-Augmented | G3: AI-Executed | G4: AI-Supervised | G5: Autonomous |
|---|---|---|---|---|---|
| **Knowledge Management (KM)** | Human supplies relevant project facts and references for the current request. Agent distinguishes supplied material from inference. | Agent retrieves relevant Platform Knowledge and Project Knowledge to support analysis and recommendations. Conflicts and source authority are surfaced. | Agent uses approved knowledge and records the sources that informed plans and outputs. | Agent maintains current contextual knowledge during execution, notices changed or conflicting inputs, and pauses or escalates when authority is unclear. | System continuously uses validated organizational and project knowledge across objectives. Project authority takes precedence over generic guidance; validated lessons may be proposed for reuse but are not silently promoted. |
| **Glossary & Semantic Management (GSM)** | Agent follows human-provided terms and asks about material ambiguity. | Agent identifies inconsistent, missing, or ambiguous terms and proposes definitions for human review. | Agent uses approved terminology in generated artifacts and flags changes to meanings for approval. | Agent checks semantic consistency across related artifacts during execution and escalates unresolved conflicts. | System maintains semantic consistency across projects and lifecycle artifacts, with governed project-specific vocabularies and explicit authority for changes. |
| **Human Decision & Approval (HDA)** | Human directs and decides each material step. Agent output remains a proposal. | Human reviews recommendations and chooses adopt, modify, reject, defer, or request revision. Decisions and rationale are recorded when material. | Required human approval is an explicit precondition for execution or authoritative state changes. Agent cannot self-approve. | Human approval is not required for every bounded execution step; material, high-impact, policy-defined, and reserved decisions route to a human. All decisions remain recorded. | Human retains strategic and consequential authority. Delegated decisions are explicit, constrained, observable, auditable, and revocable. Agent cannot approve its own recommendation or bypass reserved authority. |
| **Traceability Management (TRM)** | Agent identifies prompt inputs and source artifacts used in its response. | Recommendations link to evidence, sources, assumptions, and relevant project artifacts. | Plans, approved decisions, changed artifacts, and validation evidence are linked. | Execution actions and outcomes are continuously traceable across the work chain; gaps or broken links trigger review. | End-to-end, version-aware traceability explains objective-to-outcome reasoning, evidence, decisions, actions, and learning across lifecycle boundaries. |
| **Impact Analysis Management (IAM)** | Human leads impact analysis; Agent helps identify obvious related artifacts. | Agent proposes likely impacts and uncertainties for human assessment. | Agent analyzes impacts before approved changes and includes consequences in the approval package. | Agent reassesses impacts as conditions or artifacts change during execution and can pause, re-plan within authority, or escalate. | System predicts and adapts to cross-lifecycle effects while honoring constraints. High-consequence or uncertain impacts trigger human decision or restricted autonomy. |
| **Collaboration Management (CM)** | Direct human-Agent exchange on a bounded task. | Agent proactively raises questions, alternatives, and conflicts for human decision. | Collaboration is organized around plan review, approval, execution updates, and result review. | Human participation becomes exception-driven; Agent requests clarification or escalation when necessary and preserves discussion context. | Human and multiple specialized Agents coordinate as participants in a governed engineering system, with clear responsibilities, shared context, conflict resolution, and decision provenance. |
| **Governance Management (GOV)** | Human applies applicable policies; Agent surfaces known constraints and does not claim approval. | Agent checks recommendations against known policies and identifies possible conflicts. | Approved scope, version, and authority are recorded before execution; changes to authoritative baselines follow governance. | Controls are enforced during execution; violations stop or restrict action and are escalated. Recovery is allowed only within authority. | Governance is continuously enforced across dynamic plans and multi-agent actions. Authority, baselines, exceptions, releases, and audit remain governed. Autonomy never removes required human decisions. |
| **Agent Context & Reasoning Management (ACRM)** | Request-scoped context, with explicit distinction between facts, requirements, practice, inference, and unknowns. | Agent gathers broader relevant context and explains rationale, evidence, assumptions, and uncertainty. | Context supports a reviewable plan, approved scope, execution, and result comparison. | Persistent context spans execution chains; assumptions and constraints are monitored for change. | Persistent strategic context supports adaptive, cross-lifecycle reasoning from objective through validated outcome, with provenance and context boundaries maintained. |
| **Lifecycle Orchestration Management (LOC)** | Human selects the lifecycle task and next stage; Agent supports that stage. | Agent recommends sequencing, dependencies, and next steps; human chooses. | Agent prepares and performs explicitly approved lifecycle work; transitions remain governed. | Agent coordinates multiple lifecycle stages and feedback loops within delegated scope; it reports state and escalates blocked or consequential transitions. | System dynamically determines next actions across the canonical lifecycle to achieve the objective, while respecting stage outputs, dependencies, optional Deploy, and governance transitions. |
| **Agentic Autonomy & Control Management (AUC)** | Human retains control of decisions and actions; Agent assists without independent consequential action. | Agent may analyze and recommend proactively; human authorizes action. | Agent may act only within explicitly approved plan and scope; approval gates precede consequential execution. | Agent has bounded execution authority, monitors conditions, reduces autonomy under uncertainty, recovers from known failures, and stops/escalates on violations or authority limits. | Delegated autonomy is dynamic, measurable, observable, and earned through validated performance. System chooses actions inside explicit boundaries, while human authority, governance, intervention, and revocation remain available. |

## 4. Generation capability profiles

### G1: AI-Assisted Engineering

**Outcome:** The human engineer can use an Agent to improve the quality and speed of a task while retaining direction, decisions, and execution responsibility.

**Required capabilities:** Request-scoped context and reasoning; source-aware knowledge use; basic terminology handling; evidence references; collaboration through direct exchange; human-controlled lifecycle sequencing; explicit non-authoritative status for generated proposals; human-owned governance.

**Human control:** Human provides scope and context, evaluates output, decides what to adopt, and performs or directs all consequential actions. Agent asks when ambiguity materially affects the result.

**Architecture implications:** Provide project context boundaries, source references, artifact input/output conventions, and a clear distinction between candidate and approved artifacts. Preserve project knowledge separately from reusable platform guidance.

**Gate to G2:** Demonstrate reliable source attribution and separation of facts, requirements, existing practice, best practice, inference, and unknowns. Humans can review and correct output. No generated content becomes authoritative without explicit human adoption and applicable governance.

### G2: AI-Augmented Engineering

**Outcome:** The Agent can notice relevant information and provide useful recommendations before the human specifies every analysis step.

**Required capabilities:** Retrieval across authorized project and platform knowledge; semantic ambiguity detection; recommendation rationale and alternatives; impact hypotheses; policy awareness; contextual collaboration; lifecycle sequencing advice; traceable evidence and uncertainty.

**Human control:** Human remains the decision maker. Material recommendations include sources, assumptions, constraints, risks, dependencies, confidence or uncertainty, and potential impact. Human decisions are recorded when material.

**Architecture implications:** Add controlled retrieval, knowledge precedence, recommendation records, conflict surfacing, contextual decision packages, and a visible distinction between analysis and approved state.

**Gate to G3:** Recommendations are consistently evidence-backed and reviewable across representative lifecycle tasks. The system reliably identifies conflicts and uncertainty, and decision records can link recommendations to adopted outcomes. Human authority remains explicit.

### G3: AI-Executed Engineering

**Outcome:** The Agent can carry out a bounded engineering plan after the authorized human approves it.

**Required capabilities:** Plan generation with scope and dependencies; approval workflow; permissioned tools; change tracking; execution traceability; pre-execution impact analysis; validation evidence; rollback or recovery plan where applicable; governance of baselines and releases.

**Human control:** Approval is an explicit precondition for execution at defined authority points. Human decisions determine approved scope, boundaries, and outcome. The Agent cannot approve its own proposal or silently expand scope.

**Architecture implications:** Separate proposal, approved plan, execution, and resulting baseline states. Enforce permissions at action time, record approved plan versions, connect actions to artifacts and evidence, and block execution if approval is stale or scope has changed.

**Gate to G4:** Approved execution is repeatable, auditable, constrained to scope, and validated. Permission enforcement, action logs, baseline integrity, failure handling, and stop controls have been demonstrated. High-impact reserved decisions remain human-controlled.

### G4: AI-Supervised Engineering

**Outcome:** The Agent can execute a multi-step workflow without approval at every step, while continuously checking safety, authority, assumptions, outcomes, and policy.

**Required capabilities:** Runtime policy enforcement; continuous state and context monitoring; uncertainty and risk detection; dynamic impact analysis; controlled retry and recovery; autonomy escalation and de-escalation; stop and human escalation; continuous traceability; exception-centered collaboration.

**Human control:** Humans set objective, policy, and boundaries, supervise outcomes, and decide exceptions and consequential matters. Agent stops or reduces autonomy when confidence, authority, policy compliance, or expected outcome is insufficient.

**Architecture implications:** Implement explicit control states and policy checks at action boundaries. Track autonomy grants, revocation, state transitions, risk signals, and escalation reasons. Support safe interruption, idempotent actions where possible, recovery limits, and human takeover.

**Gate to G5:** Sustained evidence shows bounded workflows remain within policy, detect meaningful uncertainty, stop safely, recover only within delegated authority, escalate appropriately, and provide complete traceability. Human override and revocation work reliably. No autonomy claim is based only on successful normal-path runs.

### G5: Autonomous Engineering

**Outcome:** The system can pursue an engineering objective across the lifecycle, dynamically choose and coordinate actions, evaluate outcomes, and adapt within governed boundaries.

**Required capabilities:** Persistent strategic context; cross-lifecycle knowledge and semantic coherence; predictive impact reasoning; dynamic lifecycle orchestration; multi-agent coordination; continuous governance; evidence-based learning; adaptive planning; measurable and revocable autonomy; end-to-end explanation.

**Human control:** Humans define objectives, strategy, risk tolerance, reserved decisions, policies, and authority boundaries. They can inspect reasoning and evidence, intervene, revise delegation, revoke autonomy, or stop work. Strategic, regulatory, and other reserved decisions remain human-owned unless explicitly delegated through governance.

**Architecture implications:** The control fabric coordinates lifecycle models, specialized capabilities, agents, policies, knowledge, traceability, and decision records. Each action is authorized against current context and delegated scope. Learning is evaluated and validated before becoming reusable knowledge or policy.

**G5 success criterion:** The system achieves engineering objectives effectively while remaining trustworthy, explainable, governed, recoverable, traceable, and aligned with human intent.

## 5. Cross-generation control rules

1. Agent-generated content is non-authoritative by default.
2. Human decisions establish whether recommendations are adopted; decisions may be adopt, modify, reject, defer, or request revision.
3. An Agent cannot approve its own recommendation or baseline.
4. Project Knowledge is project-specific authority; reusable Platform Knowledge guides proposals and does not override project requirements.
5. Lifecycle Orchestration and Autonomy & Control are distinct: one selects what happens next; the other constrains how the Agent may act.
6. Autonomy is explicitly granted, constrained by policy and context, observable during execution, and progressively earned through validated performance.
7. Traceability, governance, and human authority apply at every generation. They become more automated and continuous as autonomy increases, but are never removed.
8. Deployment remains an optional governed transition after Test. Engineering completion and deployment authorization are separate outcomes.
9. Changes in context, authority, policy, assumptions, or risk can reduce autonomy or return control to a human.
10. Capability maturity should be assessed by demonstrated evidence and boundary adherence, not by the number of tools or agents available.

## 6. Maturity progression gates

| Transition | Evidence required before progressing |
|---|---|
| **G1 → G2** | Reliable context and source use; clear fact/inference distinction; reviewable outputs; controlled knowledge precedence; human adoption and governance remain explicit. |
| **G2 → G3** | Evidence-backed recommendations; uncertainty and conflicts surfaced; complete decision records for material outcomes; consistent human authority. |
| **G3 → G4** | Enforced approval and scope; action-level permissions; auditable execution; validated outputs; reliable stop, rollback/recovery, and baseline controls. |
| **G4 → G5** | Demonstrated runtime supervision; bounded recovery; calibrated escalation and autonomy reduction; reliable human override and revocation; sustained end-to-end traceability and policy adherence. |

Progression is capability-based, not automatic. A system may use different autonomy levels for different actions, lifecycle stages, risk classes, or projects. Delegation must match evidence and governance for that scope.

## 7. Recommended validation sequence

1. Review and approve the G1 capability profile and its G1-to-G2 evidence gate.
2. Validate each capability domain against the current project source models and identifiers, without merging cross-cutting KM/GSM/HDA/TRM/IAM/CM/GOV/ACRM/LOC/AUC families into stage-specific families such as DMC, SAC, TAC, DEC, or DPC.
3. Define representative workflows and risk classes for measuring each gate.
4. Define measurable acceptance thresholds for evidence quality, policy adherence, escalation, recovery, and outcome quality. Threshold values are intentionally left for project approval.
5. Map approved capability requirements to platform components, interfaces, records, and implementation increments.
6. Return to detailed lifecycle and business-process design after the maturity architecture has been validated.

## 8. Decisions still required

- What representative lifecycle workflows will serve as maturity evidence at each gate?
- Which actions and decisions are reserved for humans at each autonomy level?
- What risk classes require mandatory approval, reduced autonomy, or stop-and-escalate behavior?
- What metrics and thresholds demonstrate trustworthy performance and appropriate escalation?
- How should autonomy vary by project, lifecycle stage, action type, and risk?
- What governance process authorizes, reviews, expires, and revokes autonomy grants?
