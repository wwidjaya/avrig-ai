#!/usr/bin/env python3
"""Write tool for Visual Paradigm .vpp project files.

Creates/updates model elements in a .vpp (SQLite 3) database. Mirrors the
read-only tool (read-vpp/vpp_query.py) but opens the DB read-write.

Safety contract (enforced):
    - --backup is REQUIRED before any write (timestamped sibling copy).
    - --dry-run is the DEFAULT; pass --apply to actually write.
    - NEVER touches LAST_* mirrors, sqlite_sequence, USER_ID_FORMAT, or
      PROJECT_INFO (except root-level element creation).
    - Dual timestamps: row CREATE_AT/LAST_MOD_AT in seconds; DEFINITION
      lastModifiedTime/pmCreateDateTime/pmLastModified as 13-digit-ms strings.

Subcommands:
    backup                           create a timestamped backup copy
    table create <package_id> <name>  new DBTable + standard columns
    table rename <old> <new>          rename a table (NAME + DEFINITION header)
    column add <table> <name> [...]   add a DBColumn to a table's DEFINITION
    column update <table> <name> [...]  edit a column block
    column rename <table> <old> <new>  rename a column (+ domain rel address)
    fk add <table> <column> <ref_table> <ref_column> [--label]
    domain assign <table|table.column> <domain>
    diagram add-table <diagram> <table>  guarded: DIAGRAM Child + DIAGRAM_ELEMENT
    verify [name]                      read-back integrity check

Options:
    --db <path>     target .vpp file
    --backup        create a backup copy before writing
    --apply         actually write (default is dry-run)
    --force         allow writes even without --backup (not recommended)
"""

import argparse
import datetime
import random
import re
import shutil
import sqlite3
import string
import sys

DEFAULT_DB = r"D:\Cloud\OneDrive\AI\Personal\vault\02-projects\ojk\edm\data-model\2024.10.11 OJK EDM v2.0.0.vpp"

ID_CHARS = string.ascii_letters + string.digits + "._-$"
TYPE_NAME = {
    "27": "VARCHAR",
    "22": "DATETIME",
    "17": "DATE",
    "11": "DECIMAL",
    "23": "BLOB",
    "42": "FLAG/CHAR1",
}


def now_sec():
    return int(datetime.datetime.now().timestamp())


def now_ms():
    return int(datetime.datetime.now().timestamp() * 1000)


def connect(db):
    return sqlite3.connect(db)


def dec(v):
    """DEFINITION comes back as str or bytes (TEXT vs BLOB); normalize to str."""
    return v.decode("utf-8") if isinstance(v, (bytes, bytearray)) else v


def enc(v):
    """Store DEFINITION as BLOB bytes to match VP and read-vpp's decode()."""
    return v.encode("utf-8") if isinstance(v, str) else v


def _ids(cur):
    return {r[0] for r in cur.execute("SELECT ID FROM MODEL_ELEMENT")} | \
        {r[0] for r in cur.execute("SELECT ID FROM DIAGRAM")} | \
        {r[0] for r in cur.execute("SELECT ID FROM DIAGRAM_ELEMENT")}


def new_id(used):
    first = string.ascii_letters + string.digits
    while True:
        cand = random.choice(first) + "".join(random.choice(ID_CHARS) for _ in range(15))
        if cand not in used:
            return cand


def _find_table(cur, name):
    row = cur.execute(
        "SELECT ID, NAME, DEFINITION FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTable' AND NAME=?",
        (name,),
    ).fetchone()
    if row is None:
        return None
    return row[0], row[1], dec(row[2])


def _find_model(cur, mid):
    return cur.execute("SELECT ID, MODEL_TYPE, NAME FROM MODEL_ELEMENT WHERE ID=?", (mid,)).fetchone()


def _col_block_iter(defn):
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


def _col_block_for(defn, colname):
    for name, block in _col_block_iter(defn):
        if name == colname:
            return block
    return None


def make_backup(db):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = f"{db}.bak-{ts}"
    shutil.copy2(db, dest)
    print(f"backup: {dest}")
    return dest


