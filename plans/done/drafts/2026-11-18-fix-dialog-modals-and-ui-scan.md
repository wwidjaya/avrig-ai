# Fix Dialog Modals on shadcn/ui Foundations

Status: superseded by 2026-11-18-release-0.3.0-consolidated.md
Owner: plan (authoring), fe (frontend), tester (verification), build (release)
Created: 2026-11-18
Supersedes the Radix-port variant of this plan.

Reference: the "Confirm Sign Out" dialog renders as an unbackdropped box floating over the Office canvas, between the sidebar and the content column, instead of a centered modal.

## Goals and Objectives

1. The dialog layer is rebuilt on the official shadcn/ui Dialog source, not a hand-rolled div and not a private lookalike. Radix primitives underneath, shadcn composition and class names on top.
2. Every console dialog renders as a centered modal over a dimmed, viewport-filling backdrop: sign out, system info, SDLC stage gate, login modal, command palette.
3. Root cause removed: utility classes declared inside `avrig-ai/packages/ui` must reach the emitted stylesheet. Measurable acceptance is that the built CSS contains `position:fixed`, `.z-50`, `.bg-black/50`, `.max-w-lg`, `pointer-events-none`, `border-sidebar-border`, all absent today.
4. Real modal semantics, inherited from Radix rather than reimplemented: portal to `document.body`, Escape closes, backdrop click closes, focus enters and returns to the trigger, `role="dialog"` with `aria-modal` and a labelled title, background scroll locked.
5. shadcn conventions honoured: semantic tokens (`bg-background`, `border`, `text-muted-foreground`, `ring-offset-background`), `cn()` for conditional classes, no manual z-index in call sites, a Title in every dialog, `data-slot` attributes, `size-*` shorthand.
6. Light theme correct: no `bg-slate-900`, `text-slate-100`, or `border-slate-800` literals anywhere in the primitive.
7. No regression to components that currently render acceptably by accident. Enabling package scanning will newly style Sheet, CommandPalette, Table, Tabs, Input, ScrollArea, and the sidebar borders, so a five-domain visual sweep is part of acceptance.

## Key Detailed Design

### Root Cause (verified, not inferred)

`apps/web/src/styles/globals.css` is 14 lines, starts with `@import "tailwindcss";`, and has no `@source`. Tailwind v4 detects sources from the Vite project root (`apps/web`), while `@avrig/ui` resolves through a junction to `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\packages\ui`, outside that root. Its classes are never scanned.

Evidence from the shipped bundle `apps/web/dist/assets/index-BkpD1pmg.css` (48,880 bytes, the file `app.avrig.ai` serves today):

| Token | Emitted | Declared only in |
| --- | --- | --- |
| `position:fixed` | 0 | Dialog wrapper and backdrop |
| `.z-50` | 0 | Dialog wrapper, inner, CommandPalette |
| `.bg-black/70` | 0 | Dialog backdrop |
| `.max-w-lg`, `.scale-100` | 0 | wrapper, inner |
| `.bg-slate-900`, `.border-slate-800`, `.text-slate-100` | 0 | DialogContent, DialogTitle |
| `pointer-events-none`, `caption-bottom` | 0 | Button disabled, Table |
| `border-sidebar-border` | 0 | Sidebar |
| `.bg-card`, `.text-muted-foreground`, `.bg-destructive`, `.size-7` | present | used by app JSX |

Runtime effect, matching the screenshot: the wrapper `div.fixed.inset-0.z-50.flex.items-center.justify-center` keeps only `inset-0` (inert on a static box) and `flex`, so it becomes a flex item of the root row at `CommandCenterLayout.tsx:123`, wedged between the 64px sidebar and `<main>`. The backdrop div has no background and no height. `DialogContent` keeps `w-full rounded-xl border p-6 shadow-2xl` and loses every dark surface class.

Affected call sites, all one primitive: `CommandCenterLayout.tsx:234`, `shared/components/SystemInfoDialog.tsx:61`, `modules/sdlc/SdlcBoardView.tsx:272`, `modules/landing/LoginModal.tsx:52`, `packages/ui/src/components/CommandPalette.tsx:28` from `App.tsx:266`.

