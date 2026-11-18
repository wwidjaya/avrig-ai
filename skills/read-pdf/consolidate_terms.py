#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Configuration
TEMP_DIR = Path(r"D:\Cloud\OneDrive\AI\Agentic\.opencode\skills\read-pdf\temp_extraction")
OUTPUT_DIR = Path(r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management")

def consolidate():
    all_terms = {}
    
    # Read all extracted files
    for file_path in sorted(TEMP_DIR.glob("page_*.txt")):
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Simple logic to split by bolded terms (e.g., **ABC**)
            matches = re.split(r'\*\*(.*?)\*\*:', content)
            # matches will be [preamble, term, definition, ..., next_term, ...]
            for i in range(1, len(matches), 2):
                term = matches[i].strip()
                definition = matches[i+1].strip().replace('\n', ' ')
                if term not in all_terms:
                    all_terms[term] = definition

    # Categorize by first letter
    categories = {}
    for term, definition in all_terms.items():
        first_letter = term[0].upper()
        if first_letter in 'ABCDEFGHIJKLMNPQRSTVXY': # Skip common non-glossary chars
            if first_letter not in categories:
                categories[first_letter] = []
            categories[first_letter].append(f"### {term}\n\n{definition}\n\n---")

    # Write to files
    for letter, terms in categories.items():
        file_path = OUTPUT_DIR / f"{letter}.md"
        if not file_path.exists():
            # Create with base template if missing
            content = f"---\ntitle: \"Glossary — Metadata Management: {letter}\"\ntype: glossary\nstatus: active\nsource-of-truth: false\ndomain: Data\nsubdomain: Metadata Management\ncategory: Glossary\ntags:\n  - {letter}\n  - data\n  - glossary\n  - metadata-management\ncreated: 2026-08-31\nupdated: 2026-08-31\n---\n\n# Glossary — {letter}\n\nTerms beginning with **{letter}**.\n\n"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        # Append terms
        with open(file_path, "a", encoding="utf-8") as f:
            for t in terms:
                f.write(t + "\n\n")

    print("Consolidation complete.")

if __name__ == "__main__":
    consolidate()
