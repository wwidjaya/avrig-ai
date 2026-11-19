---
title: Landing and Console Unslop Redesign
plan_id: AVRIG-00002
project_indicator: AVRIG
branch: feat/AVRIG-00002-landing-console-unslop-redesign
candidate_tags: []
release_version:
status: approved
created: 2026-11-20
owner: Architect
tags:
  - ui
  - design
  - unslop
  - landing
  - console
---

# Landing and Console Unslop Redesign

## Goals and Objectives

Rebuild the avrig-ai landing page and the console (shell plus five console views) so both carry a design that only this product could have, without changing what the product is, what it claims, or the order of its sections.

Measurable outcomes:

1. Zero instances of the unslop slop signs on both surfaces: no hue gradient on any surface, no gradient text, no coloured glow or coloured shadow, no emoji in interface text, no `animate-pulse` or `animate-spin` on a non-live element, no `transition-all`, and no `bg-slate-*` class left in `packages/ui`.
2. One neutral ramp in both themes, three text roles, and a single accent used for the primary action and the current gate only. `--primary` stops being the stock shadcn blue and becomes the product's own blue.
3. No heading above weight 600, and no uppercase tracked label anywhere on either surface.
4. Pill count on the console shell drops from 17 to at most 2, and both remaining pills carry live state rather than a category.
5. Contrast: every accent-as-text pair reaches 4.5:1 or better, measured, not assumed.
6. Layout holds at 360, 768, 1280 and 1920 without a horizontal scrollbar, and the console keeps real app proportions rather than shrinking into a centred column.
7. `data-testid="sidebar-version-badge"` still resolves, and the `@avrig/ui` export surface is unchanged, so no existing test or import breaks.
8. Both locales (`en`, `id`) carry the rewritten copy, with no key removed and no key left untranslated.

Out of scope: any backend, API, schema, or infrastructure change. This plan touches presentation only.

## Key Detailed Design

### Design authority

The design artifact is `design/ui/AVRIG-00002/design.md`. It holds the unslop audit (one line per sign with where it lives), the five line direction, and the nine passes with their target files. Screenshots captured during the audit are in `.opencode/plan/shots/` and the artifact copies the relevant ones into `design/ui/AVRIG-00002/snapshots/`.

The direction, approved before any code is written:

- **Product.** avrig-ai runs software delivery as a company: agents plan, execute and verify each stage, the founder holds sole approval authority, and every artifact keeps the version pins and evidence that prove it.
- **Character.** Exact, accountable, quiet.
- **World.** The drawing office and the inspection bench. Vellum, drafting film, machined plates, ink stamps, tolerance callouts. Not a neon control room.
- **Moments.** Two. The hero gate certificate: a sheet of drafting stock carrying the current stage, its verified checklist, artifact versions in mono, and a stamp in the corner. The traceability path in the console: one plotted line from requirement through test to deployed artifact with version pins on it, the only richly drawn element on that screen.
- **Signature.** A stamped approval seal. A small square outline carrying a work item code, used only where human authority signs, never as decoration.

Direction is frozen. A change to it invalidates every pass, so it is settled before `fe` writes code.

