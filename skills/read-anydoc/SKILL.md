---
name: read-anydoc
description: Convert Word (.doc, .docx), PowerPoint (.ppt, .pptx), Excel (.xls, .xlsx), OpenDocument (.odt, .ods, .odp), RTF, EPUB, CSV, and PDF files to GitHub-Flavored Markdown. Use when a task needs the contents of an office document, spreadsheet, presentation, ebook, or PDF you cannot read directly. For scanned/image-only PDFs, falls back to local OCR API.
---

# read-anydoc Skill

Convert documents to clean Markdown using the anydoc CLI (Rust, by Firecrawl).
No install needed — runs via `npx`.

## Invocation

### Windows (PowerShell)
```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/read-anydoc/read_anydoc.ps1 <file> [-o output.md] [--dpi 200]
```

### WSL/Linux (Bash)
```bash
bash $OPENCODE_CONFIG_DIR/shared/skills/read-anydoc/read_anydoc.sh <file> [-o output.md] [--dpi 200]
```

## Rules

1. **Supported inputs:** `.doc`, `.docx`, `.docm`, `.odt`, `.rtf`, `.epub`, `.pdf`, `.ppt`, `.pps`, `.pot`, `.pptx`, `.pptm`, `.ppsx`, `.ppsm`, `.odp`, `.xls`, `.xlsx`, `.xlsm`, `.xlsb`, `.ods`, `.csv`
2. Format is auto-detected from file content. Pass `--format <name>` only for CSV from stdin or missing/wrong extension.
3. **Exit codes:** 0 = success, 1 = conversion failed, 2 = usage error, 3 = PDF needs OCR (scanned/image-only pages)
4. For large documents, write to file with `-o` and read only what you need.
5. **Local OCR fallback:** When anydoc exits with code 3 (scanned PDF), the wrapper automatically:
   - Extracts PDF pages as images (via `pymupdf`)
   - Sends each page to local OCR API (OpenAI-compatible vision endpoint)
   - Combines results into markdown with `<!-- page N -->` markers
   - Requires `OMNIROUTE_API_KEY` env var

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `<file>` | Yes | — | Path to document |
| `-o, --output` | No | stdout | Output markdown file |
| `--format` | No | auto | Force input format |
| `--dpi` | No | 200 | PDF render DPI for OCR fallback |
| `--ocr-model` | No | `ocr` | OCR model ID |
| `--ocr-base-url` | No | `http://localhost:20128/v1` | Local OCR API URL |
| `--keep-images` | No | false | Keep extracted page images |
