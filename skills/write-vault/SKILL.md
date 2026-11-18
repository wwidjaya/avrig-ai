---
name: write-vault
description: Write, reformat, and update notes and deliverables in the Obsidian vault adhering to vault metadata schema, typography rules, single-H1 hierarchy, SemVer 2.0, HTML/table escaping, and optional PDF generation via markdown-to-pdf.
---

# write-vault

Standards and operational procedures for creating, updating, and formatting canonical notes, benchmark reports, and reference documents in the Obsidian vault.

Vault locations:
- **Windows:** `D:/Cloud/OneDrive/AI/Personal/vault/`
- **WSL/Linux:** `/mnt/d/Cloud/OneDrive/AI/Personal/vault/`

## 1. Metadata Schema & Frontmatter Rules

Every note MUST include YAML frontmatter with at minimum:

```yaml
---
title: "Document Title"
type: canonical | knowledge | reference | glossary | notes
status: active | draft | deprecated | archived
source-of-truth: true | false
domain: <domain>
subdomain: <subdomain>
category: <category>
topic: <topic>
created: YYYY-MM-DD
updated: YYYY-MM-DD
author: <author>
tags:
  - tag1
  - tag2
---
```

- **Colon-Space Quoting**: Any string containing `: ` (colon followed by space) MUST be enclosed in double quotes (e.g. `title: "Report: Subtitle"`).
- **H1 Heading Alignment**: The document must have exactly ONE top-level `#` heading that matches the frontmatter `title` property verbatim.

## 2. Typography & Writing Constraints

- **Never use the em-dash (`—`)**: Replace all em-dashes with colons (`:`), commas (`,`), parentheses, or a separate sentence.
- **Tone & Style**: Plain, human, professional language. Avoid filler or robotic bullet-speak.
- **Language Fidelity**: Preserve the original language of the source/subject; do not spontaneously translate terms or headings.

## 3. Paragraph Normalization

When reformatting existing notes, normalize paragraphs before saving:

- **Remove premature newline characters**: Reflow wrapped lines so that sentence-continuation lines are joined into single flowing lines (no mid-sentence hard breaks). A line break inside a paragraph is a continuation, not a structural break.
- **Preserve sentence boundaries**: Do not join across sentence-ending punctuation (`.`, `?`, `!`) followed by a space and a capital letter. Full stops close a sentence; a newline after a sentence without a blank line is still a sentence boundary and MUST be kept as a newline.
- **Preserve paragraph breaks**: Blank lines mark paragraph boundaries and MUST be kept intact.
- **Preserve structure**: Do not reflow inside code blocks, table cells, list items, headings, or horizontal rules (`---`).
- **Preserve terminology**: Keep technical terms and original-language strings verbatim; do not reword, translate, or reorder content during normalization.

## 4. Escaping Rules (HTML Tags & Tables)

- **Escape HTML-like Tags (`\<TAG\>`)**:
  - Tags resembling HTML elements (such as `\<CODE\>`, `\<ID\>`, `\<DATE\>`, `\<TYPE\>`, `\<STATUS\>`) in prose or tables will be interpreted by Markdown parsers and headless PDF browsers as raw HTML, causing them to disappear from rendered output.
  - Always escape them as `\<CODE\>`, use HTML entities (`&lt;CODE&gt;`), or wrap in inline code spans (`` `<CODE>` ``).
- **Table Pipe Escaping (`\|`)**:
  - Any pipe character inside table cells (including wikilink display labels `[[Target\|Label]]` or option delimiters) MUST be escaped with a backslash (`\|`) to prevent breaking column alignment.

## 5. Structural Hierarchy & Formatting

- **Single Root H1**: Only one `#` heading allowed per note (at the very top).
- **Top-Level Sections & Annexes**: All major sections, appendices, and annexes MUST use `##` (e.g. `## Annex A: Matrix`).
- **Subsections**: Use `###` for sub-sections and `####` for phases/stages.
- **Section Dividers**: Place a `---` horizontal rule before every major `##` section.
- **Line Separator Spacing (`---`)**: ALWAYS ensure there is at least one blank line both above and below every standalone `---` line separator. Never place `---` directly adjacent to any table row, paragraph, list, or heading. When following a table, an unspaced `---` directly beneath the final table row breaks table parsing in Obsidian and Markdown renderers, causing table cards and trailing rows to render as unformatted text.
- **Structured Data**: Prefer markdown tables over long bulleted lists for comparative evaluations.

## 6. PDF Deliverable Generation

When asked to export or render notes to PDF:
1. Use the `markdown-to-pdf` skill script:
   - Windows: `python $env:OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "<path-to-note.md>" --output "<path-to-output.pdf>" [--orientation landscape|portrait]`
   - WSL: `python $OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "<path-to-note.md>" --output "<path-to-output.pdf>"`
2. **Orientation Choice**:
   - Use `--orientation landscape` for notes containing wide data matrices (5+ columns) to prevent clipping.
   - Use `--orientation portrait` for standard text-heavy documents without wide tables.
3. **Verification**: Confirm output PDF exists and has size > 0 bytes.

## 7. Pre-Save Quality Checklist

Before finalizing any note:
1. `title` in frontmatter matches the top `#` H1 heading exactly.
2. Frontmatter values with `: ` are quoted.
3. No em-dashes remain (`grep` for `—`).
4. HTML-like tags are escaped (`\<TAG\>` or `` `<TAG>` ``).
5. Heading levels are normalized (no subordinate `#` headings).
6. All table columns align and pipes inside cells are escaped (`\|`).
7. Every standalone separator (`---`) has a blank line above and below it (never directly adjacent to a table, paragraph, or heading).
8. Dividers (`---`) precede all top-level `##` sections.
9. Paragraphs are normalized: no premature mid-sentence newlines; sentence boundaries and paragraph breaks preserved; code blocks, tables, and list items untouched.
