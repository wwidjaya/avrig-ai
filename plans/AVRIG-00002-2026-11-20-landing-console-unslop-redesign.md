---
title: Landing and Console Unslop Redesign
plan_id: AVRIG-00002
project_indicator: AVRIG
branch: feat/AVRIG-00002-landing-console-unslop-redesign
candidate_tags: []
release_version:
status: in-progress
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

Repository `avrig-ui`:

| Path | Action | Pass |
|---|---|---|
| `packages/tokens/theme.css` | edit | 2, 5 |

There are no `apps/web/dist/` rows. `apps/web/dist/` is listed in `.gitignore` line 8 and `git ls-files apps/web/dist` returns zero files, so built output is regenerated by the build and never edited by hand. The earlier revision claimed it was committed, which was simply wrong, and editing it would have been an untracked no-op.

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

Slice branches, if two `fe` instances are used: `feat/AVRIG-00002-landing-console-unslop-redesign/landing` and `.../console`, each merged back into the plan branch at the end of the pass it belongs to, never held open across passes.

`modern-web-guidance` is mandatory before Pass 6 (surface composition and the certificate layout), Pass 7 (focus states and the SVG plot interaction) and Pass 9 (reduced motion). `fe` runs `npx modern-web-guidance@latest search "<query>"` then `retrieve <ids>` and records the retrieved ids in the pass report. A pass report without the ids is incomplete, because web platform behaviour moves faster than any of our priors.

Analyst review (stage 2) and tester matrix (stage 3) both run before any step above, and implementation does not start until both pass.

## Test Specification and Validation Matrix

Authored by `tester` at stage 3, before implementation. A plan with an empty matrix does not proceed to implementation. Every row is executable against a candidate tag and produces an artifact. A row with no artifact in the evidence folder counts as not run, not as a pass.

### Runner contract

- Harness scripts live in `apps/web/scripts/qa/` and run with `apps/web` as the working directory.
- Playwright is imported from `file:///D:/Cloud/OneDrive/AI/Agentic/avrig-ai/apps/web/node_modules/playwright/index.mjs`. Nothing resolves it from another directory.
- Screenshots are written only under `plans/evidence/AVRIG-00002/rc.<NNN>/` with absolute paths. Writes to `%TEMP%` fail silently while Playwright still returns bytes, so `%TEMP%` is never an evidence target.
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

Base URL `http://127.0.0.1:5173`. Routes under test: `/`, `/console`, `/office`, `/deliberations`, `/sdlc`, `/knowledge`, `/chat`.

### Preconditions

Session seed, applied through `page.addInitScript` before any navigation. Shape validated on the first run rather than assumed.

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
- Token cache `.secrets/test_token.json` is short lived. Refresh it at the start of each run and record the expiry; never assume the cached token is valid. The console session seed above is independent of it, so a stale token does not silently authenticate a browser row.
- Routes render with no backend running. Data endpoints returning 401 or 404 is expected and is reconciled by name in BR-04, not by a zero-error count.

### Matrix

