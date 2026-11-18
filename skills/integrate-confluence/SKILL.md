---
name: integrate-confluence
description: Create and update Confluence Cloud pages (space Composync) — search/read/create/update/append via a version-checked connector. Use when asked to publish or update documentation on Confluence.
---

# Confluence Writer Skill

Use Confluence (`massiveinonvasi.atlassian.net`, space `Composync`) as the
organization's documentation repository. The skill lets the agent:

- find existing Confluence pages
- read existing pages
- create new pages
- update existing pages
- append sections to existing pages

The connector handles authentication, REST calls, and version conflicts. The
skill defines **when and how** the agent is allowed to write.

## Invocation

Windows:

```
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/integrate-confluence/confluence-tool.ps1 <op> [args...]
```

Linux/WSL:

```
bash $OPENCODE_CONFIG_DIR/shared/skills/integrate-confluence/confluence-tool.sh <op> [args...]
```

## Operations

| Op | Command | Purpose |
|---|---|---|
| resolve space | `space resolve` | space key → space id (default: `Composync`) |
| search | `search -q "text"` | find pages by title/text within the space |
| read | `get -page-id N` | read title, version, parent, body (storage HTML) |
| create | `create -title T [-parent-id N] -doc file.json` | new page from structured doc (max/full width by default) |
| update | `update -page-id N [-title T] [-version N] -doc file.json` | version-checked update |
| append | `append -page-id N -doc file.json` | read → merge new section → update |
| full-width | `full-width -page-id N` | set an existing page to max (full) width |

The connector returns structured JSON for errors. On a version conflict it
prints `{"error": "VERSION_CONFLICT", ...}` and exits with code 2.

## Page title from source note frontmatter

When publishing/updating a page from a vault note, the Confluence page title is
resolved in this order:

1. The source note's YAML frontmatter `title` attribute (authoritative), set on
   the structured doc model's `title` field (or passed as `-title`)
2. If the frontmatter has no `title`, use the **markdown file name** (basename
   without `.md`, e.g. `01-Composync-Coding-Principle`)
3. (update only) the existing Confluence page title

The connector reads `-title` first, then the model `title`, so `-title` is now
optional on `create`.

### Locating the target page (frontmatter IDs)

Vault notes that mirror a Confluence page carry these frontmatter fields — use
them instead of searching:

- `confluence-page-id` / `confluence-page-url` — the page to update
- `confluence-parent-page-id` / `confluence-parent-page-url` — the parent page

For `update`, read `confluence-page-id` from the note's frontmatter and pass it
as `-page-id`. For `create` of a new note, read `confluence-parent-page-id` and
pass it as `-parent-id`.

### Backfill frontmatter after a write (MANDATORY)

After a successful `create` or `update`, **write the Confluence page reference
back into the source vault note's YAML frontmatter**. This is what keeps the
vault↔Confluence mirror resolvable on the next run — a note without these IDs
forces the next agent to search instead.

For a **child page** (created/updated under a parent), add all four fields,
placed after `updated:` in the frontmatter:

```yaml
confluence-page-id: 1053917216
confluence-page-url: https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/1053917216
confluence-parent-page-id: 1054638081
confluence-parent-page-url: https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/1054638081
```

Include the parent pair **whenever the Confluence page has a parent** — this is
the normal case. A note's page can be a child even when the note feels like a
"top-level" document for its folder (e.g. the glossary **index note** mirrors
`Music Publishing`, which sits under `Glossary`). Only a page that truly sits
at the **space root** (no parent) skips the parent pair:

```yaml
confluence-page-id: 1054638081
confluence-page-url: https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/1054638081
```

Check the page's parent with `get -page-id N` (it prints `parent_id=`) and set
`confluence-parent-page-id`/`-url` to that value — never assume a page is at
the root.

Rules:

- Use the exact page IDs/URLs returned by `create`/`get` — never guess them.
- Add (or update) the fields; keep all existing frontmatter intact.
- Update `updated:` to today's date in the same edit.
- This is part of the write workflow, not an afterthought: a page is not
  "done" until its note carries the correct IDs.

## Rules

1. **Never update a page without first reading its current content** (`get`).
2. **Never create a page when an existing page with the same purpose already
   exists** — search first.