Attribution: this design adapts the `unslop` method by Damir Sokolovsky (https://heydamir.design/unslop), licensed CC BY 4.0. Copyright is full (no modification of license terms), the work is adapted rather than redistributed verbatim, and the credit above plus the repository link satisfies the attribution term. `fe` keeps that credit line in `design/ui/AVRIG-00002/design.md` and in the pass report.

### Program Design

No service contract, route, request model, or crate module changes. The work is confined to React components, one CSS entry point, one token file in a sibling repository, and four SVG assets.

**Token layer.** `D:\Cloud\OneDrive\AI\Agentic\avrig-ui\packages\tokens\theme.css` is the token source of truth and lives outside this repository. It gains the warm ramp and the accent pair, keeping the existing variable names (`--background`, `--card`, `--primary`, `--border`, `--radius`, and the rest) so nothing downstream breaks. `apps/web/src/styles/globals.css` already imports it, so the swap is a value change, not a wiring change.

Ramp, from the unslop tokens, warm family:

| Role | Dark | Light |
|---|---|---|
| Deepest surface (sidebar) | `#12110f` | `#f7f4ee` |
| Page background | `#161513` | `#f7f4ee` |
| Card | `#1c1a18` | `#fdfbf7` |
| Raised (active row, input) | `#262421` | `#efe9df` |
| Primary text | `#efe9de` | `#1f1b16` |
| Secondary text | `#aaa398` | `#5e554a` |
| Muted text and icons | `#8a847a` | `#7b7266` |
| Hairline | primary text at 8% | primary text at 8% |

Accent, derived from the existing logo blue and kept solid:

| Token | Value | Use | Measured contrast |
|---|---|---|---|
| `--primary` | `#2563EB` | fills, primary action, current gate | white on it reaches 5.1:1 |
| accent as text, dark | `#7FA8FF` | accent text and icons on dark | 7.9:1 on `#161513` |
| accent as text, light | `#1D4ED8` | accent text and icons on light | 6.0:1 on `#f7f4ee` |
| positive | `#4cc38a` dark, `#16a34a` light | verified, passed | semantic only |
| negative | `#e5484d` dark, `#dc2626` light | failed, blocked | semantic only |

`#2563EB` must never be used as text on a dark surface: it measures 3.6:1 there and fails. Fills only, or the lighter accent text value.

**Type layer.** Interface family Geist, partner Geist Mono for every figure, code, version, SHA and stage identifier. The existing declaration of Inter in `theme.css` is unused by the app and is replaced. Weights 400, 500, and 600 only. Scale from the unslop tokens: hero headline 56 to 72 desktop and 36 to 44 mobile at weight 400 to 500, page title 28 to 36, body 14 to 15, small meta 12 in mono, card figures 28 to 32 in `tabular-nums`.

**Spacing and proportion.** 4px grid. Sidebar 256 wide, nav rows 34 tall with 2 between, section labels 24 above and 8 below, card padding 24, page edges 32, content capped at 1440. Landing sections 80 to 96. Hero 96 from navigation to headline on desktop, 48 on mobile.

**Radius.** Controls 8, cards 12, panels 16, nested by subtraction so an inner radius equals the outer minus the padding and never drops below 4. Pills are reserved for live state, not for categories or counts.

**Component layer.** `packages/ui` primitives keep their exports and props exactly as they are and only stop hardcoding `bg-slate-*` classes, so every consumer inherits the ramp. Any consumer that relied on the navy card fill must be checked, which the target file list covers.

### Target Program Files (Mandatory)

Repository `avrig-ai`:

| Path | Action | Pass |
|---|---|---|
| `apps/web/src/modules/landing/LandingPage.tsx` | edit | 1 to 9 |
| `apps/web/src/shared/i18n/translations.ts` | edit | 4 |
| `apps/web/src/shell/CommandCenterLayout.tsx` | edit | 1 to 9 |
| `apps/web/src/modules/office/OfficeView.tsx` | edit | 1, 2, 3, 5, 6, 7, 9 |
| `apps/web/src/modules/sdlc/SdlcBoardView.tsx` | edit | 1, 2, 3, 5, 6, 7, 9 |
| `apps/web/src/modules/deliberations/DeliberationsView.tsx` | edit | 1, 2, 3, 5, 7, 9 |
| `apps/web/src/modules/knowledge/KnowledgeView.tsx` | edit | 1, 2, 3, 5, 7, 8, 9 |
| `apps/web/src/modules/knowledge/KnowledgeChat.tsx` | edit | 1, 2, 3, 5, 7, 9 |
| `apps/web/src/styles/globals.css` | edit | 2, 5 |
| `apps/web/index.html` | edit | 5, 7 |
| `apps/web/public/avrig-logo.svg` | edit | 7 |
| `apps/web/public/avrig-mark.svg` | edit | 7 |
| `apps/web/dist/avrig-logo.svg` | edit | 7 |
| `apps/web/dist/avrig-mark.svg` | edit | 7 |
| `packages/ui/src/components/Card.tsx` | edit | 2 |
| `packages/ui/src/components/Button.tsx` | edit | 2, 7 |
| `packages/ui/src/components/Badge.tsx` | edit | 2 |
| `packages/ui/src/components/Tabs.tsx` | edit | 2 |
| `design/ui/AVRIG-00002/design.md` | create | artifact |
| `design/ui/AVRIG-00002/snapshots/` | create | artifact |

Repository `avrig-ui`:

| Path | Action | Pass |
|---|---|---|
| `packages/tokens/theme.css` | edit | 2, 5 |

`packages/ui/src/components/Table.tsx`, `Dialog.tsx`, `Sheet.tsx`, `Input.tsx`, `ScrollArea.tsx`, `AlertDialog.tsx`, `CommandPalette.tsx`, `Avatar.tsx` are edited only if a pass reaches them. `fe` records which of them actually changed in the pass report rather than editing them for consistency.

Note that `apps/web/dist/` holds built output. It is committed in this repository, so the SVG assets there are edited alongside `public/` in the same commit to keep them identical until the next build overwrites them.

### EDM Design

Not applicable. No table, column, constraint, index, or migration is created or altered. No data model in the vault changes. `edm` is not dispatched for this plan.

### Copy design

The copy rewrite keeps every claim that can be checked and removes every claim that cannot. Removals, with the reason:

| Current | Reason |
|---|---|
| `Sovereign AI Engineering Rig & Operating System` | two abstractions stacked, says nothing about what the user gets |
| `GATE VERIFIED` | asserts a verification state on a marketing page where nothing was verified |
| `16 INVARIANTS ACTIVE` | a count with no referent on that page |
| `ACTIVE COMPILATION` | implies a live build that is not running |
| `STATUS: ONLINE`, `avrig-rig://cluster-01.local` | fabricated cluster identity |
| the fabricated SHA prefixes in the terminal | fabricated evidence, which is exactly what this product exists to prevent |

Replacements say what the system does and for whom, in plain words, using only facts already present in the page, the vault design documents, or the code. Specifically: stages run in a defined order, each stage produces an artifact with a version pin, an agent cannot approve its own work, and the founder approves. Those four are the product.

The hero headline names the outcome for the founder. The subhead names the mechanism in one sentence. Nothing else changes subject.

### Signature detail specification

The stamped approval seal is a small square, 1.5px stroke, radius 4, carrying a monospace work item code at 10 to 11px and an optional short state word. It appears in exactly four places:

1. Console top bar, beside the signed-in operator, showing that the viewer holds approval authority.
2. An approved stage gate in `SdlcBoardView`, where it replaces the green check badge.
3. The accepted artifact in the hero gate certificate.
4. The released version in the console sidebar, next to `data-testid="sidebar-version-badge"` rather than replacing it.

It never appears as a section ornament, a card decoration, or a nav badge. Any fifth placement is a defect.

## Parallel Execution Plan

Two streams, one blocking gate each.

| Stream | Owner | Scope | Depends on | Mode |
|---|---|---|---|---|
| A, tokens and primitives | `fe` | `avrig-ui/packages/tokens/theme.css`, `packages/ui/src/components/*`, `apps/web/src/styles/globals.css`, `apps/web/index.html`, four logo SVGs | analyst gate, tester matrix | sequential, blocks B and C |
| B, landing | `fe` | `LandingPage.tsx`, `translations.ts` | A | parallel with C |
| C, console | `fe` | `CommandCenterLayout.tsx`, the five views | A | parallel with B |
| D, build gate | `build` | workspace build, type check | A, B, C | sequential |
| E, candidate and QA | `build` then `tester` | candidate tag, matrix run, live browser pass | D | sequential |

Rationale for A blocking: every colour, radius and type value that B and C consume lands in A first. Running B or C against the old tokens means every consumer is written twice.

Rationale for B and C running in parallel: they share no file. `translations.ts` is landing only, and the console views carry their labels inline. The one shared surface is `CommandCenterLayout`, which is C only.

Analyst review (stage 2) and tester matrix (stage 3) both run before any of the above, and implementation does not start until both pass.

Slice branches, if used: `feat/AVRIG-00002-landing-console-unslop-redesign/tokens` and `.../console`, merging back into the plan branch.

## Test Specification and Validation Matrix

Attached by `tester` at stage 3. A plan with an empty matrix does not proceed to implementation.

The matrix must cover, at minimum: a computed-style assertion that no element on either surface carries a hue gradient, `text-transparent` with `bg-clip-text`, an `animate-pulse` outside a live-status element, or a font weight above 600; a class scan proving zero `bg-slate-` occurrences in `packages/ui/src`; the contrast pairs listed in the token table measured rather than assumed; a 360/768/1280/1920 layout pass with no horizontal overflow; the `data-testid="sidebar-version-badge"` selector still resolving; the `en` and `id` key sets still matching; and a live browser journey across landing, console, office, deliberations, sdlc, knowledge and chat.

Evidence to `plans/evidence/AVRIG-00002/rc.<NNN>/`.

## Review Findings

Populated by `analyst` at stage 2, auditing this plan against the coding principles and universal programming references before implementation, and again after QA against the goals above.

## Traceability

- Design artifact: `design/ui/AVRIG-00002/design.md`
- Branch: `feat/AVRIG-00002-landing-console-unslop-redesign`
- Default branch resolution, `avrig-ai`: `main`, decided by contract step 1 (current branch tracks `origin/main` and is the only long-lived branch), corroborated by step 2 (`origin/HEAD` is `origin/main`) and step 3 (local `main` exists).
- Repositories touched: `avrig-ai`, `avrig-ui`. Each needs its own branch cut from its own resolved default branch.
- Feature request: created at stage 5b, titled `AVRIG-00002 Landing and Console Unslop Redesign`. `Release version:` line stays empty until deployment.
