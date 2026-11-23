# Product

<!-- impeccable:product-schema 1 -->

> Started from repository evidence. Human-confirmed product and surface decisions are called out explicitly below; inferred material remains labelled with its source.

## Platform

web

## Users

Inferred from `design/ui/landing-page-proposal.md` (Audience and visitor questions) and `plans/AVRIG-00002-2026-11-20-landing-console-unslop-redesign.md` (Design authority, Product).

- Founder or engineering lead, the primary user and the only actor holding approval authority. They set intent, review what agents produced, and approve or reject baselines.
- Prospective evaluator, usually a founder or engineering lead, deciding whether governed agentic delivery is credible. They need to understand the lifecycle and the human approval boundary quickly.
- Returning operator, who already has an account and wants the shortest path into the workspace.

For the public landing page, prospective evaluators and returning operators receive equal weight. Confirmed by the owner on 2026-11-20.

Role names are product vocabulary, not implementation detail: Founder, CEO/PET, department head, specialist, and ephemeral runtimes (source: `design/ui/landing-page-atlas-design.md` and `AGENTS.md`).

## Product Purpose

Inferred from `README.md` and `AGENTS.md`.

avrig-ai runs software delivery as a company: humans and AI agents plan, coordinate, and execute engineering work under shared governance. Its purpose is not autonomy for its own sake. Work becomes organized, observable, and traceable as it progresses, and a human retains authority over consequential decisions.

Success means a reader of the interface can see what stage the work is in, what evidence backs it, and who approved it, without asking anyone.

## Positioning

Inferred from `design/ui/landing-page-proposal.md` and the design invariants in `AGENTS.md`.

The mechanism a neighbouring agentic coding tool could not truthfully copy is the combination of a canonical ordered lifecycle, explicit epistemic status on every claim, version-pinned traceability between requirement, implementation, test, and approved outcome, and a hard rule that an agent cannot approve its own work. Agents propose; humans approve.

## Operating Context

Inferred from `AGENTS.md` (Development Environment), `design/ui/landing-page-proposal.md`, and `plans/AVRIG-00002-2026-11-20-landing-console-unslop-redesign.md`.

- Work moves through the canonical lifecycle stages (Requirements through Test and Verification, with deployment optional where the approved baseline says so). Stages are ordered and are not presented as skippable.
- Every stage produces artifacts that carry version pins. Traceability links pin both source and target versions.
- Deliberations are formal meetings with transcripts, quorum, and recorded outcomes.
- The product is self-hosted. Identity is standard OIDC (Rauthy, Keycloak, or Authentik are all supported), and configuration is fetched at runtime rather than baked into a build.
- The browser client renders without a backend running; data endpoints may return 401 or 404 while the console shell still renders. That is an expected state, not a defect to design around.
- Interfaces are English and Indonesian. The landing surface is translated in both locales; console strings are inline English by design.

## Capabilities and Constraints

Inferred from `AGENTS.md`, `apps/web/src/modules/*`, and the plan above.

- Implemented client surfaces: landing, auth and login dialog, SDLC board, Office, Deliberations, Knowledge (including chat).
- Several `crates/` directories are empty placeholders with no source. They signal intended decomposition, not features, and must never be presented as shipped capability or cited as dependencies.
- Presentation only: the web app is React 19 with Vite and Tailwind CSS v4, consuming `@avrig/ui` primitives. Domain logic, API calls, and business state do not belong in the design system.
- Constraints carried by the design documents: no fabricated runtime status, uptime, agent counts, hashes, or active-project claims. Any example data is illustrative and must be labelled as such.
- Shared runtime invariants: `GET /config.json` is fetched with `cache: "no-store"` before mount, OIDC uses standard discovery, and bearer tokens are injected into REST and WebSocket connections.

## Brand Commitments

Inferred from `design/ui/AVRIG-00002/design.md` (via the plan's Design authority section) and `design/ui/landing-page-proposal.md`.

- Name: avrig-ai, with "avrig.ai" as the wordmark treatment already in the code.
- Character, as frozen for the AVRIG-00002 direction: exact, accountable, quiet.
- Voice: plain, concrete, verifiable. No sovereignty rhetoric, no fabricated evidence, no claims the product cannot demonstrate.
- The product is MIT licensed and described as open source (`README.md`, `LICENSE`).
- Tone and aesthetic direction are owned by AVRIG-00002 and are frozen. This record does not restate or reopen them.

## Evidence on Hand

Inferred from the repository.

- Real design documents in `design/ui/`, including an approved direction, two alternative proposals, and static HTML prototypes.
- A working web client with five console views and two locales.
- No testimonials, customer names, case studies, benchmarks, pricing, or press. Those absences must not be filled with invented content.
- The landing page's example stage data and telemetry figures are mock, and the current code presents some of them as if live. Treating them as real would be a factual error.

## Product Principles

Derived from the invariants in `AGENTS.md` and the landing proposal.

1. Agents propose; humans approve. Approval is never an agent action, and the interface must never imply otherwise.
2. State every claim with its status. Agent inference is not a requirement, and a mock is not live telemetry.
3. Pin what you show. Versions, sources, and links are part of the evidence, not metadata.
4. Keep the lifecycle ordered. Do not present stages as reorderable or skippable.
5. Work quietly. Organization and traceability are the value; spectacle competes with them.

## Accessibility & Inclusion

Inferred from `design/ui/landing-page-proposal.md` (Interaction and responsive behavior) and `design/ui/landing-page-atlas-design.md` (Responsive and accessibility audit).

- Keyboard operation throughout, with a skip link, visible focus, and semantic landmarks.
- Status must not be communicated by colour alone; labels carry the state.
- Text contrast meets WCAG AA (4.5:1) where it is asserted.
- Reduced-motion preferences are respected; motion is never required to understand the page.
- Layout holds at narrow widths without horizontal overflow.

## Human-confirmed Surface Decisions

- The landing page should address prospective evaluators and returning operators equally.
- Use a code-first workflow for the landing page artifact.
- The selected landing page direction is the category-standard product page, with Linear and Vercel as craft references. This is scoped to the landing page, not a standing visual preference for other surfaces.

## Open Questions

These were not confirmed by a human and should not be treated as settled:

- Whether the landing page's primary action label should be “Open the workspace” or “Sign in”; the code currently uses “Console” in the nav and “Access Command Center” in the hero.
- Whether "Open the workspace" or "Sign in" is the canonical primary action label; the code currently says "Console" in the nav and "Access Command Center" in the hero.
- Whether the product is publicly launched or pre-release. The README and the plan read as active development, and `plans/AVRIG-00002` is still in progress.
- The balance between the Founder persona and a general engineering audience outside the landing page remains unresolved.
