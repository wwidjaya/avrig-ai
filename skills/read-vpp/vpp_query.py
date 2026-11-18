#!/usr/bin/env python3
"""Read-only query tool for Visual Paradigm .vpp project files.

A .vpp file is a SQLite 3 database. The core table is MODEL_ELEMENT with a
DEFINITION column holding Visual Paradigm's text-format serialization; DB
tables and their columns are encoded there.

This tool opens the file with mode=ro and never writes. It exposes safe,
semantic subcommands only.

Subcommands:
    project                       project name, DB/project version, build
    tables                        list all DBTable elements (count + names)
    table  <name>                 columns (type/length/PK/nullable) + FK constraints
    columns <name>                compact column list
    fk list                       all foreign keys (source -> target table)
    fk <table>                    foreign keys touching a table
    diagrams                      list diagrams (name, type, element count)
    search <text>                 find model elements by name
    types                         MODEL_TYPE distribution
    rootmodels                    top-level Model elements (PARENT_ID is null)
    mainview <table>              main view (diagram) of a DBTable + all views
    domains [name]                database domains (entity + flat) with types & usage

Options:
    --db <path>   target .vpp file (default: a configured .vpp in the vault)
"""

import argparse
import re
import sqlite3
import sys

DEFAULT_DB = r"D:\Cloud\OneDrive\AI\Personal\vault\02-projects\ojk\edm\data-model\2024.10.11 OJK EDM v2.0.0.vpp"


def connect(db):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True)


def _col_block_iter(defn):
    """Yield (name, block_text) for each DBColumn in a table DEFINITION."""
    pat = re.compile(r'\{(?:[^:{}]+):"([^"]+)":DBColumn \{')
    for m in pat.finditer(defn):
        start = m.end()
        depth = 1
        j = start
        n = len(defn)
        while j < n and depth > 0:
            if defn[j] == "{":
                depth += 1
            elif defn[j] == "}":
                depth -= 1
            j += 1
        yield m.group(1), defn[start : j - 1]


def _col_props(block):
    t = re.search(r"\btype=(\d+);", block)
    length = re.search(r"\blength=(\d+);", block)
    return {
        "type": t.group(1) if t else None,
        "length": length.group(1) if length else None,
        "pk": "primaryKey=T" in block,
        "nullable": not ("nullable=F" in block),
    }


def _table_def(cur, name):
    row = cur.execute(
        "SELECT DEFINITION FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTable' AND NAME=?",
        (name,),
    ).fetchone()
    if row is None:
        return None
    return row[0].decode("utf-8", "replace")


def _fk_edges(cur):
    """Return list of (name, from_table, to_table) parsed from DBForeignKey rows.

    The toModel/fromModel addresses are colon-joined paths whose LAST component
    is the referenced table's MODEL_ELEMENT ID.
    """
    ids = {r[0]: r[1] for r in cur.execute("SELECT ID, NAME FROM MODEL_ELEMENT")}
    edges = []
    pat = re.compile(r"(?:toModel|fromModel)=<([^>]+)>")
    for fid, name, defn in cur.execute(
        "SELECT ID, NAME, DEFINITION FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBForeignKey'"
    ):
        refs = pat.findall(defn.decode("utf-8", "replace"))
        to = refs[0] if refs else None
        fm = refs[1] if len(refs) > 1 else None
        to_id = to.split(":")[-1] if to else None
        fm_id = fm.split(":")[-1] if fm else None
        edges.append(
            {
                "name": name,
                "from": ids.get(fm_id, fm_id or "?"),
                "to": ids.get(to_id, to_id or "?"),
            }
        )
    return edges


def cmd_project(cur, args):
    for r in cur.execute(
        "SELECT NAME, DB_VERSION, PROJECT_VERSION, PROJECT_BUILD FROM PROJECT_INFO"
    ):
        print(f"name={r[0]} db_version={r[1]} project_version={r[2]} build={r[3]}")


