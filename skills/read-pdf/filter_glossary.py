#!/usr/bin/env python3
"""Filter glossary to retain core metadata-management-related terms only."""
import re
from pathlib import Path
from collections import defaultdict

GLOSSARY_DIR = Path(r"D:\Cloud\OneDrive\AI\Personal\vault\05-references\glossary\metadata-management")

# Core metadata management concepts - definitions must mention these
CORE_KEYWORDS = [
    'metadata management', 'master data management', 'mdm',
    'reference data management', 'rdm', 'cdmp',
    'data governance', 'data stewardship', 'data steward',
    'data catalog', 'data registry', 'data repository',
    'data architecture', 'data ecosystem',
    'data model', 'logical data model', 'conceptual data model',
    'physical data model', 'entity-relationship model',
    'data quality', 'data profiling', 'data lineage',
    'data integration', 'data migration', 'data sharing',
    'data dictionary', 'canonical data model',
    'data lifecycle', 'data lifecycle management', 'information management',
    'data asset', 'information asset', 'information governance',
    'dmbok', 'dama international', 'dataversity',
    'integration hub', 'semantic layer', 'data mesh',
    'data fabric', 'knowledge graph', 'ontology'
]

# Also accept terms that are explicitly metadata/datamodel related
PREFIX_KEYWORDS = [
    'metadata', 'data model', 'data dictionary', 'master data',
    'reference data', 'data steward', 'data governance',
    'data catalog', 'data registry', 'repository'
]

def is_metadata_related(term, definition):
    """Check if term belongs to core metadata management."""
    combined = (term + " " + (definition or "")).lower()
    
    # Check for core keywords
    for kw in CORE_KEYWORDS:
        if kw in combined:
            return True
    
    # Check term starts with metadata/data model related prefix
    for pref in PREFIX_KEYWORDS:
        if term.lower().startswith(pref):
            return True
    
    return False

def parse_glossary_file(file_path):
    """Parse a glossary .md file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except:
        return "", [], []
    
    fm_start = content.find("---")
    if fm_start == -1:
        return content, 0, []
    fm_end = content.find("---", fm_start + 3)
    if fm_end == -1:
        return content, 0, []
    
    frontmatter = content[:fm_end + 3]
    body = content[fm_end + 3:].strip()
    
    # Split sections by ---
    sections = [s.strip() for s in body.split('---') if s.strip() and '### ' in s]
    return frontmatter, sections

def rebuild_file(file_path, kept_sections, letter, total):
    """Rebuild a glossary file with kept sections."""
    frontmatter = f"""---
title: "Glossary — Metadata Management: {letter}"
type: glossary
status: active
source-of-truth: true
domain: Data
subdomain: Metadata Management
category: Glossary
tags:
  - {letter.lower()}
  - data
  - glossary
  - metadata-management
  - nist
created: 2026-08-31
updated: 2026-08-31
---

# Glossary - {letter}

Terms beginning with **{letter}**. Total: **{total}**.

---

"""
    body = ""
    for s in kept_sections:
        cleaned = s.strip().rstrip('\n')
        body += cleaned + "\n\n---\n\n"
    
    file_path.write_text(frontmatter + body, encoding="utf-8")

def filter_glossary():
    total_all = 0
    for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        file_path = GLOSSARY_DIR / f"{letter}.md"
        if not file_path.exists():
            continue
            
        _, sections = parse_glossary_file(file_path)
        kept = []
        for section in sections:
            m = re.match(r'### (.+?)(?:\n|$)', section)
            if not m:
                continue
            term = m.group(1).strip()
            defn = section[m.end():].strip()
            if is_metadata_related(term, defn):
                kept.append(section)
        
        rebuild_file(file_path, kept, letter, len(kept))
        total_all += len(kept)
        print(f"{letter}: {len(kept)} terms")
    
    print(f"Total filtered terms: {total_all}")
    return total_all

if __name__ == "__main__":
    filter_glossary()