# ---------------------------------------------------------------- columns ----


def col_block(name, ctype=None, length=None, nullable=True, pk=False, default=None, ms=None):
    ms = ms or now_ms()
    ms_str = str(ms)
    s = f'{{<COL_ID>:"{name}":DBColumn {{\n'
    s += f'\t_modelEditable=T;\n'
    if length:
        s += f'\tlength={length};\n'
    s += f'\tidGenerator=NULL;\n'
    s += f'\tpmAuthor="{DEFAULT_AUTHOR}";\n'
    if ctype:
        s += f'\ttype={ctype};\n'
    if pk:
        s += f'\tprimaryKey=T;\n'
    s += f'\tlastModifiedTime={ms};\n'
    s += f'\tpmCreateDateTime="{ms_str}";\n'
    s += f'\tnullable={"F" if not nullable else "T"};\n'
    if default is not None:
        s += f'\tdefaultValue="{default}";\n'
    s += f'\t_modelViews=NULL;\n'
    s += f'\tpmLastModified="{ms_str}";\n'
    s += f'}}'
    return s


def rebuild_child_block(cur, table_defn, new_columns):
    """Insert new column blocks into a table DEFINITION's Child=(...) list.

    new_columns: list of raw column block strings (with <COL_ID> placeholder).
    Returns (new_defn, used_col_ids).
    """
    m = re.search(r'Child=\((.*?)\);\n\tpmLastModified=', table_defn, re.S)
    if not m:
        raise SystemExit("error: table DEFINITION has no Child=(...) block")
    inner = m.group(1)
    insert = "\n\t\t" + ",\n\t\t".join(new_columns) + ",\n\t"
    if inner.strip() == "":
        new_inner = "\n\t\t" + ",\n\t\t".join(new_columns) + "\n\t"
    else:
        new_inner = inner.rstrip() + insert.rstrip("\t")
    return table_defn[: m.start()] + "Child=(" + new_inner + ");\n\tpmLastModified=" + table_defn[m.end():]


DEFAULT_AUTHOR = "write-vpp"


def _insert_model_element(cur, mid, mtype, parent_id, name, defn, author, csec, lsec):
    cur.execute(
        "INSERT INTO MODEL_ELEMENT (ID, MODEL_TYPE, PARENT_ID, NAME, DEFINITION, AUTHOR, CREATE_AT, LAST_MOD_AT) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (mid, mtype, parent_id, name, enc(defn), author, csec, lsec),
    )


# ---------------------------------------------------------------- commands ----


def cmd_backup(cur, args):
    make_backup(args.db)


def cmd_table_create(cur, args):
    used = _ids(cur)
    pid = args.package_id
    pkg = _find_model(cur, pid)
    if pkg is None:
        sys.exit(f"error: package/model {pid} not found")
    mid = new_id(used)
    ms = now_ms()
    ms_str = str(ms)
    sec = now_sec()
    name = args.name
    std_cols = [
        ("ID", None, 30, False, True, None),
        ("Code", 27, 30, False, False, None),
        ("Name", 27, 255, False, False, None),
        ("Desc", 27, 512, False, False, None),
        ("CreatedBy", 27, 30, False, False, None),
        ("CreatedAt", 22, None, False, False, None),
        ("UpdatedBy", 27, 30, True, False, None),
        ("UpdatedAt", 22, None, True, False, None),
        ("DeletedBy", 27, 255, True, False, None),
        ("DeletedAt", 22, None, True, False, None),
        ("IsActiveFlag", 27, 1, False, False, "Y"),
        ("IsDeletedFlag", 27, 1, False, False, "N"),
    ]
    col_ids = {}
    blocks = []
    for (cname, ct, cl, nullable, pk, default) in std_cols:
        cid = new_id(used)
        col_ids[cname] = cid
        blocks.append(col_block(cname, ct, cl, nullable, pk, default, ms))
    defn = (
        f'{mid}:"{name}":DBTable {{\n'
        f'\t_modelEditable=T;\n'
        f'\tprimaryKeyConstraintNamePattern="";\n'
        f'\tpmAuthor="{DEFAULT_AUTHOR}";\n'
        f'\tlastModifiedTime={ms};\n'
        f'\tpmCreateDateTime="{ms_str}";\n'
        f'\t_modelViews=NULL;\n'
        f'\tdataModel=1;\n'
        f'\tChild=(\n\t\t'
        + ",\n\t\t".join(b.replace("<COL_ID>", col_ids[cname]) for cname, b in zip([c[0] for c in std_cols], blocks))
        + "\n\t);\n"
        f'\tpmLastModified="{ms_str}";\n'
        f'}}'
    )
    _maybe_write(
        cur,
        args,
        sql=("INSERT INTO MODEL_ELEMENT ... DBTable", name),
        defn=defn,
        action=lambda c: _insert_model_element(
            c, mid, "DBTable", pid, name, defn, DEFAULT_AUTHOR, sec, sec
        ),
        success=f"table '{name}' created (id={mid}) under {pkg[2]} ({pid})",
    )


