---
name: Avrig Landing Surface
description: Public product page for a governed virtual engineering company.
colors:
  paper: "#ffffff"
  cloud: "#f8fafc"
  mist: "#f4f7fb"
  ink: "#111827"
  body: "#475569"
  muted: "#64748b"
  line: "#e2e8f0"
  line-strong: "#cbd5e1"
  blue: "#2563eb"
  blue-soft: "#eff6ff"
  blue-line: "#bfdbfe"
  green: "#15803d"
  green-soft: "#f0fdf4"
  amber: "#a16207"
  amber-soft: "#fffbeb"
typography:
  display:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(3.2rem, 5.55vw, 4.7rem)"
    fontWeight: 650
    lineHeight: 1.045
    letterSpacing: "-0.065em"
  headline:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "clamp(2rem, 3.3vw, 2.8rem)"
    fontWeight: 640
    lineHeight: 1.14
    letterSpacing: "-0.05em"
  title:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1.35rem"
    fontWeight: 640
    lineHeight: 1.3
    letterSpacing: "-0.035em"
  body:
    fontFamily: "IBM Plex Sans, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: "1rem"
    fontWeight: 400
    lineHeight: 1.55
  label:
    fontFamily: "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
    fontSize: "0.75rem"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  sm: "6px"
  md: "10px"
  lg: "16px"
spacing:
  sm: "0.5rem"
  md: "1rem"
  lg: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "0.68rem 1rem"
    height: "44px"
  button-outline:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.body}"
    rounded: "{rounded.sm}"
    padding: "0.68rem 1rem"
    height: "44px"
---

# Design System: Avrig Landing Surface

## Overview

**Creative North Star: "The Clear Operating Model"**

This system belongs to the public Avrig product page, where prospective evaluators and returning operators share equal weight. It explains a virtual engineering company through a familiar product-page structure: concise navigation, a plain-language proposition, a selectable system map, and clear routes into the product. Linear and Vercel are craft references for clarity and finish; the page uses Avrig's own product model and does not copy their visual identity.

The visual language is restrained and legible: white and soft slate surfaces, near-black text, blue for selected links and explanatory highlights, thin borders, moderate radii, and selective structural shadows. The layout uses IBM Plex Sans typography with compact monospaced labels for module and status vocabulary. This record documents the landing proposal only; the production application's existing visual contract remains in `design/ui/AVRIG-00002/design.md`.

**Key Characteristics:**
- Product-first hierarchy with a textual architecture map.
- Neutral surfaces and one restrained blue accent.
- Thin dividers, moderate radii, and limited elevation.
- Responsive layouts with visible keyboard focus and reduced-motion support.

## Colors

The palette pairs a white and cool slate foundation with a blue informational accent, plus green and amber for governance and illustrative status context.

### Primary
- **Near-black Ink**: Used for headings, primary actions, and the dark authoritative-record strip.
- **Clear Blue**: Used for links, lifecycle emphasis, focus-adjacent information, and selected explanatory callouts.

### Secondary
- **Governance Green**: Signals the human approval gate.
- **Caution Amber**: Labels illustrative examples.

### Neutral
- **White Paper**: Main page and component surface.
- **Cloud Slate**: Alternating bands, footers, and soft component surfaces.
- **Mist Tint**: Secondary pale surface behind explanatory groups.
- **Body Slate**: Paragraph text.
- **Muted Slate**: Captions, secondary text, and labels.
- **Line Slate**: Structural borders and dividers.

### Named Rules
**The Evidence Color Rule.** Blue, green, and amber carry informational meaning in the map and governance examples; keep their use restrained and preserve their distinct roles.

## Typography

**Display Font:** IBM Plex Sans (self-hosted WOFF2, with system sans-serif fallbacks)
**Body Font:** IBM Plex Sans (self-hosted WOFF2, with system sans-serif fallbacks)
**Label/Mono Font:** UI monospace stack

**Character:** IBM Plex Sans gives the page a direct product voice. Tight negative tracking distinguishes large headlines, while monospace labels mark technical vocabulary without turning the whole page into a developer console.

### Hierarchy
- **Display** (650, responsive 3.2rem to 4.7rem, 1.045 line-height): The single hero heading.
- **Headline** (640, responsive 2rem to 2.8rem, 1.14 line-height): Section headings.
- **Title** (630 to 650, 0.88rem to 1.35rem): Component and panel titles.
- **Body** (400, 1rem base, 1.55 line-height): General explanatory text; selected copy is constrained to 50ch to 78ch.
- **Label** (roughly 600, 0.72rem to 0.75rem, monospace): Module names, codes, and illustrative-status labels.

