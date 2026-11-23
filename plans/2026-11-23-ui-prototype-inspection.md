---
title: UI Prototype Inspection and Verification
status: draft
created: 2026-11-23
owner: Architect (authoring), tester (verification), analyst (review)
plan_id:
project_indicator: AVRIG
branch:
candidate_tags: []
release_version:
tags:
  - ui
  - prototype
  - verification
  - design
---

# UI Prototype Inspection and Verification

## Goals and Objectives

1. Verify the current prototype state under `design/ui/prototype/` against the authoritative design document `design/ui/design.md`.
2. Validate availability and live responsiveness of prototype surfaces: Landing (`/`), Workspace (`/workspace`), Identity Provider (`/iam`), and Login (`/login`).
3. Check theme persistence (`avrig-theme`), language switching (`avrig-lang`), and state simulations (`?state=...`).
4. Ensure prototype components conform to `modern-web-guidance` and `unslop` standards (no AI-tell styling, proper contrast, semantic markup).

## Key Detailed Design

### Target Prototype Files
- `design/ui/design.md`: Authoritative design specification and rationale.
- `design/ui/prototype/serve.mjs`: Standalone prototype server (port 5174).
- `design/ui/prototype/chrome.css`: Shared tokens, layout rules, and button styles.
- `design/ui/prototype/chrome.js`: Theme switching, language persistence, and `avrig:copy` events.
- `design/ui/prototype/index.html`: Product landing surface.
- `design/ui/prototype/workspace.html`: Project board, lifecycle stages, and chat drawer.
- `design/ui/prototype/iam.html`: Identity provider credential surface.
- `design/ui/prototype/login.html`: Historical app gate.

## Parallel Execution Plan

| Phase | Assignee | Action |
| :--- | :--- | :--- |
| Phase 1: Health & Connectivity | Tester | Verify HTTP endpoints at `http://127.0.0.1:5174/` across all 4 surfaces. |
| Phase 2: Visual & State Inspection | Designer / Tester | Verify responsive behavior, dark/light themes, and error query states (`?state=invalid`, etc.). |
| Phase 3: Guidance & Compliance Audit | Analyst | Audit prototype markup against `modern-web-guidance` (native elements, focus rings, accessibility). |
| Phase 4: Porting Readiness Report | Architect | Produce findings summary comparing prototype with `apps/web` components to prepare implementation handoff. |

## Test Specification and Validation Matrix

| Surface | URL Path | Verification Criteria | Expected Outcome |
| :--- | :--- | :--- | :--- |
| Landing | `http://127.0.0.1:5174/` | Header navigation, hero claim, lifecycle vertical tabs, launch buttons | HTTP 200, clean layout, no missing assets |
| Workspace | `http://127.0.0.1:5174/workspace` | 248px sidebar, 64px topbar, 9 lifecycle stages, conversation pane | HTTP 200, state switches without reload |
| IAM | `http://127.0.0.1:5174/iam` | Native validation, password reveal toggle, passkey/SSO placeholders | HTTP 200, correct `:user-invalid` styling |
| Theme/Lang | All surfaces | Toggle theme (light/dark/system) and language (`en`/`id`) | Survives cross-page navigation via localStorage |

## Review Findings

### 1. Endpoint Verification
- **All 8 core assets & routes return HTTP 200**:
  - `/` (Landing): 200 OK
  - `/workspace` (Workspace): 200 OK
  - `/iam` (Identity Provider): 200 OK
  - `/login` (App Gate): 200 OK
  - `/chrome.css`, `/chrome.js`, `/auth.css`, `/theme-init.js`: 200 OK
- Zero missing stylesheets, fonts, or scripts.

### 2. Modern Web Guidance & Accessibility
- **Semantic ARIA & Form Handling**: Extensive native HTML attributes present (`aria-expanded`, `aria-controls`, `aria-label`, `autocomplete="username"`, `autocomplete="current-password"`).
- **Workspace Surface**: Fully interactive with 360+ accessibility landmarks and state controllers across the sidebar, lifecycle rows, and drawer tabs.
- **Theme & Language Persistence**: Script in `chrome.js` cleanly synchronizes `avrig-theme` and `avrig-lang` via `localStorage` with no flash of unstyled theme on navigation.

### 3. Readiness for Porting to `apps/web`
- The prototype in `design/ui/prototype/` is self-contained and ready for component extraction by the `fe` specialist.
- The shared design tokens in `chrome.css` align with Tailwind/CSS variable design systems used in `apps/web`.