def _apply_or_dry(cur, args, sql, defn, action, success):
    if not args.apply:
        print("[dry-run] " + success)
        print("[dry-run] SQL: " + (sql[1] if isinstance(sql, tuple) else sql))
        if defn:
            print("[dry-run] DEFINITION:\n" + defn)
        return
    action(cur)
    print(success)


def _maybe_write(cur, args, sql=None, defn=None, action=None, success=""):
    _apply_or_dry(cur, args, sql, defn, action, success)


def cmd_table_rename(cur, args):
    row = _find_table(cur, args.old)
    if row is None:
        sys.exit(f"error: table '{args.old}' not found")
    tid, _, defn = row
    new_defn = re.sub(rf'^{tid}:"[^"]*":DBTable', f'{tid}:"{args.new}":DBTable', defn, count=1)
    sec = now_sec()
    _maybe_write(
        cur, args,
        sql="UPDATE MODEL_ELEMENT SET NAME=?, DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
        defn=None,
        action=lambda c: c.execute(
            "UPDATE MODEL_ELEMENT SET NAME=?, DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
            (args.new, enc(new_defn), sec, tid),
        ),
        success=f"table '{args.old}' renamed to '{args.new}'",
    )


def cmd_column_add(cur, args):
    row = _find_table(cur, args.table)
    if row is None:
        sys.exit(f"error: table '{args.table}' not found")
    tid, tname, defn = row
    existing = {n for n, _ in _col_block_iter(defn)}
    if args.name in existing:
        sys.exit(f"error: column '{args.name}' already exists in '{args.table}'")
    used = _ids(cur)
    cid = new_id(used)
    block = col_block(
        args.name, args.type, args.length, not args.not_null, args.pk, args.default
    ).replace("<COL_ID>", cid)
    new_defn = rebuild_child_block(cur, defn, [block])
    sec = now_sec()
    _maybe_write(
        cur, args,
        sql=f"UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
        defn=new_defn,
        action=lambda c: c.execute(
            "UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
            (enc(new_defn), sec, tid),
        ),
        success=f"column '{args.name}' added to '{args.table}' (id={cid})",
    )


def cmd_column_update(cur, args):
    row = _find_table(cur, args.table)
    if row is None:
        sys.exit(f"error: table '{args.table}' not found")
    tid, tname, defn = row
    block = _col_block_for(defn, args.name)
    if block is None:
        sys.exit(f"error: column '{args.name}' not found in '{args.table}'")
    ms = now_ms()
    new_block = col_block(
        args.name, args.type, args.length, not args.not_null, args.pk, args.default, ms
    )
    new_defn = defn.replace(block, new_block)
    sec = now_sec()
    _maybe_write(
        cur, args,
        sql="UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
        defn=new_defn,
        action=lambda c: c.execute(
            "UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
            (enc(new_defn), sec, tid),
        ),
        success=f"column '{args.name}' updated in '{args.table}'",
    )