### Fix A: Make Tailwind scan the UI package

Add `@source` under the existing import in each Tailwind entry point. Paths are relative to the CSS file and must be proven by building, not assumed:

| Entry file | Candidate directive |
| --- | --- |
| `apps/web/src/styles/globals.css` | `@source "../../../../packages/ui/src";` |
| `apps/mobile/src/styles/globals.css` | `@source "../../../../packages/ui/src";` |
| `apps/desktop/src/index.css` | `@source "../../../packages/ui/src";` |

Proof step: after `pnpm --filter @avrig/web build`, grep the emitted CSS for `position:fixed`, `.z-50`, `.bg-black\/50`. A wrong path fails silently, so grep is the only trustworthy signal. Optional guard: `scripts/check-ui-classes.mjs` extracting class tokens from `packages/ui/src/**/*.tsx` and asserting each appears.

Rejected alternatives: hand-defining the utilities in `globals.css` (drift from Tailwind output, hides the defect), and importing a prebuilt package stylesheet (the local package ships no CSS at all).

### Fix B: Adopt the official shadcn Dialog

Replace `packages/ui/src/components/Dialog.tsx` (currently a conditional `div` with `if (!open) return null`) with the upstream shadcn Dialog source.

Obtain the source through the CLI, never from memory:

```
npx shadcn@latest view @shadcn/dialog
npx shadcn@latest docs dialog alert-dialog
```

The project is not yet shadcn-initialized: no `components.json` exists anywhere in `avrig-ai` or `avrig-ui`. All three prerequisites below are therefore part of the work.

1. **Configuration.** Add `packages/ui/components.json` describing the package rather than the apps: `base: "radix"`, `tailwind` v4, `cssVariables: true`, `iconLibrary: "lucide"`, `aliases.components: "./src/components"`, `aliases.utils: "./src/lib/utils"`, `aliases.ui: "./src/components"`. Do not run a blind `npx shadcn@latest init` at the repo root: it would rewrite `apps/web/src/styles/globals.css` and the token files. If the CLI refuses to init without one, generate the config in a scratch directory and copy the resulting `components.json` in, adjusting paths. Verify with `npx shadcn@latest info`.
2. **Animation utilities.** The upstream Dialog carries `data-[state=open]:animate-in`, `fade-in-0`, `zoom-in-95`, `slide-in-from-*` classes. Neither `tw-animate-css` nor `tailwindcss-animate` is installed anywhere in the workspace, so those classes are currently inert. Install `tw-animate-css` and add `@import "tw-animate-css";` immediately after `@import "tailwindcss";` in the three app entry stylesheets. Decision taken: adopt the dependency, keep upstream classes unchanged.
3. **Component source.** Vendor `dialog` and `alert-dialog` into `packages/ui/src/components/`. Rewrite the CLI's `@/components/ui/...` and `@/lib/utils` imports to relative paths (`../lib/utils`). `"use client"` is harmless in a Vite SPA; keep it for upstream parity so future CLI updates diff cleanly. Keep `data-slot` attributes so later `shadcn add --diff` merges stay meaningful. Export the same names the app already imports (`Dialog`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription`) so no call site breaks.

Expected shape, which the CLI source will supply precisely: `Dialog` is `DialogPrimitive.Root`; `DialogContent` renders `DialogPortal` plus `DialogOverlay` plus `DialogPrimitive.Content` with `fixed top-[50%] left-[50%] z-50 grid w-full max-w-[calc(100%-2rem)] translate-x-[-50%] translate-y-[-50%] gap-4 rounded-lg border bg-background p-6 shadow-lg sm:max-w-lg`, and includes the `DialogPrimitive.Close` button with an `sr-only` label. `DialogHeader` and `DialogFooter` use `flex flex-col gap-2`, replacing the current `space-y-1.5` and `space-x-2`, per shadcn v4 spacing rules.