| ID | Check | Exact command or selector | Fixture or precondition | Pass criterion |
|---|---|---|---|---|
| ST-01 | No hue gradient background | `node scripts/qa/style.mjs --set=gradient`; per element `getComputedStyle(el).backgroundImage` | All 7 routes, both themes, seeded session | 0 elements whose `backgroundImage` matches `/(repeating-)?(linear\|radial\|conic)-gradient\(/`. `none` and `url(...)` allowed |
| ST-02 | No gradient-filled text | `node scripts/qa/style.mjs --set=cliptext`; `[class*="bg-clip-text"]` then computed `webkitTextFillColor` and `color` | All 7 routes, both themes | 0 elements combining `bg-clip-text` with a transparent fill |
| ST-03 | No heading weight above 600 | `node scripts/qa/style.mjs --set=weight`; computed `fontWeight` on every element whose text node renders | All 7 routes, both themes | Maximum computed weight ≤ 600; offenders listed by tag and text |
| ST-04 | No pulse or spin outside live status | `node scripts/qa/style.mjs --set=motion`; `[class*="animate-"]` plus computed `animationName` matching `/pulse\|spin\|ping\|bounce/` | All 7 routes, both themes | 0 offenders. A match is allowed only when itself or an ancestor carries `[data-live-status]` or `[role="status"]`. The auth-loading view in `App.tsx` is the documented allowlist entry |
| ST-05 | No `transition-all` | `node scripts/qa/style.mjs --set=transition`; computed `transitionProperty` | All 7 routes, both themes | 0 elements whose `transitionProperty` contains `all` |
| ST-06 | No coloured glow, no emoji in UI text, no uppercase tracked label | `node scripts/qa/style.mjs --set=decor`; computed `boxShadow` and `textShadow`, `textContent` scan, computed `textTransform` with `letterSpacing` | All 7 routes, both themes | 0 shadows carrying a saturated `rgb()` with blur > 0; 0 emoji in rendered text; 0 elements combining `uppercase` with non-`normal` letter spacing |
| SC-01 | Zero `bg-slate-` in the primitive layer | `git grep -n "bg-slate-" $AI -- packages/ui/src` | Candidate commit `$AI` | 0 matches. Output file kept even when empty |
| SC-02 | Zero `bg-gradient` in landing | `git grep -n "bg-gradient" $AI -- apps/web/src/modules/landing` | Candidate commit `$AI` | 0 matches |
| SC-03 | Whole-palette scan: no stock palette utility survives anywhere | `git grep -nE "bg-(slate\|blue\|emerald\|red\|amber\|purple\|zinc\|gray\|neutral)-[0-9]\|text-(slate\|blue\|emerald\|red\|amber\|purple)-[0-9]\|border-(slate\|blue\|emerald\|red\|amber\|purple)-[0-9]\|ring-blue-" $AI -- packages/ui/src apps/web/src` | Candidate commit `$AI` | 0 matches. This is the governing scan: SC-01 and SC-02 are subsets of it and are kept only as a fast signal. It catches `bg-blue-600` in `Badge.tsx` and `Button.tsx`, `bg-purple-600/20` and `bg-amber-600/20` in `OfficeView.tsx`, `bg-amber-500/20` in `SdlcBoardView.tsx`, `bg-red-500/20` in `DeliberationsView.tsx`, and `ring-blue-500` in `Input.tsx` |
| TK-01 | Token contract intact: HSL triplets, `hsl()` mappings | `node scripts/qa/tokens.mjs --check=triplets`; parses `avrig-ui/packages/tokens/theme.css` at the avrig-ui candidate SHA | Assert every colour declaration inside `:root` and `.dark` matches `^\d{1,3} \d{1,3}% \d{1,3}%$`, and every `--color-*` entry inside `@theme inline` matches `hsl(var(--...))`. Non-colour namespaces (`--radius*`, `--font-*`, `--motion-*`) are excluded because they are not triplets | 0 values outside the triplet form, 0 `--color-*` mappings missing the `hsl()` wrapper. Artifact records `git -C avrig-ui log -1 --format=%H -- packages/tokens/theme.css`. A hex written into a triplet slot is invalid CSS and breaks every surface at once, which is the failure this row exists for |
| TK-02 | No raw hex in consumers | `git grep -nE "#[0-9a-fA-F]{3,8}" $AI -- apps/web/src packages/ui/src` | `apps/web/scripts/qa/hex-allow.txt`, written as `path:line:reason`, limited to the SVG assets, the logo glyph colours, and any URL fragment the scan trips over | Every remaining match appears in `hex-allow.txt` with a reason. Any unlisted match fails the row |
| TK-03 | The six new tokens actually resolve | `node scripts/qa/tokens.mjs --check=resolve`; `getComputedStyle(document.documentElement).getPropertyValue("--color-accent-text")`, then the same for `--color-positive`, `--color-negative`, `--color-warning`, `--color-text-secondary`, `--color-border` | All 7 routes, both themes, seeded session | Each of the 6 properties returns a non-empty, non-whitespace value in both themes. A token with no `--color-*` mapping returns empty, which is the exact failure mode this row exists for |
| CT-01 | White on `#2563EB` ≥ 4.5:1 | `node scripts/qa/contrast.mjs --pair=primary`; reads computed `color` and `background-color` of the primary action | Landing plus console, dark theme | Measured WCAG ratio ≥ 4.5. The literal hex is never trusted, only the rendered pair |
| CT-02 | `#7FA8FF` on `#161513` ≥ 4.5:1 | `node scripts/qa/contrast.mjs --pair=accent-dark`; accent text element against resolved page backdrop | Console and landing, dark theme | Measured ratio ≥ 4.5 |
| CT-03 | `#1D4ED8` on `#f7f4ee` ≥ 4.5:1 | `node scripts/qa/contrast.mjs --pair=accent-light`; accent text element against resolved page backdrop | Console and landing, light theme | Measured ratio ≥ 4.5 |
| CT-04 | `#2563EB` never used as text on dark | `node scripts/qa/contrast.mjs --pair=forbid-primary-text`; every text element with computed `color` equal to `rgb(37, 99, 235)` resolved against its nearest non-transparent ancestor background | All 7 routes, dark theme | 0 such elements whose measured ratio is below 4.5. Any occurrence is listed with its resolved backdrop |
| LY-01 | Landing holds at 4 widths | `node scripts/qa/layout.mjs --route=/`; viewports 360x800, 768x1024, 1280x900, 1920x1080; assert `documentElement.scrollWidth <= clientWidth + 1` and same on `body` | Landing, both themes | No horizontal overflow at any of the 4 widths |
| LY-02 | Every console route holds at 4 widths | `node scripts/qa/layout.mjs --route=all-console`; same assertion per route per width | 6 console routes, both themes | 48 combinations (6 routes x 4 widths x 2 themes), 0 with horizontal overflow |
| LY-03 | Console keeps app proportions | `node scripts/qa/proportions.mjs`; `aside` computed width, `main` computed width | `/console` and `/sdlc` at 1280 and 1920 | Sidebar width 256 ± 1 at both widths; `main` width ≥ 1024 at 1920. No centred column narrower than `viewport - 256 - 64` |
| CP-01 | Version badge still resolves | `page.locator('[data-testid="sidebar-version-badge"]')` | All 6 console routes, both themes | Exactly 1 match per route, visible, `textContent` matching `/^v\d+\.\d+\.\d+/` |
| EX-01 | `@avrig/ui` export surface unchanged | `node scripts/qa/exports.mjs --baseline plans/evidence/AVRIG-00002/baseline/ui-exports.json`; baseline built from `git archive main packages/ui \| tar -x -C <evidence>/baseline-src` then the same script | Candidate node_modules, `apps/web` cwd | Every baseline export name still exported. Missing set empty. Added names reported as informational only |
| I18-01 | `en` and `id` key sets match exactly | `node scripts/qa/i18n.mjs --check=parity`; flattens `translations.ts` for both locales and diffs against the baseline key set from `git show main:apps/web/src/shared/i18n/translations.ts` | Candidate commit `$AI` | Both locales identical key sets, and no baseline key removed |
| I18-02 | No key left untranslated | `node scripts/qa/i18n.mjs --check=translated`; flags empty values and `id` values equal to their `en` value | `apps/web/scripts/qa/i18n-allow.txt` for proper nouns and product codes | 0 flagged keys outside the allowlist |
| PIL-01 | Pill census on the console shell | `node scripts/qa/pills.mjs`; within `aside, header`, `[class*="rounded-full"]` with non-empty `textContent` and not inside `[aria-hidden="true"]` | All 6 console routes | Count ≤ 2 on the shell, and each survivor matches `[data-live-status]` on itself or an ancestor. Text-less status dots are excluded by the text filter |
| BR-01 | Landing journey and section order | `node scripts/qa/journey.mjs --set=landing`; `boundingBox().y` for `#main-landing`, `#sdlc-cockpit`, `#architecture`, `#workflow`, then click the primary CTA | Landing, dark then light, 1440x900 and 390x844 | Each section visible with a non-empty heading; y coordinates strictly ascending in that order; CTA click leaves `/` for a console route and the shell renders |
| BR-02 | Console journey across all 6 routes | `node scripts/qa/journey.mjs --set=console`; `goto` each route, wait for the view heading | Seeded session, both themes, 1440x900 and 390x844 | Each route renders its own heading, and no `ErrorBoundary` fallback text matching `/View Error/` appears |
| BR-03 | Reduced-motion path | `node scripts/qa/journey.mjs --set=reduced`; `page.emulateMedia({ reducedMotion: "reduce" })` | Landing plus 6 console routes | 0 elements with `animationName != none`; every `transition-duration` ≤ 0.01s; all journeys in BR-01 and BR-02 still complete |
| BR-04 | Console and network reconciled by name | `node scripts/qa/console.mjs`; collects `console.error`, `pageerror`, and failed responses | Same routes as BR-01 and BR-02, `apps/web/scripts/qa/console-allow.txt` | Every `console.error` and every failed request appears in the allowlist with a reason. Backend `401` and `404` on `/api/v1/*` belong in the allowlist, not in a zero-count assertion |
| KB-01 | Skip link works on both surfaces | `page.keyboard.press("Tab")` on `/` then on `/console`; assert `document.activeElement` matches `a[href="#main-landing"]` then `a[href="#main-viewport"]`; press `Enter` | Landing and console, both themes | First Tab focuses the skip link, its box is non-zero while focused, and Enter moves focus to the section carrying that id |
| KB-02 | Every interactive element reachable | `node scripts/qa/a11y.mjs --check=tab`; Tab up to 200 presses per route, collecting distinct `activeElement` identities, compared with `a[href], button:not([disabled]), input:not([disabled]), select, textarea, [tabindex]:not([tabindex="-1"])` | Landing plus 6 console routes | Every visible focusable element is reached at least once, and focus never leaves the document |
| KB-03 | Focus ring visible | `node scripts/qa/a11y.mjs --check=ring`; focus the first 10 focusables per route, read `outlineStyle`, `outlineWidth`, `boxShadow` | Landing plus 6 console routes, both themes | For every sampled element, `outlineStyle != none` with `outlineWidth != 0px`, or a non-`none` `boxShadow` |
| KB-04 | No focus-trap regression in existing modals | `node scripts/qa/a11y.mjs --check=traps`; open CommandPalette with `Ctrl+K`, Tab 15 times, then `Escape`; additionally open any `Dialog` or `Sheet` trigger present on the route and repeat | Console routes | Focus stays inside the open surface for all 15 presses, `Escape` closes it, and focus returns to the trigger. A route with no such surface records `not applicable` with the reason, never silence |