3. Before updating, verify: **space, page title, page ID, current version**.
4. **Preserve existing content** unless the user explicitly requests replacement.
5. **Prefer appending a new section** over replacing the entire page.
6. **Never delete a page.**
7. **Never modify page permissions.**
8. **Never move a page** unless explicitly requested.
9. Use the organization's Confluence page template when one exists.
10. After writing, **read the page again and verify** the result.
11. **Report the Confluence page URL** after a successful write.
12. **Backfill the source note's frontmatter** with `confluence-page-id` /
    `confluence-page-url` (and `confluence-parent-page-id` /
    `confluence-parent-page-url` for child pages) after every create/update —
    see "Backfill frontmatter after a write".

## Read → decide → write

Follow this order — never jump straight from a user request to a write:

```
User request
    │
    ▼
search (find existing page)
    │
    ▼
Existing page?  ──no──►  create candidate → build doc → review → create
    │
   yes
    │
    ▼
get (read current content, version)
    │
    ▼
determine operation: update vs append
    │
    ▼
build structured doc (see below)
    │
    ▼
validate model (--check) → render → review changes
    │
    ▼
write (with expected version)
    │
    ▼
get → verify → report URL
    │
    ▼
backfill frontmatter (confluence-page-id/url [+ parent]) → commit
```

**Validate every model before writing.** Run
`python $env:OPENCODE_CONFIG_DIR/shared/skills/integrate-confluence/adf_render.py --check <doc.json>`
— it renders the model (catching unknown section keys, mismatched table rows,
invalid heading levels, etc.) and prints `OK` on success with exit code 0. Only
write a model that passes `--check`.

## Content model

The agent authors a **structured document model** (JSON) — never raw ADF or
storage HTML. The renderer converts it to Confluence storage-format HTML.

```json
{
  "title": "External Identifier Management",
  "links": {
    "01-Composync-Coding-Principle-Go": "https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/1052704791"
  },
  "sections": [
    {"heading": {"level": 2, "text": "Purpose"}},
    {"paragraph": "Text with **bold**, *italic*, `code`, [links](https://...), and [[wikilinks]]"},
    {"bullet_list": ["item one", "item two"]},
    {"numbered_list": ["step one", "step two"]},
    {"table": {"columns": ["Capability", "Description"],
               "rows": [["Identifier Assignment", "Assigns IDs"]]}},
    {"code_block": {"language": "powershell", "text": "Get-Service"}},
    {"link": {"text": "KB", "href": "https://..."}},
    {"panel": {"type": "info", "text": "Note text"}},
    {"rule": true}
  ]
}
```

Supported section types: `heading`, `paragraph`, `bullet_list`, `numbered_list`,
`table`, `roles_table`, `code_block`, `link`, `panel`, `rule`. See
`references/confluence-format.md` for the full schema.

### Wikilinks (Obsidian `[[...]]`)

Vault notes use `[[Note-Name]]` links. To make them clickable on the page:

1. **Build a `links` map** in the model keyed by the wikilink target (basename
   without `.md`) → Confluence page URL. Resolve the URL from the target note's
   `confluence-page-url` frontmatter (read it via the search-vault/read tools).
2. **Always set the label to the target note's document `title`** — the link
   label must be the note's frontmatter `title`, never the note file name. The
   cleanest way is a top-level `titles` map (one per note, no duplication):
   ```json
   "titles": {
     "01-Composync-Coding-Principle-Go": "Composync Coding Principles: Go",
     "02-Composync-Project-Repository-Structure-Go": "Project Repository Structure: Go"
   }
   ```
   Or, per-link, inline `{"url": ..., "title": <note title>}`:
   ```json
   "links": {
     "01-Composync-Coding-Principle-Go": {
       "url": "https://.../pages/1052704791",
       "title": "Composync Coding Principles: Go"
     }
   }
   ```
3. The renderer converts `[[Target]]` and `[[Target|label]]` into `<a>` links,
   picking the label as: explicit `[[target|label]]` > link `title` >
   `titles[target]` > humanized target. **The raw note file name is never used
   as a label.** Wikilinks **not** present in `links` stay as literal `[[…]]`
   text (never a broken anchor).

### In-page section links (same page)

To link to a section **on the same page** (e.g. "see §18"), use Obsidian
in-page syntax `[[#Section Heading|label]]`:

- The renderer collects every `heading` in the model, slugs the heading text,
  and emits a Confluence `anchor` macro immediately before each referenced
  heading.
- `[[#Section Heading|label]]` renders as `<ac:link ac:anchor="...">` pointing
  at that heading.
