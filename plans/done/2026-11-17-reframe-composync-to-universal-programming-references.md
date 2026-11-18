---
title: Reframe Composync Coding Standards to Universal Programming References
status: planned
created: 2026-11-17
updated: 2026-11-17
author: Plan Agent
tags:
  - refactor
  - standards
  - references
  - coding-standards
  - vault
---

# Reframe Composync Coding Standards to Universal Programming References

## Overview & Objective

Migrate and reframe the engineering and coding standards currently situated in `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\composync\04-coding-standards\` into a reusable, universal set of programming reference documents under `D:\Cloud\OneDrive\AI\Personal\vault\05-references\programming\`.

The refactoring will eliminate Composync-specific isolation (such as corporate ownership tags, project-specific prefixes, and narrow scoping) so that any project across the ecosystem (e.g., `avrig-ai`, `composync`, and future platforms) can reference and adhere to these shared engineering baselines.

---

## Target Taxonomy

Destination root: `D:\Cloud\OneDrive\AI\Personal\vault\05-references\programming\`

```text
05-references/programming/
├── _index.md                             (Universal Engineering & Programming Index)
├── 10-general/
│   ├── 01-coding-principles.md           (Universal core principles, clean code, SOLID)
│   ├── 02-project-repository-structure.md(Standard polyglot repository layout conventions)
│   └── 03-cicd-standards.md              (Universal CI/CD pipeline and automation standards)
├── 20-react/
│   ├── 01-coding-principles-react.md
│   └── 02-repository-structure-react.md
├── 30-flutter/
│   ├── 01-coding-principles-flutter.md
│   └── 02-repository-structure-flutter.md
├── 40-go/
│   ├── 01-coding-principles-go.md
│   └── 02-repository-structure-go.md
├── 50-python/
│   ├── 01-coding-principles-python.md
│   └── 02-repository-structure-python.md
└── 60-rust/
    ├── 01-coding-principles-rust.md
    └── 02-repository-structure-rust.md
```

---

## Step-by-Step Implementation Plan

### Phase 1: Source Discovery & Scope Cataloging
- **Assignee:** `primary`
- **Actions:**
  1. Inspect all files in `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\composync\04-coding-standards\`.
  2. Map each source markdown file (`.md`) and associated assets to its destination under `05-references\programming\`.
  3. Search the vault for existing inbound wikilinks (`[[...]]`) targeting `04-coding-standards` to maintain link continuity.

### Phase 2: Directory Setup & Structure Migration
- **Assignee:** `primary`
- **Actions:**
  1. Create the destination directory tree under `D:\Cloud\OneDrive\AI\Personal\vault\05-references\programming\`:
     - `10-general/`, `20-react/`, `30-flutter/`, `40-go/`, `50-python/`, `60-rust/`.
  2. Copy/move the markdown files from source to destination using normalized, universal file names (e.g., removing `Composync-` prefixes).

### Phase 3: Content Reframing & Metadata Normalization
- **Assignee:** `primary`
- **Actions:**
  1. Update YAML frontmatter for each target note:
     - Change `domain: References`, `subdomain: Programming`.
     - Update `category`, `topic`, and `tags` to reflect universal programming standards rather than project-exclusive tags.
     - Generalize `audience` (e.g., "All software engineers and development agents").
  2. Generalize body content:
     - Replace organization-specific references (e.g., "Composync developers", "Composync GitLab") with generalized terminology ("Project engineers", "Repository CI/CD").
     - Reframe rules so they apply across multiple project contexts (`avrig-ai`, microservices, client apps).
     - Strictly follow `write-vault` styling rules:
       - Single H1 heading matching the frontmatter title verbatim.
       - No em-dashes (use colons, commas, or parentheses).
       - Ensure table pipes are escaped (`\|`) where required.
       - Blank lines enclosing markdown horizontal rules (`---`).

### Phase 4: Master Index Creation & PDF Generation
- **Assignee:** `primary`
- **Actions:**
  1. Create `05-references\programming\_index.md` as the unified entry point and Map of Content (MOC) linking to all general and language-specific standards.
  2. Generate updated reference PDFs using `markdown-to-pdf` if universal offline PDF versions are required.

### Phase 5: Link Reconciliation & Inbound Fixups
- **Assignee:** `primary`
- **Actions:**
  1. Update `02-projects\composync\04-coding-standards\` to point to the new universal reference in `05-references\programming\` (or provide a stub index redirecting to the canonical location).
  2. Update any inbound links in `avrig-ai`, `composync`, or central indexes to link directly to `05-references/programming/...`.

### Phase 6: Verification & Review
- **Assignee:** `primary`
- **Actions:**
  1. Run a link validation check across the modified documents.
  2. Confirm formatting compliance and verify there are no broken cross-references.
