#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Convert a Markdown file to a styled PDF via headless Edge/Chrome.

Dependencies:
  - Python package: markdown (pip install markdown)
  - A Chromium browser (Microsoft Edge or Google Chrome), or pandoc as fallback

Usage:
  md_to_pdf.py input.md [--output out.pdf] [--orientation landscape|portrait]
              [--css custom.css] [--title "Title"] [--browser path-to-browser]
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

try:
    import markdown
except ImportError:
    sys.exit("ERROR: Python package 'markdown' is required. Run: pip install markdown")

DEFAULT_CSS = """
@page { size: A4 landscape; margin: 14mm 12mm; }
body { font-family: 'Segoe UI', Calibri, Arial, sans-serif; font-size: 9.5pt; color: #1a1a1a; line-height: 1.35; }
h1 { font-size: 16pt; color: #1F4E79; border-bottom: 2px solid #1F4E79; padding-bottom: 4px; }
h2 { font-size: 12.5pt; color: #1F4E79; margin-top: 18px; border-bottom: 1px solid #9db8d2; padding-bottom: 2px; }
h3 { font-size: 11pt; color: #1F4E79; }
blockquote { background: #eef3f8; border-left: 4px solid #1F4E79; padding: 6px 10px; font-size: 8.8pt; color: #333; margin: 8px 0; }
table { border-collapse: collapse; width: 100%; margin: 6px 0 10px 0; }
th { background: #1F4E79; color: #fff; font-weight: 600; text-align: left; padding: 4px 6px; font-size: 8.6pt; }
td { border: 1px solid #b8c4d0; padding: 3px 6px; vertical-align: top; font-size: 8.6pt; }
tr:nth-child(even) td { background: #f5f8fb; }
strong { color: #0d2f52; }
hr { border: 0; border-top: 1px solid #ccc; margin: 10px 0; }
pre, code { font-family: Consolas, monospace; font-size: 8.4pt; background: #f2f2f2; }
pre { padding: 6px 8px; border: 1px solid #ccc; overflow-x: auto; }
img { max-width: 100%; height: auto; display: block; margin: 10px 0; border: 1px solid #d0d7de; border-radius: 4px; }
"""

BROWSER_PATHS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/microsoft-edge",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
]


def detect_browser(explicit=None):
    if explicit and os.path.isfile(explicit):
        return explicit
    env = os.environ.get("BROWSER")
    if env and os.path.isfile(env):
        return env
    for p in BROWSER_PATHS:
        if os.path.isfile(p):
            return p
    return None


def strip_frontmatter(text):
    m = re.match(r"^---\n.*?\n---\n", text, re.S)
    return text[m.end():] if m else text