def cmd_tables(cur, args):
    rows = cur.execute(
        "SELECT NAME FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTable' ORDER BY NAME"
    ).fetchall()
    print(f"total tables: {len(rows)}")
    for (name,) in rows:
        print(name)


def cmd_table(cur, args):
    defn = _table_def(cur, args.name)
    if defn is None:
        sys.exit(f"error: table '{args.name}' not found")
    cols = [(n, _col_props(b)) for n, b in _col_block_iter(defn)]
    print(f"table={args.name} columns={len(cols)}")
    for name, p in cols:
        pk = "PK" if p["pk"] else ""
        null = "" if p["nullable"] else "NOT NULL"
        print(f"  {name:<40} type={p['type'] or '-':<4} len={p['length'] or '-':<5} {pk:<2} {null}")
    # FK constraints found in column blocks
    for name, block in _col_block_iter(defn):
        fks = re.findall(r"foreignKey=<\S+>", block)
        for fk in fks:
            print(f"  [fk constraint on {name}] {fk}")


def cmd_columns(cur, args):
    defn = _table_def(cur, args.name)
    if defn is None:
        sys.exit(f"error: table '{args.name}' not found")
    cols = [(n, _col_props(b)) for n, b in _col_block_iter(defn)]
    print(f"table={args.name}: " + ", ".join(n for n, _ in cols))


def cmd_fk_list(cur, args):
    edges = _fk_edges(cur)
    print(f"total foreign keys: {len(edges)}")
    for e in edges:
        print(f"  {e['from']} -> {e['to']}  ({e['name']})")


def cmd_fk_table(cur, args):
    edges = _fk_edges(cur)
    hits = [e for e in edges if e["from"] == args.table or e["to"] == args.table]
    print(f"foreign keys touching '{args.table}': {len(hits)}")
    for e in hits:
        print(f"  {e['from']} -> {e['to']}  ({e['name']})")


def cmd_diagrams(cur, args):
    rows = cur.execute(
        """SELECT d.ID, d.DIAGRAM_TYPE, d.NAME,
                  (SELECT COUNT(*) FROM DIAGRAM_ELEMENT de WHERE de.DIAGRAM_ID=d.ID)
           FROM DIAGRAM d ORDER BY d.NAME"""
    ).fetchall()
    print(f"total diagrams: {len(rows)}")
    for pid, dtype, name, cnt in rows:
        print(f"  {name.strip()}  [{dtype}] ({cnt} elements)")


def cmd_search(cur, args):
    rows = cur.execute(
        "SELECT MODEL_TYPE, NAME, PARENT_ID FROM MODEL_ELEMENT WHERE NAME LIKE ? ORDER BY MODEL_TYPE, NAME",
        (f"%{args.text}%",),
    ).fetchall()
    print(f"matches: {len(rows)}")
    for mtype, name, parent in rows:
        print(f"  {mtype:<24} {name}")


def cmd_types(cur, args):
    rows = cur.execute(
        "SELECT MODEL_TYPE, COUNT(*) FROM MODEL_ELEMENT GROUP BY MODEL_TYPE ORDER BY COUNT(*) DESC"
    ).fetchall()
    for mtype, cnt in rows:
        print(f"  {mtype:<30} {cnt}")


def cmd_rootmodels(cur, args):
    rows = cur.execute(
        "SELECT NAME FROM MODEL_ELEMENT WHERE MODEL_TYPE='Model' AND PARENT_ID IS NULL ORDER BY NAME"
    ).fetchall()
    print(f"root models: {len(rows)}")
    for (name,) in rows:
        print(f"  {name}")


