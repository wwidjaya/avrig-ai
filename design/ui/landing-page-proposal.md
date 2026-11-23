# Landing Page Design Proposal

**Status:** Proposed approach for review  
**Scope:** Public landing page for avrig-ai  
**Decision authority:** User  
**Basis:** Vault discovery UX process, canonical engineering lifecycle, cross-cutting human decision and approval, and the approved AVRIG-00002 visual direction

## Proposal

Position the landing page as a clear introduction to a governed engineering process. A visitor should understand three things quickly: Avrig organizes software work through a defined lifecycle, AI employees prepare and execute work, and a human retains authority over consequential decisions and approved baselines.

The page should invite the visitor to inspect how this process works. It should not claim that a live organization, agent, project, service, or verification is active unless the product can verify that state.

## Audience and visitor questions

- **Prospective user:** What does Avrig help me organize, and how does work move through it?
- **Founder or engineering lead:** What decisions remain mine, and how can I inspect the evidence?
- **Returning user:** Where do I enter the workspace?

The primary action is **Open the workspace** or **Sign in**, depending on the visitor's authentication state. The secondary action is **See how it works**, which moves to the lifecycle explanation.

## Proposed page structure

1. **Quiet navigation**: wordmark, How it works, Governance, and a sign-in action. Keep the menu short.
2. **Hero**: direct headline, one short explanation, one primary action, and one secondary anchor link.
3. **Lifecycle preview**: show the canonical journey as a sequence grouped for readability without implying that stages can be skipped or reordered.
4. **Human decision model**: explain that agents analyze, recommend, and execute permitted work while humans decide and approve.
5. **Evidence and traceability**: explain version-pinned artifacts, sources, and links between requirements, implementation, tests, and approved outcomes.
6. **Organization and execution**: introduce employees, departments, projects, and ephemeral agent runtimes as distinct concepts. Keep this section concise.
7. **Closing action and footer**: repeat the workspace entry and provide only real policy or product links.

## Hero concept: the reviewable stage record

Use an asymmetric split: explanatory copy on the left and a designed stage record on the right. The record illustrates the kind of evidence a user can inspect: stage name, status, checklist, linked artifact versions, and a human decision mark when the example is approved.

The certificate visual from the existing design is a strong motif, but its sample data must be treated as illustrative and labelled as an example. Use only identifiers and claims verified against project data. Never show invented hashes or imply that a sample is current production state. The record can link to a clearly labelled workspace preview.

If no suitable approved baseline can be represented truthfully, replace the certificate with a neutral lifecycle specimen that does not claim approval. The visual should be built from HTML and CSS so its labels remain selectable and accessible.

## Visual approach

Retain the approved direction from AVRIG-00002:

- Warm paper and ink neutrals, thin rules, precise alignment, and restrained solid blue.
- A drawing-office and inspection-bench character, with the artifact as the main visual moment.
- Sentence case, readable serif display type paired with a practical sans-serif and mono metadata.
- Square approval mark only where an actual human-approved artifact is shown.
- No fake terminals, glowing grids, generic AI sparkles, ornamental pills, unsupported operational status, or decorative motion.

The page should feel like a trustworthy software product, not a literal paper document. Use the material cues sparingly so reading and navigation remain the focus.

## Content principles

- Explain product outcomes in concrete language, not abstract platform labels.
- Describe the lifecycle as the canonical engineering sequence. Deployment is optional only where the approved lifecycle baseline says so.
- Distinguish an agent recommendation from a human decision, formal artifact approval, and governance of the resulting baseline.
- Describe epistemic status where relevant. Do not style agent inference as an authoritative requirement.
- Keep claims verifiable. Avoid uptime, readiness, autonomy, or completion claims unless supported by observed product state.
- Avoid framing the product as an unrestricted autonomous developer. Its value includes organized, observable, traceable work under shared governance.

## Interaction and responsive behavior

- Navigation links move to named sections. The sign-in action enters the existing authentication flow.
- The hero specimen is explanatory, not a fake live dashboard. If it links to a record, that record must be available to the visitor.
- At desktop widths, use a two-column hero and a horizontal lifecycle overview.
- At narrow widths, stack content in reading order: headline and actions first, specimen next, then lifecycle and governance sections.
- Keep keyboard focus visible, provide a skip link, use semantic landmarks, and ensure status is not communicated by colour alone.
- Respect reduced motion. Any entrance transition is subtle and nonessential.

## Traceability to discovery

| Discovery principle | Landing page expression |
|---|---|
| Agent proposes; human decides | Explain agent and human responsibilities separately |
| Recommendations are not authoritative by default | Label examples and distinguish proposal from approved outcome |
| Canonical lifecycle remains ordered | Show stages in sequence and label any optional deployment stage accurately |
| Artifacts and decisions require traceability | Show versioned evidence and source relationships |
| UI/UX design preserves approved user stories and rules | Treat page copy and interactions as presentation, not new product behavior |
| UI/UX prototype is reviewed before approval | Keep this document a proposal until the user confirms the approach |

## Trade-offs and alternatives

| Choice | Benefit | Trade-off |
|---|---|---|
| Lead with governed lifecycle and evidence | Differentiates Avrig through its actual operating model | Requires concise explanation for visitors unfamiliar with lifecycle engineering |
| Use a stage record as the hero visual | Demonstrates inspectable output and the human approval boundary | Must carefully label mock data and avoid implying a live approval |
| Keep the top navigation short | Preserves focus on understanding and entry | Deep product areas are introduced lower on the page |
| Keep warm editorial styling | Aligns with the approved product character | Needs careful contrast and spacing to preserve a software-product feel |

## Decisions requested

1. Confirm whether the landing page should primarily address prospective users, returning workspace users, or give both equal weight.
2. Confirm the hero visual: an explicitly illustrative stage record, or a lifecycle diagram with no example artifact data.
3. Confirm whether Organization and execution should have a dedicated landing section or remain inside the lifecycle and product explanation.

Once the approach is confirmed, the next step is to revise the UI/UX specification and build a coherent runnable prototype with labelled mock data and reviewable interactions, following the discovery UX process.

## Source references

- Vault discovery: `AGENTIC_BP_UI_UX_Design_UI_UX_Design_v1.0.md`
- Vault discovery: `AGENTIC_Canonical_Engineering_Lifecycle_v1.0.md`
- Vault discovery: `AGENTIC_Cross_Cutting_Human_Decision_Approval_v1.0.md`
- Repository design: `design/ui/AVRIG-00002/design.md`