Row count: 32.

### Not applicable

- EDM and schema validation: no table, column, constraint, or migration is touched. `edm` is not dispatched.
- API contract tests beyond BR-04: no route, request model, or response shape changes. The console rows assert only that data endpoints fail in an allowlisted way when no backend is running.
- Unit tests for new components: no component is added, and the existing primitives keep their exports and props, so coverage is the computed-style and export-surface rows rather than a new unit suite.

### Evidence files

All under `plans/evidence/AVRIG-00002/rc.<NNN>/`.

| Row group | Artifacts |
|---|---|
| ST-01 to ST-06 | `style-<theme>-<route>.json` per surface, `style-offenders.txt`, full-page PNG per route at 1440x900 and 390x844 |
| SC-01, SC-02, SC-03 | `scan-bg-slate.txt`, `scan-bg-gradient.txt`, `scan-palette.txt` (all kept even when empty), `git-grep-exit.txt` |
| TK-01 to TK-03 | `tokens-triplets.json`, `tokens-resolve-<theme>.json`, `theme-css-sha.txt`, `hex-scan.txt`, a copy of `hex-allow.txt` |
| CT-01 to CT-04 | `contrast.json` holding every measured pair with resolved colour source, `contrast-forbidden.txt` |
| LY-01 to LY-03 | `layout-<route>-<width>.json`, `proportions.json`, screenshots at each of the 4 widths |
| CP-01 | `version-badge-<route>-<theme>.json` |
| EX-01 | `ui-exports.json`, `baseline/ui-exports.json`, `baseline-src/` |
| I18-01, I18-02 | `i18n-parity.json`, `i18n-untranslated.txt` |
| PIL-01 | `pills.json` listing every surviving pill with its live-state marker |
| BR-01 to BR-04 | `journey-<set>-<theme>.webm` or Playwright trace, `console-<route>.json`, `requests-failed.json`, `journey-verdict.json` |
| KB-01 to KB-04 | `a11y-tab-<route>.json`, `a11y-ring-<route>.json`, `a11y-traps.json`, focus-order dumps |
| All rows | one `RESULT.md` with the verdict line below and the per-row pass or fail table |

Verdict line:

```text
AVRIG-00002 rc.<NNN> avrig-ai@<sha> avrig-ui@<sha> PASS 32/32 evidence plans/evidence/AVRIG-00002/rc.<NNN>/
```

A green run must name the candidate tag, both commit SHAs, the count of passing rows, and the evidence folder. If any row is blocked, the line reads BLOCKED with the row id and the reason, and the release trigger is not reported.

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
