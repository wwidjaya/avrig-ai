---
name: read-pdf
description: Read PDF documents to markdown using the PdfHybridConverter (Docling + Vision LLM hybrid extraction from DAMA-DGM converter system).
---

# read-pdf Skill

Converted PDF files to markdown using the converter module from `D:\Development\kb\ai-system\converter`. Uses `PdfHybridConverter` which applies:

- **Docling**: Native text extraction for digital PDFs
- **Vision LLM (LightOnOCR-2)**: Falls back for scanned pages requiring OCR

## Invocation

### Windows (PowerShell)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/read-pdf/cli_read.ps1 --file "path\to\document.pdf"
```

### Single Page (Windows)

```powershell
pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/read-pdf/cli_read.ps1 --file "path\to\document.pdf" --page 3
```

### WSL/Linux (Bash)

```bash
bash $OPENCODE_CONFIG_DIR/shared/skills/read-pdf/cli_read.sh --file /path/to/document.pdf
```

### Single Page (Linux)

```bash
bash $OPENCODE_CONFIG_DIR/shared/skills/read-pdf/cli_read.sh --file /path/to/document.pdf --page 3
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `--file` | Yes | Path to the PDF file |
| `--page` | No | Specific page number (1-based) |

## Output

- Full markdown content (`--page` omitted)
- Single page markdown (`--page N` specified)
- Markers `<!-- page N (Docling) -->` or `<!-- page N (OCR) -->` in markdown

## Fallback Behavior

If Vision LLM OCR fails or key unavailable, automatically falls back to PyMuPDF plain text extraction.

## Dependencies

- Python venv at `D:\Development\kb\ai-system\.venv`
- Packages: `pymupdf`, `docling`