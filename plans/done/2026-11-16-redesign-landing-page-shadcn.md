---
title: "Plan: Redesign Landing Page using shadcn/ui Principles and Components"
status: completed
completed: 2026-11-16
created: 2026-11-16
author: avrig-ai
tags:
  - plan
  - fe
  - landing-page
  - shadcn
  - ui
  - design-system
---

# Plan: Redesign Landing Page using shadcn/ui Principles and Components

## Objective

Redesign the `avrig-ai` web landing page (`apps/web/src/modules/landing/LandingPage.tsx`) following the official `shadcn/ui` design system and component composition guidelines. Replace non-standard raw markup, raw color utilities, and hand-rolled cards with standard shadcn/ui components (`Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`, `Badge`, `Button`), strict semantic colors (`bg-primary`, `bg-muted`, `text-muted-foreground`), and `size-*` layout patterns.

---

## Architectural Context & Decision Baseline

1. **shadcn/ui Component Composition:**
   - **Full Card composition:** Replaced monolithic cards and plain divs with `Card` + `CardHeader` + `CardTitle` + `CardDescription` + `CardContent` + `CardFooter`.
   - **Semantic colors:** Stripped all hardcoded tailwind color names (`emerald-500`, `indigo-500`, `sky-500`) in favor of design tokens (`primary`, `secondary`, `muted`, `accent`, `border`, `card`).
   - **Badges:** Used `<Badge variant="outline">` and `<Badge variant="secondary">` for tags, hierarchy levels, and telemetry states instead of custom styled spans.
   - **Icon & Dimensions:** Used Tailwind CSS `size-*` utility instead of `w-* h-*` when dimensions are equal.
   - **Button Variants:** Leveraged native button variants (`size="icon"`, `size="sm"`, `size="lg"`, `variant="default"`, `variant="outline"`, `variant="ghost"`).

2. **Subagent Delegation:**
   - Phase 1: Landing Page component refactoring & shadcn redesign (Assignee: `fe`) - Completed
   - Phase 2: Build and Typecheck Verification (Assignee: `fe`) - Completed
   - Phase 3: Live Browser Verification & Artifact Archival (Assignee: `fe` / `primary`) - Completed

---

## Implementation Steps & Verification Outcome

### Phase 1: Component Refactoring (Assignee: fe)
- Updated `apps/web/src/modules/landing/LandingPage.tsx`:
  - **Header & Navbar:**
    - Refined brand logo container with `size-9` and semantic token backgrounds.
    - Styled language toggle with `<Button variant="ghost" size="sm" className="gap-1.5 font-mono text-xs">`.
    - Styled theme toggle with `<Button variant="ghost" size="icon">`.
  - **Hero Section:**
    - Converted custom hero pill to `<Badge variant="outline" className="gap-2 px-3 py-1">`.
    - Refined CTA action buttons with `size="lg"` and semantic variants.
    - Refactored Telemetry indicators into composed `<Card>` components with `CardHeader` and `CardContent`.
  - **Architecture Hierarchy Section:**
    - Refactored 4-tier organization cards into standard composed `Card`s with `CardHeader`, `Badge`, `CardTitle`, and `CardDescription`.
  - **Feature Showcase Section:**
    - Refactored SDLC, Office OS, Deliberations, and OIDC cards into composed `Card`s with `CardHeader`, `CardTitle`, `CardDescription`, and `CardFooter`.
  - **Login Modal:**
    - Refactored `apps/web/src/modules/landing/LoginModal.tsx` to adhere to `size-*` and semantic color rules.
  - **Footer:**
    - Styled with semantic border and muted foreground tokens.

### Phase 2: Build & Typecheck (Assignee: fe)
- Ran `pnpm --filter @avrig/web typecheck` (tsc `--noEmit` passed with 0 errors).
- Ran `pnpm --filter @avrig/web build` (Vite production bundle generated successfully).

### Phase 3: Live Browser Verification (Assignee: primary)
- Tested live preview at `http://localhost:3000/` using the `browser` subagent:
  1. Full page layout verified in dark mode with composed shadcn components (`final_step_12.png`).
  2. Language toggle click changed language between English and Indonesian.
  3. Theme mode toggle click dynamically switched palette between Dark Mode and Light Mode.
  4. Captured visual screenshots confirming shadcn/ui layout and typography fidelity.
