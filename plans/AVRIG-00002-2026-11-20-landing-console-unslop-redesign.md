---
title: Landing and Console Unslop Redesign
plan_id: AVRIG-00002
project_indicator: AVRIG
branch: feat/AVRIG-00002-landing-console-unslop-redesign
candidate_tags:
  - avrig/00002/rc.001
release_version:
status: testing
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

Both surfaces means the landing route and every console route, including the components each one renders: `LoginModal`, `LanguageSelector` and `ThemeSelector` are part of the landing surface because `LandingPage.tsx` mounts them, and the primitives are part of the console because every view consumes them.

1. Zero instances of the unslop slop signs across both surfaces: no hue gradient on any surface, no gradient text, no coloured glow or coloured shadow, no emoji in interface text, no `animate-pulse`, `animate-ping` or `animate-spin` on a non-live element, and no `transition-all`. Additionally, zero hardcoded palette classes of the form `bg-(slate|blue|emerald|red|amber|purple|zinc|gray|neutral)-\d`, `text-...` or `ring-blue-*` in `packages/ui/src` or `apps/web/src`, and zero raw hex colour values in either. Scanning only `bg-slate-*` is not sufficient: the surviving hardcodes are `bg-blue-600` in `Badge.tsx` and `Button.tsx`, `bg-purple-600/20` and `bg-amber-600/20` in `OfficeView.tsx`, `bg-amber-500/20` in `SdlcBoardView.tsx`, `bg-red-500/20` in `DeliberationsView.tsx` and `ring-blue-500` in `Input.tsx`, and a slate-only scan reports green on all of them.
2. One warm neutral ramp in both themes, three text roles, and a single accent used for the primary action, the current gate and the signature seal only. The accent is expressed as HSL triplets in `theme.css`, because every consumer resolves colour through `hsl(var(--x))`; a hex value written into a triplet slot produces an invalid colour and takes every surface down at once.
3. No heading above weight 600, and no uppercase tracked label anywhere on either surface.
4. Pill-shaped elements on each console route drop to at most 2, and each survivor carries live state rather than a category. The counter is defined in the matrix as rendered `[class*="rounded-full"]` elements with non-empty text, per route, because `Badge` renders `rounded-full` internally and call-site counting misses every badge.
5. Contrast: every accent-as-text pair reaches 4.5:1 or better, measured from computed styles, not assumed.
6. Layout holds at 360, 768, 1280 and 1920 without a horizontal scrollbar, and the console keeps real app proportions rather than shrinking into a centred column.
7. `data-testid="sidebar-version-badge"` still resolves, and the `@avrig/ui` export surface is unchanged, proven by diffing the export list against a `main` baseline, so no existing test or import breaks.
8. The landing surface carries the rewritten copy in both locales (`en`, `id`), with no key removed and no key left untranslated. The console is explicitly out of scope for translation: no console file imports `translations.ts`, and every console string is inline English, so translating it would be a scope change rather than a copy pass.

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

**Token layer.** `D:\Cloud\OneDrive\AI\Agentic\avrig-ui\packages\tokens\theme.css` is the token source of truth and lives outside this repository.

The contract is HSL triplets, not hex. `theme.css` maps each token as `--color-x: hsl(var(--x))` inside `@theme inline`, and `globals.css` calls `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--background))` and `hsl(var(--foreground))` directly. Writing `--background: #f7f4ee` produces `hsl(#f7f4ee)`, which is invalid, and every surface colour fails at once. So the values below are written as `H S% L%` triplets and the `hsl()` wrappers stay exactly where they are. This is the smallest correct diff: no consumer changes.

Every value below is specified. `fe` converts nothing.

| Token | Dark triplet | Light triplet | `@theme inline` mapping | Role |
|---|---|---|---|---|
| `--background` | `40 7% 8%` | `40 36% 95%` | `--color-background` | page |
| `--foreground` | `39 35% 90%` | `33 17% 10%` | `--color-foreground` | text, high |
| `--card` | `30 8% 10%` | `40 60% 98%` | `--color-card` | card |
| `--card-foreground` | `39 35% 90%` | `33 17% 10%` | `--color-card-foreground` | text on card |
| `--popover` | `36 7% 14%` | `40 60% 98%` | `--color-popover` | sheet, dialog, palette |
| `--popover-foreground` | `39 35% 90%` | `33 17% 10%` | `--color-popover-foreground` | text on popover |
| `--muted` | `36 7% 14%` | `37 33% 91%` | `--color-muted` | raised row, quiet fill |
| `--muted-foreground` | `38 6% 51%` | `34 8% 38%` | `--color-muted-foreground` | meta and captions only |
| `--text-secondary` | `37 10% 63%` | `33 12% 33%` | `--color-text-secondary` | **new**, body-secondary |
| `--secondary` | `36 7% 14%` | `37 33% 91%` | `--color-secondary` | button secondary |
| `--secondary-foreground` | `39 35% 90%` | `33 17% 10%` | `--color-secondary-foreground` | text on secondary |
| `--accent` | `36 7% 14%` | `37 33% 91%` | `--color-accent` | shadcn hover surface, not the brand accent |
| `--accent-foreground` | `39 35% 90%` | `33 17% 10%` | `--color-accent-foreground` | text on hover surface |
| `--primary` | `221 83% 53%` | `221 83% 53%` | `--color-primary` | the one accent, fill |
| `--primary-foreground` | `0 0% 100%` | `0 0% 100%` | `--color-primary-foreground` | white on accent |
| `--accent-text` | `221 100% 75%` | `224 76% 48%` | `--color-accent-text` | **new**, accent as text and icon |
| `--positive` | `151 50% 53%` | `142 76% 36%` | `--color-positive` | **new**, verified, passed |
| `--negative` | `358 75% 59%` | `0 72% 51%` | `--color-negative` | **new**, failed, blocked |
| `--warning` | `38 90% 58%` | `32 88% 40%` | `--color-warning` | **new**, review required, dot and icon only |
| `--destructive` | `358 75% 59%` | `0 72% 51%` | `--color-destructive` | kept, aliases `--negative` |
| `--border` | `38 6% 20%` | `38 20% 86%` | `--color-border` | hairline |
| `--input` | `38 6% 20%` | `38 20% 86%` | `--color-input` | input border |
| `--ring` | `221 83% 53%` | `221 83% 53%` | `--color-ring` | focus ring |
| `--sidebar-background` | `40 9% 6%` | `40 36% 95%` | `--color-sidebar-background` | deepest surface |
| `--sidebar-foreground` | `39 35% 90%` | `33 17% 10%` | `--color-sidebar-foreground` | sidebar text |
| `--sidebar-primary` | `221 83% 53%` | `221 83% 53%` | `--color-sidebar-primary` | active row marker |
| `--sidebar-primary-foreground` | `0 0% 100%` | `0 0% 100%` | `--color-sidebar-primary-foreground` | on active row |
| `--sidebar-accent` | `36 7% 14%` | `37 33% 91%` | `--color-sidebar-accent` | active row surface |
| `--sidebar-accent-foreground` | `39 35% 90%` | `33 17% 10%` | `--color-sidebar-accent-foreground` | on active row |
| `--sidebar-border` | `38 6% 20%` | `38 20% 86%` | `--color-sidebar-border` | sidebar hairline |
| `--sidebar-ring` | `221 83% 53%` | `221 83% 53%` | `--color-sidebar-ring` | sidebar focus |

Six tokens are new and need their `--color-*` mapping added to `@theme inline`, or `fe` will have no utility class to reach them and will hardcode hex in components instead: `--text-secondary`, `--accent-text`, `--positive`, `--negative`, `--warning`, and the two radius tiers below. A missing mapping is a silent invitation to hardcoding.

Contrast, measured from the hex source:

| Pair | Ratio | Verdict |
|---|---|---|
| white on `--primary` (`#2563EB`) | 5.1:1 | passes at any size |
| `--accent-text` dark (`#7FA8FF`) on `--background` dark | 7.9:1 | passes |
| `--accent-text` light (`#1D4ED8`) on `--background` light | 6.0:1 | passes |
| `--foreground` dark on `--background` dark | 12.1:1 | passes |
| `--text-secondary` dark on `--background` dark | 7.3:1 | passes |
| `--muted-foreground` dark on `--background` dark | 5.0:1 | passes |
| `--text-secondary` light on `--background` light | 6.7:1 | passes |
| `--muted-foreground` light on `--background` light | 5.5:1 | passes |
| `#2563EB` as text on `--background` dark | 3.6:1 | **forbidden**, fill only |

The last row is the single most likely mistake in the implementation. `--primary` is a fill colour. When the accent has to carry text on a dark surface, it is `--accent-text`.

**Radius.** `--radius: 0.5rem` stays, so `--radius-lg` is 8 and becomes the control radius. The three roles map to named utilities rather than implicit Tailwind defaults:

| Role | Utility | Value |
|---|---|---|
| Control (button, input, select) | `rounded-lg` | 8 |
| Card | `rounded-xl` | 12 |
| Panel (sheet, dialog, certificate) | `rounded-2xl` | 16 |
| Inner element | outer minus padding, never below 4 | computed |

**Fonts.** Self-hosted, no new dependency and no external origin, because the deployment is self-hosted and a preconnected third-party link would add a CSP change that is outside this plan's scope. Two variable woff2 files are vendored into `apps/web/public/fonts/` and declared with `@font-face` in `globals.css`. That file is the real override point: its `body { font-family: -apple-system, ... }` currently beats `--font-sans` entirely, which is why the token file's Inter declaration never surfaced. Editing `theme.css` alone changes nothing visible.

So `globals.css` gains `@font-face` for Geist and Geist Mono, sets `--font-sans` and `--font-mono` on `:root`, and `body` uses `var(--font-sans)`. The `--font-sans: var(--font-sans)` entry inside `@theme inline` is self-referential and is left out of the edit rather than repaired, since nothing consumes it once `body` names the family directly.

**Type layer.** Interface family Geist, partner Geist Mono for every figure, code, version, SHA and stage identifier. Weights 400, 500, and 600 only. Scale from the unslop tokens: hero headline 56 to 72 desktop and 36 to 44 mobile at weight 400 to 500, page title 28 to 36, body 14 to 15, small meta 12 in mono, card figures 28 to 32 in `tabular-nums`.

**Spacing and proportion.** 4px grid. Sidebar 256 wide, nav rows 34 tall with 2 between, section labels 24 above and 8 below, card padding 24, page edges 32, content capped at 1440. Landing sections 80 to 96. Hero 96 from navigation to headline on desktop, 48 on mobile.

**Component layer.** The ten `packages/ui` primitives keep their exports and props exactly as they are and stop hardcoding palette classes, so every consumer inherits the ramp. `Dialog.tsx` and `AlertDialog.tsx` carry no palette hardcode and are untouched. Because `Card` currently supplies `backdrop-blur-md`, the frosted look disappears with the slate fill, which is intended: depth comes from surface steps and hairlines.

### Target Program Files (Mandatory)

Every file below is mandatory. The earlier revision named only four primitives and left eight conditional, which made Goals 1 and 2 unreachable: `fe` would have been failing assertions on files no pass was authorised to touch.

Repository `avrig-ai`, presentation surfaces:

