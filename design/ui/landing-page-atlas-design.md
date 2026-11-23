# Landing Page Atlas Design

**Status:** Alternative proposal for user review  
**Artifact:** `landing-page-atlas.html`  
**Supersedes:** Nothing. This is an alternate direction to the approved AVRIG-00002 visual design.  
**Decision authority:** User

## Design move

Replace the warm inspection-bench and hero certificate metaphor with an **engineering operations atlas**. The public page opens on a plotted system topology: Founder authority above the company roles, two operating engines in parallel, a shared harness beneath them, and authoritative records at the base. The map is explicitly labelled as an architecture definition, not live telemetry.

This is a radical visual change, while retaining the source-of-truth commitments: human authority, the canonical lifecycle, version-specific evidence, explicit knowledge status, and visualizations as projections of structured records.

## Unslop method

The environment did not contain a separately installed `unslop/SKILL.md`. I applied the audit and redesign method recorded in `design/ui/AVRIG-00002/design.md`, which attributes its adaptation of Damir Sokolovsky's unslop method under CC BY 4.0. This artifact adapts that method and is not a redistribution of the source.

### Pass 1: Audit the existing concept

- The certificate was a strong visual device, but framed Avrig first as an artifact approval surface.
- The discovery definitions describe a larger product: virtual company, separate Office and SDLC engines, cross-cutting harness, governed knowledge, and persistent workforce identities.
- A certificate mockup can imply a real approval unless its state and data provenance are unmistakable.
- The architecture was not apparent from the old landing page. Its distinctive form is the relationship between company roles, project teams, two engines, and shared governance.

### Pass 2: Reframe the visual world

- New metaphor: an architectural systems atlas, with wiring, topology, numbered systems, and editorial annotation.
- New composition: a broad system map leads the hero. Supporting sections unfold into the lifecycle route, authority boundary, knowledge model, technology layers, and organization hierarchy.
- New palette: mineral grey paper, near-black ink, restrained signal red, and limited blue/green for specific architectural meanings. This departs from the warm paper and cobalt signature of AVRIG-00002.
- New shape language: ruled, square-edged diagram frames and thin connectors replace certificate cards, pill-heavy UI, and approval-seal hero treatment.
- No decorative AI iconography, glows, faux terminals, fabricated runtime health, or invented artifact IDs.

### Pass 3: Copy and evidence audit

- The system map carries an explicit “not live telemetry” label.
- Technology components are described as the **target design**, not as proof that every module is implemented.
- Example architecture relationships use names from the vault design documents. There are no fabricated deployment statuses, version pins, hashes, employee counts, or active-project claims.
- “Deployment” is marked optional, with the approved baseline's 0..1 cardinality.
- Decision, formal artifact approval, and governance are described separately.

### Pass 4: Responsive and accessibility audit

- The system map has a dedicated simplified mobile SVG with a text alternative.
- The sixteen canonical lifecycle stages reflow from eight columns to four and then two without reordering.
- Content is grouped under semantic page sections and headings; the page has a skip link and visible focus outline.
- Colour reinforces meaning but labels carry each state and relationship.
- Motion is not needed to understand the page and is disabled under reduced-motion preferences.

## Mapping to vault design definitions

| Vault design | Landing page expression |
|---|---|
| `System-Architecture.md`: Founder authority, CEO/PET, separate Personal Assistant | Hero topology and organization section |
| `System-Architecture.md`: persistent employee identity vs. ephemeral runtime | Organization section runtime distinction |
| `System-Architecture.md`: department membership and project assignments are orthogonal | Organization section explains both dimensions |
| `System-Architecture.md`: Office Operating System and Agentic SDLC Engine | Parallel engine blocks in the system map |
| `System-Architecture.md`: shared harness modules | Context, Knowledge, Skills, Policy, Events, and Traceability layer |
| `System-Architecture.md`: canonical lifecycle and optional deployment | Numbered 16-stage route plus optional deployment note |
| `System-Architecture.md`: structured data is authoritative, visualizations are projections | System map is labelled architecture definition; records are shown as the base |
| `Knowledge-Management.md`: Project Knowledge takes precedence over Platform Knowledge | Separate project truth and reusable platform guidance panels |
| `Knowledge-Management.md`: six epistemic states | Explicit classification row distinguishing authoritative, observed, guidance, inference, and unknown |
| `Knowledge-Management.md`: lifecycle-scoped retrieval, source traceability, conflict handling, governed promotion | Knowledge-flow summary |
| `Technology-Architecture.md`: web, desktop, mobile clients | Technology map client layer |
| `Technology-Architecture.md`: Rust service and typed event surfaces | Service layer |
| `Technology-Architecture.md`: agent harness, model/provider abstraction, retrieval, and sandboxed tools | Harness and AI layer summaries |
| `Technology-Architecture.md`: PostgreSQL, Apache AGE, pgvector, and S3-compatible artifact storage | Records layer |
| `Technology-Architecture.md`: OIDC identity, policy enforcement, sandboxing, and audit | Technology-map security and identity footer |

The vault documents are target architecture definitions. The page does not imply that every named module or integration is implemented in the current codebase.

## Modern web guidance

The static prototype uses semantic HTML regions, an accessible responsive navigation, responsive CSS grids, and a reduced-motion preference. It uses inline SVG for the topology because the diagram is explanatory content and must remain crisp and labelled at different sizes.

## Sources

- `D:/Cloud/OneDrive/AI/Personal/vault/02-projects/avrig-ai/design/System-Architecture.md`
- `D:/Cloud/OneDrive/AI/Personal/vault/02-projects/avrig-ai/design/Technology-Architecture.md`
- `D:/Cloud/OneDrive/AI/Personal/vault/02-projects/avrig-ai/design/Knowledge-Management.md`
- `design/ui/AVRIG-00002/design.md` for the prior visual audit and unslop method attribution
