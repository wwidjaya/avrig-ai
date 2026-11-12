# Agentic Engineering 5-Generation Maturity Model

## Purpose

This model describes five increasing levels of autonomy on one Agentic Engineering foundation. The generations are maturity levels, not separate products. Each level changes who initiates, decides, executes, supervises, and adapts engineering work.

## Consolidated model

| Generation | Name | Agent role | Primary autonomy | Human role |
|---|---|---|---|---|
| **G1** | AI-Assisted Engineering | Assistant | L1 | Engineer |
| **G2** | AI-Augmented Engineering | Proactive Advisor | L2 | Decision Maker |
| **G3** | AI-Executed Engineering | Engineering Executor | L3 | Approver |
| **G4** | AI-Supervised Engineering | Autonomous Operator | L4 | Supervisor |
| **G5** | Autonomous Engineering | Autonomous Engineering System | L5 | Strategic Authority |

### Progression

```text
G1  HELP ME DO IT
       ↓
G2  TELL ME WHAT I SHOULD DO
       ↓
G3  DO IT FOR ME WITH APPROVAL
       ↓
G4  RUN IT AND ASK ME WHEN NECESSARY
       ↓
G5  ACHIEVE THE OBJECTIVE WITHIN MY GOVERNED BOUNDARIES
```

## Generation definitions

### G1: AI-Assisted Engineering

The human engineer directs the work and asks the agent for assistance. The agent responds to explicit requests, helps produce or understand engineering artifacts, and leaves decisions and execution under human control.

- **Agent role:** Assistant
- **Autonomy:** L1, assistance on request
- **Human role:** Engineer who directs, evaluates, and performs the work
- **Operating pattern:** Human asks; agent assists

### G2: AI-Augmented Engineering

The agent can use available context to identify issues, opportunities, or next steps and make proactive recommendations. The human evaluates the advice and decides what to do.

- **Agent role:** Proactive Advisor
- **Autonomy:** L2, analysis and recommendations
- **Human role:** Decision Maker
- **Operating pattern:** Agent observes and recommends; human decides

### G3: AI-Executed Engineering

The agent can plan and execute defined engineering work after a human approves the proposed execution. The agent produces results for human review, with approval remaining a control point before execution or consequential actions.

- **Agent role:** Engineering Executor
- **Autonomy:** L3, execution with human approval
- **Human role:** Approver
- **Operating pattern:** Agent plans; human approves; agent executes

### G4: AI-Supervised Engineering

The agent can execute multi-step engineering work within defined authority, continuously supervise its activity, detect problems, recover from expected failures, and escalate when authority, confidence, or safety is insufficient. The human does not need to approve every step.

- **Agent role:** Autonomous Operator
- **Autonomy:** L4, execution with continuous supervision
- **Human role:** Supervisor and exception decision maker
- **Operating pattern:** Agent plans and executes; agent supervises; human intervenes when needed
- **Control behavior:** Continue when normal, reduce autonomy when uncertain, recover or escalate on exceptions, and stop and escalate on violations

### G5: Autonomous Engineering

Agents autonomously plan, execute, evaluate, adapt, and continuously improve engineering work across the lifecycle. Humans retain authority over strategic objectives, governance, critical decisions, and defined autonomy boundaries.

- **Agent role:** Autonomous Engineering System
- **Autonomy:** L5, bounded autonomous execution
- **Human role:** Strategic Authority
- **Operating pattern:** The system determines and executes next actions to achieve objectives within delegated authority, evaluates outcomes, and adapts its strategy

G5 autonomy is bounded. It grants the system authority to determine and execute actions inside explicit organizational, project, and governance boundaries. It does not imply unrestricted authority over strategic, regulatory, or critical decisions.

## Human role progression

```text
G1  Human Engineer
        ↓
G2  Human Decision Maker
        ↓
G3  Human Approver
        ↓
G4  Human Supervisor
        ↓
G5  Human Strategist / Authority
```

Across the generations, humans increasingly set objectives, policies, governance, risk tolerance, authority boundaries, and autonomy limits. They retain responsibility for consequential decisions and exceptions while the system assumes a larger share of execution.

## Cross-cutting capability evolution

The same ten capabilities mature as autonomy increases. The table summarizes their progression from G1 through G5.