| Path | Action | Pass | Why it is here |
|---|---|---|---|
| `apps/web/src/modules/landing/LandingPage.tsx` | edit | 1 to 9 | the landing surface |
| `apps/web/src/modules/landing/LoginModal.tsx` | edit | 3, 4, 5, 7, 9 | rendered by `LandingPage` at line 791; carries `animate-ping`, `animate-spin`, `animated` `uppercase` and `font-bold` |
| `apps/web/src/shared/components/LanguageSelector.tsx` | edit | 3, 5 | `uppercase tracking-wider` at line 56, in the landing navigation |
| `apps/web/src/shared/components/ThemeSelector.tsx` | edit | 1, 6, 7 | in the landing navigation, shares the control radius |
| `apps/web/src/shared/i18n/translations.ts` | edit | 4 | landing copy, both locales |
| `apps/web/src/shell/CommandCenterLayout.tsx` | edit | 1 to 9 | console shell: nav badges, status pill, footer, top bar |
| `apps/web/src/modules/office/OfficeView.tsx` | edit | 1, 2, 3, 5, 6, 7, 9 | purple and amber tinted modifiers |
| `apps/web/src/modules/sdlc/SdlcBoardView.tsx` | edit | 1, 2, 3, 5, 6, 7, 8, 9 | amber review-gate tint, signature seal placement |
| `apps/web/src/modules/deliberations/DeliberationsView.tsx` | edit | 1, 2, 3, 5, 7, 9 | red tinted modifiers |
| `apps/web/src/modules/knowledge/KnowledgeView.tsx` | edit | 1, 2, 3, 5, 7, 8, 9 | the traceability plot |
| `apps/web/src/modules/knowledge/KnowledgeChat.tsx` | edit | 1, 2, 3, 5, 7, 9 | renders `Avatar` and `ScrollArea`, so inherits their fixes and needs spacing work |
| `apps/web/src/app/App.tsx` | edit | 2, 5 | `animate-spin text-primary` at line 180. Found after the console pass: it is mounted on every route, so it was always part of the surface and the first target list missed it |
| `apps/web/src/shared/auth/ProtectedRoute.tsx` | edit | 2, 3, 5, 7 | line 16 `animate-spin text-primary`; lines 25 and 48 `rounded-full` icon containers with `bg-primary/10 text-primary` and `bg-destructive/10 text-destructive`; lines 28 and 51 `font-bold` |
| `apps/web/src/modules/knowledge/MarkdownRenderer.tsx` | edit | 2, 3, 5 | line 76 `text-primary`; line 228 `bg-zinc-950 dark:bg-zinc-900/90 text-zinc-100`; line 231 `uppercase font-semibold text-zinc-400 tracking-wider`. Rendered inside `KnowledgeChat`, so it is console surface |
| `apps/web/src/shared/components/SystemInfoDialog.tsx` | edit | 2, 5 | line 66 `text-primary`; line 111 `text-amber-500 border-amber-500/30`; line 122 `bg-amber-500/10 text-amber-500`; line 149 `text-emerald-500` |

Repository `avrig-ai`, foundation:

| Path | Action | Pass | Why it is here |
|---|---|---|---|
| `apps/web/src/styles/globals.css` | edit | 2, 5 | `@font-face`, `--font-sans` and `--font-mono`, `body` family, the four `hsl(var(--x))` call sites |
| `apps/web/index.html` | edit | 5, 7 | title, and the favicon which currently points at `/vite.svg`, a file that does not exist in `public/`; it becomes `/avrig-mark.svg` |
| `apps/web/public/avrig-logo.svg` | edit | 7 | flat solid tile, gradient removed |
| `apps/web/public/avrig-mark.svg` | edit | 7 | flat solid tile, gradient removed, and the new favicon target |
| `apps/web/public/fonts/Geist-Variable.woff2` | create | 5 | self-hosted interface family |
| `apps/web/public/fonts/GeistMono-Variable.woff2` | create | 5 | self-hosted figures and codes |

Repository `avrig-ai`, shared primitives. All ten carry hardcoded palette classes today, so all ten are mandatory:

| Path | Action | Pass | Hardcode found |
|---|---|---|---|
| `packages/ui/src/components/Card.tsx` | edit | 2 | `bg-slate-900/60`, `border-slate-800`, `text-slate-100`, `text-slate-400`, `backdrop-blur-md` |
| `packages/ui/src/components/Button.tsx` | edit | 2, 7 | `bg-blue-600`, `bg-slate-800`, `border-slate-700` |
| `packages/ui/src/components/Badge.tsx` | edit | 2 | `bg-blue-600`, `bg-slate-800`, `bg-red-600`, `bg-emerald-600`, `bg-amber-600`, `rounded-full` |
| `packages/ui/src/components/Tabs.tsx` | edit | 2, 9 | `bg-slate-900`, `text-slate-400`, `border-slate-800`, `transition` (pass 9 sweeps for `transition-all`) |
| `packages/ui/src/components/Table.tsx` | edit | 2, 7 | seven `bg-slate-*` and `text-slate-*` across header, row, cell and caption |
| `packages/ui/src/components/Input.tsx` | edit | 2 | `border-slate-700`, `bg-slate-900/50`, `ring-blue-500`, `placeholder:text-slate-400` |
| `packages/ui/src/components/ScrollArea.tsx` | edit | 2 | `bg-slate-700` thumb |
| `packages/ui/src/components/Sheet.tsx` | edit | 2 | `bg-slate-900`, `border-slate-800`, `text-slate-100`, `text-slate-400` |
| `packages/ui/src/components/CommandPalette.tsx` | edit | 2 | `bg-slate-900`, `text-slate-100`, `text-slate-400` across panel, input, list and group headings |
| `packages/ui/src/components/Avatar.tsx` | edit | 2 | `bg-slate-800`, `text-slate-200` fallback |

`Dialog.tsx` and `AlertDialog.tsx` are the only primitives with no palette hardcode, so they are not edited. `fe` records any additional file touched in the pass report, and a file not on this list is a scope change.

Repository `avrig-ai`, generated output that must be regenerated:

| Path | Action | Why |
|---|---|---|
| `packages/ui/dist/**` | regenerate | `packages/ui/package.json` resolves `exports` to `./dist/index.js`, so the app renders the committed `dist`, not the converted `src`. Converting `src` without rebuilding and committing `dist` changes nothing on screen. `packages/api-client/dist` and `packages/types/dist` are tracked the same way, and the root `build` script is `pnpm -r run build`, so committing regenerated `dist` is this repository's convention and not an accident. |

`apps/web/dist/` is the opposite case and the earlier revision had it backwards: it is listed in `.gitignore` line 8 and `git ls-files apps/web/dist` returns zero files, so it is regenerated by the build and never edited by hand.

Repository `avrig-ui`:

| Path | Action | Pass |
|---|---|---|
| `packages/tokens/theme.css` | edit | 2, 5 |

There are no `apps/web/dist/` rows. `apps/web/dist/` is listed in `.gitignore` line 8 and `git ls-files apps/web/dist` returns zero files, so built output is regenerated by the build and never edited by hand. The earlier revision claimed it was committed, which was simply wrong, and editing it would have been an untracked no-op.

`packages/ui/dist` is the opposite: tracked, consumed, and therefore regenerated in the tree. That distinction was missed in the first revision and again in the A1 gate, and it is the same class of error as the `apps/web/dist` one, inverted.

`@avrig/tokens` stays at `0.1.0`. No package bump is made, because `apps/web/package.json` resolves it as `link:../../../avrig-ui/packages/tokens`, a symlink that never consults the version field, and the repository-level release tag is what records the change. Bumping it would add a version-sync surface with no consumer.

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

The passes are sequential, not parallel. The method requires that a pass finish across the whole surface before the next begins, so a stream table that ran landing and console side by side while passes spanned both was unsatisfiable. What can run side by side is the two surface groups inside a single pass, once the foundation of that pass has landed.

Cross-repository ordering is the one hard gate that is easy to miss. `apps/web/package.json` resolves `@avrig/tokens` as `link:../../../avrig-ui/packages/tokens`, a filesystem symlink, so the `avrig-ai` build reads the sibling working tree and never a committed ref. Two consequences:

1. The token change is not inside the `avrig-ai` tree, so the `avrig-ai` commit alone does not describe the shipped CSS.
2. A candidate is reproducible only as the pair `(avrig-ai SHA, avrig-ui SHA)`.

So the candidate identity is that pair, both SHAs are recorded in `plans/evidence/AVRIG-00002/rc.<NNN>/` and in the verdict line, and the QA runner checks out both tags as worktrees with the `avrig-ui` one at the relative depth the symlink resolves to. A single-SHA verdict is a defect.

`avrig-ui`'s default branch resolves to `main`: the checkout is on `main`, `origin/HEAD` advertises `origin/main`, and `main` is the only local branch. Step 1 and step 2 of the contract agree, so there is no disagreement to record.

No early merge to `avrig-ui/main`. The token commit lands on the `avrig-ui` plan branch, the `avrig-ai` candidate is cut after that commit exists and its SHA is known, and both repositories merge to their own defaults together at stage 13, which is what the release policy already requires. Merging `avrig-ui` early would put unreviewed work on a default branch before QA.

| Step | Owner | Scope | Depends on |
|---|---|---|---|
| A0 | `fe` | `avrig-ui` branch, `packages/tokens/theme.css` triplet swap, six new `--color-*` mappings, commit, record SHA | analyst and tester gates |
| A1 | `fe` | `globals.css` fonts, primitives sweep (all ten, Pass 2), `index.html`, logo SVGs | A0 |
| P1 to P9 | `fe` | passes 1 to 9, sequential, each across the whole surface | A1 |
| B | `build` | workspace build, type check, candidate tag | P1 to P9 |
| Q | `tester` | matrix run against both SHAs, live browser pass, evidence | B |

Inside each pass, the foundation file for that pass lands first, then the landing group and the console group may go to two `fe` instances concurrently because they share no file. `translations.ts` is landing only and every console string is inline. The one file both sides would want is `CommandCenterLayout.tsx`, which belongs to the console group.

Slice branches are **not** usable here, despite the taxonomy defining them. Git refs form a tree, so `refs/heads/feat/X` and `refs/heads/feat/X/landing` cannot coexist and `git worktree add -b feat/X/landing` fails with `cannot lock ref ... exists; cannot create`. Because the plan branch must stay checked out to be worked on, the nested slice names are impossible while it exists locally. The two surfaces therefore run sequentially in the single plan-branch worktree, and each agent stages explicit paths rather than using `git add -A` so that one agent's commit cannot sweep up the other's in-progress files. The parallel allowance above stands where it can be honoured: the surface groups are independent once the foundation lands, they simply cannot be given separate worktrees under nested ref names.

`modern-web-guidance` is mandatory before Pass 6 (surface composition and the certificate layout), Pass 7 (focus states and the SVG plot interaction) and Pass 9 (reduced motion). `fe` runs `npx modern-web-guidance@latest search "<query>"` then `retrieve <ids>` and records the retrieved ids in the pass report. A pass report without the ids is incomplete, because web platform behaviour moves faster than any of our priors.

Analyst review (stage 2) and tester matrix (stage 3) both run before any step above, and implementation does not start until both pass.

## Test Specification and Validation Matrix

Authored by `tester` at stage 3, before implementation. A plan with an empty matrix does not proceed to implementation. Every row is executable against a candidate tag and produces an artifact. A row with no artifact in the evidence folder counts as not run, not as a pass.

### Runner contract

- The harness is committed at `apps/web/scripts/qa/`. One entry point, `run.mjs`, runs the whole matrix; the per-row drivers live in `rows/` and the shared plumbing in `lib/`. Nothing sits under `src/`, so `tsc` and the Vite build are unaffected.
- Playwright is imported as the bare specifier `playwright`. Node resolves it by walking up from the driver file to `apps/web/node_modules`, so the harness runs from any working directory in either checkout and embeds no absolute path.
- Every row is a subset run of the same entry point, and the whole matrix is one command without `--only`:

```powershell
$BASE     = "http://127.0.0.1:5173"
$EVIDENCE = "plans/evidence/AVRIG-00002/rc.<NNN>"

node apps/web/scripts/qa/run.mjs --base $BASE --evidence $EVIDENCE --pair $AI`:$UI
node apps/web/scripts/qa/run.mjs --base $BASE --evidence $EVIDENCE --pair $AI`:$UI --only ST-01
```

