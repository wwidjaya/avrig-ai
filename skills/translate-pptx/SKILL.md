---
name: translate-pptx
description: Translate a .pptx file from Indonesian to English, preserving all formatting, tables, charts, speaker notes, and comments.
---

## Translation Prompt

Use this prompt verbatim when translating:

> You are a professional Indonesian-to-English translator.
> Translate the text faithfully into natural, formal English.
> Rules:
> - Preserve the original meaning exactly.
> - Do not summarize, explain, or add information.
> - Preserve headings, numbering, tables, and formatting.
> - Keep official terms and abbreviations unless an official English equivalent exists.
> - Output only the translated text.

## Workflow

The skill uses a 3-phase process:

### Phase 1 — Extract

Run the extract script to read the .pptx and produce a JSON file of all translatable text segments:

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-pptx/translate_pptx.ps1 -Extract -Path "path/to/presentation.pptx"
```

This creates `path/to/presentation.pptx.segments.json`.

### Phase 2 — Translate (batched, agent-driven)

1. Read the segments JSON file.
2. Count total segments. Process in **batches of 50 text segments**.
3. For each batch, construct a translation request:
   - Present the 50 text values to translate using the Translation Prompt above.
   - After receiving the translations, write them back into the JSON:
     - Add `"translated_text": "<translation>"` to each segment object.
   - Save the JSON file after every batch.
4. Repeat until all segments have `translated_text`.

Example translated segment:
```json
{"id": 0, "type": "paragraph", "text": "Ini adalah paragraf pertama.", "translated_text": "This is the first paragraph."}
```

### Phase 3 — Apply

Run the apply script to write the translated text back into a new .pptx:

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-pptx/translate_pptx.ps1 -Apply -Path "path/to/presentation.pptx"
```

This produces `path/to/presentation.en.pptx` in the same folder as the original.

### Usage example flow

```powershell
# Step 1: Extract
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-pptx/translate_pptx.ps1 -Extract -Path "D:\docs\presentasi.pptx"

# Step 2: Translate segments in presentasi.pptx.segments.json (agent-driven)

# Step 3: Apply
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-pptx/translate_pptx.ps1 -Apply -Path "D:\docs\presentasi.pptx"
```

## Content Types Handled

| Type | Source |
|---|---|
| `paragraph` | Text in slide shapes (text boxes, auto shapes, titles, grouped shapes) |
| `table_cell` | Text in table cells on slides |
| `chart_text` | Chart titles, category axis titles, value axis titles |
| `notes` | Speaker notes text |
| `comment` | Slide comments |

## Notes

- **Grouped shapes**: Traversed recursively — groups within groups are fully supported.
- **Charts**: Only titles and axis titles are translated. Data labels and series names are skipped.
- **SmartArt**: Not supported.
- Segments containing only numbers, whitespace, or punctuation are skipped automatically.
- If a segment's `translated_text` equals the original `text`, it is left unchanged in the document.
- The original file is never modified; a new `.en.pptx` is always created.
- Formatting (fonts, sizes, bold, italic, colors, alignment, table structure) is fully preserved.

