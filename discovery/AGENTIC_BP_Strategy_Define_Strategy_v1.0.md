# AGENTIC Strategy Process

**Process:** Define Strategy\
**Lifecycle Stage:** Strategy\
**Status:** Approved Baseline

## 1. Purpose

Define and approve the strategic approaches for achieving the approved
Mission Set.

Unlike Vision and Mission, the Strategy process is **agent-proposed
first**. AGENTIC analyzes the approved Mission Set and available Project
Context and proposes candidate strategies for the user to review and
revise.

## 2. Process Flow

``` text
Approved Mission Set
        ↓
Agent proposes Strategy
        ↓
User reviews
        ↓
User revises / clarifies
        ↓
        ┌─────┴─────┐
        │           │
   Needs changes   Sufficient
        │           │
        └──→ Agent ─┘
             refines
                ↑
                │
        multiple rounds
                │
                ↓
          User approves
                ↓
       Approved Strategy Set
```

The core pattern is:

``` text
INPUT
  ↓
AGENT PROPOSES
  ↓
REVIEW ↔ REVISE
  ↓
APPROVE
  ↓
OUTPUT
```

## 3. Activities

  --------------------------------------------------------------------------
  ID             Activity       Performer      Description    Output
  -------------- -------------- -------------- -------------- --------------
  S-01           Propose        Agent          Analyze the    Proposed
                 Strategy                      approved       Strategy Set
                                               Mission Set    
                                               and available  
                                               Project        
                                               Context and    
                                               propose one or 
                                               more strategic 
                                               approaches for 
                                               achieving the  
                                               Missions.      

  S-02           Review /       User + Agent   User reviews   Revised
                 Revise                        the proposed   Strategy Set
                 Strategy                      strategies,    
                                               revises or     
                                               clarifies      
                                               them, and the  
                                               Agent refines  
                                               the proposal   
                                               accordingly.   

  S-03           Approve        User           Explicitly     Approved
                 Strategy                      approve the    Strategy Set
                                               Strategy Set   
                                               as the basis   
                                               for the        
                                               Business       
                                               Capability     
                                               stage.         
  --------------------------------------------------------------------------

## 4. Iteration

Activities **S-01** and **S-02** may be repeated multiple times.

``` text
Round 1
Agent → User → Agent

Round 2
Agent → User → Agent

Round 3
Agent → User → Agent

...

Final
User → Approve
```

The number of rounds is not predetermined.

The iteration ends when the user considers the Strategy Set sufficiently
clear and appropriate and approves it.

The iteration itself is **not modeled as additional process
activities**. It is a repeatable execution of the Propose and Review /
Revise activities.

## 5. Strategy Multiplicity

The process supports one or multiple Strategies.

``` text
Mission Set
    ↓
Strategy A
Strategy B
Strategy C
```

AGENTIC may propose multiple strategies when different strategic
approaches are meaningful.

A separate Strategy should not be created merely to fragment one
coherent approach.

A useful rule is:

> Create a separate Strategy when it represents a distinct major
> approach for achieving one or more Missions.

## 6. User Authority

The Agent proposes and refines strategies, but the **user remains the
decision maker**.

The Agent must not treat its proposed Strategy as approved until the
user explicitly approves it.

``` text
Agent Proposal
      ↓
User Review / Revision
      ↓
Agent Refinement
      ↓
User Approval
```

## 7. Clarification Behavior

Clarification is conditional.

AGENTIC should ask questions only when ambiguity materially affects the
strategic recommendation or when an important decision cannot reasonably
be inferred from the available Project Context and Mission Set.

If the strategy is sufficiently clear:

``` text
Approved Mission Set
      ↓
Agent Proposes Strategy
      ↓
User Reviews
      ↓
Approve
```

No unnecessary clarification round is required.

## 8. Approval

Approval is an explicit user action.

The Strategy process is complete only when the user approves the
resulting Strategy Set.

``` text
Proposed / Revised Strategy Set
          ↓
       User Approval
          ↓
    Approved Strategy Set
```

The approved Strategy Set becomes the input to the **Business
Capability** stage.

## 9. Process Design Principle

The Strategy process follows the AGENTIC principle:

> Keep every process as simple as possible and introduce only the
> information, activities, decisions, and controls necessary to produce
> a usable downstream output.

The Agent takes more initiative at the Strategy stage, while the user
retains review, revision, and approval authority.