def cmd_column_rename(cur, args):
    row = _find_table(cur, args.table)
    if row is None:
        sys.exit(f"error: table '{args.table}' not found")
    tid, tname, defn = row
    block = _col_block_for(defn, args.old)
    if block is None:
        sys.exit(f"error: column '{args.old}' not found in '{args.table}'")
    new_block = re.sub(rf':"{re.escape(args.old)}":DBColumn', f':"{args.new}":DBColumn', block, count=1)
    new_defn = defn.replace(block, new_block)
    # update domain rel addresses table$old -> table$new
    new_defn = re.sub(rf"{re.escape(tid)}\${re.escape(args.old)}", f"{tid}${args.new}", new_defn)
    sec = now_sec()
    _maybe_write(
        cur, args,
        sql="UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
        defn=new_defn,
        action=lambda c: c.execute(
            "UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
            (enc(new_defn), sec, tid),
        ),
        success=f"column '{args.old}' renamed to '{args.new}' in '{args.table}'",
    )


def cmd_fk_add(cur, args):
    child = _find_table(cur, args.table)
    ref = _find_table(cur, args.ref_table)
    if child is None or ref is None:
        sys.exit("error: table not found (child or ref)")
    cid_, cname, cdefn = child
    rid_, rname, rdefn = ref
    # child column block
    block = _col_block_for(cdefn, args.column)
    if block is None:
        sys.exit(f"error: column '{args.column}' not found in '{args.table}'")
    # ref column existence (loose check)
    rblock = _col_block_for(rdefn, args.ref_column)
    if rblock is None:
        sys.exit(f"error: ref column '{args.ref_column}' not found in '{args.ref_table}'")
    used = _ids(cur)
    fkid = new_id(used)
    ms = now_ms()
    ms_str = str(ms)
    sec = now_sec()
    label = args.label or ""
    # FK definition with fromModel/toModel addresses
    parent = cur.execute("SELECT PARENT_ID FROM MODEL_ELEMENT WHERE ID=?", (cid_,)).fetchone()[0]
    ref_parent = cur.execute("SELECT PARENT_ID FROM MODEL_ELEMENT WHERE ID=?", (rid_,)).fetchone()[0]
    fk_defn = (
        f'{fkid}:"{label}":DBForeignKey {{\n'
        f'\t_modelEditable=T;\n'
        f'\ttoModel=<{ref_parent}:{rid_}>;\n'
        f'\tpmAuthor="{DEFAULT_AUTHOR}";\n'
        f'\tlastModifiedTime={ms};\n'
        f'\tpmCreateDateTime="{ms_str}";\n'
        f'\tdataModel=1;\n'
        f'\tfromModel=<{parent}:{cid_}>;\n'
        f'\t_modelViews=NULL;\n'
        f'\tpmLastModified="{ms_str}";\n'
        f'}}'
    )
    # add foreignKey= to the child column block
    new_block = block + f"\n\tforeignKey=<_:_:{fkid}>;"
    new_cdefn = cdefn.replace(block, new_block)
    _maybe_write(
        cur, args,
        sql="INSERT DBForeignKey + UPDATE child DEFINITION",
        defn=fk_defn,
        action=lambda c: (
            c.execute(
                "INSERT INTO MODEL_ELEMENT (ID, MODEL_TYPE, PARENT_ID, NAME, DEFINITION, AUTHOR, CREATE_AT, LAST_MOD_AT) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (fkid, "DBForeignKey", None, label, enc(fk_defn), DEFAULT_AUTHOR, sec, sec),
            ),
            c.execute(
                "UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
                (enc(new_cdefn), sec, cid_),
            ),
        ),
        success=f"FK '{label or '(no label)'}' added: {args.table}.{args.column} -> {args.ref_table}.{args.ref_column} (id={fkid})",
    )


