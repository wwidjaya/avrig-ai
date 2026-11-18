#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
design-ocdf-structure :: universal entity documentation tool for Visual Paradigm .vpp

Single reusable helper (no per-entity scripts). Probes an entity's DEFINITION
blob, classifies each column's documentation anchor (regular / FK / untyped),
and (with --apply) writes table + column `documentation_plain=` blocks from a
JSON spec. Always backs up before writing and verifies integrity + brace
balance + escaping.

Usage
-----
  # Probe only (write nothing): print columns, existing docs, anchor kinds, and a spec template
  python doc_entity.py --entity RegulationSAC [--db <path>]

  # Apply from a spec file (backs up first)
  python doc_entity.py --entity RegulationSAC --spec regulation-sac.spec.json --apply [--db <path>]

Spec JSON
---------
  {
    "table_plain": "Full table description (plain text).",
    "cols": {
      "ColumnName": "column description",
      "OtherColumn": "another description"
    }
  }

Columns already carrying documentation_plain in the vpp are skipped (never
overwritten). A pre-existing short table-level documentation_plain tagline is
preserved; only the missing HTML `documentation=` block is added.
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import time

DEFAULT_DB = (r"D:\Cloud\OneDrive\AI\Personal\vault\02-projects\ojk\ocdf"
              r"\03-ocdf-design\2024.10.11 OJK EDM v2.0.1.vpp")


def get_definition(conn, entity):
    cur = conn.cursor()
    cur.execute(
        "SELECT ID, DEFINITION FROM MODEL_ELEMENT "
        "WHERE MODEL_TYPE='DBTable' AND NAME=?", (entity,))
    row = cur.fetchone()
    if row is None:
        raise SystemExit(f"entity not found: {entity}")
    rid, blob = row
    d = blob.decode("utf-8") if isinstance(blob, bytes) else blob
    return rid, d


def list_columns(d):
    return re.findall(r':"([^"]+)":DBColumn \{', d)


def column_block(d, label):
    m = re.search(r':"' + re.escape(label) + r'":DBColumn \{', d)
    if not m:
        return None
    i = m.start()
    j = m.end() - 1
    depth = 0
    end = len(d)
    for k in range(j, len(d)):
        if d[k] == "{":
            depth += 1
        elif d[k] == "}":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    return d[j:end], i


def col_kind(d, label):
    """Return (kind, token, pos_in_d) for where to insert documentation_plain.
    Returns (None, None, None) if no suitable anchor found."""
    blk = column_block(d, label)
    if blk is None:
        return (None, None, None)
    block, i = blk
    tm = re.search(r'type=\d+;', block)
    if tm:
        return ("type", tm.group(0), d.index(tm.group(0), i))
    fm = re.search(r'foreignKeyNamePattern="[^"]*";', block)
    if fm:
        return ("fk", fm.group(0), d.index(fm.group(0), i))
    lm = re.search(r'pmLastModified="\d+";', block)
    if lm:
        return ("end", lm.group(0), d.index(lm.group(0), i))
    return (None, None, None)

def col_existing_doc(d, label):
    m = re.search(r':"' + re.escape(label) + r'":DBColumn \{', d)
    if not m:
        return None
    i = m.start()
    j = m.end() - 1
    depth = 0
    end = len(d)
    for k in range(j, len(d)):
        if d[k] == "{":
            depth += 1
        elif d[k] == "}":
            depth -= 1
            if depth == 0:
                end = k + 1
                break
    pm = re.search(r'documentation_plain="([^"]*)"', d[j:end])
    return pm.group(1) if pm else None


def build_table_html(plain):
    return (
        '<head>\n'
        '    <style type=\\"text/css\\">\n'
        '      <!--\n'
        '        body { color: #000000; font-family: Dialog; font-size: 12px }\n'
        '      -->\n'
        '    </style>\n'
        '  </head>\n'
        '  <body>\n'
        '    <p><b>Description:</b>' + plain + '</p>\n'
        '  </body>'
    )


