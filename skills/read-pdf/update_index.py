#!/usr/bin/env python3
import json
import re
from pathlib import Path
from collections import defaultdict

# Paths
JSON_PATH = Path(r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management\references\glossary-export\glossary-export.json")
INDEX_FILE = Path(r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management\_metadata_management_glossary_index.md")

def get_obsidian_anchor(term):
    """Convert a term to an Obsidian heading anchor."""
    # Obsidian anchors: lowercase, spaces replaced by hyphens, special chars removed
    anchor = term.lower().replace(' ', '-')
    anchor = re.sub(r'[^a-z0-9-]', '', anchor)
    return anchor

def main():
    with open(JSON_PATH, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    
    parent_terms = data['parentTerms']
    
    terms_by_letter = defaultdict(list)
    for term_data in parent_terms:
        term = term_data.get('term', '').strip()
        definitions = term_data.get('definitions')
        if not term or not definitions:
            continue
        first_letter = term[0].upper()
        if not ('A' <= first_letter <= 'Z'):
            first_letter = 'A'
        terms_by_letter[first_letter].append(term)
    
    total_terms = sum(len(terms) for terms in terms_by_letter.values())
    
    content = f"""---
title: "Metadata Management Glossary"
type: glossary
status: active
source-of-truth: true
domain: Data
subdomain: Metadata Management
category: Glossary
tags:
  - data
  - glossary
  - index
  - metadata-management
  - nist
  - reference
created: 2026-08-27
updated: 2026-08-31
---

# Metadata Management Glossary

A letter-organized glossary of **metadata management** terminology, compiled
from:

- **NIST Computer Security Resource Center (CSRC) Glossary**
  ([https://csrc.nist.gov/glossary](https://csrc.nist.gov/glossary)) — aggregate of
  terms and definitions from NIST cybersecurity/privacy publications and
  CNSSI 4009-2022. Source data: official
  [JSON export](https://csrc.nist.gov/csrc/media/glossary/glossary-export.zip)
  ({data.get('totalRecords', total_terms):,} term records).

**Total terms: {total_terms:,}**

> NIST note: definitions are aggregated from various standards/guidelines and
> are not "official/preferred" definitions. **Cite the source publication**, not
> the glossary page.

---

## By Letter

| Letter | Terms | Index |
| ------ | ----: | ----- |
"""
    
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        count = len(terms_by_letter.get(letter, []))
        content += f"| **{letter}** | {count:>5} | [[{letter}.md\|{letter}]] |\n"
    
    content += f"""

---

## All Terms (A–Z)

Below is a sample of glossary entries organized alphabetically. Each link
navigates to the full definition in the corresponding letter file.
"""
    
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        terms = sorted(terms_by_letter.get(letter, []))
        if not terms:
            continue
        content += f"\n### {letter}\n\n"
        
        # Show first 10 terms
        for term in terms[:10]:
            anchor = get_obsidian_anchor(term)
            content += f"- [[{letter}#{anchor}|{term}]]\n"
        
        if len(terms) > 10:
            content += f"\n*(showing 10 of {len(terms)} terms. See [[{letter}.md]] for full list.)*\n\n"
        else:
            content += "\n\n"
    
    content += "---\n\n"
    content += f"*Source: [NIST CSRC Glossary](https://csrc.nist.gov/glossary).*\n"
    
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Index file updated. Total terms: {total_terms}")

if __name__ == "__main__":
    main()