def cmd_domain_assign(cur, args):
    target = args.target
    domain = args.domain
    is_col = "." in target
    domain_type = "DBColumnDomain" if is_col else "DBTableDomain"
    did = cur.execute(
        "SELECT ID FROM MODEL_ELEMENT WHERE MODEL_TYPE=? AND NAME=?",
        (domain_type, domain),
    ).fetchone()
    if did is None:
        sys.exit(f"error: domain '{domain}' not found ({domain_type})")
    did = did[0]
    used = _ids(cur)
    ms = now_ms()
    ms_str = str(ms)
    sec = now_sec()

    if is_col:
        tname, cname = target.split(".", 1)
        row = _find_table(cur, tname)
        if row is None:
            sys.exit(f"error: table '{tname}' not found")
        tid, _, defn = row
        block = _col_block_for(defn, cname)
        if block is None:
            sys.exit(f"error: column '{cname}' not found in '{tname}'")
        rid = new_id(used)
        rel_defn = (
            f'{rid}:NULL:DBColumnDomainRelationship {{\n'
            f'\tpmLastModified="{ms_str}";\n'
            f'\tpmAuthor="{DEFAULT_AUTHOR}";\n'
            f'\tpmCreateDateTime="{ms_str}";\n'
            f'\tfromModel=<_:{tid}${cname}>;\n'
            f'\t_modelViews=NULL;\n'
            f'\tlastModifiedTime={ms};\n'
            f'\ttoModel=<_:{did}>;\n'
            f'\t_modelEditable=T;\n'
            f'}}'
        )
        _maybe_write(
            cur, args,
            sql="INSERT DBColumnDomainRelationship",
            defn=rel_defn,
            action=lambda c: c.execute(
                "INSERT INTO MODEL_ELEMENT (ID, MODEL_TYPE, NAME, DEFINITION, AUTHOR, CREATE_AT, LAST_MOD_AT) "
                "VALUES (?,?,?,?,?,?,?)",
                (rid, "DBColumnDomainRelationship", None, enc(rel_defn), DEFAULT_AUTHOR, sec, sec),
            ),
            success=f"column domain '{domain}' assigned to {target} (rel id={rid})",
        )
    else:
        row = _find_table(cur, target)
        if row is None:
            sys.exit(f"error: table '{target}' not found")
        tid, _, defn = row
        rid = new_id(used)
        rel_defn = (
            f'{rid}:NULL:DBTableDomainRelationship {{\n'
            f'\tpmLastModified="{ms_str}";\n'
            f'\tpmAuthor="{DEFAULT_AUTHOR}";\n'
            f'\tpmCreateDateTime="{ms_str}";\n'
            f'\tfromModel=<_:{tid}>;\n'
            f'\t_modelViews=NULL;\n'
            f'\tlastModifiedTime={ms};\n'
            f'\ttoModel=<_:{did}>;\n'
            f'\t_modelEditable=T;\n'
            f'}}'
        )
        _maybe_write(
            cur, args,
            sql="INSERT DBTableDomainRelationship",
            defn=rel_defn,
            action=lambda c: c.execute(
                "INSERT INTO MODEL_ELEMENT (ID, MODEL_TYPE, NAME, DEFINITION, AUTHOR, CREATE_AT, LAST_MOD_AT) "
                "VALUES (?,?,?,?,?,?,?)",
                (rid, "DBTableDomainRelationship", None, enc(rel_defn), DEFAULT_AUTHOR, sec, sec),
            ),
            success=f"table domain '{domain}' assigned to {target} (rel id={rid})",
        )


