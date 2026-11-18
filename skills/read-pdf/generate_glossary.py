#!/usr/bin/env python3
import json
import re
from pathlib import Path

# Paths
JSON_PATH = Path(r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management\references\glossary-export\glossary-export.json")
GLOSSARY_DIR = Path(r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management")

FRONTMATTER_TEMPLATE = """---
title: "Glossary — Metadata Management: {letter}"
type: glossary
status: active
source-of-truth: false
domain: Data
subdomain: Metadata Management
category: Glossary
tags:
  - {letter_lower}
  - data
  - glossary
  - metadata-management
  - nist
created: 2026-08-31
updated: 2026-08-31
---
"""

def clean_text(text):
    """Clean HTML-like tags and extra whitespace from text."""
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', text)
    # Normalize whitespace
    clean = ' '.join(clean.split())
    return clean

def main():
    with open(JSON_PATH, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    parent_terms = data['parentTerms']
    
    from collections import defaultdict
    terms_by_letter = defaultdict(list)
    
    for term_data in parent_terms:
        term = term_data.get('term', '').strip()
        definitions = term_data.get('definitions')
        
        if not term or not definitions:
            continue
        
        first_letter = term[0].upper()
        if not ((first_letter >= 'A' and first_letter <= 'Z') or first_letter in 'ÅÆØ'):
            continue
            
        # Handle terms that start with special chars
        if first_letter not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            first_letter = 'A'  # Fallback for special chars
            
        terms_by_letter[first_letter].append({
            'term': term,
            'definitions': definitions,
            'sources': term_data.get('term', '')
        })
    
    # Generate files
    for letter, terms in sorted(terms_by_letter.items()):
        file_path = GLOSSARY_DIR / f"{letter}.md"
        
        content = FRONTMATTER_TEMPLATE.format(
            letter=letter,
            letter_lower=letter.lower()
        )
        content += f"# Glossary - {letter}\n\n"
        content += f"Terms beginning with **{letter}**. Total: **{len(terms)}**.\n\n"
        content += "---\n\n"
        
        # Sort terms alphabetically
        terms_sorted = sorted(terms, key=lambda x: x['term'].lower())
        
        for item in terms_sorted:
            term = item['term']
            defs = item['definitions']
            
            content += f"### {term}\n\n"
            
            # Write definitions
            for i, d in enumerate(defs):
                if isinstance(d, dict):
                    text = clean_text(d.get('text', ''))
                    sources = d.get('sources', [])
                    if sources:
                        source_str = '; '.join([clean_text(s.get('text', '')) for s in sources])
                        content += f"{text} ({source_str})\n\n"
                    else:
                        content += f"{text}\n\n"
                elif isinstance(d, str):
                    content += f"{clean_text(d)}\n\n"
            
            content += "---\n\n"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Wrote {file_path} ({len(terms)} terms)")

if __name__ == "__main__":
    main()