def cmd_mainview(cur, args):
    row = cur.execute(
        "SELECT ID, DEFINITION FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTable' AND NAME=?",
        (args.name,),
    ).fetchone()
    if row is None:
        sys.exit(f"error: table '{args.name}' not found")
    table_id, defn = row[0], row[1].decode("utf-8", "replace")
    master = re.search(r'_masterViewId="([^"]+)"', defn)
    master_id = master.group(1) if master else None
    print(f"table={args.name} masterViewId={master_id or '-'}")
    if master_id:
        d = cur.execute(
            "SELECT d.NAME FROM DIAGRAM_ELEMENT de JOIN DIAGRAM d ON d.ID=de.DIAGRAM_ID WHERE de.ID=?",
            (master_id,),
        ).fetchone()
        if d:
            print(f"main view: {d[0].strip()}")
    views = cur.execute(
        """SELECT d.NAME, d.DIAGRAM_TYPE, de.ID
           FROM DIAGRAM_ELEMENT de JOIN DIAGRAM d ON d.ID=de.DIAGRAM_ID
           WHERE de.MODEL_ELEMENT_ID=? ORDER BY d.NAME""",
        (table_id,),
    ).fetchall()
    print(f"views on diagrams: {len(views)}")
    for name, dtype, deid in views:
        tag = "  [MASTER]" if deid == master_id else "  [AUX]"
        print(f"  {name.strip()}  [{dtype}]{tag}")


TYPE_NAME = {
    "27": "VARCHAR",
    "22": "DATETIME",
    "17": "DATE",
    "11": "DECIMAL",
    "23": "BLOB",
    "42": "FLAG/CHAR1",
    "-": "untyped",
}


def _domain_cols(cur):
    """Return {domain_id: [(col_id, col_name), ...]} for DBColumnDomain children."""
    kids = {}
    for cid, cname, parent in cur.execute(
        "SELECT ID, NAME, PARENT_ID FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBColumnDomain'"
    ):
        kids.setdefault(parent, []).append((cid, cname))
    return kids


def _col_domain_line(cur, ids, cid, name):
    d = cur.execute("SELECT DEFINITION FROM MODEL_ELEMENT WHERE ID=?", (cid,)).fetchone()
    defn = d[0].decode("utf-8", "replace") if d else ""
    t = re.search(r"\btype=(\d+);", defn)
    l = re.search(r"\blength=(\d+);", defn)
    s = re.search(r"\bscale=(\d+);", defn)
    tc = t.group(1) if t else "-"
    pk = "PK " if "primaryKey=T" in defn else ""
    nn = "" if "nullable=F" not in defn else "NOT NULL "
    line = (
        f"  {name:<28} type={tc:<3} {TYPE_NAME.get(tc, '?'):<10} "
        f"len={l.group(1) if l else '-':<5} scale={s.group(1) if s else '-':<3} {pk}{nn}"
    )
    ref = cur.execute(
        "SELECT ID FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBColumnDomainRefRelationship'"
    ).fetchall()
    for (rid,) in ref:
        rd = cur.execute("SELECT DEFINITION FROM MODEL_ELEMENT WHERE ID=?", (rid,)).fetchone()
        rdefn = rd[0].decode("utf-8", "replace")
        fm = re.search(r"fromModel=<([^>]+)>", rdefn)
        to = re.search(r"toModel=<([^>]+)>", rdefn)
        if fm and to and fm.group(1).split(":")[-1] == cid:
            line += f" -> alias {ids.get(to.group(1).split(':')[-1], '?')}"
    return line


def _domain_usage(cur):
    """Return {column_domain_id: count} of mapped columns via DBColumnDomainRelationship."""
    usage = {}
    for r in cur.execute(
        "SELECT DEFINITION FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBColumnDomainRelationship'"
    ):
        d = r[0].decode("utf-8", "replace")
        fm = re.search(r"fromModel=<([^>]+)>", d)
        to = re.search(r"toModel=<([^>]+)>", d)
        if fm and to:
            tid = to.group(1).split(":")[-1]
            usage[tid] = usage.get(tid, 0) + 1
    return usage


def _print_domain(cur, ids, kids, usage, did, name, show_usage):
    print(f"=== Entity Domain: {name} (id {did}) ===")
    for cid, cname in kids.get(did, []):
        print(_col_domain_line(cur, ids, cid, cname))
        if show_usage and usage.get(cid):
            print(f"       used by {usage[cid]} columns")
    print()