def first_h1(html, fallback):
    m = re.search(r"<h1>(.*?)</h1>", html, re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return fallback


def resolve_obsidian_images(md_text, base_dir):
    if not base_dir:
        return md_text

    def _replace_img(match):
        raw = match.group(1).strip()
        parts = raw.split("|")
        img_name = parts[0].strip()
        curr = os.path.abspath(base_dir)
        found = None
        while True:
            for cand in [os.path.join(curr, img_name), os.path.join(curr, "07-attachments", img_name)]:
                if os.path.isfile(cand):
                    found = cand
                    break
            if found:
                break
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
        if found:
            src = "file:///" + found.replace("\\", "/")
            return f'<img src="{src}" alt="{img_name}" />'
        return match.group(0)

    return re.sub(r"!\[\[(.*?)\]\]", _replace_img, md_text)


def build_html(md_text, css_text, title, base_dir=None):
    if base_dir:
        md_text = resolve_obsidian_images(md_text, base_dir)
    body = markdown.markdown(
        md_text, extensions=["tables", "fenced_code", "sane_lists", "nl2br"]
    )
    if not title:
        title = first_h1(body, "Document")
    return f"""<!DOCTYPE html>
<html lang="id"><head><meta charset="utf-8"><title>{title}</title>
<style>{css_text}</style></head>
<body>{body}</body></html>"""


def render_with_browser(browser, html_path, pdf_path):
    url = "file:///" + html_path.replace("\\", "/")
    user_data = tempfile.mkdtemp(prefix="chrome_pdf_")
    try:
        cmd = [browser, "--headless=new", "--disable-gpu", "--allow-file-access-from-files",
               f"--user-data-dir={user_data}", "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", url]
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not (os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0):
            cmd[1] = "--headless"
            subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    finally:
        shutil.rmtree(user_data, ignore_errors=True)
    return os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0


def render_with_pandoc(md_path, pdf_path):
    if not shutil.which("pandoc"):
        return False
    for engine in ("weasyprint", "wkhtmltopdf", "pdflatex"):
        try:
            cmd = ["pandoc", md_path, "-o", pdf_path, f"--pdf-engine={engine}"]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if os.path.isfile(pdf_path) and os.path.getsize(pdf_path) > 0:
                return True
        except subprocess.CalledProcessError:
            continue
    return False


def main():
    ap = argparse.ArgumentParser(description="Convert Markdown to styled PDF.")
    ap.add_argument("input", help="Path to the .md file")
    ap.add_argument("--output", help="Output PDF path (default: input with .pdf)")
    ap.add_argument("--orientation", choices=["landscape", "portrait"], default="landscape")
    ap.add_argument("--css", help="Path to a custom CSS file")
    ap.add_argument("--title", default="", help="Document title override")
    ap.add_argument("--browser", default=None, help="Explicit path to Edge/Chrome")
    args = ap.parse_args()

    if not os.path.isfile(args.input):
        sys.exit(f"ERROR: input file not found: {args.input}")

    output = args.output or os.path.splitext(args.input)[0] + ".pdf"
    if not output.lower().endswith(".pdf"):
        output += ".pdf"
    output = os.path.abspath(output)

    with open(args.input, encoding="utf-8") as fh:
        raw = fh.read()
    md_text = strip_frontmatter(raw)

    css_text = DEFAULT_CSS.replace("A4 landscape", f"A4 {args.orientation}")
    if args.css:
        if not os.path.isfile(args.css):
            sys.exit(f"ERROR: CSS file not found: {args.css}")
        with open(args.css, encoding="utf-8") as fh:
            css_text = fh.read()

    base_dir = os.path.dirname(os.path.abspath(args.input))
    html = build_html(md_text, css_text, args.title, base_dir=base_dir)

    tmpdir = tempfile.mkdtemp(prefix="md_to_pdf_")
    html_path = os.path.join(tmpdir, "doc.html")
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(html)

    ok = False
    method = "unknown"
    browser = detect_browser(args.browser)
    if browser:
        ok = render_with_browser(browser, html_path, output)
        method = os.path.basename(browser)
    if not ok:
        ok = render_with_pandoc(args.input, output)
        method = "pandoc"
    if not ok:
        shutil.rmtree(tmpdir, ignore_errors=True)
        sys.exit(
            "ERROR: could not render PDF. No usable browser (Edge/Chrome) or pandoc found.\n"
            "  - Install Edge/Chrome, or\n"
            "  - pip install xhtml2pdf and render the generated HTML manually:\n"
            f"    xhtml2pdf {html_path} {output}"
        )

    shutil.rmtree(tmpdir, ignore_errors=True)
    size = os.path.getsize(output)
    print(f"PDF written: {output} ({size} bytes) via {method}")

    # Optional text sanity check if pymupdf is available
    try:
        import fitz
        doc = fitz.open(output)
        text = "".join(str(p.get_text()) for p in doc)
        if not text.strip():
            print("WARNING: PDF contains no extractable text (may be image-only).")
        print(f"Pages: {len(doc)}")
        doc.close()
    except ImportError:
        pass


if __name__ == "__main__":
    main()