4. **Destructive confirmations.** shadcn reserves `AlertDialog` for confirmations and `Dialog` for informational modals. Convert the two that ask a question with a destructive action: sign out (`CommandCenterLayout.tsx:234`, buttons Cancel and Sign Out) and the SDLC stage gate review (`SdlcBoardView.tsx:272`). Keep `Dialog` for `SystemInfoDialog`, `LoginModal`, and `CommandPalette`. Decision taken: adopt `AlertDialog` for those two, since the semantic difference is `role="alertdialog"` and the absence of a close X.
5. **Rebuild the package.** The app consumes `packages/ui/dist`, not `src`, so `pnpm --filter @avrig/ui build` must run before any app build.

Guardrails:

1. `LoginModal.tsx:116` already draws its own `absolute inset-0` scrim inside the landing page. Once the real overlay appears, check for double dimming or double blur, and delete the local scrim if it doubles.
2. `CommandPalette` nests `cmdk` inside `Dialog`. Confirm the palette centers, takes keyboard input, and that `cmdk` styling arrives once the scan is fixed.
3. Closing behaviour changes: today the zero-height backdrop means some dialogs close on clicks that land in the wrapper area. Confirm backdrop-only closing, and that a click inside dialog content never closes.
4. Every dialog keeps a `DialogTitle`. Radix logs a console warning without one, and the shadcn rule is absolute; use `className="sr-only"` when a title is visually redundant.
5. No `z-index` added at call sites. If stacking ever conflicts, fix it in the primitive.

### Target Program Files (Mandatory)

| File | Action | Purpose |
|---|---|---|
| `avrig-ai/packages/ui/components.json` | create | shadcn config for the component package, base radix |
| `avrig-ai/packages/ui/src/components/Dialog.tsx` | rewrite | official shadcn Dialog |
| `avrig-ai/packages/ui/src/components/AlertDialog.tsx` | create | official shadcn AlertDialog for confirmations |
| `avrig-ai/packages/ui/src/index.ts` | edit | export AlertDialog parts |
| `avrig-ai/packages/ui/package.json` | edit | `tw-animate-css` if adopted, Radix alert-dialog if not already present |
| `avrig-ai/apps/web/src/styles/globals.css` | edit | `@source` for `packages/ui/src`, `@import "tw-animate-css"` |
| `avrig-ai/apps/mobile/src/styles/globals.css` | edit | same two lines |
| `avrig-ai/apps/desktop/src/index.css` | edit | same two lines |
| `avrig-ai/apps/web/src/shell/CommandCenterLayout.tsx` | edit | sign out confirm becomes AlertDialog |
| `avrig-ai/apps/web/src/modules/sdlc/SdlcBoardView.tsx` | edit | stage gate review becomes AlertDialog |
| `avrig-ai/apps/web/src/shared/components/SystemInfoDialog.tsx` | review | stays Dialog, verify `space-y` to `gap` shifts |
| `avrig-ai/apps/web/src/modules/landing/LoginModal.tsx` | review | remove duplicate scrim if needed |
| `avrig-ai/packages/ui/src/components/Sheet.tsx` | review | same inline-panel pattern |
| `avrig-ai/packages/ui/src/components/CommandPalette.tsx` | review | nested inside Dialog |
| `avrig-ai/apps/web/dist/` | rebuild | embedded at compile time, do not commit |
| `avrig-ai/scripts/check-ui-classes.mjs` | create (optional) | class-token coverage guard |

### EDM Design

No EDM changes. Presentation layer only.

## Parallel Execution Plan

| Stream | Owner | Work | Depends on |
|---|---|---|---|
| C1 Scan fix | fe | `@source` in the three entry files, rebuild web, prove the missing tokens exist | none |
| C2 shadcn groundwork | fe | `components.json`, `tw-animate-css`, `npx shadcn@latest view @shadcn/dialog alert-dialog` | none |
| C3 Primitive rewrite | fe | Vendor Dialog and AlertDialog, fix imports, rebuild `packages/ui` | C1, C2 |
| C4 Call sites | fe | Sign out and stage gate to AlertDialog, sweep the other three, LoginModal scrim | C3 |
| C5 Visual verification | tester | Playwright or wmux, five domains, both themes | C4 |
| C6 Build and deploy | build | `pnpm build`, `make build`, `make deploy` | C5 |
| C7 Release | build | Version bump covering this plus the in-flight composync work | C6 |