def cmd_diagram_add_table(cur, args):
    d = cur.execute("SELECT ID, NAME, DEFINITION FROM DIAGRAM WHERE NAME LIKE ?", (f"%{args.diagram}%",)).fetchall()
    if len(d) == 0:
        sys.exit(f"error: diagram '{args.diagram}' not found")
    if len(d) > 1:
        print("ambiguous diagram; matches:")
        for (did, name, _) in d:
            print(f"  {name.strip()}")
        sys.exit(1)
    did, dname, ddefn = d[0]
    ddefn = dec(ddefn)
    row = _find_table(cur, args.table)
    if row is None:
        sys.exit(f"error: table '{args.table}' not found")
    tid, tname, tdefn = row
    used = _ids(cur)
    deid = new_id(used)
    ms = now_ms()
    ms_str = str(ms)
    sec = now_sec()
    # DIAGRAM_ELEMENT row (shape) + add to DIAGRAM Child=(...)
    shape_defn = (
        f'{deid}:"{tname}":DBTable {{\n'
        f'\tcreatorDiagramType="ERDiagram";\n'
        f'\ty=100;\n\tx=100;\n'
        f'\tmetaModelElement=<{tid}>;\n'
        f'\theight=120;\n\twidth=200;\n'
        f'}}'
    )
    child_ref = f"<{did}:{deid}>"
    new_ddefn = ddefn
    m = re.search(r'Child=\((.*?)\);', ddefn, re.S)
    if m:
        inner = m.group(1).rstrip()
        new_inner = inner + ",\n\t\t" + child_ref if inner.strip() else "\n\t\t" + child_ref
        new_ddefn = ddefn[: m.start()] + "Child=(" + new_inner + ");" + ddefn[m.end():]
    else:
        new_ddefn = ddefn.rstrip() + "\n\tChild=(\n\t\t" + child_ref + "\n\t);"
    # wire the table's _masterViewId/_modelViews so mainview reports MAIN
    model_views_block = (
        f'_modelViews=(\n\t\t{{{deid}:"View":ModelView {{\n\t\t\tcontainer=<{did}>;\n\t\t\tview="{deid}";\n\t\t}}}}\n\t);'
    )
    if "_masterViewId" in tdefn:
        new_tdefn = re.sub(r'_masterViewId="[^"]*"', f'_masterViewId="{deid}"', tdefn, count=1)
        if "_modelViews=NULL;" in new_tdefn:
            new_tdefn = new_tdefn.replace("_modelViews=NULL;", model_views_block, 1)
        else:
            new_tdefn = re.sub(r'_modelViews=\([^)]*\);', model_views_block, new_tdefn, count=1)
    else:
        new_tdefn = tdefn.replace("dataModel=1;", f"dataModel=1;\n\t_masterViewId=\"{deid}\";\n\t{model_views_block}")
    print("WARNING: diagram shape blobs (PROJECT_FILE) are derived and not updated;")
    print("         VP will regenerate them when the file is opened.")
    _maybe_write(
        cur, args,
        sql="INSERT DIAGRAM_ELEMENT + UPDATE DIAGRAM DEFINITION",
        defn=shape_defn,
        action=lambda c: (
            c.execute(
                "INSERT INTO DIAGRAM_ELEMENT (ID, SHAPE_TYPE, DIAGRAM_ID, MODEL_ELEMENT_ID, DEFINITION) "
                "VALUES (?,?,?,?,?)",
                (deid, "DBTable", did, tid, enc(shape_defn)),
            ),
            c.execute("UPDATE DIAGRAM SET DEFINITION=? WHERE ID=?", (enc(new_ddefn), did)),
            c.execute("UPDATE MODEL_ELEMENT SET DEFINITION=?, LAST_MOD_AT=? WHERE ID=?",
                      (enc(new_tdefn), sec, tid)),
        ),
        success=f"table '{tname}' placed on diagram '{dname.strip()}' (element id={deid})",
    )


def cmd_verify(cur, args):
    name = getattr(args, "name", None)
    if name:
        rows = cur.execute(
            "SELECT MODEL_TYPE, NAME FROM MODEL_ELEMENT WHERE NAME=? LIMIT 10", (name,)
        ).fetchall()
        print(f"verify: {len(rows)} element(s) named '{name}'")
        for r in rows:
            print(f"  {r[0]:<28} {r[1]}")
        return
    n = cur.execute("SELECT COUNT(*) FROM MODEL_ELEMENT WHERE MODEL_TYPE='DBTable'").fetchone()[0]
    print(f"verify: DB readable; tables={n}")


# ---------------------------------------------------------------- main -------


