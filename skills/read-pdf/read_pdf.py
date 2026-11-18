#!/usr/bin/env python3
import argparse
import sys
import os
from pathlib import Path

# Insert core converter path to resolve imports
sys.path.insert(0, "D:/Development/kb/ai-system")

try:
    from converter.converters.pdf_hybrid import PdfHybridConverter
except ImportError as e:
    print(f"Import Error: {e}", file=sys.stderr)
    sys.exit(1)

def extract_page(markdown: str, page_num: int) -> str:
    """Extract content for a specific page from hybrid markdown."""
    pages = []
    current_page = None
    content = []

    # Hybrid markers: <!-- page N (Method) -->
    for line in markdown.splitlines():
        if line.startswith("<!-- page") and "-->" in line:
            # Extract page number from "<!-- page 1 (Docling) -->"
            try:
                # Split by 'page ' and ' ('
                parts = line.split("page ")[1].split(" (")[0].strip()
                current_page = int(parts)
            except (IndexError, ValueError):
                current_page = None
            
            if current_page == page_num:
                content = []
            elif current_page is not None:
                # End of requested page
                if content:
                    return "\n".join(content)
        elif current_page == page_num:
            content.append(line)
            
    if content and (current_page == page_num or not current_page):
        return "\n".join(content)
    return ""

def main():
    parser = argparse.ArgumentParser(description="Read PDF as markdown using PdfHybridConverter.")
    parser.add_argument("--file", required=True, help="Path to the PDF file")
    parser.add_argument("--page", type=int, help="Specific page number to extract")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        # Instantiate converter. 
        # Note: settings.llm.vision_model is used internally by PdfHybridConverter
        conv = PdfHybridConverter()
        
        with open(args.file, "rb") as f:
            file_bytes = f.read()
            
        # convert returns (markdown, page_details)
        # filename and mime_type are needed for the converter logic
        filename = os.path.basename(args.file)
        markdown, _ = conv.convert(file_bytes, filename, "application/pdf")
        
        if args.page:
            result = extract_page(markdown, args.page)
            if not result:
                print(f"Error: Page {args.page} not found or empty.", file=sys.stderr)
                sys.exit(1)
            print(result)
        else:
            print(markdown)
            
    except Exception as e:
        # Fallback to PyMuPDF plain text if Hybrid/Docling/Vision fails
        import pymupdf as fitz
        try:
            doc = fitz.open(args.file)
            if args.page:
                if 1 <= args.page <= len(doc):
                    page = doc[args.page - 1]
                    print(page.get_text())
                else:
                    print(f"Error: Page {args.page} out of range (1-{len(doc)}).", file=sys.stderr)
                    sys.exit(1)
            else:
                full_text = []
                for page in doc:
                    full_text.append(page.get_text())
                print("\n\n".join(full_text))
            doc.close()
        except Exception as fallback_e:
            print(f"Critical Error: Both hybrid and fallback extraction failed.\nOriginal: {e}\nFallback: {fallback_e}", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
