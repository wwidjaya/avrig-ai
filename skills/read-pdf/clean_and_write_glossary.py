#!/usr/bin/env python3
"""Clean DAMA terms extracted and write into glossary files."""
import json
import re
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(r"D:\Cloud/OneDrive/AI/Personal/vault/05-references/glossary/metadata-management")
INPUT_JSON = Path(r"D:\Cloud/OneDrive/AI/Agentic/.opencode\skills/read-pdf\dama_terms.json")

# Stopwords to filter out noise
TERM_STOPWORD_PATTERNS = [
    r'^An? ',
    r'^The ',
    r'^In ',
    r'^To ',
    r'^A ',
    r'^It ',
    r'^For ',
    r'^This ',
    r'^That ',
    r'^Use ',
    r'^Each ',
    r'^Each ',
    r'^Such ',
    r'^With ',
    r'^From ',
    r'^One ',
    r'^Usually ',
]

def is_valid_term(term):
    """Check if term is a valid glossary entry."""
    term = term.strip()
    if not term:
        return False
    
    # Must start with a letter
    if not re.match(r'^[a-zA-Z]', term):
        return False
    
    # Reasonable length
    words = term.split()
    if len(words) > 6:
        return False
    
    # Not a sentence (should be noun phrase, not verb phrase starting with verb)
    if term.endswith('.') or term.endswith(',') or term.endswith(';'):
        return False
    
    # Has at least one capital letter (not all lowercase)
    if term.islower():
        return False
    
    # Not a fragment with sentence-like patterns
    if any(term.lower().startswith(p.lower()) for p in TERM_STOPWORD_PATTERNS):
        return False
    
    # Not a definition fragment (ends with common definition patterns)
    if re.match(r'^[aeiou][a-z]+$', term.lower()):  # Single word starting with vowel
        pass  # Keep these
    
    # Reject obvious definition fragments
    def_fragments = [
        'database', 'data', 'information', 'system', 'process', 'management',
        'software', 'access', 'storage', 'manipulation', 'creation',
        'control', 'integration', 'analysis', 'decision', 'support',
    ]
    if len(words) == 1 and term.lower() in def_fragments:
        return False
    
    return True

def is_valid_definition(definition):
    """Check if definition is substantial enough."""
    return len(definition.strip()) >= 20

def main():
    with open(INPUT_JSON, 'r', encoding='utf-8') as f:
        terms = json.load(f)
    
    print(f"Loaded {len(terms)} terms from JSON")
    
    # Filter valid terms
    valid_terms = []
    for t in terms:
        if is_valid_term(t['term']) and is_valid_definition(t['definition']):
            valid_terms.append(t)
    
    print(f"After filtering: {len(valid_terms)} valid terms")
    
    # Deduplicate (case-insensitive)
    seen = set()
    unique = []
    for t in valid_terms:
        key = t['term'].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(t)
    
    print(f"After deduplication: {len(unique)} unique terms")
    
    # Group by letter
    by_letter = defaultdict(list)
    for t in unique:
        fl = t['term'][0].upper()
        if fl.isalpha() and 'A' <= fl <= 'Z':
            by_letter[fl].append(t)
    
    total_count = 0
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        file_path = BASE_DIR / f"{letter}.md"
        terms_list = sorted(by_letter[letter], key=lambda x: x['term'].lower())
        
        # Write header content
        content_lines = [
            f"---\ntitle: \"Glossary — Metadata Management: {letter}\"\ntype: glossary\nstatus: active\nsource-of-truth: true\ndomain: Data\nsubdomain: Metadata Management\ncategory: Glossary\ntags:\n  - {letter.lower()}\n  - data\n  - glossary\n  - metadata-management\n  - dama\ncreated: 2026-08-31\nupdated: 2026-08-31\n---\n",
            f"# Glossary — {letter}\n",
            f"Terms beginning with **{letter}**. Total: **{len(terms_list)}**.\n",
        ]
        
        for t in terms_list:
            # Escape pipe in links
            term_link = t['term'].replace('|', '\\|')
            content_lines.append(f"### {t['term']}")
            content_lines.append("")
            content_lines.append(t['definition'].strip())
            content_lines.append("")
            content_lines.append("---")
            content_lines.append("")
        
        file_path.write_text('\n'.join(content_lines), encoding='utf-8')
        total_count += len(terms_list)
        print(f"{letter}: {len(terms_list)} terms")
    
    print(f"\nTotal terms written: {total_count}")
    
    # Save final cleaned list
    with open(INPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(unique, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