| Capability | G1: AI-Assisted | G2: AI-Augmented | G3: AI-Executed | G4: AI-Supervised | G5: Autonomous |
|---|---|---|---|---|---|
| **Knowledge Management** | Uses knowledge supplied for the current request | Retrieves relevant knowledge to inform recommendations | Applies approved knowledge during execution | Continuously consumes contextual project knowledge | Maintains and uses continuous organizational and project knowledge |
| **Semantic Management** | Uses terms and definitions provided by the human | Detects and clarifies semantic issues in recommendations | Applies agreed semantics to generated and changed artifacts | Monitors semantic consistency at runtime | Maintains enterprise-wide semantic consistency |
| **Human Decision** | Human directs each task and decision | Human chooses among recommendations | Human approves planned execution and consequential actions | Human handles exceptions and high-impact decisions | Human retains strategic and consequential authority |
| **Traceability** | Human reviews outputs and source context | Recommendations include supporting context | Execution steps and outputs are recorded for review | Execution is continuously traceable | Autonomous engineering has continuous end-to-end explanation and traceability |
| **Impact Analysis** | Human identifies impacts with agent assistance | Agent identifies likely impacts for human decision | Agent analyzes impacts before approved execution | Agent assesses impacts dynamically during execution | System reasons predictively and adaptively about impacts across the lifecycle |
| **Collaboration** | Human works with one assistant | Human and proactive advisor exchange context | Human and executor coordinate around approval points | Human intervention becomes exception-driven | Humans and multiple specialized agents collaborate within a governed system |
| **Governance** | Human applies governance to each activity | Agent surfaces relevant policies and constraints | Agent follows controls attached to approved work | Policies and controls are continuously enforced | Governance is embedded and continuously enforced across autonomous work |
| **Context & Reasoning** | Request-scoped context and reasoning | Broader context supports proactive advice | Context supports planning and execution | Persistent context spans execution chains | Persistent strategic reasoning spans the engineering system |
| **Lifecycle Orchestration** | Human coordinates lifecycle stages | Agent recommends sequencing and dependencies | Agent executes approved stages | Agent autonomously coordinates multiple stages | System autonomously orchestrates work across the lifecycle |
| **Autonomy & Control** | Human controls all consequential actions | Agent recommends; human controls action | Agent executes within explicit approvals | Dynamic autonomy, supervision, recovery, and escalation | Delegated autonomy is dynamic, governed, and measurable |

## Architectural conclusion

The five generations are not five separate products. They are increasing levels of autonomy operating on the same Agentic Engineering foundation. The same lifecycle and control fabric can support G1 through G5; the primary difference is who initiates, decides, executes, supervises, and adapts.

```text
                 ┌─────────────────────────────────┐
                 │         HUMAN AUTHORITY          │
                 │ Strategy • Decisions • Governance│
                 └────────────────┬────────────────┘
                                  │
                 ┌────────────────▼────────────────┐
                 │      AGENTIC CONTROL FABRIC      │
                 │                                 │
                 │ Knowledge                       │
                 │ Semantics                       │
                 │ Context & Reasoning             │
                 │ Traceability                    │
                 │ Impact Analysis                 │
                 │ Collaboration                   │
                 │ Human Decision                  │
                 │ Governance                      │
                 │ Lifecycle Orchestration         │
                 │ Autonomy & Control              │
                 └────────────────┬────────────────┘
                                  │
                 ┌────────────────▼────────────────┐
                 │       ENGINEERING LIFECYCLE     │
                 │                                 │
                 │ Vision → Strategy → Business    │
                 │ → Requirements → Data → UX      │
                 │ → Architecture → Technology     │
                 │ → Development → Test            │
                 │ → Deployment (Optional)         │
                 └─────────────────────────────────┘
```

The platform's target is not merely workflow automation. At G5 it can understand an engineering objective, reason across lifecycle context, choose and coordinate actions, execute within delegated boundaries, validate outcomes, learn from evidence, and adapt its strategy. Human authority remains at the strategic and governance layer.

## Success criterion

> How effectively can the Agentic Engineering system achieve engineering objectives autonomously while remaining trustworthy, explainable, governed, recoverable, and aligned with human intent?