- **Label uses the section title, never a note file name or a section symbol.**
  If the explicit label is a bare section reference (`§3`, `§18`, `§4.1.3`),
  it is replaced with the full section title; any other explicit label wins;
  omitted label falls back to the heading text.
- Unknown headings stay as literal `[[#…]]` text (never a broken anchor).

Example — §18 of the CSD:
```json
{"paragraph": "Follow the process in [[#18. Development Lifecycle & Governance|§18]]."}
```
renders as an in-page anchor link labeled
`18. Development Lifecycle & Governance` (the section title) that jumps to
that heading.

### Table style (Composync convention)

Match the `User Roles` page / Composync Coding Principle style exactly:

- **Table width**: 1800px (`data-table-width="1800"`) — Confluence
  `data-table-width` is in **pixels**; 1800 is the maximum. There is no
  percentage table width.
- **Column widths**: pixels, not % — always **calculated from cell content**,
  scaled to the 1800px table width (no hardcoded per-column-count defaults). An
  explicit `width` on a column overrides the calculation for that column.
  Sizing is content-driven: the header row is included, and wikilinks are
  measured by their **display label** (not the raw `[[…]]` syntax), so link
  cells like `[[organizations|Organizations & Societies]]` size from the label,
  never from an inflated token that over-widens the column.
- **Header row**: yellow `#ffc400` background, white bold text
- **Number cell**: center-aligned
- **Main roles**: bold H4 name, numbered rows
- **Sub-roles**: H5 name (no bold), empty light-blue `#DEEBFF` number cell
- **Descriptions**: paragraph(s) + bullet lists; "…by:" / "…including:" leads
  straight into a bullet list

Use **`roles_table`** for role/permission-matrix pages (mirrors the User Roles
page). Use plain **`table`** elsewhere. Both render with the same styling.

### Page width (full-width default)

**Every new page is created at maximum width** — the connector automatically
sets the `content-appearance-draft` and `content-appearance-published` content
properties to `full-width` right after `create`. Do **not** try to set width via
the body/ADF (`containerLayout` is rejected by the API); it is a content
property. To create at the default fixed width instead, pass `--no-full-width`.

**Existing pages:** to make a page that already exists full-width, run
`full-width -page-id N` (sets both `content-appearance-*` properties). Verify
with `get`/properties that both keys are present.

Write the model to a temp file (e.g. `C:\Users\wwidj\AppData\Local\Temp\opencode\page.json`)
and pass it with `-doc`.

### Encoding pitfall: never round-trip the model through PowerShell text cmdlets

The model JSON may contain **UTF-8 multi-byte characters** (box-drawing
`│ ├ └`, arrows `↓ →`, the `§` sign). If you rewrite it with PowerShell
`Get-Content`/`Set-Content` (or `.Replace()` + `-Encoding UTF8`), the characters
get double-encoded and the published page shows mojibake (`â”‚`, `â†“`, `Â§`).

- **Write the model only** with the `write` tool or `[System.IO.File]::WriteAllText`
  with a no-BOM `UTF8Encoding($false)`.
- **Edit strings in JSON** via `python -c` / `io.open(..., encoding="utf-8")` +
  `json.load/dump(ensure_ascii=False)`, never via PowerShell string cmdlets.
- If you already corrupted a file, repair it by re-encoding:
  `text.encode("cp1252").decode("utf-8")` (per string), then re-render + re-push.

## Version handling

Confluence versions every page. The connector captures the version on read and
requires the expected version on update. If a human edits the page between your
read and your write, the connector returns `VERSION_CONFLICT`. On conflict:

1. re-read the page (`get`)
2. reconcile your changes with the new content
3. retry the update with the new version

Never force an overwrite without reconciling.

## Approval modes

| Mode | Behavior |
|---|---|
| `draft` | Render content, do **not** write. Show the doc for review. |
| `review` | Show target (space/page/operation) + change summary, get user confirmation, then write. **Default for update and append.** |
| `publish` | Write directly after showing the plan. **Default for create.** |

Present the change summary to the user and obtain approval before any
`update`/`append` write. For `create`, show the plan (space, title, parent) and
proceed.

## References

- `references/confluence-format.md` — storage-format node reference + structured-model schema (incl. percentage widths)
- `references/publishing-policy.md` — approval modes, version-conflict policy, workflow
- `examples/create-page.json`, `examples/update-page.json`, `examples/append-section.json`, `examples/roles-table.json`

## Credentials

Stored in `confluence.env` (gitignored) in this skill folder. Never print or
commit the API token.

