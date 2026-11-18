---
name: translate-docx
description: Translate a .docx file between languages, preserving all formatting, tables, headers/footers, footnotes, endnotes, comments, and text boxes.
---

## Workflow

One-shot translation via an Ollama LLM. Run the skill script:

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-docx/translate_docx.ps1 -Path "path/to/document.docx" -SourceLang "Indonesian" -TargetLangName "English" -TargetLang "en"
```

### Parameters

| Parameter | Purpose | Default |
|---|---|---|
| `-Path` | Input .docx file (required) | — |
| `-SourceLang` | Source language name or ISO code | `Indonesian` |
| `-TargetLangName` | Target language name for the LLM | `English` |
| `-TargetLang` | Code used for the output suffix | `en` |
| `-OllamaModel` | Ollama model | `gemma4:latest` |
| `-OllamaHost` / `-OllamaPort` | Ollama endpoint | `10.30.200.32` / `11434` |
| `-Output` | Explicit output .docx path | `<doc>\<base>.<TargetLang>.docx` |
| `-Config` | Optional JSON config (glossary, repairs, TOC headings) | — |
| `-DryRun` | Scan and report counts without calling the LLM | off |
| `-ShowProgress` | Print per-paragraph progress | off |

Examples:

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-docx/translate_docx.ps1 -Path "path/to/document.docx"
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-docx/translate_docx.ps1 -Path "path/to/document.docx" -SourceLang "French" -TargetLangName "Chinese" -TargetLang "zh"
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-docx/translate_docx.ps1 -Path "path/to/document.docx" -OllamaModel "gemma4" -OllamaHost "localhost" -OllamaPort "11434"
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/translate-docx/translate_docx.ps1 -Path "path/to/document.docx" -DryRun -ShowProgress
```

### Output

The original file is never modified; a new `path/to/document.{TargetLang}.docx` is created (e.g., `document.en.docx`). Use `-Output` to choose a different destination.

### Config file

`-Config` accepts a JSON file whose keys mirror the translator config fields. Useful for controlling terminology and quality:

```json
{
  "temperature": 0.1,
  "delay": 0.3,
  "context_hint": "This is an official government document; use a professional register.",
  "fixed_terms": { "RAHASIA": "CONFIDENTIAL" },
  "word_repairs": { "REPORT FINAL": "FINAL REPORT" },
  "toc_headings": ["DAFTAR ISI", "TABLE OF CONTENTS"]
}
```

- `fixed_terms` — whole-segment overrides applied before any LLM call (exact uppercase match; critical terms can never drift).
- `word_repairs` — exact-phrase fixes applied to the translated text after assembly (per-run and across run boundaries).
- `context_hint` — extra register/terminology guidance given to the LLM.

## Content Types Handled

| Type | Source |
|---|---|
| paragraph | Body paragraphs (text merged across runs for context) |
| table_cell | Table cell paragraphs (each translated with run-level preservation) |
| textbox | Text inside shapes/text boxes |
| header | Section headers |
| footer | Section footers |
| first_page_header | First-page header |
| first_page_footer | First-page footer |
| even_page_header | Even-page header |
| even_page_footer | Even-page footer |
| footnote | Footnotes (id > 0) |
| endnote | Endnotes (id > 0) |
| comment | Document comments |

## How formatting is preserved

- Runs are grouped into segments by identical formatting (bold/italic/underline, font, size, color, ...). Each lexical segment is translated as one unit, so e.g. a bold phrase is translated in a single LLM call and its translated words are trivially bold — no marker tags.
- Translated words are distributed back onto the original runs proportionally by word count, keeping each run's own font properties and original leading/trailing spaces.
- Structural runs (pure punctuation/spaces) are kept verbatim.
- Runs inside hyperlinks are translated like any other run.

## Notes

- Paragraphs containing only whitespace or punctuation are skipped automatically.
- Table-of-contents areas (TOC field instructions, `PAGEREF` entries, and configured TOC headings) are detected and copied verbatim, untouched.
- A deterministic typographic polish pass fixes comma/paren spacing, glued words, and duplicate punctuation after translation.
- Headers/footers linked to the previous section are processed once at their definition point.
- If a segment is echoed back unchanged by the model, one strict retry is attempted.

