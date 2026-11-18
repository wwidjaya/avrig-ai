#!/usr/bin/env python3
import fitz
import os
import re
from pathlib import Path

# Configuration
PDF_PATH = r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management\references\DAMA_Dictionary_of_Data_Management_2nd_Ed.pdf"
OUTPUT_DIR = Path(r"D:\Cloud\OneDrive\AI\Agentic\.opencode\skills\read-pdf\temp_extraction")

def extract_terms():
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"Found {total_pages} pages. Extracting terms from page 18 onwards...")

    for i in range(17, total_pages):  # 0-indexed, starts at page 18
        page = doc[i]
        text = page.get_text()
        
        # Regex to find "Term\nDefinition" patterns or similar structures
        # Since DAMA Dictionary has many formats, we'll capture lines that look like terms
        # and their following blocks until the next term/header.
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        terms_on_page = []
        for j, line in enumerate(lines):
            # Heuristic: Lines that are short and uppercase or contain common acronyms
            # are likely terms.
            if (line.isupper() and len(line) < 30) or (re.search(r'\b[A-Z]{2,}\b', line) and len(line) < 20):
                term = line
                definition = ""
                # Grab following lines as definition until next term or empty
                k = j + 1
                while k < len(lines):
                    if any(c.isupper() for c in lines[k]) and len(lines[k]) < 30 and not lines[k].isdigit():
                        # Next term found
                        break
                    definition += lines[k] + " "
                    k += 1
                terms_on_page.append((term, definition.strip()))

        if terms_on_page:
            out_path = OUTPUT_DIR / f"page_{i+1}.txt"
            with open(out_path, "w", encoding="utf-8") as f:
                for t, d in terms_on_page:
                    f.write(f"**{t}**: {d}\n")
            print(f"Extracted page {i+1}")

    doc.close()

if __name__ == "__main__":
    extract_terms()