def cmd_domains(cur, args):
    ids = {r[0]: r[1] for r in cur.execute("SELECT ID, NAME FROM MODEL_ELEMENT")}
    kids = _domain_cols(cur)
    usage = _domain_usage(cur)
    show_usage = not getattr(args, "no_usage", False)

    if args.name:
        row = cur.execute(
            "SELECT ID FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTableDomain' AND NAME=?",
            (args.name,),
        ).fetchone()
        if row is None:
            sys.exit(f"error: domain '{args.name}' not found")
        _print_domain(cur, ids, kids, usage, row[0], args.name, show_usage)
        # tables using this entity domain
        tables = []
        for r in cur.execute(
            "SELECT DEFINITION FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTableDomainRelationship'"
        ):
            d = r[0].decode("utf-8", "replace")
            to = re.search(r"toModel=<([^>]+)>", d)
            if to and to.group(1).split(":")[-1] == row[0]:
                fm = re.search(r"fromModel=<([^>]+)>", d)
                if fm:
                    tables.append(ids.get(fm.group(1).split(":")[-1], "?"))
        if tables:
            print(f"used by {len(tables)} tables: {', '.join(sorted(tables))}")
        return

    n_entity = cur.execute(
        "SELECT COUNT(*) FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTableDomain'"
    ).fetchone()[0]
    print(f"=== Entity Domains ({n_entity}) ===")
    for did, name in cur.execute(
        "SELECT ID, NAME FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTableDomain' ORDER BY NAME"
    ):
        _print_domain(cur, ids, kids, usage, did, name, show_usage)

    flat = []
    for cid, cname in cur.execute(
        "SELECT ID, NAME FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBColumnDomain' AND PARENT_ID IN (SELECT ID FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBColumnDomainContainer') ORDER BY NAME"
    ):
        flat.append((cid, cname))
    print(f"=== Flat Column Domains ({len(flat)}) ===")
    for cid, cname in flat:
        print(_col_domain_line(cur, ids, cid, cname))
        if show_usage and usage.get(cid):
            print(f"       used by {usage[cid]} columns")
    print()


def build_parser():
    parser = argparse.ArgumentParser(prog="vpp_query", description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help="target .vpp file (default: OJK EDM v2.0.0)")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_db(p):
        p.add_argument("--db", default=None, help="target .vpp file (overrides global --db)")

    sp = sub.add_parser("project")
    add_db(sp)
    sp.set_defaults(func=cmd_project)

    s = sub.add_parser("tables")
    add_db(s)
    s.set_defaults(func=cmd_tables)

    t = sub.add_parser("table")
    t.add_argument("name")
    add_db(t)
    t.set_defaults(func=cmd_table)

    c = sub.add_parser("columns")
    c.add_argument("name")
    add_db(c)
    c.set_defaults(func=cmd_columns)

    f = sub.add_parser("fk")
    f.add_argument("table", nargs="?")
    add_db(f)
    f.set_defaults(func=None)

    d = sub.add_parser("diagrams")
    add_db(d)
    d.set_defaults(func=cmd_diagrams)

    sr = sub.add_parser("search")
    sr.add_argument("text")
    add_db(sr)
    sr.set_defaults(func=cmd_search)

    ty = sub.add_parser("types")
    add_db(ty)
    ty.set_defaults(func=cmd_types)

    rm = sub.add_parser("rootmodels")
    add_db(rm)
    rm.set_defaults(func=cmd_rootmodels)

    mv = sub.add_parser("mainview")
    mv.add_argument("name")
    add_db(mv)
    mv.set_defaults(func=cmd_mainview)

    dm = sub.add_parser("domains")
    dm.add_argument("name", nargs="?")
    dm.add_argument("--no-usage", action="store_true", help="omit per-domain column usage counts")
    add_db(dm)
    dm.set_defaults(func=cmd_domains)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    db = getattr(args, "db", None) or DEFAULT_DB
    con = connect(db)
    try:
        cur = con.cursor()
        if args.command == "fk":
            (cmd_fk_table if args.table else cmd_fk_list)(cur, args)
        else:
            args.func(cur, args)
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