def apply_spec(conn, rid, entity, d, spec):
    table_plain = spec.get("table_plain")
    cols = spec.get("cols", {})

    # --- table HTML block (insert before dataModel=1; if missing) ---
    if table_plain:
        if 'documentation="' not in d[:d.find("dataModel=1;") if "dataModel=1;" in d else len(d)]:
            html = build_table_html(table_plain)
            d = d.replace("dataModel=1;", 'documentation="' + html + '";\n\tdataModel=1;', 1)

        # table plain: only add if no documentation_plain already exists before Child=(
        anchor_after = "dataModel=1;\n\tChild=("
        if "documentation_plain=" not in d[:d.find("Child=(") if "Child=(" in d else len(d)]:
            if anchor_after in d:
                d = d.replace(
                    anchor_after,
                    "dataModel=1;\n\tdocumentation_plain=\"" + table_plain + "\";\n\tChild=(",
                    1)
            else:
                # fallback: table already has plain tagline -> keep it, skip
                pass

    # --- column docs ---
    skipped = []
    added = []
    for col, doc in cols.items():
        existing = col_existing_doc(d, col)
        if existing is not None:
            skipped.append((col, existing))
            continue
        res = col_kind(d, col)
        if res[0] is None:
            print(f"  ! skip {col}: no anchor found", file=sys.stderr)
            continue
        kind, token, pos = res
        if token is None or pos is None:
            print(f"  ! skip {col}: no anchor found", file=sys.stderr)
            continue
        j = pos + len(token)
        d = d[:j] + '\n\t\t\tdocumentation_plain="' + doc + '";' + d[j:]
        added.append((col, kind))

    return d, added, skipped


def verify(d, conn, rid, expected_cols=None):
    issues = []
    if re.search(r'PRAGMA', d):
        pass
    if d.count("{") != d.count("}"):
        issues.append("braces unbalanced")
    if d.count('type="text/css"') > 0:
        issues.append("unescaped text/css bug present")
    cols = list_columns(d)
    if expected_cols is not None and len(cols) != expected_cols:
        issues.append(f"column count {len(cols)} != expected {expected_cols}")
    return cols, issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entity", "-e", required=True)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--spec", "-s")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        raise SystemExit(f"vpp not found: {args.db}")

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    rid, d = get_definition(conn, args.entity)
    cols = list_columns(d)
    existing_table_plain = re.search(r'documentation_plain="([^"]*)"', d)
    print(f"entity    : {args.entity}")
    print(f"db        : {args.db}")
    print(f"columns   : {len(cols)} -> {cols}")
    print(f"table doc : {'present' if existing_table_plain else 'absent'} "
          f"{('('+existing_table_plain.group(1)+')') if existing_table_plain else ''}")
    print("--- column documentation status ---")
    for c in cols:
        kind = col_kind(d, c)
        edoc = col_existing_doc(d, c)
        tag = edoc if edoc is not None else f"anchor={kind[0]}"
        print(f"  {c:32} {tag}")
    conn.close()

    if not args.spec:
        # print a spec template for the operator to fill in
        template = {
            "table_plain": "<paste the vault entity description here>",
            "cols": {c: "<column description from vault>" for c in cols
                     if col_existing_doc(d, c) is None},
        }
        print("\n--- spec template (save as <entity>.spec.json, fill, re-run with --spec/--apply) ---")
        print(json.dumps(template, indent=2, ensure_ascii=False))
        return

    with open(args.spec, "r", encoding="utf-8") as f:
        spec = json.load(f)

    if not args.apply:
        print("\n(dry-run) would apply spec; re-run with --apply to write.")
        return

    # backup
    bak = args.db + f".bak-{args.entity.lower()}"
    if not os.path.exists(bak):
        shutil.copy2(args.db, bak)
        print(f"\nbackup -> {bak}")

    conn = sqlite3.connect(f"file:{args.db}?mode=rw", uri=True)
    rid, d = get_definition(conn, args.entity)
    before = len(list_columns(d))
    d, added, skipped = apply_spec(conn, rid, args.entity, d, spec)

    now = int(time.time())
    now_ms = str(int(time.time() * 1000))
    d = re.sub(r'lastModifiedTime=\d+', 'lastModifiedTime=' + now_ms, d)
    d = re.sub(r'pmLastModified="\d+"', 'pmLastModified="' + now_ms + '"', d)

    cur = conn.cursor()
    cur.execute("UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
                (d.encode("utf-8"), now, rid))
    assert cur.rowcount == 1, f"rowcount={cur.rowcount} (expected 1)"
    conn.commit()

    cur.execute("PRAGMA integrity_check")
    ic = cur.fetchone()[0]
    cols, issues = verify(d, conn, rid, expected_cols=before)
    conn.close()

    print(f"\nadded    : {added}")
    print(f"skipped  : {skipped}")
    print(f"integrity: {ic}")
    print(f"issues   : {issues if issues else 'none'}")


if __name__ == "__main__":
    main()
