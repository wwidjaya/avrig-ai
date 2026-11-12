# AGENTIC Vision Process

**Process:** Define Vision\
**Lifecycle Stage:** Vision\
**Status:** Approved Baseline

## 1. Purpose

Define and approve the desired future state that the Project intends to
create.

The process is intentionally simple. The user provides an initial vision
in any suitable form, and AGENTIC helps expand, clarify, and refine it
until the user approves the result.

## 2. Process Flow

``` text
User provides simple Vision definition
              ↓
      Agent generates / expands
              ↓
      User reviews / clarifies
              ↓
        ┌─────┴─────┐
        │           │
   Needs changes   Clear
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
        Approved Vision
```

The core pattern is:

``` text
INPUT
  ↓
GENERATE
  ↓
REFINE ↔ CLARIFY
  ↓
APPROVE
  ↓
OUTPUT
```

## 3. Activities

  -----------------------------------------------------------------------------
  ID             Activity       Performer      Description       Output
  -------------- -------------- -------------- ----------------- --------------
  V-01           Provide Vision User           Provide a simple  Initial Vision
                 Definition                    description of    
                                               the desired       
                                               future state. The 
                                               input may be      
                                               informal and does 
                                               not require a     
                                               predefined        
                                               template.         

  V-02           Generate /     Agent          Interpret the     Proposed
                 Expand Vision                 user's definition Vision
                                               and develop it    
                                               into a clear,     
                                               coherent Vision.  

  V-03           Refine /       User + Agent   Review the        Refined Vision
                 Clarify Vision                proposed Vision,  
                                               identify          
                                               ambiguity or      
                                               unwanted          
                                               interpretation,   
                                               clarify intent,   
                                               and refine the    
                                               Vision.           

  V-04           Approve Vision User           Explicitly        Approved
                                               approve the       Vision
                                               Vision as the     
                                               basis for the     
                                               next lifecycle    
                                               stage.            
  -----------------------------------------------------------------------------

## 4. Iteration

Activities **V-02** and **V-03** form an iterative loop.

The loop may occur multiple times:

``` text
Round 1
User → Agent → User

Round 2
User → Agent → User

Round 3
User → Agent → User

...

Final
User → Approve
```

The number of rounds is not predetermined.

The iteration ends when the user considers the Vision sufficiently clear
and approves it.

The iteration itself is **not modeled as additional process
activities**. It is a repeatable execution of the Generate / Expand and
Refine / Clarify activities.

## 5. Clarification Behavior

Clarification should be conditional.

AGENTIC should ask questions only when ambiguity materially affects the
Vision or its downstream interpretation.

If the initial definition is already sufficiently clear:

``` text
User Input
    ↓
Agent Generate / Expand
    ↓
User Review
    ↓
Approve
```

No unnecessary clarification round is required.

## 6. Approval

Approval is an explicit user action.

The Vision process is complete only when the user approves the resulting
Vision.

``` text
Proposed / Refined Vision
          ↓
     User Approval
          ↓
    Approved Vision
```

The approved Vision becomes the input to the **Mission** stage.

## 7. Process Design Principle

The Vision process follows the AGENTIC principle:

> Keep every process as simple as possible and introduce only the
> information, activities, decisions, and controls necessary to produce
> a usable downstream output.

Iteration is handled through a loop rather than by creating additional
workflow stages.
