---
title: "Plan: Fix Landing Page and Convert Language/Theme Selectors to Toggles"
status: completed
completed: 2026-11-16
created: 2026-11-16
author: avrig-ai
tags:
  - plan
  - fe
  - landing-page
  - ui
  - ux
  - i18n
  - theme
---

# Plan: Fix Landing Page and Convert Language/Theme Selectors to Toggles

## Objective

Enhance and refine the `avrig-ai` web landing page (`apps/web/src/modules/landing/LandingPage.tsx`). Transform the Language and Theme Mode selector dropdown menus into one-click toggles for frictionless user experience, optimize navigation scroll offsets, clean up unused dependencies, and verify live rendering and toggle behavior using the browser subagent.

---

## Architectural Context & Decision Baseline

1. **UX Friction Reduction:**
   - Previous design utilized `@avrig/ui`'s `DropdownMenu` component for both Language (`en` / `id`) and Theme (`light` / `dark` / `system`).
   - For binary choices like Language (`en` <-> `id`) and active Themes (`light` <-> `dark`), dropdown menus introduce unnecessary interaction steps (2 clicks, popover portals, focus management).
   - One-click toggle buttons directly switch state (`en` <-> `id` and `light` <-> `dark`), showing immediate visual feedback and clear icon/label indicators.

2. **Scroll Offset Invariant:**
   - The landing page uses a sticky header (`sticky top-0 z-40`). Target sections (`#architecture`, `#sdlc`, `#office`, `#deliberations`) have scroll margin padding (`scroll-mt-16` / `scroll-mt-24`) so top navigation jumps do not conceal section headings behind the sticky header.

3. **Subagent Delegation:**
   - Step 1: Implementation of UI/UX improvements (Assignee: `fe`) - Completed
   - Step 2: Build and TypeScript verification (Assignee: `fe`) - Completed
   - Step 3: Launch live preview and browser verification (Assignee: `fe` / `primary`) - Completed

---

## Implementation Steps & Verification Outcome

### Phase 1: Convert Selectors to One-Click Toggles (Assignee: fe)
- Modified `apps/web/src/modules/landing/LandingPage.tsx`:
  - Replaced `DropdownMenu` for language switching with a toggle `Button`:
    - Shows `Languages` icon + uppercase locale code (`EN` / `ID`).
    - Clicking toggles between `en` and `id` via `setLocale(locale === "en" ? "id" : "en")`.
    - Includes accessible `title` and `aria-label`.
  - Replaced `DropdownMenu` for theme switching with a toggle `Button`:
    - Reads `resolvedTheme` from `useTheme()`.
    - Clicking toggles between `light` and `dark` via `setTheme(resolvedTheme === "dark" ? "light" : "dark")`.
    - Renders `<Moon className="text-sky-400" />` in dark mode and `<Sun className="text-amber-500" />` in light mode.
    - Includes accessible `title` and `aria-label`.
  - Cleaned up unused `@avrig/ui` dropdown imports (`DropdownMenu`, `DropdownMenuTrigger`, `DropdownMenuContent`, `DropdownMenuItem`) and icon `Laptop`.

### Phase 2: Navigation & Section Scroll Anchoring (Assignee: fe)
- Added `scroll-mt-16` to `#architecture` and `#sdlc`, and `scroll-mt-24` to `#office` and `#deliberations`.

### Phase 3: TypeScript Validation & Monorepo Build (Assignee: fe)
- Ran `pnpm --filter @avrig/web typecheck` (tsc `--noEmit` passed with 0 errors).
- Ran `pnpm --filter @avrig/web build` (Vite production bundle generated successfully).

### Phase 4: Live Browser Verification (Assignee: primary)
- Started Vite preview server on `http://localhost:3000/`.
- Executed automated visual tests via `browser` subagent:
  1. Initial state confirmed (Dark theme active with Moon icon; Language displaying `EN`).
  2. Language toggle click changed all nav links, badges, headings, and CTAs to Indonesian (`id`).
  3. Language toggle click reverted all strings seamlessly back to English (`en`).
  4. Mode toggle click toggled theme to Light Mode (html class removed, Sun icon rendered, styles updated).
  5. Mode toggle click toggled theme back to Dark Mode (html class `dark` restored, Moon icon rendered).
  6. Final screenshot confirmed visual design fidelity.
