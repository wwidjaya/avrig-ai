# Confluence Format Reference

## Structured document model → storage format

The LLM authors a JSON document model. `adf_render.py` renders it to Confluence
**storage-format HTML** required by the REST API. The LLM never writes raw
storage HTML or ADF.

The model `title` field maps from the source note's YAML frontmatter `title`
attribute (falling back to the markdown file name); the connector uses it for
the Confluence page title when `-title` is not given.

## Model file encoding (important)

Models routinely contain **UTF-8 multi-byte characters**: box-drawing
(`│ ├ └ ─`), arrows (`↓ →`), the `§` sign. Keep the JSON file UTF-8 **without
BOM**.

- Write it with the `write` tool or `[System.IO.File]::WriteAllText(path, text,
  (New-Object System.Text.UTF8Encoding($false)))`.
- Never rewrite it through PowerShell `Get-Content`/`Set-Content` (or
  `.Replace()` + `-Encoding UTF8`) — that double-encodes non-ASCII characters,
  producing mojibake on the published page (`â”‚`, `â†“`, `Â§`).
- To edit strings, use Python: `io.open(path, "r", encoding="utf-8")` →
  `json.load` → modify → `json.dump(..., ensure_ascii=False)`.
- If a file is already corrupted, repair each string with
  `s.encode("cp1252").decode("utf-8")`, then re-render and re-push.

## Page width (full-width default)

**Every new page is created at maximum (full) width.** Page layout is *not* a
body property — Confluence Cloud stores it as a content property. After
`create`, the connector sets:

- `content-appearance-draft` = `full-width`
- `content-appearance-published` = `full-width`

Setting these via `POST /wiki/api/v2/pages/{id}/properties` makes the page
render full-width. Do **not** put a layout attribute in the body/ADF
(`containerLayout`/`fullWidth` in `atlas_doc_format` is rejected by the API with
`Error converting ADF to storage format`). Pass `--no-full-width` on `create` to
opt out. To make an **existing** page full-width, run
`full-width -page-id N` (sets both properties); verify both keys exist via the
page properties endpoint.

## Table widths (important)

Confluence table `width` (`data-table-width`) is measured in **pixels** (ADF
spec: editor defaults 760/960/1800, **max 1800**). There is **no percentage
table width** — submitting `data-table-width="95"` produces a 95px table, not
95%.

Pattern used by the skill (matches the Composync Coding Principle tables):

- **Table width:** 1800px (`data-table-width="1800"`), the maximum
- **Column widths:** pixels, e.g. `<col style="width: 152.0px;" />`
- **Column widths are always calculated from content** — there are no hardcoded
  per-column-count defaults. The renderer computes pixel widths from the
  longest cell in each column, scaled to the table width, so a "Language"
  column is not crushed next to a wide one and a short "No."/"Terms" column is
  not stretched to a wide default.
- **A column is never narrower than its longest unbreakable token** — a long
  package name or path (e.g. `02-Composync-Project-Repository-Structure-Rust`)
  sets a hard minimum width so it does not wrap mid-token. The floor is applied
  first, then the remaining table width is distributed proportionally, so short
  columns (e.g. "Audience", "No.") keep readable widths instead of being
  squeezed to a sliver by a wide neighbour.
- **Header row is part of the sizing** — the column header text is fed into the
  content matrix, so a short numeric column (e.g. "No.", "Terms") keeps a
  readable width instead of collapsing to the width of its smallest cell.
- **Wikilinks are measured by their display label, not the raw `[[…]]` syntax** —
  a cell containing `[[organizations|Organizations & Societies]]` is sized from
  the label "Organizations & Societies", not the 30-char token
  `[[organizations|Organizations`. Without this, link syntax inflates the column
  minimum and a Category-like column renders far too wide.
- An explicit model `width` on a column overrides the content calculation and
  keeps that column fixed; the remaining table width is distributed among the
  other columns.

Model `width` values are pixels (e.g. `"width": 152` means 152px).

## Schema

Top-level:

```json
{
  "title": "string (optional)",
  "sections": [ <section>, ... ]   // required, non-empty
}
```

Each `<section>` is a single-key object. Supported keys:

### heading

```json
{"heading": {"level": 2, "text": "Purpose"}}
```

`level`: 1–6 (default 2).

### paragraph

```json
{"paragraph": "text"}
```

Inline markup supported: `**bold**`, `*italic*`, `` `code` ``, `[text](https://url)`,
`[[Wikilink]]` / `[[Wikilink|label]]`. Wikilinks resolve via the model's top-level
`links` map (see below). Display label priority: explicit `[[target|label]]` >
link `title` > target. Unresolvable wikilinks render as literal `[[…]]` text.

### bullet_list

```json
{"bullet_list": ["item one", "item two"]}
```

### numbered_list

```json
{"numbered_list": ["step one", "step two"]}
```

### table

Generic table with Composync styling (see "Composync table style" below).

```json
{"table": {
  "columns": ["No.", "Name", "Description"],
  "rows": [
    [{"text": "1", "align": "center"},
     "System Owner",
     "Description text"],
    [{"text": "", "align": "center", "background": "#DEEBFF"},
     {"text": "Analyst", "bold": true},
     {"blocks": [
        {"paragraph": "Supports by:"},
        {"bullet_list": ["item one", "item two"]}
     ]}]
  ]
}}
```

- `columns`: strings, or `{"title": "...", "width": N}` where `N` is **pixels** (e.g. `152` = 152px). Omitted widths are computed **proportionally to the cell content**; the table width defaults to **1800px** (max).
- Cell value may be a **string**, a **dict** `{text, align, background, bold}`, or **`{blocks: [<section>, ...]}`** for multi-block cells (paragraph/list/heading).
- `align`: `center` or `right` adds an alignment mark; `background` sets the cell color; `bold` adds a strong mark.
- An empty-string first-column cell gets the light-blue sub-row background `#DEEBFF`.

### roles_table

Renders the Composync role-matrix style exactly (see "Composync table style").

```json
{"roles_table": {
  "columns": ["No.", "Name", "Description"],     // optional
  "roles": [
    {"name": "System Owner", "description": "..."},
    {"name": "Membership Officer",
     "description": "The Membership Officer role specializes into these sub-roles:",
     "sub_roles": [
       {"name": "Artist Service Specialist",
        "description": [
          {"lead": "Perform outbond Songwriter registration activities, including:",
           "items": ["Proactively identifying...", "Engaging directly with prospects..."]}
        ]}
     ]}
  ]
}}
```

- Main roles become **numbered** rows: bold `heading` level 4 name, centered number.
- `sub_roles` become **unnumbered** rows: `heading` level 5 name (no bold), empty light-blue `#DEEBFF` number cell.
- `description` may be a string (paragraph) or a list of `{"lead": "...", "items": [...]}` entries — each renders as a lead paragraph followed by a bullet list (the "…by:" / "…including:" notation).

### code_block

```json
{"code_block": {"language": "powershell", "text": "Get-Service"}}
```

`language` is optional; if omitted, no language attribute is set.

### link

```json
{"link": {"text": "KB", "href": "https://example.com"}}
```

### links (top-level)

Resolve Obsidian `[[wikilinks]]` used in inline text to page URLs. Keys are the
wikilink target (note basename without `.md`). Values are either a Confluence
page URL string, or `{"url": ..., "title": ...}` where `title` is the display
label.

**Label rule: the link label is the target note's document `title`, never its
file name.** Prefer a top-level `titles` map (one `title` per note, no
duplication); per-link `{"url", "title"}` is equivalent:

```json
{
  "title": "…",
  "titles": {
    "01-Composync-Coding-Principle-Go": "Composync Coding Principles: Go",
    "02-Composync-Project-Repository-Structure-Go": "Project Repository Structure: Go"
  },
  "links": {
    "01-Composync-Coding-Principle-Go": "https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/1052704791",
    "Composync-Coding-Standards": {
      "url": "https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/370573405",
      "title": "Coding Standards Document (CSD)"
    }
  },
  "sections": [ … ]
}
```

Label priority when rendering `[[Target]]`: explicit `[[Target|label]]` >
`links[Target].title` > `titles[Target]` > humanized target (leading number
prefix and `.md` stripped, `-`/`_` → spaces). **The raw note file name is never
used as a label.**