def build_parser():
    parser = argparse.ArgumentParser(prog="vpp_write", description=__doc__)
    parser.add_argument("--db", default=DEFAULT_DB, help="target .vpp file")
    parser.add_argument("--backup", action="store_true", help="create backup before writing")
    parser.add_argument("--apply", action="store_true", help="actually write (default: dry-run)")
    parser.add_argument("--force", action="store_true", help="write without --backup (not recommended)")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_db(p):
        p.add_argument("--db", default=None)
        p.add_argument("--backup", action="store_true")
        p.add_argument("--apply", action="store_true")
        p.add_argument("--force", action="store_true")

    sp = sub.add_parser("backup")
    sp.set_defaults(func=cmd_backup)

    tc = sub.add_parser("table")
    tcs = tc.add_subparsers(dest="table_sub", required=True)
    t_create = tcs.add_parser("create")
    t_create.add_argument("package_id")
    t_create.add_argument("name")
    add_db(t_create)
    t_create.set_defaults(func=cmd_table_create)
    t_ren = tcs.add_parser("rename")
    t_ren.add_argument("old")
    t_ren.add_argument("new")
    add_db(t_ren)
    t_ren.set_defaults(func=cmd_table_rename)

    cc = sub.add_parser("column")
    ccs = cc.add_subparsers(dest="col_sub", required=True)
    c_add = ccs.add_parser("add")
    c_add.add_argument("table")
    c_add.add_argument("name")
    c_add.add_argument("--type", default=None)
    c_add.add_argument("--length", type=int, default=None)
    c_add.add_argument("--not-null", action="store_true")
    c_add.add_argument("--pk", action="store_true")
    c_add.add_argument("--default", default=None)
    add_db(c_add)
    c_add.set_defaults(func=cmd_column_add)
    c_upd = ccs.add_parser("update")
    c_upd.add_argument("table")
    c_upd.add_argument("name")
    c_upd.add_argument("--type", default=None)
    c_upd.add_argument("--length", type=int, default=None)
    c_upd.add_argument("--not-null", action="store_true")
    c_upd.add_argument("--pk", action="store_true")
    c_upd.add_argument("--default", default=None)
    add_db(c_upd)
    c_upd.set_defaults(func=cmd_column_update)
    c_ren = ccs.add_parser("rename")
    c_ren.add_argument("table")
    c_ren.add_argument("old")
    c_ren.add_argument("new")
    add_db(c_ren)
    c_ren.set_defaults(func=cmd_column_rename)

    fk = sub.add_parser("fk")
    fks = fk.add_subparsers(dest="fk_sub", required=True)
    fk_add = fks.add_parser("add")
    fk_add.add_argument("table")
    fk_add.add_argument("column")
    fk_add.add_argument("ref_table")
    fk_add.add_argument("ref_column")
    fk_add.add_argument("--label", default="")
    add_db(fk_add)
    fk_add.set_defaults(func=cmd_fk_add)

    dm = sub.add_parser("domain")
    dms = dm.add_subparsers(dest="dm_sub", required=True)
    dm_assign = dms.add_parser("assign")
    dm_assign.add_argument("target")
    dm_assign.add_argument("domain")
    add_db(dm_assign)
    dm_assign.set_defaults(func=cmd_domain_assign)

    dg = sub.add_parser("diagram")
    dgs = dg.add_subparsers(dest="diag_sub", required=True)
    d_add = dgs.add_parser("add-table")
    d_add.add_argument("diagram")
    d_add.add_argument("table")
    add_db(d_add)
    d_add.set_defaults(func=cmd_diagram_add_table)

    v = sub.add_parser("verify")
    v.add_argument("name", nargs="?")
    add_db(v)
    v.set_defaults(func=cmd_verify)

    return parser


def _guard(args):
    if not getattr(args, "apply", False):
        return
    if getattr(args, "backup", False):
        make_backup(args.db)
        return
    if getattr(args, "force", False):
        print("WARNING: --force set; writing WITHOUT backup")
        return
    sys.exit(
        "error: --apply requires --backup (or --force). Refusing to write without a backup."
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    db = getattr(args, "db", None) or DEFAULT_DB
    args.db = db
    if args.command == "backup":
        make_backup(db)
        return 0
    _guard(args)
    con = sqlite3.connect(db)
    try:
        cur = con.cursor()
        args.func(cur, args)
        if getattr(args, "apply", False):
            con.commit()
    except Exception as e:
        con.rollback()
        raise
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
