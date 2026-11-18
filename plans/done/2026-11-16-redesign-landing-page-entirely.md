---
title: "Plan: Complete Redesign of avrig.ai Landing Page"
status: completed
created: 2026-11-16
author: avrig-ai
tags:
  - plan
  - fe
  - landing-page
  - redesign
  - shadcn
  - i18n
---

# Plan: Complete Redesign of avrig.ai Landing Page

## Objective

Completely redesign the `avrig-ai` web landing page into a world-class, premium sovereign AI engineering platform showcase adhering strictly to the `shadcn/ui` skill guidelines, with complete bilingual English/Indonesian i18n, interactive module showcase tabs (SDLC, Office OS, Deliberations, Knowledge), Bento architecture grid, responsive layout, and flawless toggle and routing behavior.

---

## Architectural Context & Decision Baseline

1. **Design System & Components:**
   - Use standard `@avrig/ui` components: `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`, `Badge`, `Button`, `Tabs`, `TabsList`, `TabsTrigger`, `TabsContent`.
   - Strict semantic tokens (`bg-background`, `bg-card`, `bg-muted`, `text-foreground`, `text-muted-foreground`, `text-primary`, `border-border`).
   - Tailwind `size-*` convention throughout.
2. **Interactive Showcase Primitives:**
   - Incorporate an interactive Command Center preview tab interface demonstrating the 4 core product domains.
3. **i18n & Theme:**
   - Full bilingual support in `translations.ts` (`en` and `id`).
   - Smooth toggles for Language and Dark/Light Mode.
4. **Routing & Auth Lifecycle:**
   - "Launch Console" routes directly to Operator Preview if logged in; opens Login Dialog if not logged in.
   - Sign Out cleanly resets session and returns to Landing Page.

---

## Implementation Steps

### Phase 1: Enrich i18n Translations (Assignee: fe)
- Extend `translations.ts` with keys for the interactive tabs, bento highlights, and bottom CTA banner in both `en` and `id`.

### Phase 2: Complete Landing Page Redesign (Assignee: fe)
- Rewrite `LandingPage.tsx` using full shadcn composition:
  - Sticky glassmorphic navbar with logo, nav links, language toggle, theme toggle, and Launch Console CTA.
  - High-impact Hero section with badge, typography, CTAs, and trust metrics.
  - Interactive Showcase component using `Tabs` (SDLC Engine, Office OS, Deliberations, Knowledge Graph).
  - Bento Architecture Grid detailing 4-Tier governance and cryptographic invariance.
  - Step-by-step Autonomous Workflow strip.
  - High-contrast Call to Action card.
  - Clean semantic footer.

### Phase 3: TypeScript Typecheck & Build (Assignee: fe)
- Run `pnpm --filter @avrig/web typecheck`.
- Run `pnpm --filter @avrig/web build`.

### Phase 4: Live Browser Verification in Dev Mode (Assignee: primary)
- Verify in `browser` subagent on `http://localhost:3000/`.
- Verify language switching across all new sections, theme toggling, and console routing.
- Archive plan upon completion.