### In-page section links (`[[#Heading|label]]`)

To link to a section **within the same page** (e.g. "see §18"), use Obsidian
in-page syntax `[[#Section Heading|label]]` in any inline text. No `links`
entry is needed — the renderer resolves it against the model's own headings:

- Every `heading` in the model gets a slugged anchor name; a Confluence
  `anchor` macro is emitted immediately before each heading that is referenced.
- `[[#Section Heading|label]]` → `<ac:link ac:anchor="<slug>">` +
  `<ri:page ri:content-title="<model title>"/>` + the label in
  `<ac:plain-text-link-body>`.
- **Label priority**: explicit `[[#Heading|label]]` > the heading text —
  except that a **bare section-symbol label** (`§3`, `§18`, `§4.1.3`) is
  replaced with the full section title. Labels are the section title — never a
  note file name or a section symbol.
- An unknown heading renders as literal `[[#…]]` text (never a broken anchor).

The generated storage format:
```html
<ac:structured-macro ac:name="anchor" ac:schema-version="1">
  <ac:parameter ac:name="">18-development-lifecycle-governance</ac:parameter>
</ac:structured-macro>
<h2>18. Development Lifecycle &amp; Governance</h2>
...
<ac:link ac:anchor="18-development-lifecycle-governance">
  <ri:page ri:content-title="Coding Standards Document (CSD)"/>
  <ac:plain-text-link-body><![CDATA[18. Development Lifecycle & Governance]]></ac:plain-text-link-body>
</ac:link>
```

> **CDATA is raw text.** Inside `<![CDATA[...]]>` (link labels, code blocks),
> do **not** HTML-escape — `&` stays `&` (never literal `&amp;`). Only the CDATA
> terminator `]]>` is neutralized. The `<h2>` heading above is normal HTML and
> *is* escaped.

### panel

```json
{"panel": {"type": "info", "text": "Note text"}}
```

`type` ∈ `info`, `note`, `success`, `warning`, `error`.

### rule

```json
{"rule": true}
```

## Composync table style

Reference: `User Roles` page
(`https://massiveinonvasi.atlassian.net/wiki/spaces/Composync/pages/307331175`).

Every table on the page follows this exact convention:

| Element | Value |
|---|---|
| Table layout | `align-start`, width **1800px** (`data-table-width="1800"`, max) |
| Columns | `No. | Name | Description`, column widths **computed from content** (narrow "No.", wide "Description") |
| Header cells | background `#ffc400` (yellow), text white (`#ffffff`) + **bold** |
| Number cell | paragraph, center-aligned |
| Main role name | `heading` level 4 + **bold** |
| Sub-role name | `heading` level 5, no bold |
| Sub-role row | empty number cell with background `#DEEBFF` (light blue) |
| Description | paragraph(s) + bullet list(s), interleaved as needed |

### "…by:" notation

Role descriptions list responsibilities with a lead sentence ending in `by:` or
`including:`, immediately followed by a bullet list:

> Manage song metadata **by:**
> - Overseeing and maintaining song metadata entry
> - Validating incoming metadata batches

Render this as `{"lead": "...by:", "items": [...]}` inside `roles_table`, or as
`{"paragraph": "...by:"}` + `{"bullet_list": [...]}` inside a generic table cell.

## Validation

The renderer rejects: unknown section keys, empty/non-list `sections`,
mismatched table rows, invalid heading levels or panel types, and non-string
text values. Errors are reported as `error: invalid document model: <reason>`.

Before creating/updating a page, validate every model with `--check` — it
renders (catching structural errors) and prints `OK` without dumping HTML:

```
python $env:OPENCODE_CONFIG_DIR/.opencode/skills/integrate-confluence/adf_render.py --check doc.json
```

Exit code 0 means the model is publishable.

## Invoking the renderer standalone

```
python $env:OPENCODE_CONFIG_DIR/.opencode/skills/integrate-confluence/adf_render.py doc.json
```

Prints the storage-format HTML to stdout (useful for `draft`/review before
publishing).
