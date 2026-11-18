#!/usr/bin/env python3
"""Parse DAMA Dictionary scanned pages into term-definition pairs."""
import re
import json
from pathlib import Path
from collections import defaultdict

TEMP_DIR = Path(r"D:\Cloud/OneDrive/AI/Agentic/.opencode\skills/read-pdf\temp_extraction")
OUTPUT_JSON = Path(r"D:\Cloud/OneDrive/AI/Agentic/.opencode\skills/read-pdf\dama_terms.json")

def parse_dama_style_text(text):
    """Parse DITA-style glossary text into term-definition pairs."""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    terms = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip page headers, footers, DRM watermarks
        if any(x in line for x in ['Order 85101', 'purchaser device', 'DRM', 'RapidOCR', 
                                    'objects are still open', '©', 'copyright', 'terms reserved']):
            i += 1
            continue
        if line.startswith('page ') and len(line) < 20:
            i += 1
            continue
        if line in ['Terms and Definitions', 'Acronyms', 'Glossary', '']:
            i += 1
            continue
        if 'Dictionary of Data Management' in line:
            i += 1
            continue
        
        # Term: starts with capital letter, short (<8 words), no punctuation at end unless abbreviation
        # Definition: starts lowercase or starts with "(Brackett" etc.
        
        is_term = (
            line[0].isupper() if line else False
            and ':' not in line  # Not key-value
            and len(line.split()) <= 6
            and not re.match(r'^\d+\.', line)  # Not numbered list at start
            and not re.match(r'^[\[\(\{]', line)  # Not a punctuation list item
        )
        
        if is_term:
            term = line.rstrip('.')
            definition_parts = []
            i += 1
            
            # Collect definition lines until next term or blank line
            while i < len(lines):
                next_line = lines[i]
                if not next_line:
                    i += 1
                    break
                
                # Check if this starts a new term
                next_is_term = (
                    next_line[0].isupper() if next_line else False
                    and ':' not in next_line
                    and len(next_line.split()) <= 6
                    and not re.match(r'^\d+\.', next_line)
                    and not re.match(r'^[\[\(\{]', next_line)
                    and not re.match(r'^(SEE |Alternate|page)', next_line, re.IGNORECASE)
                )
                
                if next_is_term:
                    break
                
                definition_parts.append(next_line)
                i += 1
            
            definition = ' '.join(definition_parts).strip()
            if len(definition) > 15:
                terms.append({'term': term, 'definition': definition})
            continue
        
        i += 1
    
    return terms

def main():
    all_terms = []
    
    for file_path in sorted(TEMP_DIR.glob("page_*.txt")):
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            if len(content.strip()) < 100:
                continue
            parsed = parse_dama_style_text(content)
            all_terms.extend(parsed)
        except Exception as e:
            continue
    
    if not all_terms:
        print("No terms parsed!")
        return
    
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
    
    # Group by letter
    by_letter = defaultdict(list)
    for t in unique:
        fl = t['term'][0].upper()
        if fl.isalpha():
            by_letter[fl].append(t)
    
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        if letter in by_letter:
            sample = [t['term'] for t in by_letter[letter][:3]]
            print(f"  {letter}: {len(by_letter[letter])} (e.g., {', '.join(sample)})")

if __name__ == "__main__":
    main()