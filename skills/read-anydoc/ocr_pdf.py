#!/usr/bin/env python3
"""Convert scanned PDF to Markdown using local OCR API.

Extracts PDF pages as images, sends each to a local OpenAI-compatible
OCR endpoint, and combines the results into a single Markdown document.
"""
import argparse
import base64
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

OCR_PROMPT = (
    "Convert this document page to clean, well-structured Markdown. "
    "Preserve headings, lists, tables, and text layout. "
    "Return ONLY markdown content, no explanations."
)


def get_api_key():
    key = os.environ.get("OMNIROUTE_API_KEY")
    if not key:
        print("Error: OMNIROUTE_API_KEY env var not set.", file=sys.stderr)
        sys.exit(1)
    return key


def pdf_to_images(pdf_path, dpi=200):
    """Extract PDF pages as PNG images using pymupdf."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("Error: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
        sys.exit(1)

    doc = fitz.open(pdf_path)
    images = []
    tmpdir = tempfile.mkdtemp(prefix="read_anydoc_")
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_path = os.path.join(tmpdir, f"page_{page_num + 1:04d}.png")
        pix.save(img_path)
        images.append(img_path)
    return images, tmpdir


def ocr_image(image_path, base_url, api_key, model):
    """Send image to local OCR API and return extracted markdown."""
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": OCR_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
            }
        ],
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"OCR API HTTP {e.code}: {body}", file=sys.stderr)
        return ""
    except Exception as e:
        print(f"OCR API error: {e}", file=sys.stderr)
        return ""

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        print(f"Unexpected OCR response: {result}", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser(description="OCR scanned PDF to Markdown")
    parser.add_argument("--file", required=True, help="Path to scanned PDF")
    parser.add_argument("--output", help="Output markdown file (default: stdout)")
    parser.add_argument("--base-url", default="http://localhost:20128/v1", help="OCR API base URL")
    parser.add_argument("--ocr-model", default="ocr", help="OCR model ID")
    parser.add_argument("--dpi", type=int, default=200, help="PDF render DPI")
    parser.add_argument("--keep-images", action="store_true", help="Keep page images")
    args = parser.parse_args()

    api_key = get_api_key()

    print(f"Extracting pages from {args.file}...", file=sys.stderr)
    images, tmpdir = pdf_to_images(args.file, dpi=args.dpi)

    if not images:
        print("No pages extracted from PDF.", file=sys.stderr)
        sys.exit(1)

    pages = []
    for i, img_path in enumerate(images, 1):
        print(f"OCR page {i}/{len(images)}...", file=sys.stderr)
        markdown = ocr_image(img_path, args.base_url, api_key, args.ocr_model)
        pages.append(f"<!-- page {i} -->\n\n{markdown}")

    output = "\n\n---\n\n".join(pages)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Written to {args.output}", file=sys.stderr)
    else:
        print(output)

    if not args.keep_images:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
