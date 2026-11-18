---
name: markdown-to-pdf
description: Convert a Markdown file to a styled PDF. Use when the user asks to "convert to PDF", "markdown to pdf", "export as PDF", "write as pdf", "render .md to .pdf", "make a PDF of", or "print to pdf" a .md file. Handles YAML frontmatter, tables, and code blocks; outputs a formatted PDF via headless Edge/Chrome with pandoc/xhtml2pdf fallbacks.
---

# markdown-to-pdf

Convert a Markdown file into a formatted PDF, keeping YAML frontmatter out of the output and styling tables/headings for readability.

## When to use

- User asks to convert/export/write/render a `.md` file as PDF.
- Producing PDF deliverables from vault notes, reports, or spec documents.

## Workflow

1. **Locate the input** — confirm the `.md` path exists. If none is given, ask which file.
2. **Determine output path** — if not specified, write the PDF next to the source with the same base name (`.md` → `.pdf`).
3. **Run the converter script** (see below).
4. **Verify** the PDF was produced (file exists, size > 0; optionally text-check with pymupdf if available).
5. **Report the output path** to the user.

## Converter script

The self-contained script lives at `scripts/md_to_pdf.py` (relative to this skill's base directory).

```powershell
# Basic conversion (output next to source, A4 landscape default)
python $env:OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "path\to\input.md"

# Explicit output + portrait orientation
python $env:OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "input.md" --output "out.pdf" --orientation portrait

# Custom title override + custom CSS
python $env:OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "input.md" --title "My Report" --css "path\to\custom.css"

# Explicit browser (if auto-detection fails)
python $env:OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "input.md" --browser "C:\Program Files\Google\Chrome\Application\chrome.exe"
```

```bash
# bash/Linux equivalent
python3 $OPENCODE_CONFIG_DIR/shared/skills/markdown-to-pdf/scripts/md_to_pdf.py "input.md"
```

### Script arguments

| Argument | Description | Default |
|---|---|---|
| `input` (positional) | Path to the `.md` file | required |
| `--output` | Output PDF path | same dir as input, `.pdf` extension |
| `--orientation` | `landscape` or `portrait` | `landscape` |
| `--css` | Path to a custom CSS file (injected into `<style>`) | built-in default |
| `--title` | Override the H1/title shown in the PDF | first H1 of the doc |
| `--browser` | Explicit path to Edge/Chrome executable | auto-detect |

### Dependencies

- **Python + `markdown`** package (already present in this environment: `D:\miniconda3\python.exe`).
- **A Chromium browser** (Edge or Chrome) for HTML→PDF rendering.

### Browser auto-detection order

1. `--browser <path>` argument
2. `$env:BROWSER` / `BROWSER` environment variable
3. Windows standard paths:
   - `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`
   - `C:\Program Files\Microsoft\Edge\Application\msedge.exe`
   - `C:\Program Files\Google\Chrome\Application\chrome.exe`
   - `C:\Program Files (x86)\Google\Chrome\Application\chrome.exe`
4. `pandoc` (as fallback renderer if no browser is found)

## Fallbacks (no browser available)

If no Chromium browser is detected, in order:

1. **pandoc**: `pandoc input.md -o output.pdf --pdf-engine=weasyprint` (requires pandoc + a PDF engine).
2. **Python** `xhtml2pdf` or `reportlab`: `pip install xhtml2pdf` then render the generated HTML.

## Styling defaults

- A4 page, `14mm x 12mm` margins, landscape by default (portrait via `--orientation portrait`).
- Font: Segoe UI / Calibri; H1/H2 in `#1F4E79` with bottom rules.
- Tables: header row `#1F4E79` white text, thin borders, alternating row shading — suited for wide data tables (e.g., regulation matrices).

## Notes

- YAML frontmatter is stripped before rendering (never appears in the PDF).
- Blockquotes are rendered as light-blue callouts; fenced code is preserved.
- The output PDF is a static snapshot — regenerate whenever the `.md` changes.