C1 is independently valuable: it alone restores backdrop and centering, because the existing hand-rolled component already asks for `fixed inset-0 z-50`. Ship it even if C3 slips.

## Test Specification and Validation Matrix

| ID | Check | Method | Pass criteria |
|---|---|---|---|
| D1 | Utilities emitted | grep built CSS for `position:fixed`, `.z-50`, `.bg-black\/50`, `.max-w-lg`, `pointer-events-none`, `border-sidebar-border` | all present |
| D2 | Centering | open sign out, read `getBoundingClientRect()` vs viewport | center within 8px, width at most 512px or `calc(100% - 2rem)` on narrow |
| D3 | Backdrop | computed styles of overlay element | fixed, inset 0, alpha at least 0.5, `z-index` at least 50 |
| D4 | Escape | open, press Escape | unmounts, no navigation side effect |
| D5 | Backdrop click | click 10px inside the overlay edge | unmounts |
| D6 | Content click | click inside dialog body | stays open |
| D7 | Focus | open | focus inside dialog, Tab cycles, returns to trigger on close |
| D8 | ARIA | inspect attributes | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` resolves to the title |
| D9 | Scroll lock | open over a long page | background frozen, restored after close |
| D10 | AlertDialog semantics | sign out and stage gate | `role="alertdialog"`, no close X, Cancel receives initial focus |
| D11 | Light theme | switch theme, open each modal | readable, no slate remnant, body contrast at least 4.5:1 |
| D12 | All five modals | sign out, system info, stage gate, login modal, palette | each passes D2, D3, D4 |
| D13 | Palette keyboard | open with shortcut, type, arrows, Enter | filtering and selection work, palette centers |
| D14 | Landing modal | open LoginModal from landing | single scrim, no double blur, form usable |
| D15 | Domain sweep | Office, Deliberations, SDLC, Knowledge, Chat | no breakage from newly emitted sidebar, table, tab, input utilities |
| D16 | Console clean | capture console on each domain | no Radix title warnings, no React errors |
| D17 | Mobile and desktop builds | `pnpm --filter @avrig/mobile build`, `--filter @avrig/desktop` | builds pass, `@source` resolves rather than silently empty |
| D18 | shadcn config sanity | `npx shadcn@latest info` inside `packages/ui` | resolves aliases, reports base radix |
| D19 | Live | `curl.exe --ssl-no-revoke https://app.avrig.ai/` then Playwright on the deployed bundle | served hash moved off `index-CMLIAyMM.js`, dialogs behave as in D2 to D12 |

## Review Findings

To be populated by `analyst` after verification. Expected audit points: the primitive is genuinely upstream shadcn source obtained through the CLI, the scanner root cause is fixed rather than papered over, `data-slot` and semantic tokens survive so future `shadcn add --diff` stays meaningful, every dialog path was swept rather than only the one in the screenshot, and light theme contrast is measured.

## Decisions

Both were taken in favour of upstream shadcn parity.

1. **`tw-animate-css` is adopted.** The upstream Dialog ships `animate-in`, `fade-in-0`, `zoom-in-95`, and `slide-in-from-*` classes. Shipping classes that generate nothing is worse than either alternative, and dropping them means the primitive no longer matches upstream source, which breaks the point of using `shadcn add --diff` later. Install it in `packages/ui` and import it in the three app entry stylesheets.
2. **`AlertDialog` is adopted for the two destructive confirmations.** Sign out and the SDLC stage gate review move to `AlertDialog`, giving `role="alertdialog"`, no close X, and initial focus on Cancel. `SystemInfoDialog`, `LoginModal`, and `CommandPalette` stay on `Dialog`. Test row D10 exists to prove the split, so a regression that silently reverts to `Dialog` fails verification.