- `--only` selects rows for development and prints a line beginning `SUBSET` instead of the verdict line, so a green subset can never be read as a green candidate. The plan's verdict line is printed only by a full run.
- Exit code 0 means every selected row passed, 1 means at least one row failed, 2 means the run could not be performed (base URL unreachable) or a row is blocked. A blocked row is never a pass.
- Screenshots and JSON are written only under the `--evidence` directory, in absolute paths, and one `RESULT.md` carries the verdict line and the per-row table. Writes to `%TEMP%` fail silently while Playwright still returns bytes, so `%TEMP%` is never an evidence target.
- Served tree is the candidate, never the working tree. Two repositories carry the change, so both SHAs are recorded:

```powershell
$AI  = git -C D:\Cloud\OneDrive\AI\Agentic\avrig-ai rev-parse "avrig/00002/rc.<NNN>^{commit}"
$UI  = git -C D:\Cloud\OneDrive\AI\Agentic\avrig-ui  rev-parse "<ui candidate tag>^{commit}"
git -C D:\Cloud\OneDrive\AI\Agentic\avrig-ai worktree add D:\Cloud\OneDrive\AI\Agentic\.rc\AVRIG-00002-rc<NNN> $AI
git -C D:\Cloud\OneDrive\AI\Agentic\avrig-ui  worktree add D:\Cloud\OneDrive\AI\Agentic\.rc\AVRIG-00002-ui-rc<NNN> $UI
# @avrig/tokens is link:../../../avrig-ui/packages/tokens, so the avrig-ui worktree must sit at ..\..\..\avrig-ui
pnpm -C D:\Cloud\OneDrive\AI\Agentic\.rc\AVRIG-00002-rc<NNN>\apps\web install
pnpm -C D:\Cloud\OneDrive\AI\Agentic\.rc\AVRIG-00002-rc<NNN>\apps\web dev -- --port 5173 --strictPort
```

- Base URL is an argument rather than a constant, so the same harness serves a local worktree and a deployment. `http://127.0.0.1:5173` is the conventional local value. Routes under test: `/`, `/console`, `/office`, `/deliberations`, `/sdlc`, `/knowledge`, `/chat`.
- `run.json` records the base URL, both SHAs, the resolved default branch and the deciding step, the `HEAD` at run time, and the row coverage assertion: every declared row produced exactly once, none missing, none duplicated, none invented.

### Preconditions

Session seed, applied through `page.addInitScript` before any navigation, in one shared helper (`lib/session.mjs`) rather than repeated per driver. Shape validated on the first run rather than assumed.

```js
await page.addInitScript((user) => {
  sessionStorage.setItem("oidc.user:https://iam.avrig.ai:avrig-web-ui", JSON.stringify(user));
  localStorage.setItem("avrig-logged-in", "true");
  localStorage.setItem("avrig-operator-mode", "true");
}, {
  id_token: "<id_token>", access_token: "<access_token>", token_type: "Bearer",
  scope: "openid profile email",
  profile: { sub: "<sub>", email: "<email>", name: "<name>" },
  expires_at: Math.floor(Date.now() / 1000) + 3600
});
```

- Theme fixture: `localStorage["avrig-theme"] = "dark" | "light"`. The key is `avrig-theme`, read in `apps/web/src/shared/theme/ThemeContext.tsx` line 15; there is no `avrig-ui-theme` key, and a fixture that writes the wrong name leaves every row running in dark while still reporting a pass. Assert the resolved theme before running a row: `document.documentElement.classList.contains("dark")` must agree with the requested theme. Every computed-style row runs in both themes unless the row says otherwise.
- The console shell's `<main>` carries `id="main-viewport"`, not a test id. Rows that need the authenticated shell presence read `document.getElementById("main-viewport")`; `document.querySelectorAll('[data-testid="main-viewport"]')` is empty and is reported as such in `state-adopted.json` so the mismatch stays visible rather than being papered over.
- Token cache `.secrets/test_token.json` is short lived. Refresh it at the start of each run and record the expiry; never assume the cached token is valid. The console session seed above is independent of it, so a stale token does not silently authenticate a browser row.
- Routes render with no backend running. Data endpoints returning 401 or 404 is expected and is reconciled by name in BR-04, not by a zero-error count.

### Matrix

Each row is one invocation of the committed entry point. `$BASE`, `$EVIDENCE`, `$AI` and `$UI` are the values named in the runner contract; the per-row command adds `--only <ID>` to the full run.

