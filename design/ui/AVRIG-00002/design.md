---
title: Landing and Console Unslop Design
plan_id: AVRIG-00002
project_indicator: AVRIG
status: approved
created: 2026-11-20
owner: Architect
executor: fe
verifier: analyst
tags:
  - design
  - unslop
  - landing
  - console
---

# Landing and Console Unslop Design

Design artifact for `AVRIG-00002`. Plan: `plans/AVRIG-00002-2026-11-20-landing-console-unslop-redesign.md`.

Method adapted from `unslop` by Damir Sokolovsky (https://heydamir.design/unslop), licensed CC BY 4.0. This artifact is an adaptation for avrig-ai, not a redistribution of the original, and the attribution above is retained as the license requires.

## Surface and scope

Two surfaces, one product, one direction.

| Surface | Files | Before-state evidence |
|---|---|---|
| Landing | `apps/web/src/modules/landing/LandingPage.tsx`, `apps/web/src/modules/landing/LoginModal.tsx`, `apps/web/src/shared/components/LanguageSelector.tsx`, `apps/web/src/shared/components/ThemeSelector.tsx`, `apps/web/src/shared/i18n/translations.ts` | `snapshots/final-landing-dark.png`, `snapshots/landing-light-hero.png`, `snapshots/landing-mobile.png` |
| Console shell and five views | `apps/web/src/shell/CommandCenterLayout.tsx`, `apps/web/src/modules/office/OfficeView.tsx`, `apps/web/src/modules/sdlc/SdlcBoardView.tsx`, `apps/web/src/modules/deliberations/DeliberationsView.tsx`, `apps/web/src/modules/knowledge/KnowledgeView.tsx`, `apps/web/src/modules/knowledge/KnowledgeChat.tsx` | `snapshots/con-office.png` to `snapshots/con-chat.png` |
| Shared foundation | `avrig-ui/packages/tokens/theme.css`, ten files under `packages/ui/src/components/` (`Avatar`, `Badge`, `Button`, `Card`, `CommandPalette`, `Input`, `ScrollArea`, `Sheet`, `Table`, `Tabs`), `apps/web/src/styles/globals.css`, `apps/web/index.html`, two logo SVGs, two vendored woff2 | not rendered separately, read as source |

`LoginModal` is listed with the landing rather than as a separate surface because `LandingPage.tsx` mounts it at line 791. It carries `animate-ping`, `animate-spin` and three uppercase labels of its own, so a pass that ignores it leaves the landing surface half-finished.

`avrig-ui/packages/ui` is not a dependency of `apps/web` (only `@avrig/tokens` is, through a `link:`), so no component in that package is touched. Its checklist coverage is not implied by this artifact.

Verdict: **heavy slop**. Signs appear across colour, type, icons, copy, details and motion on both surfaces. Full process, not polish mode.

Screenshots were captured against the live site `https://app.avrig.ai` at 1280 wide, dark by default, with the light and mobile variants where the layout differs. The console requires an OIDC session; the audit session seeded `sessionStorage["oidc.user:https://iam.avrig.ai:avrig-web-ui"]` and `localStorage avrig-logged-in` to reach the authenticated views. The theme key is `avrig-theme`, not `avrig-ui-theme`; a fixture that writes the wrong name runs every light-theme check in dark and still reports a pass.

## 1. Audit

One line per sign, with where it lives. Sourced from the rendered pages (computed styles) and from the source.

### Surfaces and colour

1. Gradient text: hero H1 highlight span uses `bg-gradient-to-r from-primary via-primary/90 to-foreground bg-clip-text text-transparent`, `LandingPage.tsx` line 190.
2. Hue gradient on a surface: the closing CTA banner uses `bg-gradient-to-b from-primary/10 to-background`, so the banner is a colour wash rather than a surface.
3. Gradient in the logo: `apps/web/public/avrig-logo.svg` and `avrig-mark.svg` define `linearGradient` from `#4B8DF7` to `#2563EB` behind the white stroke glyph. A gradient tile logo is the first tell a generated interface shows.
4. Hardcoded palette fills under a themed shell: ten of the twelve `packages/ui` primitives hardcode Tailwind palette classes instead of theme tokens, so the theme cannot reach them. `Card.tsx` supplies `bg-slate-900/60`, `border-slate-800` and `backdrop-blur-md`; `Button.tsx` and `Badge.tsx` supply `bg-blue-600`; `Badge.tsx` also carries `bg-red-600`, `bg-emerald-600` and `bg-amber-600`; `Input.tsx` carries `ring-blue-500`; `Table.tsx` carries seven slate classes across header, row, cell and caption; `Sheet.tsx`, `CommandPalette.tsx`, `ScrollArea.tsx` and `Avatar.tsx` carry the rest. Only `Dialog.tsx` and `AlertDialog.tsx` are clean.
5. Near-identical tints repeated across unrelated roles: console renders `rgb(59, 130, 246)` on 8 elements that share no meaning, and `rgb(161, 161, 170)` on 21.
6. Everything highlighted: every console nav row carries a badge (`OG/WF`, `MT`, `RE-TE`, `KM/TR`, `KM/AI`), so no row is distinguished from any other.
7. Permanently lit status: `Consensus Engine: Active` sits in the console top bar as a green pill at all times, a status that never changes and therefore says nothing.
8. Multicoloured status pills: agent status renders as purple "Deliberating", blue "Working", green, amber, each a tinted `rounded-full` badge with matching text colour and no neutral default.
9. Tinted modifiers painted at the call site rather than in the primitive: `bg-purple-600/20` and `bg-amber-600/20` in `OfficeView.tsx`, `bg-amber-500/20` in `SdlcBoardView.tsx`, `bg-red-500/20` in `DeliberationsView.tsx`. These sit outside the primitive layer, so a `bg-slate-*` scan reports green while they survive, and fixing the primitives alone would not close Goal 1.

### Type

10. Headings at weight 800 and 900: landing carries 5 elements at 900 (`font-black` wordmark), 6 at 800 (`font-extrabold` hero), and 29 at 700. Hierarchy is carried by weight rather than size.
11. Weight-only hierarchy in the console: 21 elements at 600 and 10 at 700, with no size or colour step to separate them.
12. Uppercase tracked labels: `Autonomous Engineering Rig` at 10px with `tracking-widest`, `RIG.V1` at 9px with `tracking-wider`, `CANONICAL SDLC GATE INSPECTOR` at 11px, four telemetry labels at 11px with 0.55px tracking, `Product Domains` at 11px with 0.55px tracking, `uppercase tracking-wider` at `LanguageSelector.tsx` line 56, and three more in `LoginModal.tsx` at lines 68, 71 and 119.
13. Type nobody chose: the landing renders in the `-apple-system` stack because `globals.css` sets `body { font-family: -apple-system, ... }`, while `theme.css` declares Inter and nothing applies it. The real override point is `globals.css`, not the token file, so editing tokens alone would have changed nothing visible.

### Icons

14. Sparkle used as an AI badge: `Sparkles` inside the hero badge, the most generic "AI product" marker available.
15. Icons carrying their own colour: three `CheckCircle2` at `text-primary` in the hero trust strip, and the badge icon at `text-primary`, so icons compete with the accent instead of deferring to it.
16. Icons in tinted circles: console card headers wrap each icon in a coloured round container.
17. Broken character instead of an entity: the landing footer renders a bare `c` where a copyright symbol belongs (`LandingPage.tsx` line 787), so the intended mark is simply absent. Corrected with `&copy;` rather than by pasting the glyph, so the source stays readable.

### Copy

18. Unverifiable claims: `GATE VERIFIED`, `16 INVARIANTS ACTIVE`, `ACTIVE COMPILATION`, `STATUS: ONLINE`. Each asserts a state that is not being observed.
19. Fabricated evidence: the hero terminal prints invented commit SHA prefixes. In a product whose entire proposition is that claims carry evidence, invented evidence is the worst possible placeholder.
20. Fabricated identity: `avrig-rig://cluster-01.local` and `STATUS: ONLINE` describe a cluster that does not exist.
21. Abstraction stacking in the headline: `Sovereign AI Engineering Rig & Operating System`, three abstractions and no statement of what the reader gets.

### Details and layout

22. Everything is a pill: 19 elements on the landing at a full-round radius, reported by the browser as `3.35544e+07px` (the float form of `9999px`). On the console, `Badge.tsx` renders `rounded-full` on its own line, so every `Badge` is a pill regardless of its call site, and counting pills at call sites undercounts by every badge on the screen.
23. Counts and meta rendered as pills: versions, stage codes and counts are badges rather than quiet mono text.
24. Badge stacked on the wordmark: the `RIG.V1` pill sits beside `avrig.ai` in the logo lockup.
25. No product colour: `--primary` is `221.2 83.2% 53.3%`, the stock shadcn blue, identical to any scaffolded app. The product has no accent of its own.
26. A second design language on the landing surface: `LoginModal.tsx` is mounted by `LandingPage.tsx` at line 791 and brings its own treatments, `uppercase font-bold tracking-wider` at line 68, `font-bold tracking-tight` at line 71, `uppercase` at line 119, `animate-ping` at line 83, `animate-spin` at line 103. It is part of the landing surface and was missing from the first target list.

### Motion

27. Looping motion with no meaning: `animate-pulse` on the emerald dot inside the `RIG.V1` badge, on one console pill dot, and `animate-ping` on the `LoginModal` status ring at line 83.
28. `animate-spin` on a console svg that is not loading anything, and on `RefreshCw` in `LoginModal.tsx` line 103.
29. Catch-all transitions: `transition-all` on the landing stage switcher buttons, `transition` on `Tabs.tsx` line 29 inside the shared primitive so it reaches every consumer, and `transition-colors duration-300` on the landing root, which animates every theme swap at a duration nothing else uses.

### What is already good and stays

- The console keeps real app proportions: a fixed sidebar and fluid content. It is not shrunk into a column.
- The landing has seven sections in a deliberate order, and that order is preserved.
- `SdlcBoardView` already models the canonical 16-stage pipeline with a real status vocabulary, which is the product's actual structure. Nothing invented needs to be added to make the screen true.
- Accessibility groundwork exists: a skip link, `focus-visible` rings, `aria-label` on navigation. Keep all of it.

## 2. Direction

Approved by the user on 2026-11-20 before any code was written. Frozen.

**Product.** avrig-ai runs software delivery as a company: agents plan, execute and verify each stage, the founder holds sole approval authority, and every artifact keeps the version pins and evidence that prove it.

**Character.** Exact, accountable, quiet. Three words, each testable: a screen is exact if nothing is off the grid, accountable if every claim on it is checkable, quiet if the chrome does not compete with the content.

**World.** The drawing office and the inspection bench. Vellum, drafting film, machined plates, ink stamps, tolerance callouts. Not a neon control room.

Why this world and not another: the product's defining invariant is that a human authority signs an artifact and the signature is recorded against a specific version. That is an inspection bench, not a command centre. The command centre metaphor is what produced the fake terminal, the fake cluster hostname and the all-lit status pills. The bench metaphor produces a sheet, a stamp and a tolerance, which are things the product actually emits.

**Moments.** Two, and the only two places where colour and material get rich.

1. **Hero gate certificate.** A single sheet of drafting stock, edge-lit, carrying the current stage name, its verified checklist, artifact versions in tabular mono, and the approval stamp in the lower corner. It replaces the fake terminal. It shows the product's real output: an approved stage artifact. The sheet is built in code, not generated, because it is data rather than scenery.
2. **Traceability path in the console.** One plotted line from requirement through test to deployed artifact with version pins sitting on the line, drawn by hand in SVG. The one richly drawn element on that screen. Everything else on it is neutral.

**Signature.** A stamped approval seal. A small square, 1.5px stroke, radius 4, carrying a monospace work item code and an optional short state word. It appears in exactly four places: the console top bar beside the operator, an approved stage gate in `SdlcBoardView`, the accepted artifact on the hero certificate, and beside the released version in the console sidebar. Never a section ornament, never a nav badge, never a card decoration.

The signature is the product's governance rule rendered as a mark. A competitor could not copy it without also copying the invariant behind it.

## 3. Palette and type

### Neutral ramp: warm

Tinted toward paper and machined metal. Saturation stays very low so no surface reads as a colour on its own.

Values are HSL triplets, not hex. `theme.css` maps every token as `--color-x: hsl(var(--x))` inside `@theme inline`, and `globals.css` calls `hsl(var(--border))`, `hsl(var(--primary))`, `hsl(var(--background))` and `hsl(var(--foreground))` directly, so a hex value written into a triplet slot produces `hsl(#f7f4ee)`, which is invalid, and every surface dies at once. The exact triplets for all 32 tokens are in the plan, in the token table. The hex below is the reference form, for reading only.

| Role | Dark | Dark triplet | Light | Light triplet |
|---|---|---|---|---|
| Deepest surface (sidebar) | `#12110f` | `40 9% 6%` | `#f7f4ee` | `40 36% 95%` |
| Page background | `#161513` | `40 7% 8%` | `#f7f4ee` | `40 36% 95%` |
| Card | `#1c1a18` | `30 8% 10%` | `#fdfbf7` | `40 60% 98%` |
| Raised (active row, input) | `#262421` | `36 7% 14%` | `#efe9df` | `37 33% 91%` |
| Primary text | `#efe9de` | `39 35% 90%` | `#1f1b16` | `33 17% 10%` |
| Secondary text | `#aaa398` | `37 10% 63%` | `#5e554a` | `33 12% 33%` |
| Muted text and icons | `#8a847a` | `38 6% 51%` | `#6b6257` | `34 8% 38%` |
| Hairline | `#2a2724` | `38 6% 20%` | `#e2dcd2` | `38 20% 86%` |

Three text roles only, and they are three distinct tokens rather than three shades of one: `--foreground` for body, `--text-secondary` for supporting text, `--muted-foreground` for meta and captions. `--text-secondary` is new. Without it, shadcn's single `--muted-foreground` would have to serve both roles, and the result is exactly the near-identical-tint soup the audit flagged.

### Accent: the product blue, solid

The logo already carries a real brand colour. It keeps the hue and loses the gradient. A gradient tile is not a brand mark.

| Token | Dark triplet | Light triplet | Use | Contrast |
|---|---|---|---|---|
| `--primary` | `221 83% 53%` | `221 83% 53%` | fills, primary action, current gate | white on it is 5.1:1 |
| `--accent-text` | `221 100% 75%` | `224 76% 48%` | accent text and icons | 7.9:1 dark, 6.0:1 light |

`#2563EB` as text on a dark surface measures 3.6:1 and fails. It is a fill colour only. This is the single most likely mistake in the implementation, so it is stated once here and checked in the matrix.

Semantic colours are toned into the ramp and never used decoratively: `--positive` `151 50% 53%` dark and `142 76% 36%` light, `--negative` `358 75% 59%` dark and `0 72% 51%` light, `--warning` `38 90% 58%` dark and `32 88% 40%` light. Warning is for the "review required" gate state and appears as a dot or icon only, never as text, so no contrast claim is made for it.

All six new tokens need a `--color-*` entry in `@theme inline`. A token with no mapping has no utility class, and the next thing that happens is a hex value in a component.

The accent covers a few percent of each screen: the primary action, the current gate, and the signature seal.

### Radius

`--radius: 0.5rem` stays, so `--radius-lg` is 8 and becomes the control radius.

| Role | Utility | Value |
|---|---|---|
| Control (button, input, select) | `rounded-lg` | 8 |
| Card | `rounded-xl` | 12 |
| Panel (sheet, dialog, certificate) | `rounded-2xl` | 16 |
| Inner element | outer minus padding, never below 4 | computed |

Pills are reserved for live state, not for categories or counts.

### Type

| Role | Family | Weight | Size |
|---|---|---|---|
| Interface | Geist | 400, 500 | 14 to 15 body, 13 to 14 secondary |
| Interface, rare emphasis | Geist | 600 | page title, active nav item |
| Figures, codes, versions, SHAs, stage ids | Geist Mono | 400, 500 | 12 meta, 28 to 32 card figures, `tabular-nums` |
| Hero headline | Geist | 400 to 500 | 56 to 72 desktop, 36 to 44 mobile |
| Hero subhead | Geist | 400 | 18 to 20, secondary colour, max 36rem |

No weight above 600 anywhere. No italic. No negative tracking below 20px. Tracking tightens only on display sizes.

Both families are self-hosted as variable woff2 in `apps/web/public/fonts/` and declared with `@font-face` in `globals.css`. No external origin, so no CSP change and no third-party runtime dependency on a self-hosted deployment.

`globals.css` is the override that matters. Its `body { font-family: -apple-system, ... }` beats `--font-sans` outright, which is why `theme.css`'s Inter declaration never reached the screen. Changing tokens alone would have looked like it did nothing.

## 4. The nine passes

Executed in order by `fe`. A pass finishes across the whole surface before the next begins. Spacing first because the rhythm changes how everything else reads, copy before type and layout because headline length decides its size, visuals and motion last because they must fit a screen that already works.

Each pass lists its target files. Files outside a pass's list are not touched in that pass. Wording in the lists below is exact:

- **the five views** means `apps/web/src/modules/office/OfficeView.tsx`, `apps/web/src/modules/sdlc/SdlcBoardView.tsx`, `apps/web/src/modules/deliberations/DeliberationsView.tsx`, `apps/web/src/modules/knowledge/KnowledgeView.tsx`, `apps/web/src/modules/knowledge/KnowledgeChat.tsx`.
- **the landing surface** means `apps/web/src/modules/landing/LandingPage.tsx`, `apps/web/src/modules/landing/LoginModal.tsx`, `apps/web/src/shared/components/LanguageSelector.tsx`, `apps/web/src/shared/components/ThemeSelector.tsx`.
- **the shell** means `apps/web/src/shell/CommandCenterLayout.tsx`.
- **the primitives** means the ten files under `packages/ui/src/components/` named in the plan's target table: `Avatar`, `Badge`, `Button`, `Card`, `CommandPalette`, `Input`, `ScrollArea`, `Sheet`, `Table`, `Tabs`. `Dialog` and `AlertDialog` are not in the set.

`LoginModal` is part of the landing surface because `LandingPage.tsx` mounts it at line 791, and it brings its own uppercase labels, ping and spin. Leaving it out is how the first revision ended up failing its own goals.

### Pass 1: Spacing

Establish the 4px grid, uniform row heights, and grouping by space.

- Sidebar 256 wide. Nav rows 34 tall with 2 between, icons in one column, labels on one line. Section labels 24 above and 8 below, closer to their own items than to the section above.
- Card padding 24. Page edges 32. Content capped at 1440. Top bar 56 tall.
- Landing: hero 96 from navigation to headline on desktop, 48 on mobile. Section padding 80 to 96. Remove every one-off value not on the 4px scale.
- Stat rows share one height. Card grids get a rhythm rather than equal widths.

Files: the landing surface, the shell, the five views.

### Pass 2: Colour

Move every surface onto the warm ramp and reduce to one accent.

- Rewrite the token values in `theme.css` as the HSL triplets from the plan's token table, all 32 of them, keeping every variable name and every `hsl()` wrapper exactly where it is. Add the six new tokens and their `--color-*` mappings in `@theme inline`. A hex value here breaks every surface at once.
- Sweep every primitive for hardcoded palette classes: `bg-slate-*`, `bg-blue-600`, `bg-emerald-600`, `bg-red-*`, `bg-amber-*`, `text-slate-*`, `border-slate-*` and `ring-blue-500`. Replace each with the token utility that carries the same role. Also drop `backdrop-blur-md` from `Card`: depth comes from surface steps and hairlines, not frost.
- Sweep the call sites for the same classes. The tinted modifiers live in `OfficeView`, `SdlcBoardView` and `DeliberationsView`, not in the primitives, so the primitives alone will not close the goal.
- Delete the hero H1 gradient text and render the highlight in `--accent-text`.
- Delete the CTA banner gradient and make it a raised surface with a hairline.
- Collapse the multicoloured status pills to one neutral badge plus a semantic dot. Purple and blue disappear from the status vocabulary; `--positive`, `--negative` and `--warning` carry the three remaining meanings.
- Remove the coloured icon circles.

Files: `avrig-ui/packages/tokens/theme.css`, the primitives, the landing surface, the shell, the five views.

This pass is the one that must not be split across the two repositories carelessly. `theme.css` lands first and its commit SHA is recorded, because everything after it reads that file through a filesystem symlink into the sibling checkout.

### Pass 3: Icons

One set, one size, one stroke, one colour role.

- Lucide only, 16px, 1.5 stroke. Icons take their text role colour and never their own.
- Drop `Sparkles` from the hero badge.
- Drop the triple `CheckCircle2` trust strip: the three facts become plain mono text separated by hairlines.
- Drop the per-row nav badges. A row that needs a category gets a single leading glyph.
- Replace the bare `c` in the landing footer with `&copy;`.
- Sweep the landing surface's own chrome: `LanguageSelector` and `LoginModal` both carry uppercase labels and their own icon treatments.
- Drop icons that add nothing, including any icon that only duplicates its own label.

Files: the landing surface, the shell, the five views.

### Pass 4: Copy

Say what the product does, for whom, without a claim that cannot be checked.

Removed, with reason:

| Removed | Reason |
|---|---|
| `Sovereign AI Engineering Rig & Operating System` | three abstractions, no outcome |
| `GATE VERIFIED` | asserts a verification that is not happening |
| `16 INVARIANTS ACTIVE` | a count with no referent |
| `ACTIVE COMPILATION` | implies a running build |
| `STATUS: ONLINE`, `avrig-rig://cluster-01.local` | fabricated cluster identity |
| fabricated SHA prefixes | fabricated evidence |

The replacement copy uses only four facts, each already true in the code and the vault design documents: stages run in a defined order, every stage produces an artifact with a version pin, an agent cannot approve its own work, and the founder approves.

Rules: sentence case, no exclamation marks, no trailing period on short strings, no hype words, mock data plausible rather than bracketed.

Files: `apps/web/src/shared/i18n/translations.ts` (both `en` and `id`), the landing surface, the shell.

The console is not translated. No console file imports `translations.ts` and every console string is inline English, so translating it would be a scope change, not a copy pass.

### Pass 5: Type

Install and apply the chosen families, then reduce to two weights.

- Vendor `Geist-Variable.woff2` and `GeistMono-Variable.woff2` into `apps/web/public/fonts/` and declare them with `@font-face` in `globals.css`. No `@fontsource`, no preconnected external link: the deployment is self-hosted, and an external origin would need a CSP change that is outside this plan.
- `globals.css` is the override point. Set `--font-sans` and `--font-mono` on `:root` and change `body` to `font-family: var(--font-sans)`. Until that line changes, nothing on screen moves, because `-apple-system` is currently winning.
- Leave the self-referential `--font-sans: var(--font-sans)` inside `@theme inline` alone. Nothing consumes it once `body` names the family.
- Weights become 400 and 500, with 600 only for page titles and the active nav item. Every `font-black`, `font-extrabold` and `font-bold` goes, including the three in `LoginModal`.
- Gradient text is already gone in Pass 2; confirm no `bg-clip-text` remains.
- Hero headline 56 to 72 desktop and 36 to 44 mobile. Page title 28 to 36. Body 14 to 15. Meta 12 in mono.
- `tabular-nums` on every figure, one number format across each screen.
- `Product Domains` becomes `Product domains`. Every uppercase tracked label becomes sentence case with zero tracking, including `LanguageSelector` and the three in `LoginModal`.

Files: `apps/web/src/styles/globals.css`, `apps/web/public/fonts/Geist-Variable.woff2`, `apps/web/public/fonts/GeistMono-Variable.woff2`, `avrig-ui/packages/tokens/theme.css`, `apps/web/index.html`, the landing surface, the shell, the five views.

### Pass 6: Layout

Recompose the first screen as a whole and keep app proportions in the console.

- Landing hero becomes an asymmetric split: text on 5 of 12 columns, the gate certificate on 7. The certificate runs past the bottom edge so the first screen invites a scroll, and there is no dead empty band.
- Text block centres vertically against the certificate. One primary action and at most one secondary. The trust facts move out of the hero if they crowd it.
- Navigation stays quiet: wordmark, the four existing links, one button. The language and theme selectors remain but sit as quiet controls rather than competing with the action.
- Console keeps a fixed 256 sidebar and fluid content capped at 1440, page as long as its content. Card grids get a rhythm: three or four compact stats above one wide element, or a wide element beside a narrow list.
- Mobile stacks in reading order, headline at 36 to 44, certificate after the actions. The certificate simplifies to fewer rows rather than scaling down. No text below 11px in it.

Files: the landing surface, the shell, the five views.

### Pass 7: Details

Corners, states, small text, and the logo.

- Radius follows the role table: controls `rounded-lg`, cards `rounded-xl`, panels `rounded-2xl`, inner elements by subtraction and never below 4. Pills reduced to the two per console route that carry live state.
- Counts, versions and SHAs become muted mono text, not badges.
- Hover and focus states exist, stay inside the palette, and a visible focus ring remains for keyboard users.
- Table and row states are distinguishable from each other: header, value in use, selection, keyboard focus. `Table.tsx` currently paints all of them with the same slate pair.
- Logo: flat solid `--primary` tile with the white stroke glyph. No gradient, no glow. `apps/web/dist/` is gitignored build output and is not edited.
- `index.html`: title corrected, and the favicon moves from `/vite.svg`, which does not exist in `public/`, to `/avrig-mark.svg`, which does.
- The signature seal appears in its four places and nowhere else.

Files: the landing surface, the shell, the five views, `packages/ui/src/components/Button.tsx`, `apps/web/index.html`, `apps/web/public/avrig-logo.svg`, `apps/web/public/avrig-mark.svg`.

### Pass 8: Visuals

Two moments, both built in code. No generated images for the console, per the method's app rule, and none for the hero either, because the hero must show data rather than scenery.

- **Hero gate certificate.** A raised sheet on a ruled ground: 1% grid, hairline border, radius 16. Contents top to bottom: the stage identifier as a mono eyebrow, the stage name, the verified checklist with small square ticks, the artifact versions in tabular mono with their short SHAs, and the approval seal in the lower right. Plausible values drawn from the existing mock stage data, never invented identifiers.
- **Console traceability path.** In `KnowledgeView`, replace the stacked card list with one SVG plot: requirements on the left, artifacts in the middle, tests and deployed artifacts on the right, joined by a single continuous path with version pins at each junction. The pin for the selected link takes the accent; everything else sits in neutral steps. Hovering a pin raises its detail beside the path rather than in a modal.
- Remove every decorative element that survives: blobs, orbs, glowing grids, floating shapes.

Files: `apps/web/src/modules/landing/LandingPage.tsx`, `apps/web/src/modules/knowledge/KnowledgeView.tsx`.

### Pass 9: Motion

Keep only motion that explains a state change.

- Remove `animate-pulse` from the `RIG.V1` dot and the console pill dot. A status is a coloured dot, not a pulse.
- Remove `animate-ping` from the `LoginModal` status ring.
- Remove `animate-spin` from the console svg and from `RefreshCw` in `LoginModal`.
- Replace `transition-all` with named properties: `transition-colors`, `transition-[transform,opacity]`. `Tabs.tsx` carries `transition` inside the shared primitive, so it reaches every consumer and is fixed there once.
- One easing curve and three durations, 120ms for feedback, 180ms for state, 240ms for entering.
- Never animate width, height, top, left, margin or a large blur.
- One entrance on load: the hero content fades and rises 8px with a 40ms stagger across three children. No card flies in from a different side.
- Press is a 1px scale down. Hover is a colour or surface change, nothing more.
- Wrap the entrance and every transition in `prefers-reduced-motion: reduce`, which drops them to `none` and `0.01ms`. The screen must be complete and static for a user who asks for that. Run `modern-web-guidance` for the current reduced-motion idiom before writing it.

Files: the landing surface, the shell, the five views, `packages/ui/src/components/Tabs.tsx`.

## 5. Constraints for the executor

- Keep the section order, the feature set and the content. This is a craft pass, not a product change.
- `data-testid="sidebar-version-badge"` must still resolve after Pass 7.
- The `@avrig/ui` export surface does not change. Internals change, props and names do not. Prove it by diffing the export list against a `main` baseline, not by reading the diff.
- No new dependency. Fonts are vendored woff2, not a package.
- Camera-ready values live in this file and in the unslop `references/tokens.md`. Where they disagree, this file wins, because the direction was set here.
- Do not add decoration to replace removed decoration. No glass, grain, noise, neon or bento grid.
- Run the `modern-web-guidance` skill before Pass 6 (surface composition), Pass 7 (focus states and the SVG plot) and Pass 9 (reduced motion), and record the retrieved ids in the pass report.
- No raw hex in `apps/web` or `packages/ui`. If a value has no token, the token is missing, not the value.
- Report per pass: what changed, the files touched, and any deviation from this artifact with its reason.

## 6. Verification of the design against the checklist

| Check | Where it is satisfied |
|---|---|
| Direction written, every pass follows it | Section 2, and each pass names the files it moves |
| Spacing on the 4px scale, equal things equal | Pass 1 |
| Icons, labels, figures each in one aligned column | Passes 1, 3, 7 |
| One tinted ramp, three text roles, one accent with contrast | Section 3, Pass 2 |
| Colour reaches components through tokens, not hex, and the token contract stays HSL triplets | Section 3, Pass 2, with the no-raw-hex constraint |
| No hardcoded palette class anywhere, not just `bg-slate-*` | Pass 2, across the primitives and their call sites |
| No hue gradients, gradient text, glow, coloured shadow or blob | Passes 2, 8 |
| No broken character standing in for a symbol | Pass 3, footer `&copy;` |
| No emoji left in the interface | Pass 3 |
| One icon set, one size, one stroke | Pass 3 |
| Type chosen for the character, 400 to 600, no uppercase tracked labels, no italic, no negative tracking on small text | Section 3, Pass 5 |
| The rendered family matches the declared family | Pass 5, via `globals.css` `body` |
| No exclamation marks, no trailing periods, no greeting headline, no unverified claims | Pass 4 |
| Numbers in one format with tabular figures | Pass 5 |
| Nested radii add up, and radius roles map to named utilities | Section 3, Pass 7 |
| Table row states read apart | Pass 7 |
| Buttons share the control radius | Pass 7 |
| Hero has a real visual with a moment, never a labeled placeholder | Pass 8 |
| First screen composed as a whole, no dead band | Pass 6 |
| No looping or bouncy motion, one easing curve, no animated layout properties | Pass 9 |
| Reduced motion is honoured and the screen is complete without motion | Pass 9 |
| Template check: would this fit another product's name | Section 2, the gate certificate and the approval seal are this product's own output and own governance rule. A generic project tool could not carry either. |

## 7. Snapshot index

Before-state captures in `design/ui/AVRIG-00002/snapshots/`. They exist to prove the audit and to be compared against the final render, not to be shipped.

| File | Shows |
|---|---|
| `final-landing-dark.png` | landing, full page, dark |
| `landing-light-hero.png` | landing hero, light, for the surface tint comparison |
| `landing-mobile.png` | landing, 390 wide |
| `con-office.png` | console, Office view, dark |
| `con-sdlc.png` | console, SDLC pipeline view, dark |
| `con-deliberations.png` | console, deliberations view, dark |
| `con-knowledge.png` | console, knowledge and traceability view, dark |
| `con-chat.png` | console, knowledge chat view, dark |

After-state captures go to `plans/evidence/AVRIG-00002/rc.<NNN>/` with the QA run, not here.

## 8. Execution deviations, accepted

Recorded so the analyst reviews the actual result rather than the intended one.

**The certificate does not cross the fold.** Pass 8 asked for the sheet to run past the bottom edge of the first screen. With only honest content it is 471px tall at 1280x900, so it was built to fill the height of the copy block instead: both columns end at the same y, and the hero still ends below the fold at 924 against a 900 viewport. Making the sheet itself cross the fold would need roughly 220px of padding-only air, which would read as emptiness rather than as scale, and emptiness is the dead band the requirement existed to prevent. The requirement's purpose is met by the taller composition; its literal phrasing is not, and the literalism loses to the purpose.

**The ruled ground behind the sheet was dropped.** Pass 8 specified a repeating gradient suggesting drafting film. It read as visual noise at 1280 rather than as stock, and the matrix independently forbids any `backgroundImage` matching a gradient on these surfaces. The sheet sits on its hairline alone. This is the design's own escape hatch applied: if a texture reads as decoration rather than as the material, remove it.

**`packages/ui/dist` had to be regenerated and committed.** The app resolves `@avrig/ui` through `exports` to `dist`, so converting `src` alone changes nothing on screen. See the plan's Stage Gate Record for the full account; the short version is that this artifact's target files listed `src` and the plan excluded `apps/web/dist`, and neither statement mentioned that a second `dist` tree is tracked and consumed.

**The Indonesian headline was rewritten, not translated.** A literal rendering broke to five lines in a 469px column. Copy was recomposed in `id` so the headline holds two to three lines, which is a copy decision inside the direction rather than a layout workaround.