### Named Rules
**The Two Voice Rule.** Use IBM Plex Sans for prose and hierarchy; reserve monospace for compact technical labels and codes.

## Layout

The centered content area caps at 1160px with fluid side gutters. The first view uses an asymmetric two-column hero, collapsing to one column below 980px. Below that, sections use two- and three-column grids, a four-column ordered stage grid, and a six-step knowledge flow; these reduce to three, two, or one columns at the 980px, 700px, and 400px breakpoints as appropriate. The navigation becomes a horizontally scrollable row on narrow screens. Section padding and headline sizes use `clamp()` for fluid scaling. A 3rem gutter is standard, 2rem below 700px, and 1.5rem below 400px.

## Elevation & Depth

Depth is mostly structural: white and cloud-slate surfaces are separated by thin borders and bands. Two information panels receive soft shadows, while most cards remain flat. The primary button has a minimal shadow. These treatments keep the system map legible without implying live telemetry.

### Shadow Vocabulary
- **System Map Panel** (`0 18px 44px rgb(15 23 42 / 8%), 0 2px 8px rgb(15 23 42 / 4%)`): Gives the hero architecture map gentle separation from the page.
- **Decision Example** (`0 8px 24px rgb(15 23 42 / 5%)`): Separates the illustrative governance panel from adjacent content.
- **Primary Action** (`0 1px 2px rgb(15 23 42 / 14%)`): Minimal control definition.

### Named Rules
**The Structural Depth Rule.** Keep resting cards flat; reserve soft shadows for the hero system map and the illustrative decision panel.

### Named Rules

**The Authority Link Rule.** The Founder-to-system connector draws in once over 520ms with a restrained ease-out; reduced-motion preferences shorten transitions to 0.01ms.

## Shapes

The shape language uses gently rounded controls (6px), compact content surfaces (10px), and larger grouped panels (16px). Pills are reserved for definition/status labels. Thin neutral borders define cards and tables; architecture groups clip their contents to the enclosing radius. Most geometry is rectangular and consistent.

## Components

### Buttons
- **Character:** Compact, confident actions with a slight lift on hover.
- **Shape:** Gently rounded corners (6px), 44px minimum height, 0.68rem by 1rem padding.
- **Primary:** Near-black fill with white text; hover shifts to a lighter slate and moves up 1px.
- **Outline:** White fill with stronger slate border; hover uses cloud slate and a darker border.
- **Link:** Text action with minimal horizontal padding and no enclosing fill.
- **Hover / Focus:** 160ms background, border, color, and transform transitions; visible keyboard focus uses a 3px blue outline with 3px offset.

### Chips
- **Style:** White or cloud surface with thin slate border and compact label text; technical relation chips use monospace.
- **State:** Informational tags, not selectable controls.

### Cards / Containers
- **Corner Style:** 10px for compact engine and shared-harness panels; 16px for grouped system, engine, organization, governance, and registry panels.
- **Background:** White or cloud slate; blue tint is reserved for selected explanatory content.
- **Shadow Strategy:** See Elevation & Depth; most containers rely on borders.
- **Border:** 1px slate divider, with 2px near-black top rules on model blocks.
- **Internal Padding:** Common values range from 0.8rem to 1.45rem, with larger panels scaling to 2.35rem.

### Navigation
The header uses a 76px minimum-height horizontal row with brand, in-page links, and an outlined workspace action. Links are slate and become near-black on hover. At 700px, navigation moves below the brand/action row and scrolls horizontally.

### Signature Component: System Map
A labelled, text-based definition diagram orders Founder authority above the two operating engines, then the shared harness and authoritative records. It is a product model, not live telemetry. On small screens the surrounding page stacks, while the map stays compact and readable.

## Do's and Don'ts

### Do:
- **Do** use the dark action treatment and keep blue for links and restrained explanatory highlights.
- **Do** distinguish the architecture definition and target technology view from live status.
- **Do** keep status/example labels visible where governance illustrations appear.
- **Do** preserve the semantic page structure, skip link, visible keyboard focus, and reduced-motion behavior.

### Don't:
- **Don't** use color alone to communicate the human approval boundary or example status.
- **Don't** make architecture maps or illustrative artifact examples appear to be live telemetry.
- **Don't** treat this landing proposal as a visual contract for the production app.