| ID | Check | Exact command or selector | Fixture or precondition | Pass criterion |
|---|---|---|---|---|
| ST-01 | No hue gradient background | `node apps/web/scripts/qa/run.mjs --only ST-01 --base $BASE --evidence $EVIDENCE --pair $AI:$UI`; per element `getComputedStyle(el).backgroundImage` | All 7 routes, both themes, seeded session | 0 elements whose `backgroundImage` matches `/(repeating-)?(linear\|radial\|conic)-gradient\(/`. `none` and `url(...)` allowed |
| ST-02 | No gradient-filled text | `node apps/web/scripts/qa/run.mjs --only ST-02 ...`; `[class*="bg-clip-text"]` then computed `webkitTextFillColor` and `color` | All 7 routes, both themes | 0 elements combining `bg-clip-text` with a transparent fill |
| ST-03 | No heading weight above 600 | `node apps/web/scripts/qa/run.mjs --only ST-03 ...`; computed `fontWeight` on every element whose text node renders | All 7 routes, both themes | Maximum computed weight ≤ 600; offenders listed by tag and text |
| ST-04 | No pulse or spin outside live status | `node apps/web/scripts/qa/run.mjs --only ST-04 ...`; `[class*="animate-"]` plus computed `animationName` matching `/pulse\|spin\|ping\|bounce/` | All 7 routes, both themes | 0 offenders. A match is allowed only when itself or an ancestor carries `[data-live-status]` or `[role="status"]`. The auth-loading view in `App.tsx` is the documented allowlist entry |
| ST-05 | No `transition-all` | `node apps/web/scripts/qa/run.mjs --only ST-05 ...`; computed `transitionProperty` and `transitionDuration` | All 7 routes, both themes | 0 elements whose `transitionProperty` contains `all` **and** whose `transitionDuration` is non-zero. The conjunction is required: `all` is the initial value of `transition-property`, so the property alone matches 162 to 294 elements per surface that declare no transition at all. Raw counts are kept in `style-<theme>-<route>.json` so the corrected metric stays auditable |
| ST-06 | No coloured glow, no emoji in UI text, no uppercase tracked label | `node apps/web/scripts/qa/run.mjs --only ST-06 ...`; computed `boxShadow` and `textShadow`, `textContent` scan, computed `textTransform` with `letterSpacing` | All 7 routes, both themes | 0 shadows carrying a saturated `rgb()` with blur > 0; 0 emoji in rendered text; 0 elements combining `uppercase` with non-`normal` letter spacing |
| SC-01 | Zero `bg-slate-` in the primitive layer | `node apps/web/scripts/qa/run.mjs --only SC-01 ...`; internally `git grep -n "bg-slate-" $AI -- packages/ui/src` | Candidate commit `$AI` | 0 matches. `scan-sc01-bg-slate.txt` is kept even when empty, with the scan command, exit status and match count |
| SC-02 | Zero `bg-gradient` in landing | `node apps/web/scripts/qa/run.mjs --only SC-02 ...`; internally `git grep -n "bg-gradient" $AI -- apps/web/src/modules/landing` | Candidate commit `$AI` | 0 matches |
| SC-03 | Whole-palette scan: no stock palette utility survives anywhere | `node apps/web/scripts/qa/run.mjs --only SC-03 ...`; internally `git grep -nE "bg-(slate\|blue\|emerald\|red\|amber\|purple\|zinc\|gray\|neutral)-[0-9]\|text-(slate\|blue\|emerald\|red\|amber\|purple)-[0-9]\|border-(slate\|blue\|emerald\|red\|amber\|purple)-[0-9]\|ring-blue-" $AI -- packages/ui/src apps/web/src` | Candidate commit `$AI` | 0 matches. This is the governing scan: SC-01 and SC-02 are subsets of it and are kept only as a fast signal. It catches `bg-blue-600` in `Badge.tsx` and `Button.tsx`, `bg-purple-600/20` and `bg-amber-600/20` in `OfficeView.tsx`, `bg-amber-500/20` in `SdlcBoardView.tsx`, `bg-red-500/20` in `DeliberationsView.tsx`, and `ring-blue-500` in `Input.tsx` |
| SC-04 | Rendered primitive conversion: a primary `Button` and a `Card` paint from the cascade, not from a stale `dist` | `node apps/web/scripts/qa/run.mjs --only SC-04 ...`; `getComputedStyle` on the first button whose `backgroundColor` equals a `bg-primary` probe, on the first `div.rounded-xl` inside `#main-viewport`, and on two probes appended to `body` as `<div class="bg-primary">` and `<div class="bg-card">` | `/sdlc`, both themes, seeded session, `en` locale; probes appended and removed with `page.evaluate`. `rounded-xl` is the Card radius in both the converted build and the pre-conversion build, so the selector does not presuppose the fix | Button `backgroundColor` is neither `rgba(0, 0, 0, 0)` nor `transparent`, and equals the `bg-primary` probe's `backgroundColor`; Card `backgroundColor` equals the `bg-card` probe's, and Card `backdropFilter` is `none`. All four hold in both themes. This is the row that fails first when `packages/ui/dist` was not rebuilt from the converted `src`, and no grep of `src` or of the tracked tree can stand in for it |
| SC-05 | `packages/ui/dist` freshness: the built primitives carry the converted classes, not the palette | `node apps/web/scripts/qa/run.mjs --only SC-05 ...`; reads `packages/ui/dist/components/<Name>.js` at `$AI` for all ten converted primitives (`Card, Button, Badge, Tabs, Table, Input, ScrollArea, Sheet, CommandPalette, Avatar`), and records the newest mtime under `packages/ui/src` against the oldest under `packages/ui/dist` | Candidate commit `$AI`; no dev server needed | 0 of the ten files matches `/(bg\|text\|border\|ring)-(slate\|blue\|emerald\|red\|amber\|purple\|zinc\|gray\|neutral)-[0-9]/` and 0 contains `focus:ring`; `dist/components/Button.js` contains `bg-primary` and `rounded-lg`; `dist/components/Card.js` contains `bg-card` and no `backdrop-blur`. mtime is reported in `dist-freshness.json` and never decides the row, because a clock is not content |
| SC-06 | Scan scope covers the mounted closure, not a hand-written file list | `node apps/web/scripts/qa/run.mjs --only SC-06 ...`; walks relative and `@/` imports transitively from `apps/web/src/main.tsx`, keeps every `.tsx` under `apps/web/src`, and diffs that closure against the root declared by each scan row (SC-01, SC-02, SC-03, SC-05, TK-02) | `apps/web/src` at `$AI`; route set `/`, `/console`, `/office`, `/deliberations`, `/sdlc`, `/knowledge`, `/chat`. The closure is computed once from `main.tsx` because all seven route entries are reached from it, which is stricter than seven separate walks; the report also names the first route that reaches each file | Every file in the closure lies inside at least one scan row's declared root, or appears in `scope-out-of-surface.txt` with a reason. Closure size is reported. A closure file no row covers fails the row, because that is exactly how defect 2 happened. Expected: 20 `.tsx` files, with `App.tsx`, `ProtectedRoute.tsx`, `MarkdownRenderer.tsx` and `SystemInfoDialog.tsx` admitted by SC-03's whole-tree `apps/web/src` root. Wiring the check to the *declared* roots rather than to a file list is the point: a row whose root is narrower than the surface is a defect, not a pass |
| SC-07 | State adopted before measurement: theme, locale, auth and viewport are read back before any assertion | `node apps/web/scripts/qa/run.mjs --only SC-07 ...`; theme reads `document.documentElement.classList.contains("dark")` and `document.documentElement.style.colorScheme`; locale renders the landing page in `en` and in `id` and compares the first landing paragraph to the string `hero.badge` holds for that locale, because `documentElement.lang` is never written by `I18nContext`; auth reads `document.getElementById("main-viewport")` presence and records that `[data-testid="main-viewport"]` matches 0 elements; viewport reads `window.innerWidth` and `window.innerHeight` | Every row that sets a state: ST-01 to ST-06, CT-01 to CT-04, LY-01 to LY-03, BR-01 to BR-03, SC-04, SC-08, SC-09, SC-10, KB-01 to KB-03. Fixture keys are `localStorage["avrig-theme"]` and `localStorage["avrig-lang"]` | The read-back agrees with the requested state, and the row aborts as `STATE_NOT_ADOPTED` instead of measuring when it does not. For theme specifically, `classList.contains("dark") === (theme === "dark")` holds before any colour assertion runs. This is the generalised form of the `avrig-ui-theme` defect, where every light-theme row ran in dark and still reported a pass |
| SC-08 | Seal placement census: exactly where human authority signs, and nowhere else | `node apps/web/scripts/qa/run.mjs --only SC-08 ...`; counts elements whose class list carries `rounded-[4px]`, `border-[1.5px]` and `font-mono` and whose `textContent` matches `/^[A-Z][A-Z0-9]{1,9}-\d{5}$/`, with a second pass over `span` elements whose computed `borderTopWidth` is 1 to 2px, `borderRadius` is 4px and family is monospace, so a rebuilt seal with different classes is still counted | `/` and the six console routes, both themes, seeded session. Each counted seal is reported with its placement site in `seals.json`, resolved by walking up from the seal to `aside`, `header`, `#main-landing` or a card, and each gated site is reported with the state that gates it (the certificate stage's `approved` flag on `/`, a `review_required` stage on `/sdlc`) | `/` renders exactly 1 seal while the displayed certificate stage is approved and 0 while it is not, in both cases only inside the hero gate certificate. Each console route renders exactly 2: one in the top bar, one adjacent to `[data-testid="sidebar-version-badge"]`. `/sdlc` renders exactly 1 more, inside the card of a `review_required` stage, and records `not rendered, no review_required stage` when the view holds none. 0 matches anywhere else, and 0 on an element whose text is not a work item code. The frozen signature specification names four authority sites, which renders as 1 on landing, 2 per console route and 1 approved gate in `SdlcBoardView`; both a fifth placement and a missing designed placement fail the row. The gate wording is recorded rather than decided: this candidate gates the `/sdlc` seal on the furthest-along `completed` stage, which is reported with the count |
| SC-09 | Rendered font family: Geist resolves through the cascade, and Geist Mono reaches the figures | `node apps/web/scripts/qa/run.mjs --only SC-09 ...`; `getComputedStyle(document.body).fontFamily`, the same on `document.querySelector(".font-mono")`, and `[...document.fonts]` mapped to `{family, status}` | `/` and `/console`, both themes, seeded session, with `await document.fonts.ready` before the read | body `fontFamily` begins with `Geist` as the first family in the list, not merely contained somewhere in it; the `font-mono` element's first family contains `Geist Mono`; `document.fonts` reports both `Geist` and `Geist Mono` with `status === "loaded"`. A family declared in `theme.css` and overridden by `globals.css` leaves the OS default first in the list, which is how the app rendered for its whole life before this plan |
| SC-10 | Focus ring is keyboard-only: none on mouse click, visible on keyboard focus | `node apps/web/scripts/qa/run.mjs --only SC-10 ...`; per target, read the resting `boxShadow`, `outlineStyle` and `outlineWidth` first, then `click()`, then read `el.matches(":focus-visible")` with the same three computed values; then leave and re-enter the target with `page.keyboard.press("Tab")` and read the same set | `/console` and `/sdlc`, both themes. Targets: a primary `Button` found by matching its `backgroundColor` against a `bg-primary` probe, a `Badge` (the row sets `tabIndex = 0` on the element in the page, test-only, because `Badge` is a `div` and cannot match `:focus-visible` otherwise), the `Dialog` close control after opening `SystemInfoDialog` from `[data-testid="sidebar-version-badge"]`, and an `Input` after opening `CommandPalette` with `Ctrl+K` | For the button, badge and dialog close: a mouse click leaves `:focus-visible` false with `boxShadow` and `outlineStyle` unchanged from the resting read (a control may carry a resting `shadow-sm`, so "unchanged" is the only reading that distinguishes a focus ring from a shadow that was always there), and keyboard focus leaves `:focus-visible` true with either a changed `boxShadow` or a painted `outlineStyle`. A `focus:ring` rule fails the click half, which is the defect `Badge.tsx` and `Dialog.tsx` both carried and which a static grep cannot settle. The `Input` target cannot satisfy the click half on Chromium, which reports `:focus-visible: true` for any focused text-entry control; that reading is recorded as a measurement with its reason rather than excused, and it is flagged for amendment by the tester rather than passed by an assertion that cannot hold. Until it is amended a full run reports this row as the single failure, which is why the self-check below is not a release trigger |
| TK-01 | Token contract intact: HSL triplets, `hsl()` mappings | `node apps/web/scripts/qa/run.mjs --only TK-01 ...`; parses `avrig-ui/packages/tokens/theme.css` at the avrig-ui candidate SHA | Assert every colour declaration inside `:root` and `.dark` matches `^\d{1,3} \d{1,3}% \d{1,3}%$`, and every `--color-*` entry inside `@theme inline` matches `hsl(var(--...))`. Non-colour namespaces (`--radius*`, `--font-*`, `--motion-*`) are excluded because they are not triplets | 0 values outside the triplet form, 0 `--color-*` mappings missing the `hsl()` wrapper. `theme-css-sha.txt` records `git -C avrig-ui log -1 --format=%H -- packages/tokens/theme.css`. A hex written into a triplet slot is invalid CSS and breaks every surface at once, which is the failure this row exists for |
| TK-02 | No raw hex in consumers | `node apps/web/scripts/qa/run.mjs --only TK-02 ...`; internally `git grep -nE "#[0-9a-fA-F]{3,8}" $AI -- apps/web/src packages/ui/src` | Candidate commit `$AI`. `apps/web/scripts/qa/hex-allow.txt` was header-only, read by no script in the repository, and is deleted by this change rather than wired up: an allowlist nothing reads is not an authority, it is a place to park a value | 0 matches across both roots, with no allowlist and no per-file carve-out. There is no exemption mechanism to add an entry to, and the correct response to a match is to convert the value |
| TK-03 | The six new tokens resolve: HSL triplet on `:root`, and the utility each one feeds computes to that triplet | `node apps/web/scripts/qa/run.mjs --only TK-03 ...`; `getComputedStyle(document.documentElement).getPropertyValue("--accent-text")` and the same for `--positive`, `--negative`, `--warning`, `--text-secondary`, `--border`, then one probe `<span>` per utility appended to `body` and read back: `text-accent-text`, `text-positive`, `text-negative`, `text-warning`, `text-text-secondary` through computed `color`, and `border-border` through computed `borderTopColor` | All 7 routes, both themes, seeded session. `tokens-resolve.json` records each triplet, each utility's computed value, the RGB the triplet converts to, and the value read from each corresponding `--color-*` name | All six triplets are present on `:root`, match `^\d{1,3} \d{1,3}% \d{1,3}%$`, and differ between the two themes; each utility's computed colour equals the RGB conversion of its own triplet within one unit per channel. `--color-<name>` is deliberately **not** asserted: `@theme inline` in `avrig-ui/packages/tokens/theme.css` inlines `hsl(var(--token))` into the utility instead of emitting a `--color-*` custom property, so `getPropertyValue("--color-accent-text")` on `:root` returns the empty string by design, and TK-01 separately requires that inline form. Asserting a DOM `--color-*` would fail correct work and pass a token file that violates TK-01; the triplet plus the utility is the pair that carries the contract |
| CT-01 | White on `#2563EB` ≥ 4.5:1 | `node apps/web/scripts/qa/run.mjs --only CT-01 ...`; reads computed `color` and `background-color` of the primary action | Landing plus console, dark theme | Measured WCAG ratio ≥ 4.5. The literal hex is never trusted, only the rendered pair |
| CT-02 | `#7FA8FF` on `#161513` ≥ 4.5:1 | `node apps/web/scripts/qa/run.mjs --only CT-02 ...`; accent text element against resolved page backdrop | Console and landing, dark theme | Measured ratio ≥ 4.5 |
| CT-03 | `#1D4ED8` on `#f7f4ee` ≥ 4.5:1 | `node apps/web/scripts/qa/run.mjs --only CT-03 ...`; accent text element against resolved page backdrop | Console and landing, light theme | Measured ratio ≥ 4.5 |
| CT-04 | `#2563EB` never used as text on dark | `node apps/web/scripts/qa/run.mjs --only CT-04 ...`; every text element with computed `color` equal to `rgb(37, 99, 235)` resolved against its nearest non-transparent ancestor background | All 7 routes, dark theme | 0 such elements whose measured ratio is below 4.5. Any occurrence is listed in `contrast-forbidden.json` with its resolved backdrop |
| LY-01 | Landing holds at 4 widths | `node apps/web/scripts/qa/run.mjs --only LY-01 ...`; viewports 360x800, 768x1024, 1280x900, 1920x1080; assert `documentElement.scrollWidth <= clientWidth + 1` and same on `body` | Landing, both themes | No horizontal overflow at any of the 4 widths |
| LY-02 | Every console route holds at 4 widths | `node apps/web/scripts/qa/run.mjs --only LY-02 ...`; same assertion per route per width | 6 console routes, both themes | 48 combinations (6 routes x 4 widths x 2 themes), 0 with horizontal overflow |
| LY-03 | Console keeps app proportions | `node apps/web/scripts/qa/run.mjs --only LY-03 ...`; `aside` and `#main-viewport` bounding widths, plus the `#main-viewport > div` content area less its own horizontal padding | `/console` and `/sdlc` at 1280 and 1920, both themes | Sidebar width 256 ± 1 at both widths; `main` width ≥ 1024 at 1920; the content area is not narrower than `viewport - 256 - 64` at either width, which is 960 at 1280 and 1600 at 1920. The `mx-auto` wrapper inside it is capped by `max-w-[1440px]` and is recorded in `proportions.json` without deciding the row, because a capped reading column is the design and the criterion names the area that must fill the main region |
| CP-01 | Version badge still resolves | `node apps/web/scripts/qa/run.mjs --only CP-01 ...`; `[data-testid="sidebar-version-badge"]` | All 6 console routes, both themes | Exactly 1 match per route, visible, `textContent` matching `/^v\d+\.\d+\.\d+/` |
| EX-01 | `@avrig/ui` export surface unchanged | `node apps/web/scripts/qa/run.mjs --only EX-01 ...`; reads `packages/ui/src` at the candidate commit and at the resolved default branch through `git ls-tree` and `git show`, and diffs the exported name sets | Candidate commit `$AI` and the resolved default branch, both read from the repository rather than from a saved baseline file | Every baseline export name still exported. Missing set empty. Added names reported as informational only. `ui-exports.json` records both name sets, both commits and the branch the baseline came from |
| I18-01 | `en` and `id` key sets match exactly | `node apps/web/scripts/qa/run.mjs --only I18-01 ...`; flattens `translations.ts` for both locales and diffs against the baseline key set from `git show <default-branch>:apps/web/src/shared/i18n/translations.ts` | Candidate commit `$AI`. The file is parsed structurally, so no bundler and no dev server are involved | Both locales identical key sets, and no baseline key removed. `i18n-parity.json` records both counts, both difference sets and the baseline commit |
| I18-02 | No key left untranslated: every key whose `id` value equals its `en` value is either translated or declared non-translatable with a category | `node apps/web/scripts/qa/run.mjs --only I18-02 ...`; flattens both locale objects and compares leaf values | The in-row list `NON_TRANSLATABLE` in `apps/web/scripts/qa/rows/i18n.mjs`. Eleven entries, each an exact `en` value plus one category from `proper noun`, `product name`, `token tag`, `numeral`. No external allowlist file exists, because a list nothing reads or nothing expires is not an authority: here each entry is checked against the current `en` string, so a reworded key invalidates its own entry | 0 empty `id` values. Every key whose `id` value equals its `en` value appears in the list with a category, and any identical key absent from the list fails. Any entry whose key no longer exists, or whose `id` value now differs from `en`, fails as a stale declaration. Reported counts: empty, identical, declared, undeclared, stale. In this candidate 11 are identical and 11 are declared: proper noun `certificate.pin`; product names `bento.card4Badge` and `bento.card4Footer`; token tags `showcase.sdlc.item1Code` to `item4Code`; numerals `workflow.step1Num` to `step4Num`. 0 undeclared, 0 stale |
| PIL-01 | Pill census on the console shell | `node apps/web/scripts/qa/run.mjs --only PIL-01 ...`; within `aside, header`, `[class*="rounded-full"]` with non-empty `textContent` and not inside `[aria-hidden="true"]` | All 6 console routes | Count ≤ 2 on the shell, and each survivor matches `[data-live-status]` on itself or an ancestor. Text-less status dots are excluded by the text filter |
| BR-01 | Landing journey and section order | `node apps/web/scripts/qa/run.mjs --only BR-01 ...`; `boundingBox().y` for `#main-landing`, `#sdlc-cockpit`, `#architecture`, `#workflow`, then click the primary CTA | Landing, dark then light, 1440x900 and 390x844 | Each section visible with a non-empty heading; y coordinates strictly ascending in that order; CTA click leaves `/` for a console route and the shell renders |
| BR-02 | Console journey across all 6 routes | `node apps/web/scripts/qa/run.mjs --only BR-02 ...`; `goto` each route, wait for the view heading | Seeded session, both themes, 1440x900 and 390x844 | Each route renders its own heading, and no `ErrorBoundary` fallback text matching `/View Error/` appears |
| BR-03 | Reduced-motion path | `node apps/web/scripts/qa/run.mjs --only BR-03 ...`; context created with `reducedMotion: "reduce"` | Landing plus 6 console routes | 0 elements with `animationName != none`; every `transition-duration` ≤ 0.01s; every surface still renders |
| BR-04 | Console and network reconciled by name, and the application's WebSocket URL asserted | `node apps/web/scripts/qa/run.mjs --only BR-04 ...`; (a) installs a `WebSocket` wrapper through `page.addInitScript` that records the constructor's first argument and then delegates to the native constructor, so no network request is needed to observe the URL; (b) collects `console.error`, `pageerror`, failed requests and responses of 400 or above per surface | All 7 routes, both themes, seeded session. No allowlist file: the tolerated classes are defined in `rows/surfaces.mjs` as `CONSOLE_EXCLUSIONS`, each with its reason and its exact URL pattern, and every one used is counted in `br04-console-network.json` | (a) On every console surface at least one application socket is constructed, its pathname is exactly `/ws/command-center`, the `/ws` segment appears once so a doubled segment fails, and `origin + pathname` equals `<wsBaseUrl from /config.json>/command-center`. The Vite hot-module-reload socket is excluded by identity, as a socket whose host is the serving host, with its exact URL recorded; nothing is excluded by matching the expected answer. (b) 0 unexpected `console.error`, 0 `pageerror`, 0 failed request and 0 error response outside the in-row exclusions, which are `ws-production-host` (`loadConfig` rewrites `wsBaseUrl` only when the origin contains `app.avrig.ai`, so a local origin dials `wss://app.avrig.ai/ws/command-center` from the shipped config and no handshake completes) and `absent-backend` (`/api/` traffic while no backend runs). Anything else fails with its own text. A blocked row is never reported as a pass, and an empty exclusion set is reported as `nothing to reconcile` rather than as silence |
| KB-01 | Skip link works on both surfaces | `node apps/web/scripts/qa/run.mjs --only KB-01 ...`; `page.keyboard.press("Tab")` on `/` then on `/console`; assert `document.activeElement` matches `a[href="#main-landing"]` then `a[href="#main-viewport"]`; press `Enter` | Landing and console, both themes | First Tab focuses the skip link, its box is non-zero while focused, and Enter moves focus to the section carrying that id |
| KB-02 | Every interactive element reachable: focusables outside a tab group by Tab, every tab inside one by arrow key | `node apps/web/scripts/qa/run.mjs --only KB-02 ...`; walks the real Tab order per route with `page.keyboard.press("Tab")` until the order cycles, tagging each focusable with a `data-qa-focus` attribute and reading it back from `document.activeElement`, then drives each `[role="tablist"]` one `ArrowRight` at a time, waiting for the focused element to change before reading it | Landing plus 6 console routes, dark, 1440x900. Selector `a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])`, visible elements only | (i) Every visible focusable outside a `[role="tablist"]` is reached at least once by Tab, and focus never leaves the document. (ii) Inside each `[role="tablist"]` exactly one `[role="tab"]` carries `tabindex != -1`, because the roving tabindex makes the whole group a single Tab stop, which is the ARIA pattern and not a defect; and every tab in the group is reached by `ArrowRight`. Counting sibling tabs as Tab-unreachable would measure the pattern as a failure of itself, which is why the two halves are reported separately with their own counts, for example `124/124 focusables outside a tablist reached by Tab; 1 tab group with 4 tabs, one in the Tab order and 4 reached by arrow key` |
| KB-03 | Focus ring visible | `node apps/web/scripts/qa/run.mjs --only KB-03 ...`; focus the first 10 focusables per route, read `outlineStyle`, `outlineWidth`, `boxShadow` | Landing plus 6 console routes, both themes | For every sampled element, `outlineStyle != none` with `outlineWidth != 0px`, or a non-`none` `boxShadow` |
| KB-04 | No focus-trap regression in existing modals | `node apps/web/scripts/qa/run.mjs --only KB-04 ...`; open CommandPalette with `Ctrl+K`, Tab 15 times, then `Escape`; then open `SystemInfoDialog` from `[data-testid="sidebar-version-badge"]` and repeat | `/console` and `/sdlc`, both themes. A route with no such surface records `not applicable` with the reason, never silence | Focus stays inside the open surface for all 15 presses, `Escape` closes it, and focus returns to the trigger, which for the dialog is the version badge |

Row count: 39.

### Not applicable

- EDM and schema validation: no table, column, constraint, or migration is touched. `edm` is not dispatched.
- API contract tests beyond BR-04: no route, request model, or response shape changes. The console rows assert only that data endpoints fail in an allowlisted way when no backend is running.
- Unit tests for new components: no component is added, and the existing primitives keep their exports and props, so coverage is the computed-style and export-surface rows rather than a new unit suite.

### Evidence files

All under `plans/evidence/AVRIG-00002/rc.<NNN>/`. Every file below is written by `run.mjs`, so the list is the script's output rather than an aspiration.

| Row group | Artifacts |
|---|---|
| ST-01 to ST-06 | `style-<theme>-<route>.json` per surface, `surfaces.json`, `shots/<route>-<theme>-1440.png` and `shots/<route>-<theme>-390.png` per route |
| SC-01, SC-02, SC-03, TK-02 | `scan-sc01-bg-slate.txt`, `scan-sc02-bg-gradient.txt`, `scan-sc03-palette.txt`, `scan-tk02-hex.txt`, each carrying the scan command, its exit status, the match count and the matches, kept even when empty |
| SC-04, SC-09, SC-10 | `computed-primitives.json` (both computed backgrounds plus both probe values, per theme), `fonts.json` (two computed stacks plus the `document.fonts` dump), `focus-visible.json` (resting, click and keyboard reads per target per surface), `shots/computed-primitives-sdlc-<theme>.png`, `shots/sc10-<route>-<theme>.png` |
| SC-05 | `dist-scan.json` per primitive with its matched palette utilities and focus-ring flag, `dist-freshness.json` with the mtime pair |
| SC-06 | `scope-closure.json` (closure list, size, covering rows and the routes that reach each file), `scope-coverage.txt`, `scope-out-of-surface.txt` |
| SC-07 | `state-adopted.json` keyed by route and theme, plus the four locale read-backs and the `data-testid` mismatch count |
| SC-08 | `seals.json` with every match's text, box, typography, border and placement site per route and theme |
| TK-01 to TK-03 | `tokens-triplets.json`, `theme-css-sha.txt`, `tokens-resolve.json` (each triplet, its RGB conversion, its utility value and the empty `--color-*` read, per surface) |
| CT-01 to CT-04 | `contrast.json` holding every measured pair with resolved colour source, `contrast-forbidden.json` |
| LY-01 to LY-03 | `layouts.json`, `proportions.json`, `shots/layout-<route>-<theme>-390.png` |
| CP-01 | `version-badge.json` per route and theme |
| EX-01 | `ui-exports.json` (both export name sets, both commits, the baseline branch) |
| I18-01, I18-02 | `i18n-parity.json`, `i18n-untranslated.txt`, `i18n-nontranslatable.json` (declared entries with categories, identical keys, undeclared, stale) |
| PIL-01 | `pills.json` listing every surviving pill with its live-state marker |
| BR-01 to BR-04 | `journey-landing.json`, `journey-console.json`, `reduced-motion.json`, `br04-console-network.json` (application sockets, excluded dev-server sockets with their exact URL, reconciled console classes, unexpected errors), `shots/landing-<theme>-<width>x<height>.png` |
| KB-01 to KB-04 | `skip-link.json`, `a11y-tab.json`, `a11y-ring.json`, `a11y-traps.json` |
| All rows | `run.json` (base URL, both SHAs, default branch and deciding step, row coverage assertion), `result.json`, and one `RESULT.md` with the verdict line below and the per-row pass, fail or block table |

`plans/evidence/**` matches `.gitignore` line 50, so every artifact above is written to disk and is not committed. This plan's evidence sits in `plans/evidence/AVRIG-00002/` in the plan-branch worktree, keyed by `rc.<NNN>`. That is the intended retention policy rather than an oversight: an empty `git log -- plans/evidence/AVRIG-00002` is not missing evidence, and a reader looking for a run's screenshots or traces looks on the machine, not in history. A specific artifact is committed only by exempting its path, which this plan does not do.

Verdict line:

```text
AVRIG-00002 rc.<NNN> avrig-ai@<sha> avrig-ui@<sha> PASS 39/39 evidence plans/evidence/AVRIG-00002/rc.<NNN>/
```

A green run must name the candidate tag, both commit SHAs, the count of passing rows, and the evidence folder. If any row is blocked, the line reads BLOCKED with the row id and the reason, and the release trigger is not reported.

Result for rc.001:

```text
AVRIG-00002 rc.001 avrig-ai@4e6900b7e1528b588d2968f24cf8693f4d59ecb0 avrig-ui@777bbb6ee0e36a8db96980490b1cd637257ac7e4 FAIL 33/39 evidence plans/evidence/AVRIG-00002/rc.001/
```

Six rows failed, none blocked. Two were product defects (`SC-10`, `KB-04`) and four were rows whose criterion cannot hold as written (`TK-03`, `BR-04`, `I18-02`, `KB-02`), so no release trigger was reported. The per-row table, the measured values and the root cause of each failure are in `plans/evidence/AVRIG-00002/rc.001/RESULT.md`.

Amendment after rc.001, recorded here because it changes what the next candidate is measured against:

- `TK-03`, `BR-04`, `I18-02` and `KB-02` are rewritten above. Each now measures the property the row exists for: the triplet on `:root` with the utility it feeds, the WebSocket URL as constructed plus named console exclusions instead of a missing allowlist, identical translations against an in-row list with categories, and a roving tabindex reported as one Tab stop plus arrow reachability.
- The harness those rows name is committed at `apps/web/scripts/qa/`. Before this change the matrix named scripts that did not exist, which is why rc.001 was measured by purpose-written drivers recorded as deviation 1 in its own report.
- A self-check against the plan-branch tree at `83d5355` with avrig-ui at `777bbb6` gives `FAIL 38/39`: every row passes except `SC-10`, whose `Input` target is unsatisfiable as written because Chromium reports `:focus-visible: true` for any focused text-entry control, so a mouse click into the command palette input is indistinguishable from keyboard focus. The three non-text targets in that row pass. That is a row defect to amend, not a product defect, and it is recorded rather than excused. That run is not a candidate result: it was taken against the working tree with the dev server on a free port, and no candidate tag was cut for it.

## Traceability

- Design artifact: `design/ui/AVRIG-00002/design.md`
- Branch, `avrig-ai`: `feat/AVRIG-00002-landing-console-unslop-redesign`
- Branch, `avrig-ui`: `feat/AVRIG-00002-landing-console-unslop-redesign`
- Default branch resolution, `avrig-ai`: `main`, decided by contract step 1 (current branch tracks `origin/main` and is the only long-lived branch), corroborated by step 2 (`origin/HEAD` is `origin/main`) and step 3 (local `main` exists).
- Default branch resolution, `avrig-ui`: `main`, decided by contract step 1, corroborated by step 2 (`origin/HEAD` is `origin/main`) and step 3 (`main` is the only local branch). Steps 1 and 2 agree, so no disagreement needs recording.
- Repositories touched: `avrig-ai`, `avrig-ui`. Each gets its own branch cut from its own resolved default branch, and both merge together at stage 13.
- Candidate identity: the pair `(avrig-ai SHA, avrig-ui SHA)`. Both appear in the evidence folder and in the verdict line, because `@avrig/tokens` resolves through a filesystem symlink into the sibling checkout and the `avrig-ai` tag alone does not describe the shipped CSS.
- `@avrig/tokens` stays at `0.1.0`. No package bump, because `link:` resolution ignores the version field and the repository release tag records the change.
- EDM: not applicable, no schema surface.
- Feature request: [issue 5](https://github.com/wwidjaya/avrig-ai/issues/5), titled `AVRIG-00002 Landing and Console Unslop Redesign`, created at stage 5b with the `Release version:` line present and empty.
- Candidate workspace: `D:\Cloud\OneDrive\AI\Agentic\AVRIG-00002\{avrig-ai,avrig-ui}`. The pairing is not cosmetic. `apps/web/package.json` resolves `@avrig/tokens` as `link:../../../avrig-ui/packages/tokens`, and from `<P>/apps/web` three levels up is `parent(P)`. Placing both worktrees under one parent makes the symlink resolve to the `avrig-ui` plan-branch worktree instead of the unrelated `main` checkout beside it. A worktree at `Agentic\avrig-ai-AVRIG-00002` would silently read `main`'s tokens, which is the exact defect the SHA pair exists to prevent.

## Stage Gate Record

**Stage 5a, reconciliation.** `gh auth status` reports `github.com` as `wwidjaya` with `repo` scope. Both repositories resolve their default branch to `main` by contract step 1 and agree with `origin/HEAD`. After `git fetch origin --tags --prune`, every release tag was tested with `git merge-base --is-ancestor`:

| Repository | Default | Release tags tested | Not an ancestor | Merges performed |
|---|---|---|---|---|
| `avrig-ai` | `main` | 0.2.0, 0.2.1, 0.3.0, 0.4.0, 0.5.0 | none | none |
| `avrig-ui` | `main` | 0.2.0, 0.2.1, 0.3.0, 0.4.0, 0.5.0 | none | none |

Both default branches already contain every released artifact, so no reconciliation merge was needed and no tag was created, moved or deleted.

**Stage 5b, feature request.** Issue 5 created on `wwidjaya/avrig-ai` with `gh issue create`. The body is generated from this plan: goals, scope with the mandatory target file list, acceptance criteria from the measurable outcomes, the design artifact link with the frozen direction, and a traceability footer whose `Release version:` line is present and empty. No issue carried the code beforehand, so nothing was duplicated. The `enhancement` label was applied only after `gh label list` confirmed it exists.

**Stage 5c, branches.**

| Repository | Branch | Created by | Linked to issue | Notes |
|---|---|---|---|---|
| `avrig-ai` | `feat/AVRIG-00002-landing-console-unslop-redesign` | `gh issue develop 5 --base main` | yes, confirmed by `gh issue develop --list 5` | cut from `main` at `d79f992` |
| `avrig-ui` | `feat/AVRIG-00002-landing-console-unslop-redesign` | `git push origin main:refs/heads/...` | **no, by design** | cut from `main` at `c61d338`. The issue lives in `avrig-ai`, so the linking API cannot attach a branch in another repository. Recorded here so the unlinked state is never mistaken for a completed link. |

Both branches were created without switching either primary checkout, so the sibling `AVRIG-00003` session kept a stable tree. `D:\Cloud\OneDrive\AI\Agentic\avrig-ai` and `D:\Cloud\OneDrive\AI\Agentic\avrig-ui` both remain on `main`.

**Stage 5d, worktrees.** `git worktree add` created `D:\Cloud\OneDrive\AI\Agentic\AVRIG-00002\avrig-ai` and `...\avrig-ui`, each tracking its own plan branch. Verified that `<avrig-ai>/apps/web/../../../avrig-ui/packages/tokens/theme.css` resolves to the plan-branch worktree rather than the `main` checkout. Both worktrees need `pnpm install` before `fe` can run a dev server; that is a stage 6 prerequisite, not a stage 5 one.

**Hard rules held.** No candidate tag merged, no tag created, moved or force-pushed, no implementation commit made, and the default branches received nothing beyond what was already there.

## Stage Gate Record: Implementation

**A0, token layer.** Commit `777bbb6` in `avrig-ui` on the plan branch. One file, `packages/tokens/theme.css`, 66 insertions and 51 deletions. Verified: zero raw hex, all 64 colour declarations in HSL triplet form, all 32 `--color-*` mappings wrapped in `hsl(var(...))`, and the file parses clean under postcss. Token count and mapping count are equal at 32, so no new token lacks a utility class.

`--destructive-foreground` was the one token the plan's table did not list. It already existed at `0 0% 98%` and already had a `--color-*` mapping, and it sits on a `0 72% 51%` fill where it measures about 4.5:1. Decision: left as it is rather than assigned a warm value, because inventing a ramp value for a token the direction never discussed would be a design change dressed as a cleanup, and removing it would break a mapping that exists.

**A1, shared foundation.** Commit `3f3b977` in `avrig-ai`, 17 files. Geist and Geist Mono vendored at the verified byte sizes and confirmed loaded through `document.fonts`, with `getComputedStyle(document.body).fontFamily` resolving to `Geist, ui-sans-serif, system-ui, sans-serif`. The `var()` path worked without a literal fallback because an unlayered `:root` in `globals.css` outranks both the layered token `:root` and the self-referential `--font-sans` in `@theme inline`. Zero palette classes and zero `ring-blue-` remain in `packages/ui/src`, `backdrop-blur` is gone from `Card.tsx`, and the export surface is unchanged.

Three role judgements were escalated rather than guessed and are accepted: `ScrollArea`'s thumb takes the hairline role (`bg-border`), `Badge` renders its semantic dot through `before:` utilities so the DOM and prop surface are untouched while `rounded-full` disappears, and `Input.tsx` moved to `rounded-lg` alongside `Button.tsx` because the control radius would otherwise have been unreachable by any pass.

`apps/web/src/main.tsx` carries raw hex in its pre-mount fatal-error fallback. That is pre-existing, it renders before any stylesheet or token class exists, and it is allowlisted rather than changed.

**Landing surface, passes 1 to 9.** Commits `d6c4f9c`, `7da1255`, `08bf6da`, `917fefe`. Five files, +595 / -713. The hero is a 5/12 copy and 7/12 gate certificate split, the certificate is built in code from the existing mock stage data, and the fabricated SHA prefixes and cluster hostname are gone, replaced by `sha256:unset` and the real `__APP_VERSION__`. Translation keys went from 129 to 150 with `onlyEn=[]` and `onlyId=[]`. No horizontal overflow at 1280, 1024, 768 or 360 in either theme or either locale. `document.getAnimations()` is empty under reduced motion.

The Indonesian headline was rewritten rather than translated literally, because the literal rendering broke to five lines in a 469px column. That is a copy decision, not a layout workaround.

**Finding: `packages/ui/dist` shipped stale, and every gate passed anyway.** `packages/ui/package.json` resolves `exports` to `./dist/index.js`, and `packages/ui/dist` is tracked, 60 files. A1 converted `packages/ui/src` and verified with `git grep` against `src`, so every acceptance check returned zero while the browser still rendered `bg-blue-600`, `rounded-md` and `bg-slate-900` from the committed `dist`. Every primary button rendered with a transparent background. The landing pass caught it only by rebuilding `dist` locally to judge the real surfaces and then reverting it.

This is the third instance of one pattern in this plan, and the most expensive: a check that measures the source while the artifact is produced from somewhere else. The first was `avrig-ui-theme` versus `avrig-theme`, which ran every light-theme row in dark. The second was the symlinked token package, whose change lived outside the tag. This one is the same shape one level down: the conversion lived in `src` while the app read `dist`.

Root cause is a gap in the plan, not in execution. The target list named `src` files and `apps/web/dist` only to say it was excluded; it never named `packages/ui/dist`, and the phrase "built output is never hand-edited" was read as applying to both `dist` trees when it only applies to one. `packages/api-client/dist` and `packages/types/dist` are tracked identically, and the root build is `pnpm -r run build`, so the convention was discoverable and I did not check it.

Fix in flight: regenerate with `pnpm --filter @avrig/ui build` and commit `packages/ui/dist`. Not untracked and not gitignored, because that would change the build pipeline across three packages to solve a problem in one.

Matrix consequence: a row that greps `src`, or greps the tracked tree, cannot detect this. The matrix needs a row that asserts the rendered computed style of a primary button has a non-transparent background matching `--primary`, because that is the only observation that distinguishes a converted primitive from a stale one.

**Console surface, passes 1 to 9.** Commits `38bed48` (dist rebuild), `e2cdd56`, `66df816`, `35e4a39`. Rendered pill count is 0 on all six routes at all four widths in both themes, well under the ceiling of 2; the remaining `rounded-full` nodes are status dots and avatars carrying no text. All 48 route/width/theme cells authenticated against `#main-viewport` with a real `h1`, zero horizontal overflow including 360. The seal appears exactly twice per console route, neutral in the top bar and `text-accent-text` beside the sidebar version badge. `data-testid="sidebar-version-badge"` still resolves, still `rounded-md`, still `v0.5.0`. The traceability path is one card with three recorded routes, orthogonal 9px corners rather than a spline, each pin a real `<button>` with an accessible name and a visible focus ring, the plot itself `aria-hidden`.

Honest limitation, recorded rather than smoothed over: the column-to-column jogs are only 20 to 34px, so the three lanes read nearly flat at a glance and the route character is subtler than the direction intends. The fix is wider per-column jitter plus the identifier printed beside each lane's first pin, so the plot is readable without hovering.

One addition: `/chat` had no page heading at all, so `KnowledgeChat` now opens with the same title block as the other four views.

**Finding: the target list was incomplete a second time, in five files.** A full-tree scan after the console pass found these, every one of them violating a goal that was being reported as met:

| File | Violation |
|---|---|
| `apps/web/src/app/App.tsx` | `text-primary` as icon colour on a loading spinner |
| `apps/web/src/shared/auth/ProtectedRoute.tsx` | `text-primary` and `text-destructive` as icon colour, two `rounded-full` icon circles, two `font-bold` headings |
| `apps/web/src/modules/knowledge/MarkdownRenderer.tsx` | `text-primary`, `bg-zinc-950`, `dark:bg-zinc-900/90`, `text-zinc-100`, `text-zinc-400`, `uppercase`, `tracking-wider` |
| `apps/web/src/shared/components/SystemInfoDialog.tsx` | `text-primary`, `text-amber-500`, `border-amber-500/30`, `bg-amber-500/10`, `text-emerald-500` |
| `packages/ui/src/components/Badge.tsx` | `focus:ring-2` rather than `focus-visible:ring-2`, so the ring fires on mouse click |

The structural reason is worth naming. Both earlier target lists were built from the two surfaces I had surveyed, and I treated each surface as the set of files I had listed rather than as everything the surface renders. `MarkdownRenderer` renders inside `KnowledgeChat` and `SystemInfoDialog` inside the shell, so both were console surface all along, while `App.tsx` and `ProtectedRoute.tsx` sit on every route including the landing. The lesson is that a surface has to be enumerated by what mounts, not by what I happened to open.

Scope is now extended to these five files rather than the goals being quietly narrowed to match what was done. `animate-spin` stays on the three loading spinners, because the goal forbids motion on non-live elements and a loading indicator is live state.

A fourth instance of the same measurement problem, and the cheapest to state: reporting a goal as met because the scan that checked it was scoped to the files that had already been fixed. Three of the four instances in this plan share that shape, which suggests the matrix needs every negative-assertion row to name its scan root explicitly, and a row whose root is narrower than the surface is a defect rather than a pass.

**Close-out, and one decision about exceptions.** Commit `c87f858` converted `text-primary` to `text-accent-text` in all five places it appeared as text or icon colour, replaced two `rounded-full` icon circles with panel-radius squares, dropped `font-bold` to `font-semibold`, moved the markdown code block and its language label onto `bg-muted`, `text-foreground` and `text-muted-foreground` with the uppercase tracking removed, and took amber and emerald onto `warning` and `positive`. Verified live against token probes rather than by eye: the code block background read `rgb(38, 36, 33)`, which is exactly `bg-muted`, and the language label rendered `text-transform: none` and `letter-spacing: normal`.

Two items were escalated rather than fixed inside the authorised set, and the decision on both was to remove the violation rather than write an exception into the goal:

`Dialog.tsx` line 66 carried the same `focus:` instead of `focus-visible:` defect as `Badge.tsx`. `Dialog.tsx` was excluded from the sweep because it has no palette hardcode, which was a reason to leave its colours alone and never a reason to leave its focus behaviour alone.

`apps/web/src/main.tsx` carried five raw hex values in the pre-mount bootstrap error screen. The tempting move was to amend Goal 1 with an exception for it, on the grounds that it renders when the app is already broken. That is a real argument, and it loses to a simpler one: `./styles/globals.css` is imported at line 10 at module scope, so the stylesheet has loaded by the time the error screen runs, and the token classes are available. Converting four elements is smaller than maintaining a carve-out, and a goal with an exception cannot be tested as a single assertion. The error message is also now escaped before interpolation, since that screen renders text derived from an exception and should not be able to render markup.

Commit `cbc295f` closes both. All seven negative assertions now return zero across `apps/web/src` and `packages/ui/src` with no allowlist: palette classes, `text-primary` as text, `uppercase`, tracked or heavy weight, `transition-all`, `focus:ring`, and raw hex. The forced-error screen was verified live by throwing `new Error("<b>probe</b>")` through the real catch path: the wrapper resolved to `rgb(22, 21, 19)` and `rgb(38, 36, 33)`, which are the token values, and the probe rendered as literal text with zero `<b>` elements created.

`apps/web/scripts/qa/hex-allow.txt` was created during A1 as an exception record and is now empty to its header, because nothing legitimately matches. It has no consumer in the repository: no script reads it. It is vestigial and should be deleted or wired into a real check rather than left as an authority that nothing enforces.

## Stage 7, Workspace Build Gate

**Build id `AVRIG-00002-build.001`** at `cbc295f`.

`pnpm -r run build` succeeds for all six workspace projects: `packages/types`, `packages/api-client`, `packages/ui`, `apps/desktop`, `apps/mobile`, `apps/web`. The single warning is the pre-existing chunk-size advisory on `apps/web`, measured at 561.65 kB against 561.60 kB before this plan, so 50 bytes smaller and nothing introduced.

**The gate's real assertion is dist freshness, and it passes.** `packages/ui/dist` did not drift after a full workspace rebuild, which means the committed `dist` is byte-equivalent to what a clean build produces. That is the strongest available proof that the artifact the app imports actually reflects the converted source, and it is the check that would have caught the stale-`dist` defect immediately.

**Operational wart, recorded because it will bite the candidate tag.** A clean workspace build mutates tracked output in two unrelated places: `apps/desktop/dist` and `apps/mobile/dist` carry content-hashed asset filenames, so every build rewrites `index.html` and replaces both asset files, and `packages/{api-client,types}/dist` show as modified purely from CRLF normalisation with an empty content diff (`git diff --numstat` returns nothing for them). A build therefore cannot leave a worktree clean, and a candidate tag cut without restoring those paths would tag a tree that differs from the branch for reasons unrelated to this plan. Verified handling: `git restore -- .` plus removing the untracked hashed assets returns the tree to clean, after which `HEAD:packages/ui/dist/components/Button.js` carries `bg-primary`, `rounded-lg` and `focus-visible:ring`, with no `bg-blue-600`, no `rounded-md` and no `focus:ring`.

**Slice branch convention defect, found in practice.** The taxonomy defines slice branches as `<type>/<CODE>-<NNNNN>-<slug>/<slice>`, nested under the plan branch, and the parallel plan above repeats it. Git refs form a tree, so `refs/heads/feat/X` and `refs/heads/feat/X/landing` cannot coexist: `git worktree add -b feat/X/landing` fails with `cannot lock ref ... exists; cannot create`. The convention only works if the plan branch exists solely as a remote ref, which it cannot, because the plan branch is what gets checked out to do the work.

Consequence for this plan: the two surfaces run sequentially in the single plan-branch worktree rather than as concurrent slices, with explicit-path staging so no commit sweeps up the other agent's files. Both surfaces still land on the plan branch, which is what the merge expectations require; only the nested ref names were dropped. This is worth fixing in the taxonomy rather than silently working around, because the next plan will hit it at the same point.

## Stage 8, Candidate Tag

**Two commits landed after the gate, so the candidate was cut from a reconciled tree.** The seal placement (`838f5be`) and a `--no-ff` merge of `origin/main` (`4e6900b`) came after `cbc295f`. The merge was not cosmetic: stage 13 asserts the default branch is an ancestor of the candidate, and `origin/main` at `415650d` was not an ancestor of the branch, so a candidate cut before the merge would have failed the ancestry assertion and shipped a tag whose plan file predates the work it describes. The gate's assertions were re-run on the merged tree: all six projects build, and `packages/ui/dist` did not drift.

Build id is **`AVRIG-00002-build.001`**, anchored to the candidate commit rather than to the gate run, so `build.<NNN>` and `rc.<NNN>` stay aligned at `.001`.

| Repository | Commit | Tag |
|---|---|---|
| `avrig-ai` | `4e6900b7e1528b588d2968f24cf8693f4d59ecb0` | `avrig/00002/rc.001` |
| `avrig-ui` | `777bbb6ee0e36a8db96980490b1cd637257ac7e4` | `avrig/00002/rc.001` |

Both annotated tags are pushed and resolve on the remote to exactly those commits (`ls-remote` confirms `^{}` dereferences). Candidate identity for this plan is the pair, not either SHA alone, because the token CSS lives in `avrig-ui` while the consuming app lives in `avrig-ai` and `@avrig/tokens` resolves through a `link:` symlink that no tag in `avrig-ai` can describe.

`avrig/00002/rc.001` is immutable from this point. Any fix produces `rc.002`, never a moved tag. The taxonomy defines slice branches as `<type>/<CODE>-<NNNNN>-<slug>/<slice>`, nested under the plan branch. Git refs form a tree, so `refs/heads/feat/X` and `refs/heads/feat/X/landing` cannot coexist: `git worktree add -b feat/X/landing` fails with `cannot lock ref ... exists; cannot create`. The convention only works if the plan branch exists solely as a remote ref, which it cannot, because the plan branch is what gets checked out to work on. Consequence for this plan: the two surfaces run sequentially in the single plan-branch worktree rather than as concurrent slices, with explicit-path staging so no commit sweeps up the other agent's files. Both slices still live logically on the plan branch, which is what the merge expectations require; only the nested ref names were dropped. This is worth fixing in the taxonomy, and it is recorded here rather than silently worked around.

## Stage 9, Test Verification

### Candidate rc.001

Tested `2026-11-20` against the pair, both tagged `avrig/00002/rc.001`:

| Repository | Commit |
|---|---|
| `avrig-ai` | `4e6900b7e1528b588d2968f24cf8693f4d59ecb0` |
| `avrig-ui` | `777bbb6ee0e36a8db96980490b1cd637257ac7e4` |

Served at `http://127.0.0.1:5176` from the candidate checkout, Playwright `1.65.1`, Chromium headless, Node `v26.7.0`. The tree-equality gate before testing printed an empty diff between the candidate commit and the plan branch head, excluding `plans/` and `design/`.

Coverage: all 7 routes in both themes. Journeys at `1440x900` and `390x844`; layout at `360x800`, `768x1024`, `1280x900`, `1920x1080`; computed-style, seal, token and focus rows at 1280. No row was run in one theme only.

**Verdict: `FAIL 33/39`.** 33 rows pass, 6 fail, 0 blocked. No release trigger is reported.

| Row | Class | Finding |
|---|---|---|
| `SC-10` | product | The command palette input `[cmdk-input]` paints no focus indicator on keyboard focus (`boxShadow: none`, `outlineStyle: none`) and matches `:focus-visible` on mouse click. `CommandPalette.tsx` styles it `outline-none` with no `ring`. WCAG 2.4.7. Button, Badge and Dialog close pass both halves |
| `KB-04` | product | Closing `SystemInfoDialog` with `Escape` leaves focus on `BODY` instead of the `button[data-testid="sidebar-version-badge"]` that opened it. The dialog is driven controlled with no `DialogTrigger`, so Radix has no `onCloseAutoFocus` target |
| `TK-03` | row | All six `--color-*` reads return empty because `@theme inline` inlines the value into the utility instead of emitting the custom property, which `TK-01` in the same matrix requires. The utilities resolve correctly, so the row contradicts `TK-01` |
| `BR-04` | row | One `console.error` recurs 14 times on the WebSocket handshake to `wss://app.avrig.ai/ws/ws/command-center`, and `apps/web/scripts/qa/console-allow.txt` does not exist at the candidate, so it cannot be allowlisted |
| `I18-02` | row | 11 `id` values equal their `en` value (product names, `[RE]`..`[TE]`, `01`..`04`, `Pin`), and `apps/web/scripts/qa/i18n-allow.txt` does not exist at the candidate |
| `KB-02` | row | 23 visible focusables on `/`, 19 Tab-reached. The 4 unreached are the landing showcase Radix tab group, which the row's selector re-admits through `button:not([disabled])`; `ArrowRight` moves through all four |

**What passed, including the rows that fail first.** `SC-04`: the `Review stage gate` button paints `rgb(36, 99, 235)`, equal to the `bg-primary` probe, and the card paints the `bg-card` probe with `backdropFilter: none`, in both themes. `SC-06`: the mounted closure is 26 files, 20 of them `.tsx`, and 0 fall outside a scan root. `SC-07`: all 4 locale read-backs and all 14 surface read-backs agree on theme, locale, auth and viewport before any measurement. `SC-05`: 0 of the 10 dist primitives carry a palette class or `focus:ring`. `SC-01`, `SC-02`, `SC-03`, `TK-02` and `SC-08`'s placement census return 0 matches or exact counts. `CT-01` 5.17:1, `CT-02` 7.41 to 8.12:1, `CT-03` 6.07 to 6.45:1, `CT-04` 0 forbidden text. `I18-01` 150 keys in both locales with no baseline key removed. `EX-01` 76 exports before and after. `PIL-01` 0 pills in the shell on all six console routes. `CP-01` exactly one visible `v0.5.0` badge per console route. Fonts, reduced motion (0 animations), skip links, layout at four widths and 24 console journeys all clean.

Seals: 1 on `/`, 2 on each of the five console views, 3 on `/sdlc` (top bar, sidebar, `TA-03 approved` on the Technology Architecture card). Every seal is `h=16px`, `fs=10px`, `lh=10px`, `radius=4px`, `borderTopWidth=1px`. The `/sdlc` seal is 98px wide and occupies exactly 1 line box in both themes, measured as distinct `y` values of `Range.getClientRects()`.

**Deviations from the matrix, all disclosed per row in `RESULT.md`.** The named harness scripts and the two allowlist files do not exist at the candidate (only `hex-allow.txt` does), so every row ran through a purpose-written Playwright driver in `plans/evidence/AVRIG-00002/rc.001/_runner/`. The port is 5176 rather than 5173. `[data-testid="main-viewport"]` does not exist, so `SC-04`, `SC-07` and `SC-08` read `#main-viewport`. `ST-05` was measured as `transition-duration > 0` together with `transitionProperty: all`, because the literal test matches 162 to 294 elements per surface purely from the property's initial value; the literal counts are preserved. `SC-08`'s `/sdlc` seal gates on the furthest-along `completed` stage (`TA-03`), not a `review_required` stage (`ED-04`), while the count criterion holds exactly.

Next: two product fixes on a fresh candidate `rc.002` (`fe`), and four row amendments before the rerun. `plans/evidence/AVRIG-00002/rc.001/` holds the 44 screenshots, 38 result artifacts, the five static scan transcripts and the drivers.

## Review Findings

Audited by `analyst` at stage 2 against the coding principles and the universal programming references, with every claim re-verified against the repository rather than accepted from the plan.

**Verdict at first pass: BLOCK.** Four blockers each either broke the build, made an acceptance goal unreachable, or left the tested artifact outside the candidate tag. All four are corrected in this revision, along with every should-fix. The gate clears.

| # | Severity | Finding | Resolution |
|---|---|---|---|
| 1 | blocker | Goals 1 and 3 could not be met: the target list named four primitives and left eight conditional, while `Avatar`, `ScrollArea`, `Table`, `Input`, `Sheet` and `CommandPalette` all carry palette hardcodes, and `LoginModal.tsx` and `LanguageSelector.tsx` carry slop on the landing surface | All ten primitives are now mandatory, both landing components added, and Goal 1 rescoped to the whole palette namespace with the exact carriers named |
| 2 | blocker | Hex ramp values against an `hsl(var(--x))` contract would produce `hsl(#f7f4ee)`, which is invalid, and take every surface down at once | Goal 2 and the token layer now specify HSL triplets for all 32 tokens, with the `hsl()` wrappers left in place |
| 3 | blocker | New accent-text, positive, negative and warning tokens had no `--color-*` mapping, so `fe` would hardcode hex to reach them | Six new tokens added with their `@theme inline` mappings; the matrix gains a no-raw-hex row |
| 4 | blocker | The cross-repo token change had no mechanism, no order gate and no SHA record, so a passing candidate was not reproducible from its tag | Candidate identity is now the SHA pair; A0 lands the avrig-ui commit before the avrig-ai candidate; the verdict line carries both SHAs; `avrig-ui/main` resolved and recorded; no-bump decision stated |
| 5 | blocker | The test matrix was a requirement list with no cases, commands or criteria | Cleared: `tester` attached 28 executable rows with commands, fixtures, pass criteria and an evidence mapping |
| 6 | should-fix | `apps/web/dist/` is gitignored with zero tracked files, so two target rows were impossible and the "committed" premise was false | Both dist rows removed; the section now states dist is build output and never hand-edited |
| 7 | should-fix | Passes 2 and 5 omit `CommandCenterLayout.tsx` while mandating changes that live in it, contradicting the plan's own table | Both passes now list the shell explicitly; every "all five views" replaced with explicit paths |
| 8 | should-fix | Pass-major sequencing cannot coexist with stream-parallel execution | Passes are now explicitly sequential; parallelism is confined to the surface groups inside a pass |
| 9 | should-fix | Font strategy was undecided, and the real override point is `globals.css` `body`, not `theme.css` | Self-hosted woff2 in `public/fonts/`, `@font-face` and `body { font-family: var(--font-sans) }` in `globals.css`; no dependency, no lockfile, no CSP change. Two font rows added |
| 10 | should-fix | Goal 4's "17 to 2" baseline was unreproducible: the shell holds four, and `Badge` renders `rounded-full` internally so call-site counting misses every badge | Restated per route, with the counter defined as rendered `[class*="rounded-full"]` with non-empty text |
| 11 | should-fix | A `bg-slate-` scan reports green while `bg-blue-600`, `bg-purple-600/20`, `bg-amber-500/20`, `bg-red-500/20` and `ring-blue-500` survive | Goal 1 and the scan rows now cover the whole palette namespace |
| 12 | should-fix | `Tabs.tsx` carries `transition-all` and no pass reached it | `Tabs.tsx` named in passes 2 and 9 |
| 13 | should-fix | `modern-web-guidance` was required by the artifact but was not a plan step | Added as a mandatory precondition for passes 6, 7 and 9, with retrieved ids required in the pass report |
| 14 | should-fix | Radius roles had no token mapping, leaving `rounded-xl` and `rounded-2xl` implicit | Explicit role to utility table added |
| 15 | should-fix | No `prefers-reduced-motion` anywhere | Pass 9 gains a reduced-motion requirement; the matrix already carries it as BR-03 |
| 16 | should-fix | Export stability was asserted but not proven | Goal 7 now requires a diff against a `main` baseline; the matrix proves it as EX-01 |
| 17 | should-fix | The favicon pointed at `/vite.svg`, a file absent from `public/`, and no asset was named | `index.html` now points at `/avrig-mark.svg`, which exists, with no new file |
| 18 | note | "Both locales carry the rewritten copy" was ambiguous, since no console file imports translations | Goal 8 now scopes translation to the landing surface and states the console is inline English by design |
| 19 | note | Two audit claims were not reproducible: the footer renders a bare `c`, not an emoji `©`, and `3.35544e+07px` is a float artefact | Both corrected in the artifact; the footer fix becomes `&copy;` |
| 20 | note | `avrig-ui/packages/ui` is not a dependency of `apps/web` and stays untouched | Recorded in the artifact so the checklist is not read as covering it |
| 21 | note | Plan identity, indicator match, draft-number safety, status vocabulary, EDM not-applicable reasoning, direction gate ordering, CC BY 4.0 attribution and the `rounded-md` version badge placement all verified clean | No action |

The `rounded-md` detail matters for the signature seal: `data-testid="sidebar-version-badge"` is a `rounded-md` button, not a pill, so placing the seal beside it does not collide with the pill reduction.

### Stage 9 goals audit

Audited from the rc.001 evidence rather than from this plan's own claims. `analyst` could not be dispatched from the testing session (`subagent depth limit reached`), so this pass is first-party by `tester` and should be re-audited by `analyst` before any release decision.

| Goal | Verdict | Deciding rows |
|---|---|---|
| 1, zero unslop signs and zero palette or hex hardcodes | achieved | `ST-01` 0 gradient backgrounds, `ST-02` 0 gradient text, `ST-04` 0 pulse or spin outside a live element, `ST-06` 0 coloured glow, 0 emoji, 0 uppercase tracked, `ST-05` 0 declared `transition-all`, `SC-01` 0 `bg-slate-`, `SC-02` 0 `bg-gradient`, `SC-03` 0 whole-palette matches, `TK-02` 0 raw hex with no allowlist |
| 2, one warm neutral ramp, three text roles, one accent, HSL triplets | achieved, one caveat | `TK-01` 32 `:root` and 32 `.dark` triplets, 32 `hsl()` mappings, 0 violations; `SC-04` renders `bg-primary` as `rgb(36, 99, 235)` and `bg-card` as `rgb(28, 26, 23)` / `rgb(253, 251, 247)`; `CT-02` and `CT-03` read the accent as `rgb(128, 168, 255)` and `rgb(29, 79, 215)`. Caveat: `TK-03` cannot read the `--color-*` mapping because `@theme inline` inlines it, so the goal rests on the utilities the surfaces actually paint, which resolve |
| 3, no heading above weight 600, no uppercase tracked label | achieved | `ST-03` max 500 on landing and 600 on all six console routes; `ST-06` 0 elements combining uppercase with letter spacing |
| 4, pills drop to at most 2 with live state | achieved | `PIL-01` 0 pills inside `aside, header` on all six console routes, both themes, so 0 survivors need a live-state marker |
| 5, every accent-as-text pair reaches 4.5:1 | achieved | `CT-01` 5.17:1, `CT-02` 7.41 to 8.12:1, `CT-03` 6.07 to 6.45:1, `CT-04` 0 text elements in the forbidden primary colour |
| 6, layout holds at 360, 768, 1280 and 1920 with real proportions | achieved | `LY-01` 0 overflow at all four widths in both themes, `LY-02` 0 of 56 console combinations, `LY-03` aside 256 and main 1664 at 1920 |
| 7, version badge resolves and the export surface is unchanged | achieved | `CP-01` exactly one visible `v0.5.0` badge per console route, still `rounded-md` at radius 6px and not a pill; `EX-01` 76 exports at `main` and 76 at the candidate, missing set empty |
| 8, landing copy in both locales with no key removed and none untranslated | partially achieved | `I18-01` 150 keys in each locale, 129 in the baseline, 0 removed. `I18-02` flags 11 `id` values identical to `en` with no allowlist file at the candidate: `OIDC`, `Rauthy, Keycloak, Authentik`, `Pin`, `[RE]` to `[TE]`, `01` to `04` |

The preamble claim holds: the rebuild does not change what the product claims or the order of its sections. `BR-01` finds the four landing sections in strictly ascending order with non-empty headings in both themes at `1440x900` and `390x844`, and the CTA lands on the console; `BR-02` renders each console route's own heading across 24 journeys with no `View Error` fallback.

Two gaps in this goals section, both exposed by the evidence rather than by opinion.

First, keyboard accessibility is asserted by the matrix and by nothing in this list. `SC-10` and `KB-01` to `KB-04` encode WCAG 2.4.7 and 2.4.3, and two of them fail on the product: the command palette input paints no focus indicator, and closing `SystemInfoDialog` drops focus to `body` instead of returning it to the version badge. A plan whose goals never name the property cannot claim it, so a keyboard-accessibility goal belongs here before the rerun.

Second, goal 8's second clause is untestable as written, because the allowlist the matrix delegates to (`apps/web/scripts/qa/i18n-allow.txt`) does not exist at the candidate. Eleven values are identical across locales and every one is a product name, a stage code or a numeral, which is the shape an allowlist exists to admit. The goal is satisfiable, the row is not.

Standing: `rc.001` fails 33 of 39 rows. Two product defects and four row amendments stand between this candidate and a release trigger, and no goal here is blocked outright.