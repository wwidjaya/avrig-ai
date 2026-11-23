---
title: Knowledge Chat Model and Landing Selector Parity
plan_id:
project_indicator: AVRIG
branch:
candidate_tags: []
release_version:
status: draft
created: 2026-11-19
owner: Architect
tags:
  - raw-draft
  - knowledge-chat
  - ui-parity
---

# Knowledge Chat Model and Landing Selector Parity

Raw draft. Captured verbatim from the user request on 2026-11-19. No discovery, no design, no analysis yet. A draft carries no work-item code, no ledger row, and no branch.

## Goals and Objectives

Unmeasured. To be defined once the user approves further discovery.

## Requested Work

1. Change the knowledge chat model to DeepSeek V4.1 Flash.
2. Make the language selector and the light mode (theme) selector use the same component as the landing page. The landing page is the reference.

## Key Detailed Design

Not authored yet.

### Program Design

Not authored yet.

### Target Program Files (Mandatory)

Not authored yet. Preliminary leads only, unverified:

- `apps/web/src/modules/knowledge/KnowledgeChat.tsx`
- `apps/web/src/shell/CommandCenterLayout.tsx`
- `apps/web/src/modules/landing/LandingPage.tsx`
- `apps/web/src/shared/components/LanguageSelector.tsx`
- `apps/web/src/shared/components/ThemeSelector.tsx`

The knowledge chat model setting has no file identified yet. Backend and configuration surface unknown at draft time.

### EDM Design

Not applicable so far. Revisit if the model selection is stored.

## Parallel Execution Plan

Not authored yet.

## Test Specification and Validation Matrix

Not authored yet. Owned by `tester`.

## Review Findings

Not authored yet. Owned by `analyst`.

## Open Questions

- Which layer decides the knowledge chat model: web client, gateway, or Rust service configuration?
- Does "same component" mean visual parity, or literally one shared component instance used by both the landing page and the command center chrome?
- Is there a model picker in the UI, or is the model fixed in configuration?

## Status History

| Date | Status | Note |
|---|---|---|
| 2026-11-19 | draft | Raw capture of the user request, no analysis performed |
