#!/usr/bin/env python3
import json
from pathlib import Path
import pymupdf

# Paths
PDF_PATH = r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management\references\DAMA_Dictionary_of_Data_Management_2nd_Ed.pdf"
OUTPUT_JSON = Path(r"D:\Cloud\OneDrive\AI\Agentic/.opencode\skills\read-pdf\dama_terms.json")

KEYWORDS = [
    'metadata', 'data management', 'governance', 'data steward',
    'data catalog', 'data registry', 'repository', 'data architecture',
    'data model', 'master data', 'reference data', 'data quality',
    'data lineage', 'data integration', 'dama', 'dmbok', 'iso 11179',
    'dublin core', 'data dictionary', 'entity-relation',
    'conceptual data model', 'logical data model',
    'physical data model', 'data element', 'data object', 'information govern',
    'mdm', 'rdm', 'eim', 'ilm', 'cdmp',
    'ontology', 'semantic', 'taxonomy', 'data mesh', 'data fabric'
]

def is_metadata_related(term, definition):
    combined = (term + " " + (definition or "")).lower()
    return any(kw in combined for kw in KEYWORDS)

def main():
    doc = pymupdf.open(PDF_PATH)
    all_terms = []
    
    # Start from page 10 onwards (skip intro)
    for i in range(9, len(doc)):
        page = doc[i]
        text = page.get_text()
        if not text.strip(): continue
        
        # DAMA Dictionary entries usually follow "Term\nDefinition" 
        # or are part of a list with markers like "1.", "2."
        # We split by double newlines to isolate potential blocks
        blocks = [b.strip() for b in text.split('\n\n') if b.strip()]
        
        for j, block in enumerate(blocks):
            # Skip headers/noise
            if any(x in block for x in ['DAMA Dictionary', 'Copyright', 'Order 85101', 'Terms and Definitions']):
                continue
            
            # Try to find term-definition pairs within a single OCR-merged block
            # Heuristic: first few words are term (Capitalized, short)
            # Remaining part is definition
            lines = block.split('\n')
            if len(lines) > 1:
                # Check if first line is a term (short, capitalized)
                first_line = lines[0].strip()
                if len(first_line.split()) <= 6 and first_line[0].isupper():
                    definition = " ".join(lines[1:])
                    terms_found = []
                    # If there are multiple terms in one block (e.g. multiple short definitions)
                    # we might need to split them, but for now keep as one
                    if is_metadata_related(first_line, definition):
                        all_terms.append({
                            'term': first_line,
                            'definition': definition,
                            'type': 'definition'
                        })
            else:
                # If single line block, check if it's a term/definition combo
                # e.g. "Term: Definition" or "Term \n Definition" (if \n is lost)
                if ":" in block:
                    parts = block.split(":", 1)
                    term_p = parts[0].strip()
                    defn_p = parts[1].strip()
                    if is_metadata_related(term_p, defn_p):
                        all_terms.append({
                            'term': term_p,
                            'definition': defn_p,
                            'type': 'definition'
                        })

    doc.close()
    
    # Deduplicate
    seen = set()
    unique = []
    for t in all_terms:
        key = t['term'].lower().strip()
        if key and key not in seen:
            seen.add(key)
            unique.append(t)
    
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)
    print(f"Extracted {len(unique)} unique terms")

if __name__ == "__main__":
    main()
