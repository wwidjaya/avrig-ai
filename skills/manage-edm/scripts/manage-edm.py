#!/usr/bin/env python3
"""manage-edm CLI: CRUD entities/domains/modules/connections in a .edm/ corpus.

Folder layout (per project root, resolved from --root or nearest .edm/ ancestor):
  .edm/
    data/<project>-edm.db               SQLite database (source of truth)
    ddl/<version>/<domain>-<module>-<entity>.sql
                                        generated DDL, versioned centrally

Domains, modules, entities, data types, templates, and version state all live
in SQLite; no per-domain/per-module folders are created on disk anymore.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlencode, urlparse, urlunparse
from urllib.request import HTTPCookieProcessor, Request, build_opener, urlopen

import yaml
from cryptography.fernet import Fernet

DEFAULT_CONN_DB_KEYS = ("type", "url")

EDM_DIR_NAME = ".edm"
EDM_DIR_NAME_LEGACY = "edm"

_KEY_NAME = "manage-edm"
DEFAULT_VERSION = "0.0.1"
# Vault Address: Defaults to external/internal vault.avrig.ai
_VAULT_ADDR = os.environ.get("VAULT_ADDR", "https://vault.avrig.ai")
_WSL_DISTRO = os.environ.get("EDM_WSL_DISTRO", "avrig-ai")

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")

def load_version(root: Path) -> str:
    """Load current active EDM version from the SQLite version table."""
    import sqlite3
    db = edm_db_path(root)
    if db.exists():
        try:
            conn_sql = sqlite3.connect(db)
            ensure_version_table(conn_sql)
            cur = conn_sql.cursor()
            cur.execute("SELECT version_code FROM version WHERE is_active = 1 AND is_deleted = 0 LIMIT 1")
            row = cur.fetchone()
            conn_sql.close()
            if row and row[0]:
                return str(row[0]).strip()
        except Exception:
            pass
    return DEFAULT_VERSION

def save_version(root: Path, version: str) -> None:
    """Write current EDM version to SQLite version table as active (is_active = 1)."""
    import sqlite3
    import datetime
    v_clean = str(version).strip()
    if not _SEMVER_RE.match(v_clean):
        sys.exit(f"error: invalid SemVer 2.0 version '{v_clean}'. Expected MAJOR.MINOR.PATCH (e.g. 0.0.1).")
    db = edm_db_path(root)
    if db.exists():
        conn_sql = sqlite3.connect(db)
        ensure_version_table(conn_sql)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # Deactivate all active rows
        conn_sql.execute("UPDATE version SET is_active = 0 WHERE is_active = 1")
        # Check if version already exists
        cur = conn_sql.cursor()
        cur.execute("SELECT id FROM version WHERE version_code = ? AND is_deleted = 0", (v_clean,))
        existing = cur.fetchone()
        if existing:
            conn_sql.execute("UPDATE version SET is_active = 1, updated_time = ? WHERE id = ?", (now, existing[0]))
        else:
            conn_sql.execute("""
                INSERT INTO version (version_code, version_name, is_active, created_time, updated_time, is_deleted)
                VALUES (?, ?, 1, ?, ?, 0)
            """, (v_clean, v_clean, now, now))
        conn_sql.commit()
        conn_sql.close()

def op_naming_style(root, args):
    """Read or set the entity and column naming style (S: snake_case, C: camelCase)."""
    if getattr(args, "style", None):
        val = args.style.strip().upper()
        if val in ("SNAKE", "SNAKE_CASE", "S"):
            clean = "S"
        elif val in ("CAMEL", "CAMELCASE", "C"):
            clean = "C"
        else:
            sys.exit(f"error: invalid style '{args.style}'. Expected 'S' (snake_case) or 'C' (camelCase).")
        set_naming_style(root, clean)
        label = "snake_case (S)" if clean == "S" else "camelCase (C)"
        print(f"set EDM naming style -> {label}")
    else:
        current = get_naming_style(root)
        label = "snake_case (S)" if current == "S" else "camelCase (C)"
        print(f"EDM naming style: {label}")


def op_set_version(root, args):
    """Set/read the current EDM version in SQLite version table.

    Omitting <version> prints the current version. Passing --list displays all
    recorded versions. Passing a new <version> is a gated operation: it succeeds
    only when approved via `--force` (since version-increment gate at >=0.0.8).
    """
    import sqlite3
    if getattr(args, "list", False):
        db = edm_db_path(root)
        if not db.exists():
            sys.exit(f"no EDM database found at {db}")
        conn_sql = sqlite3.connect(db)
        ensure_version_table(conn_sql)
        rows = conn_sql.execute("""
            SELECT version_code, is_active, created_time, updated_time
            FROM version
            WHERE is_deleted = 0
            ORDER BY id
        """).fetchall()
        conn_sql.close()
        if not rows:
            print("no versions recorded")
            return
        print(f"# EDM Versions ({len(rows)} recorded)")
        print()
        print("| Version | Active | Created | Updated |")
        print("|---------|--------|---------|---------|")
        for vc, act, ct, ut in rows:
            act_mark = "Yes" if act else "No"
            print(f"| {vc} | {act_mark} | {ct or ''} | {ut or ''} |")
        return
    if not args.version:
        print(load_version(root))
        return
    cur = load_version(root)
    if args.version == cur:
        print(f"EDM version already set to {cur}")
        return
    if not getattr(args, "force", False):
        sys.exit(f"refusing version bump {cur} -> {args.version} "
                 "(dry-run). Re-run with --force to approve version increment.")
    save_version(root, args.version)
    print(f"set EDM version -> {args.version}")


def op_read_version_history(root, args):
    """Display EDM audit history log from version_history table."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"no EDM database found at {db}")
    conn_sql = sqlite3.connect(db)
    ensure_version_history_table(conn_sql)

    where = ["vh.is_deleted = 0"]
    params = []
    if getattr(args, "table", None):
        where.append("vh.table_name = ?")
        params.append(args.table.strip())
    if getattr(args, "version", None):
        v_arg = str(args.version).strip()
        if v_arg.isdigit():
            where.append("vh.version_id = ?")
            params.append(int(v_arg))
        else:
            where.append("v.version_code = ?")
            params.append(v_arg)

    limit = getattr(args, "limit", None) or 50
    params.append(int(limit))

    query = f"""
        SELECT vh.id, COALESCE(v.version_code, vh.version_id), vh.table_name,
               vh.record_id, vh.change_type_flag, vh.change_detail_desc, vh.created_time
        FROM version_history vh
        LEFT JOIN version v ON vh.version_id = v.id
        WHERE {' AND '.join(where)}
        ORDER BY vh.id DESC
        LIMIT ?
    """
    rows = conn_sql.execute(query, params).fetchall()
    conn_sql.close()

    if not rows:
        print("no version history recorded")
        return

    print(f"# Version History ({len(rows)} entries)")
    print()
    print("| ID | Version | Table | Rec ID | Type | Description | Timestamp |")
    print("|----|---------|-------|--------|------|-------------|-----------|")
    for rid, vcode, tbl, rec_id, flag, desc, ts in rows:
        flag_label = {"C": "Create", "M": "Modify", "D": "Delete"}.get(flag, flag)
        desc_clean = (desc or "").replace("\n", " ").replace("|", "/")
        if len(desc_clean) > 80:
            desc_clean = desc_clean[:77] + "..."
        ts_clean = (ts or "")[:19].replace("T", " ")
        print(f"| {rid} | {vcode} | {tbl} | {rec_id} | {flag_label} | {desc_clean} | {ts_clean} |")

def op_init(root, args):
    """Create .edm/data/ + SQLite database named <project parent>-edm.db with connection table."""
    import sqlite3
    import datetime
    edm = edm_dir(root)
    parent = edm.parent.name
    data_dir = edm / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = edm_db_path(root)
    conn_sqlite = sqlite3.connect(db_path)
    try:
        ensure_connection_table(conn_sqlite)
        ensure_domain_table(conn_sqlite)
        ensure_module_table(conn_sqlite)
        ensure_data_type_table(conn_sqlite)
        ensure_version_table(conn_sqlite)
        ensure_entity_domain_table(conn_sqlite)
        ensure_column_domain_table(conn_sqlite)
        ensure_entity_table(conn_sqlite)
        ensure_version_history_table(conn_sqlite)
        _ensure_version_id_columns(conn_sqlite)
        domains = _migrate_domains_md(root, conn_sqlite)
        modules = _migrate_modules_md(root, conn_sqlite)
        module_schemas = _migrate_module_schema(root, conn_sqlite)
        data_types = _migrate_data_types_md(root, conn_sqlite)
        tpl_entity, tpl_column = _migrate_templates(root, conn_sqlite)
        entities = _migrate_entities(root, conn_sqlite)
        _ensure_version_id_columns(conn_sqlite)
        conn_sqlite.commit()
    except Exception as e:
        conn_sqlite.close()
        sys.exit(f"error: could not initialize SQLite database at {db_path}: {e}")
    conn_sqlite.close()
    print(f"initialized EDM data folder: {data_dir}")
    if domains:
        print(f"migrated {domains} domain(s) from _domains.md to {db_path.name}")
    if modules:
        print(f"migrated {modules} module(s) from _modules.md to {db_path.name}")
    if data_types:
        print(f"migrated {data_types} data type(s) from data-types.md to {db_path.name}")
    if tpl_entity:
        print(f"migrated {tpl_entity} entity-domain template(s) to {db_path.name}")
    if tpl_column:
        print(f"migrated {tpl_column} column-domain template(s) to {db_path.name}")
    if entities:
        print(f"migrated {entities} entity(ies) to {db_path.name}")
    print(f"created SQLite database: {db_path}")

def _parse_order(row: dict) -> int:
    """Parse a display order from a registry row, tolerating 'Order'/'display order' headers."""
    raw = ""
    for key in ("order", "display_order", "display order", "displayorder"):
        if row.get(key):
            raw = str(row.get(key)).strip()
            break
    try:
        return int(raw) if raw else 0
    except ValueError:
        return 0


def _migrate_domains_md(root: Path, conn_sqlite) -> int:
    """Migrate .edm/_domains.md into the domain table, resolving connection references. Returns count migrated."""
    import datetime
    reg_path = domains_registry(root)
    if not reg_path.exists():
        return 0
    try:
        _, rows = read_registry_table(reg_path)
    except Exception as e:
        sys.exit(f"error: could not read {reg_path}: {e}")
    migrated = 0
    for row in rows:
        code = (row.get("code") or "").strip()
        name = (row.get("name") or code).strip()
        desc = (row.get("description") or "").strip()
        if not code:
            continue
        # Resolve connection reference from _<domain>_index.md frontmatter
        conn_id = None
        di = domain_index(root, kebab(name))
        if di.exists():
            dfm, _ = read_frontmatter(di)
            conn_ref = dfm.get("connection", "") or dfm.get("connection_code", "")
            if conn_ref:
                cur = conn_sqlite.cursor()
                cur.execute("SELECT id FROM connection WHERE connection_code = ? AND is_deleted = 0", (conn_ref,))
                res = cur.fetchone()
                if res:
                    conn_id = res[0]
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        display_order = _parse_order(row)
        conn_sqlite.execute("""
            INSERT OR IGNORE INTO domain (
                domain_code, domain_name, domain_desc, connection_id,
                display_order, is_active, created_time, updated_time, is_deleted
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (code, name, desc, conn_id, display_order, now, now))
        migrated += 1
    if migrated:
        conn_sqlite.commit()
        try:
            reg_path.unlink()
        except OSError:
            pass
    return migrated


def _migrate_modules_md(root: Path, conn_sqlite) -> int:
    """Migrate .edm/<domain>/_modules.md into the module table, resolving domain references. Returns count migrated."""
    import datetime
    edm = edm_dir(root)
    migrated = 0
    for reg_path in sorted(edm.glob("*/_modules.md")):
        try:
            _, rows = read_registry_table(reg_path)
        except Exception as e:
            sys.exit(f"error: could not read {reg_path}: {e}")
        domain_k = reg_path.parent.name
        cur = conn_sqlite.cursor()
        cur.execute("SELECT id, domain_name, domain_code FROM domain WHERE is_deleted = 0")
        domain_id = None
        for did, dname, dcode in cur.fetchall():
            if kebab(dname) == domain_k or dcode == domain_k:
                domain_id = did
                break
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        inserted = []
        for row in rows:
            code = (row.get("code") or "").strip()
            name = (row.get("name") or code).strip()
            desc = (row.get("description") or "").strip()
            if not code:
                continue
            sc = (row.get("schema") or kebab(name)).strip()
            parent_ref = (row.get("parent") or row.get("parent_module") or row.get("parent module") or "").strip()
            display_order = _parse_order(row)
            conn_sqlite.execute("""
                INSERT OR IGNORE INTO module (
                    module_code, module_name, module_desc, schema, domain_id,
                    display_order, is_active, created_time, updated_time, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
            """, (code, name, desc, sc, domain_id, display_order, now, now))
            inserted.append((code, parent_ref))
            migrated += 1
        # Second pass: resolve parent references within the same domain (parents may appear after children)
        for code, parent_ref in inserted:
            if not parent_ref or parent_ref.casefold() == code.casefold():
                continue
            p = conn_sqlite.execute(
                "SELECT id FROM module WHERE domain_id = ? AND (module_code = ? OR module_name = ?) AND is_deleted = 0",
                (domain_id, parent_ref, parent_ref)).fetchone()
            if p is None:
                sys.exit(f"error: parent module '{parent_ref}' for sub-module '{code}' not found in domain '{domain_k}'")
            conn_sqlite.execute(
                "UPDATE module SET parent_module_id = ? WHERE module_code = ? AND domain_id = ? AND is_deleted = 0",
                (p[0], code, domain_id))
        try:
            reg_path.unlink()
        except OSError:
            pass
    if migrated:
        conn_sqlite.commit()
    return migrated


def _migrate_module_schema(root: Path, conn_sqlite) -> int:
    """Backfill `module.schema` from `_<module>_index.md` frontmatter where schema is NULL. Returns updated count."""
    ensure_module_table(conn_sqlite)
    cur = conn_sqlite.cursor()
    cur.execute("""
        SELECT m.id, m.module_code, m.module_name, d.domain_name, d.domain_code
        FROM module m
        JOIN domain d ON m.domain_id = d.id
        WHERE m.schema IS NULL AND m.is_deleted = 0
    """)
    rows = cur.fetchall()
    updated = 0
    for mid, code, name, dname, dcode in rows:
        sc = ""
        for dom in (kebab(dname), dcode):
            for mod in (kebab(name), code, name):
                mi = module_index(root, dom, mod)
                if mi.exists():
                    try:
                        fm, _ = read_frontmatter(mi)
                        sc = str(fm.get("schema") or "").strip()
                        if sc:
                            break
                    except Exception:
                        pass
            if sc:
                break
        if not sc:
            sc = kebab(name)
        cur.execute("UPDATE module SET schema = ? WHERE id = ?", (sc, mid))
        updated += 1
    if updated:
        conn_sqlite.commit()
    return updated


def _migrate_data_types_md(root: Path, conn_sqlite) -> int:
    """Migrate .edm/data-types.md into the data_type table, linked to default DB connection. Returns count migrated."""
    import datetime
    p = edm_dir(root) / "data-types.md"
    if not p.exists():
        return 0
    rows = []
    found_table = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if "| Category | Canonical Type |" in line:
            found_table = True
            continue
        if found_table and line.startswith("|") and not any(x in line for x in ("---", "Category")):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 3 and cells[1]:
                rows.append((cells[0], cells[1], cells[2]))
    if not rows:
        return 0
    cur = conn_sqlite.cursor()
    cur.execute("SELECT id FROM connection WHERE connection_type_flag = 'DB' AND is_deleted = 0 ORDER BY id LIMIT 1")
    res = cur.fetchone()
    conn_id = res[0] if res else None
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    migrated = 0
    for category, canonical, aliases in rows:
        conn_sqlite.execute("""
            INSERT OR IGNORE INTO data_type (
                data_type_code, data_type_name, category, aliases, connection_id,
                is_active, created_time, updated_time, is_deleted
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (canonical.lower(), canonical, category, aliases, conn_id, now, now))
        migrated += 1
    conn_sqlite.commit()
    try:
        p.unlink()
    except OSError:
        pass
    return migrated


def _migrate_templates(root: Path, conn_sqlite) -> tuple[int, int]:
    """Migrate .edm/entity-domain/ and .edm/column-domain/ templates into SQLite. Returns (entity_count, column_count)."""
    import datetime
    import shutil
    counts = {"entity": 0, "column": 0}
    kinds = (
        ("entity", entity_domain_dir(root), "entity_domain", "entity_domain_code", "entity_domain_name"),
        ("column", column_domain_dir(root), "column_domain", "column_domain_code", "column_domain_name"),
    )
    for kind_key, t_dir, table, code_col, name_col in kinds:
        if not t_dir.is_dir():
            continue
        md_files = sorted(p for p in t_dir.glob("*.md") if not p.name.startswith("_"))
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for p_md in md_files:
            code = p_md.stem
            try:
                fm, body = read_frontmatter(p_md)
                cols, fks = parse_columns(body)
                name = fm.get("title") or code
                desc = fm.get("description") or ""
                if not desc:
                    # extract _..._ line from Description section if present
                    m_desc = re.search(r"## Description\s*\n+_(.*?)_", body, re.S)
                    if m_desc:
                        desc = m_desc.group(1).strip()
                cols_json = json.dumps(cols, ensure_ascii=False)
                fks_json = json.dumps(fks, ensure_ascii=False)
                conn_sqlite.execute(f"""
                    INSERT OR IGNORE INTO {table} (
                        {code_col}, {name_col}, template_desc, columns_json, fks_json,
                        is_active, created_time, updated_time, is_deleted
                    ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0)
                """, (code, name, desc, cols_json, fks_json, now, now))
                counts[kind_key] += 1
            except Exception:
                pass
            try:
                p_md.unlink()
            except OSError:
                pass
            p_aml = t_dir / f"{code}.aml"
            if p_aml.exists():
                try:
                    p_aml.unlink()
                except OSError:
                    pass
        # Clean up empty directory
        try:
            remaining = [p for p in t_dir.iterdir() if p.name != "_index.md"]
            if not remaining:
                shutil.rmtree(t_dir)
        except OSError:
            pass
    conn_sqlite.commit()
    return counts["entity"], counts["column"]


def _migrate_entities(root: Path, conn_sqlite) -> int:
    """Migrate all .edm/*/*/entities/*.md files into SQLite entity table. Returns count migrated."""
    import datetime
    import shutil
    edm = edm_dir(root)
    if not edm.is_dir():
        return 0
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    migrated = 0

    # Build cache of entity_domain and column_domain templates: code/name -> id
    cur = conn_sqlite.cursor()
    ed_map = {}
    for tid, tcode, tname in cur.execute("SELECT id, entity_domain_code, entity_domain_name FROM entity_domain WHERE is_deleted = 0").fetchall():
        ed_map[tcode.lower()] = tid
        ed_map[tname.lower()] = tid
    cd_map = {}
    for tid, tcode, tname in cur.execute("SELECT id, column_domain_code, column_domain_name FROM column_domain WHERE is_deleted = 0").fetchall():
        cd_map[tcode.lower()] = tid
        cd_map[tname.lower()] = tid

    for p_md in sorted(edm.glob("*/*/entities/*.md")):
        module_dir_p = p_md.parent.parent
        domain_dir_p = module_dir_p.parent
        if domain_dir_p.name in ("connections", "data", "entity-domain", "column-domain"):
            continue

        domain_k = domain_dir_p.name
        module_k = module_dir_p.name

        # Resolve domain and module IDs from SQLite
        cur.execute("SELECT id FROM domain WHERE (domain_code = ? OR domain_name = ?) AND is_deleted = 0", (domain_k, domain_k))
        d_res = cur.fetchone()
        if not d_res:
            continue
        domain_id = d_res[0]

        cur.execute("SELECT id FROM module WHERE (module_code = ? OR module_name = ?) AND domain_id = ? AND is_deleted = 0",
                    (module_k, module_k, domain_id))
        m_res = cur.fetchone()
        if not m_res:
            continue
        module_id = m_res[0]

        try:
            fm, body = read_frontmatter(p_md)
            cols, fks = parse_columns(body)
            entity_code = p_md.stem
            entity_name = fm.get("title") or fm.get("entity") or entity_code
            desc = fm.get("description") or ""
            if not desc:
                m_desc = re.search(r"## Description\s*\n+_(.*?)_", body, re.S)
                if m_desc:
                    desc = m_desc.group(1).strip()

            # Process entity_domains refs
            raw_ed = fm.get("entity-domains") or fm.get("entity-domain") or []
            if isinstance(raw_ed, str):
                raw_ed = [raw_ed]
            entity_domains_list = []
            ed_col_provenance = {}  # col_name -> tid
            for r in raw_ed:
                rname = r.get("name") if isinstance(r, dict) else str(r)
                rcols = r.get("columns", []) if isinstance(r, dict) else []
                tid = ed_map.get(rname.lower())
                entity_domains_list.append({"name": rname, "entity_domain_id": tid, "columns": rcols})
                for c in rcols:
                    ed_col_provenance[c] = tid

            # Process column_domains refs
            raw_cd = fm.get("column-domains") or fm.get("column-domain") or []
            if isinstance(raw_cd, str):
                raw_cd = [raw_cd]
            column_domains_list = []
            cd_col_provenance = {}  # col_name -> tid
            for r in raw_cd:
                rname = r.get("name") if isinstance(r, dict) else str(r)
                rcols = r.get("columns", []) if isinstance(r, dict) else []
                tid = cd_map.get(rname.lower())
                column_domains_list.append({"name": rname, "column_domain_id": tid, "columns": rcols})
                for c in rcols:
                    cd_col_provenance[c] = tid

            # Tag each column with entity_domain_id or column_domain_id
            for c in cols:
                cname = c["name"]
                c["entity_domain_id"] = ed_col_provenance.get(cname)
                c["column_domain_id"] = cd_col_provenance.get(cname)

            cols_json = json.dumps(cols, ensure_ascii=False)
            fks_json = json.dumps(fks, ensure_ascii=False)
            ed_json = json.dumps(entity_domains_list, ensure_ascii=False)
            cd_json = json.dumps(column_domains_list, ensure_ascii=False)

            conn_sqlite.execute("""
                INSERT OR IGNORE INTO entity (
                    entity_code, entity_name, entity_desc, module_id,
                    columns_json, fks_json, entity_domains_json, column_domains_json,
                    is_active, created_time, updated_time, is_deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
            """, (entity_code, entity_name, desc, module_id, cols_json, fks_json, ed_json, cd_json, now, now))
            migrated += 1
        except Exception:
            pass

        try:
            p_md.unlink()
        except OSError:
            pass
        p_aml = p_md.with_suffix(".aml")
        if p_aml.exists():
            try:
                p_aml.unlink()
            except OSError:
                pass

        # Clean up stale entity link from _<module>_index.md
        mi = module_dir_p / f"_{module_k}_index.md"
        if mi.exists():
            try:
                mi_fm, mi_body = read_frontmatter(mi)
                mi_body = re.sub(rf"^- \[.*\]\(\./entities/{re.escape(entity_code)}\.md\).*$\n?", "", mi_body, flags=re.M)
                write_md(mi, mi_fm, mi_body.strip() + "\n")
            except Exception:
                pass

    # Clean empty entities folders
    for e_dir in edm.glob("*/*/entities"):
        try:
            if not any(e_dir.iterdir()):
                shutil.rmtree(e_dir)
        except OSError:
            pass

    conn_sqlite.commit()
    return migrated


def _vault_get_key() -> Optional[bytes]:
    """Retrieve Fernet key from Vault (via vault.avrig.ai HTTP API using proxy token, fallback to CLI)."""
    import json
    import ssl
    import urllib.error
    import urllib.request
    
    # Try fetching the token from the local WSL instance proxy token
    token = os.environ.get("VAULT_TOKEN")
    if not token:
        try:
            res = subprocess.run(
                ["wsl", "-d", _WSL_DISTRO, "--", "cat", "/var/lib/vault-proxy/token"],
                capture_output=True, text=True, check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                token = res.stdout.strip()
        except Exception:
            pass

    if token:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = f"{_VAULT_ADDR}/v1/secret/data/{_KEY_NAME}"
            req = urllib.request.Request(url, headers={"X-Vault-Token": token})
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                val = data.get("data", {}).get("data", {}).get("key")
                if val:
                    return val.encode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception:
            pass

    return None

def _vault_put_key(new_key: str) -> None:
    """Store Fernet key in Vault KV engine."""
    import json
    import ssl
    import urllib.request
    
    token = os.environ.get("VAULT_TOKEN")
    if not token:
        try:
            res = subprocess.run(
                ["wsl", "-d", _WSL_DISTRO, "--", "cat", "/var/lib/vault-proxy/token"],
                capture_output=True, text=True, check=False
            )
            if res.returncode == 0 and res.stdout.strip():
                token = res.stdout.strip()
        except Exception:
            pass

    if token:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            url = f"{_VAULT_ADDR}/v1/secret/data/{_KEY_NAME}"
            body = json.dumps({"data": {"key": new_key}}).encode("utf-8")
            req = urllib.request.Request(
                url, data=body,
                headers={"X-Vault-Token": token, "Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=5) as resp:
                if resp.status in (200, 204):
                    return
        except Exception as e:
            sys.exit(f"error: failed to store encryption key in vault at {_VAULT_ADDR}: {e}")

    # Fallback to CLI if HTTP API direct call failed
    wsl_cmd = f"export VAULT_ADDR='{_VAULT_ADDR}' && /usr/bin/vault kv put secret/{_KEY_NAME} key='{new_key}'"
    subprocess.run(
        ["wsl", "-d", _WSL_DISTRO, "--", "bash", "-lc", wsl_cmd],
        capture_output=True, text=True, check=False
    )

def _get_or_create_key() -> bytes:
    """Get Fernet key from Vault KV engine (secret/manage-edm), or create new key if missing."""
    key = _vault_get_key()
    if key:
        return key
    
    # Generate new key and store in Vault
    new_key = Fernet.generate_key().decode("utf-8")
    _vault_put_key(new_key)
    return new_key.encode("utf-8")

def _encrypt(value: str) -> str:
    """Encrypt a string value using Fernet symmetric encryption."""
    key = _get_or_create_key()
    f = Fernet(key)
    return f.encrypt(value.encode("utf-8")).decode("utf-8")

def _decrypt(value: str) -> str:
    """Decrypt a Fernet-encrypted string value."""
    key = _get_or_create_key()
    f = Fernet(key)
    return f.decrypt(value.encode("utf-8")).decode("utf-8")

# ---------------------------------------------------------------- path utils

def to_snake_case(name: str) -> str:
    """Convert string to snake_case."""
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    s2 = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1)
    s3 = re.sub(r'[^0-9a-zA-Z]+', '_', s2)
    return s3.strip('_').lower()


def to_camel_case(name: str) -> str:
    """Convert string to camelCase."""
    words = [w for w in re.split(r'[^0-9a-zA-Z]+', name) if w]
    if not words:
        return ""
    return words[0].lower() + "".join(w.capitalize() for w in words[1:])


def format_by_naming_style(name: str, style_flag: str) -> str:
    """Format an entity or column name according to style_flag ('S': snake_case, 'C': camelCase)."""
    if style_flag == "C":
        return to_camel_case(name)
    return to_snake_case(name)


def kebab(name: str) -> str:
    """'01. Platform Support (PS)' -> '01-platform-support-ps'"""
    n = name.strip().lower()
    n = re.sub(r"[^0-9a-z]+", "-", n)
    n = re.sub(r"-+", "-", n)
    return n.strip("-")


def load_allowed_types(root: Path, connection_id: Optional[int] = None) -> dict[str, str]:
    """Load map of alias -> canonical type from SQLite data_type table (or fallback to .edm/data-types.md)."""
    import sqlite3
    db = edm_db_path(root)
    types = {}
    if db.exists():
        try:
            conn_sql = sqlite3.connect(db)
            ensure_data_type_table(conn_sql)
            cur = conn_sql.cursor()
            if connection_id is not None:
                cur.execute("""
                    SELECT data_type_name, aliases FROM data_type
                    WHERE (connection_id = ? OR connection_id IS NULL) AND is_deleted = 0
                """, (connection_id,))
            else:
                cur.execute("SELECT data_type_name, aliases FROM data_type WHERE is_deleted = 0")
            for canonical, aliases_str in cur.fetchall():
                types[canonical.lower()] = canonical
                if aliases_str:
                    for a in aliases_str.split(","):
                        a_clean = a.strip().lower()
                        if a_clean:
                            types[a_clean] = canonical
            conn_sql.close()
            if types:
                return types
        except Exception:
            pass

    # Legacy fallback
    p = edm_dir(root) / "data-types.md"
    if not p.exists():
        return {}
    found_table = False
    for line in p.read_text(encoding="utf-8").splitlines():
        if "| Category | Canonical Type |" in line:
            found_table = True
            continue
        if found_table and line.startswith("|") and not any(x in line for x in ("---", "Category")):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2:
                canonical = cells[1]
                aliases = cells[2].split(",") if cells[2] else []
                types[canonical.lower()] = canonical
                for a in aliases:
                    types[a.strip().lower()] = canonical
    return types


def validate_column_type(type_str: str, allowed: dict[str, str]) -> tuple[bool, str]:
    """Check if type is valid. Return (is_valid, canonical_type)."""
    if not type_str:
        return False, ""
    # strip length suffixes like (256)
    base_type = re.sub(r"\(.*\)", "", type_str).lower().strip()
    canonical = allowed.get(base_type)
    if canonical:
        return True, canonical
    return False, type_str

def project_root(start: Path) -> Path:
    """project root heuristic search ancestors for semantic markers."""
    markers = ("package.json", "tsconfig.json", "pyproject.toml", "setup.py",
               "Cargo.toml", "pom.xml", "go.mod", "Makefile", ".git")
    for p in [start, *start.parents]:
        if any((p / m).exists() for m in markers):
            return p
    return start


def find_root(path: Optional[str]) -> Path:
    """.edm/ root: --root wins, else nearest ancestor containing .edm/ (legacy edm/ tolerated)."""
    if path:
        return Path(path)
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        if (p / EDM_DIR_NAME).is_dir() or (p / EDM_DIR_NAME_LEGACY).is_dir():
            return p
    # fallback: project root + .edm/
    if ((project_root(cwd) / EDM_DIR_NAME).is_dir()
            or (project_root(cwd) / EDM_DIR_NAME_LEGACY).is_dir()):
        return project_root(cwd)
    return cwd


def edm_dir(root: Path) -> Path:
    return root / EDM_DIR_NAME


def edm_db_path(root: Path) -> Path:
    edm = edm_dir(root)
    return edm / "data" / f"{edm.parent.name}-edm.db"


def ensure_connection_table(conn_sqlite) -> None:
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS connection (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        connection_code TEXT NOT NULL UNIQUE,
        connection_name TEXT NOT NULL,
        connection_desc TEXT,
        connection_type_flag TEXT NOT NULL,
        connection_string TEXT NOT NULL,
        version_id INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (version_id) REFERENCES version(id)
    );
    """)
    conn_sqlite.commit()


def _migrate_domain_table(conn_sqlite) -> None:
    """Idempotent domain-table migration: insert display_order between version_id and is_active.

    SQLite cannot insert a column mid-table, so the existing table is rebuilt with display_order
    placed before is_active. Only active (is_deleted = 0) rows are carried over, hard-deleting
    soft-deleted (unused) domains; orphaned soft-deleted modules pointing at purged domains are
    hard-deleted as well.
    """
    cols = {r[1] for r in conn_sqlite.execute("PRAGMA table_info(domain)")}
    if "display_order" in cols:
        return
    conn_sqlite.execute("PRAGMA foreign_keys=OFF")
    try:
        conn_sqlite.execute("""
        CREATE TABLE domain_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            domain_code TEXT NOT NULL UNIQUE,
            domain_name TEXT NOT NULL,
            domain_desc TEXT,
            connection_id INTEGER,
            version_id INTEGER,
            display_order INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT,
            created_time TEXT NOT NULL,
            updated_by TEXT,
            updated_time TEXT NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_by TEXT,
            deleted_time TEXT,
            FOREIGN KEY (connection_id) REFERENCES connection(id),
            FOREIGN KEY (version_id) REFERENCES version(id)
        );
        """)
        conn_sqlite.execute("""
            INSERT INTO domain_new (id, domain_code, domain_name, domain_desc, connection_id,
                                    version_id, display_order, is_active, created_by, created_time,
                                    updated_by, updated_time, is_deleted, deleted_by, deleted_time)
            SELECT id, domain_code, domain_name, domain_desc, connection_id, version_id,
                   0, is_active, created_by, created_time, updated_by, updated_time,
                   is_deleted, deleted_by, deleted_time
            FROM domain
            WHERE is_deleted = 0
        """)
        conn_sqlite.commit()
        conn_sqlite.execute("DROP TABLE domain")
        conn_sqlite.execute("ALTER TABLE domain_new RENAME TO domain")
        conn_sqlite.execute(
            "DELETE FROM module WHERE is_deleted = 1 AND domain_id NOT IN (SELECT id FROM domain)")
        conn_sqlite.commit()
        conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_domain_connection_id ON domain(connection_id);")
        conn_sqlite.commit()
    finally:
        conn_sqlite.execute("PRAGMA foreign_keys=ON")


def ensure_domain_table(conn_sqlite) -> None:
    """Create the domain table following the standard entity domain, linking to connection(id)."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS domain (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain_code TEXT NOT NULL UNIQUE,
        domain_name TEXT NOT NULL,
        domain_desc TEXT,
        connection_id INTEGER,
        version_id INTEGER,
        display_order INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (connection_id) REFERENCES connection(id),
        FOREIGN KEY (version_id) REFERENCES version(id)
    );
    """)
    _migrate_domain_table(conn_sqlite)
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_domain_connection_id ON domain(connection_id);")
    conn_sqlite.commit()


def ensure_module_table(conn_sqlite) -> None:
    """Create the module table following the standard entity domain, linking to domain(id)."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS module (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        module_code TEXT NOT NULL UNIQUE,
        module_name TEXT NOT NULL,
        module_desc TEXT,
        repo_name TEXT,
        schema VARCHAR(30) UNIQUE,
        domain_id INTEGER,
        version_id INTEGER,
        display_order INTEGER NOT NULL DEFAULT 0,
        is_active INTEGER NOT NULL DEFAULT 1,
        parent_module_id INTEGER,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (domain_id) REFERENCES domain(id),
        FOREIGN KEY (version_id) REFERENCES version(id),
        FOREIGN KEY (parent_module_id) REFERENCES module(id)
    );
    """)
    _ensure_module_columns(conn_sqlite)
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_module_domain_id ON module(domain_id);")
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_module_parent_id ON module(parent_module_id);")
    conn_sqlite.commit()


def _ensure_module_columns(conn_sqlite) -> None:
    """Migrate module table by rebuilding so `repo_name`, `schema`, `display_order` and `parent_module_id` exist in correct position.

    SQLite ALTER TABLE ADD COLUMN cannot add a UNIQUE column, so existing DBs are rebuilt in place.
    The rebuild keeps only active (is_deleted = 0) rows, hard-deleting soft-deleted (unused) modules.
    """
    cols = [r[1] for r in conn_sqlite.execute("PRAGMA table_info(module)").fetchall()]
    if cols and "parent_module_id" in cols and "schema" in cols and "repo_name" in cols and "display_order" in cols:
        return
    cols_sql = (
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "module_code TEXT NOT NULL UNIQUE,"
        "module_name TEXT NOT NULL,"
        "module_desc TEXT,"
        "repo_name TEXT,"
        "schema VARCHAR(30) UNIQUE,"
        "domain_id INTEGER,"
        "version_id INTEGER,"
        "display_order INTEGER NOT NULL DEFAULT 0,"
        "is_active INTEGER NOT NULL DEFAULT 1,"
        "parent_module_id INTEGER,"
        "created_by TEXT,"
        "created_time TEXT NOT NULL,"
        "updated_by TEXT,"
        "updated_time TEXT NOT NULL,"
        "is_deleted INTEGER NOT NULL DEFAULT 0,"
        "deleted_by TEXT,"
        "deleted_time TEXT,"
        "FOREIGN KEY (domain_id) REFERENCES domain(id),"
        "FOREIGN KEY (version_id) REFERENCES version(id),"
        "FOREIGN KEY (parent_module_id) REFERENCES module(id)"
    )
    old_cols = ", ".join(cols) if cols else "id, module_code, module_name, module_desc, repo_name, schema, domain_id, version_id, is_active, parent_module_id, created_by, created_time, updated_by, updated_time, is_deleted, deleted_by, deleted_time"
    conn_sqlite.execute("PRAGMA foreign_keys=OFF")
    try:
        conn_sqlite.execute(f"CREATE TABLE module__new ({cols_sql})")
        conn_sqlite.execute(f"INSERT INTO module__new ({old_cols}) SELECT {old_cols} FROM module WHERE is_deleted = 0")
        conn_sqlite.commit()
        conn_sqlite.execute("DROP TABLE module")
        conn_sqlite.execute("ALTER TABLE module__new RENAME TO module")
        conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_module_domain_id ON module(domain_id);")
        conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_module_parent_id ON module(parent_module_id);")
        conn_sqlite.commit()
    finally:
        conn_sqlite.execute("PRAGMA foreign_keys=ON")


def ensure_data_type_table(conn_sqlite) -> None:
    """Create the data_type table following the standard entity domain, linking to connection(id)."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS data_type (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        data_type_code TEXT NOT NULL UNIQUE,
        data_type_name TEXT NOT NULL,
        data_type_desc TEXT,
        category TEXT,
        aliases TEXT,
        connection_id INTEGER,
        version_id INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (connection_id) REFERENCES connection(id),
        FOREIGN KEY (version_id) REFERENCES version(id)
    );
    """)
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_data_type_connection_id ON data_type(connection_id);")
    conn_sqlite.commit()


def ensure_config_table(conn_sqlite) -> None:
    """Create the config key-value table if missing and seed default naming_style_flag = 'S'."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        value TEXT NOT NULL,
        desc TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_time TEXT NOT NULL,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0
    );
    """)
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur = conn_sqlite.cursor()
    cur.execute("SELECT id FROM config WHERE key = 'naming_style_flag' AND is_deleted = 0")
    if not cur.fetchone():
        conn_sqlite.execute("""
            INSERT INTO config (key, value, desc, is_active, created_time, updated_time, is_deleted)
            VALUES ('naming_style_flag', 'S', 'Entity and column naming style: S (snake_case) or C (camelCase)', 1, ?, ?, 0)
        """, (now, now))
    conn_sqlite.commit()


def get_naming_style(root: Path) -> str:
    """Read naming_style_flag from config table ('S' or 'C'). Defaults to 'S'."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return "S"
    try:
        conn = sqlite3.connect(db)
        ensure_config_table(conn)
        cur = conn.cursor()
        cur.execute("SELECT value FROM config WHERE key = 'naming_style_flag' AND is_deleted = 0 LIMIT 1")
        row = cur.fetchone()
        conn.close()
        if row and row[0]:
            val = str(row[0]).strip().upper()
            return "C" if val == "C" else "S"
    except Exception:
        pass
    return "S"


def set_naming_style(root: Path, flag: str) -> None:
    """Set naming_style_flag in config table ('S' or 'C')."""
    import sqlite3
    import datetime
    clean_flag = str(flag).strip().upper()
    if clean_flag not in ("S", "C"):
        sys.exit(f"error: invalid naming style flag '{flag}'. Expected 'S' (snake_case) or 'C' (camelCase).")
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not found at {db}")
    conn = sqlite3.connect(db)
    ensure_config_table(conn)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur = conn.cursor()
    cur.execute("SELECT id FROM config WHERE key = 'naming_style_flag' AND is_deleted = 0")
    row = cur.fetchone()
    if row:
        conn.execute("UPDATE config SET value = ?, updated_time = ? WHERE id = ?", (clean_flag, now, row[0]))
    else:
        conn.execute("""
            INSERT INTO config (key, value, desc, is_active, created_time, updated_time, is_deleted)
            VALUES ('naming_style_flag', ?, 'Entity and column naming style: S (snake_case) or C (camelCase)', 1, ?, ?, 0)
        """, (clean_flag, now, now))
    conn.commit()
    conn.close()


def ensure_version_table(conn_sqlite) -> None:
    """Create the version table following the standard entity domain. Single active row via unique partial index."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS version (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version_code TEXT NOT NULL UNIQUE,
        version_name TEXT NOT NULL,
        version_desc TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT
    );
    """)
    conn_sqlite.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_version_active
        ON version(is_active) WHERE is_active = 1
    """)
    conn_sqlite.commit()


def ensure_version_history_table(conn_sqlite) -> None:
    """Create the version_history table for auditing EDM changes."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS version_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        version_id INTEGER NOT NULL,
        table_name TEXT NOT NULL,
        record_id INTEGER NOT NULL,
        change_type_flag TEXT NOT NULL,
        change_detail_desc TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (version_id) REFERENCES version(id)
    );
    """)
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ix_vh_version ON version_history(version_id);")
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ix_vh_target ON version_history(table_name, record_id);")
    conn_sqlite.commit()


def _ensure_template_table(conn_sqlite, table: str, code_col: str) -> None:
    conn_sqlite.execute(f"""
    CREATE TABLE IF NOT EXISTS {table} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {code_col} TEXT NOT NULL UNIQUE,
        {table.replace('_domain', '_domain')}_name TEXT NOT NULL,
        template_desc TEXT,
        columns_json TEXT,
        fks_json TEXT,
        version_id INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (version_id) REFERENCES version(id)
    );
    """)
    conn_sqlite.commit()


def ensure_entity_domain_table(conn_sqlite) -> None:
    """Create the entity_domain template table (standard entity domain)."""
    _ensure_template_table(conn_sqlite, "entity_domain", "entity_domain_code")


def ensure_column_domain_table(conn_sqlite) -> None:
    """Create the column_domain template table."""
    _ensure_template_table(conn_sqlite, "column_domain", "column_domain_code")
    try:
        conn_sqlite.execute("ALTER TABLE column_domain ADD COLUMN data_type TEXT")
        conn_sqlite.commit()
    except Exception:
        pass


def ensure_entity_table(conn_sqlite) -> None:
    """Create the entity table following the standard entity domain, linking to module(id)."""
    conn_sqlite.execute("""
    CREATE TABLE IF NOT EXISTS entity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        entity_code TEXT NOT NULL,
        entity_name TEXT NOT NULL,
        entity_desc TEXT,
        module_id INTEGER NOT NULL,
        schema VARCHAR(30),
        columns_json TEXT,
        fks_json TEXT,
        entity_domains_json TEXT,
        column_domains_json TEXT,
        version_id INTEGER,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_by TEXT,
        created_time TEXT NOT NULL,
        updated_by TEXT,
        updated_time TEXT NOT NULL,
        is_deleted INTEGER NOT NULL DEFAULT 0,
        deleted_by TEXT,
        deleted_time TEXT,
        FOREIGN KEY (module_id) REFERENCES module(id),
        FOREIGN KEY (version_id) REFERENCES version(id),
        UNIQUE (module_id, entity_code)
    );
    """)
    # Migration for existing corpora: add entity-level schema override column.
    try:
        conn_sqlite.execute("ALTER TABLE entity ADD COLUMN schema VARCHAR(30)")
    except Exception:
        pass
    _reorder_entity_schema_after_module_id(conn_sqlite)
    conn_sqlite.execute("CREATE INDEX IF NOT EXISTS ux_entity_module_id ON entity(module_id);")
    conn_sqlite.commit()


def _reorder_entity_schema_after_module_id(conn_sqlite) -> None:
    """Rebuild the entity table so `schema` sits right after `module_id`.

    SQLite has no column-reorder; when the lazy ALTER appended `schema` at the end
    we recreate the table with the canonical order and copy rows across. No-op when
    the column is already in the desired position (fresh `init` corpora).
    """
    cols = [r[1] for r in conn_sqlite.execute("PRAGMA table_info(entity)").fetchall()]
    try:
        schema_idx = cols.index("schema")
    except ValueError:
        return
    if schema_idx == cols.index("module_id") + 1:
        return
    cols.remove("schema")
    mod_idx = cols.index("module_id") + 1
    cols.insert(mod_idx, "schema")
    col_list = ", ".join(cols)
    tmp = "_entity_reorder_tmp"
    conn_sqlite.executescript(f"""
        DROP TABLE IF EXISTS {tmp};
        CREATE TABLE {tmp} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_code TEXT NOT NULL,
            entity_name TEXT NOT NULL,
            entity_desc TEXT,
            module_id INTEGER NOT NULL,
            schema VARCHAR(30),
            columns_json TEXT,
            fks_json TEXT,
            entity_domains_json TEXT,
            column_domains_json TEXT,
            version_id INTEGER,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_by TEXT,
            created_time TEXT NOT NULL,
            updated_by TEXT,
            updated_time TEXT NOT NULL,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            deleted_by TEXT,
            deleted_time TEXT,
            FOREIGN KEY (module_id) REFERENCES module(id),
            FOREIGN KEY (version_id) REFERENCES version(id),
            UNIQUE (module_id, entity_code)
        );
        INSERT INTO {tmp} ({col_list}) SELECT {col_list} FROM entity;
        DROP TABLE entity;
        ALTER TABLE {tmp} RENAME TO entity;
    """)
    conn_sqlite.commit()


def _ensure_version_id_columns(conn_sqlite) -> None:
    """Ensure version_id column exists on all 7 EDM tables and backfill missing values with active version id."""
    tables = ("connection", "domain", "module", "data_type", "entity_domain", "column_domain", "entity")
    cur = conn_sqlite.cursor()
    ensure_version_table(conn_sqlite)
    cur.execute("SELECT id FROM version WHERE is_active = 1 AND is_deleted = 0 LIMIT 1")
    v_row = cur.fetchone()
    active_vid = v_row[0] if v_row else None

    for tbl in tables:
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({tbl})").fetchall()]
        if cols and "version_id" not in cols:
            cur.execute(f"ALTER TABLE {tbl} ADD COLUMN version_id INTEGER REFERENCES version(id)")
        if active_vid is not None and cols:
            cur.execute(f"UPDATE {tbl} SET version_id = ? WHERE version_id IS NULL", (active_vid,))
    conn_sqlite.commit()


def get_active_version_id(conn_sqlite) -> Optional[int]:
    """Return the active version id from SQLite version table."""
    _ensure_version_id_columns(conn_sqlite)
    cur = conn_sqlite.cursor()
    ensure_version_table(conn_sqlite)
    cur.execute("SELECT id FROM version WHERE is_active = 1 AND is_deleted = 0 LIMIT 1")
    row = cur.fetchone()
    return row[0] if row else None


def record_change(conn_sqlite, table_name: str, record_id: int,
                  change_type_flag: str, change_detail_desc: str = "") -> None:
    """Audit a change in version_history table."""
    import datetime
    ensure_version_history_table(conn_sqlite)
    v_id = get_active_version_id(conn_sqlite)
    if v_id is None:
        v_id = 1
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sqlite.execute("""
        INSERT INTO version_history (
            version_id, table_name, record_id, change_type_flag,
            change_detail_desc, is_active, created_time, updated_time, is_deleted
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, 0)
    """, (v_id, table_name[:30], record_id, change_type_flag[:1], (change_detail_desc or "")[:4000], now, now))


def _resolve_connection_id(root: Path, conn_ref: Optional[str]) -> Optional[int]:
    """Resolve a connection id or code to the integer id in the connection table."""
    import sqlite3
    if not conn_ref or not str(conn_ref).strip():
        return None
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    ensure_connection_table(conn_sql)
    cur = conn_sql.cursor()
    ref = str(conn_ref).strip()
    if ref.isdigit():
        cur.execute("SELECT id FROM connection WHERE id = ? AND is_deleted = 0", (int(ref),))
        row = cur.fetchone()
        if row:
            conn_sql.close()
            return row[0]
    cur.execute("SELECT id FROM connection WHERE connection_code = ? AND is_deleted = 0", (ref,))
    row = cur.fetchone()
    conn_sql.close()
    return row[0] if row else None


def _fetch_domain_row(root: Path, code: str) -> Optional[dict]:
    """Fetch a non-deleted domain row from SQLite, joining connection metadata."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_domain_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT d.*, c.connection_code, c.connection_name, c.connection_type_flag
        FROM domain d
        LEFT JOIN connection c ON d.connection_id = c.id
        WHERE d.domain_code = ? AND d.is_deleted = 0
    """, (code.strip(),))
    row = cur.fetchone()
    conn_sql.close()
    return dict(row) if row else None


def _fetch_domain_id(root: Path, code: str) -> Optional[int]:
    """Resolve a domain code or name to the integer domain id."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    ensure_domain_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT id FROM domain
        WHERE (domain_code = ? OR domain_name = ?) AND is_deleted = 0
    """, (code.strip(), code.strip()))
    row = cur.fetchone()
    conn_sql.close()
    return row[0] if row else None


def _fetch_module_row(root: Path, code: str) -> Optional[dict]:
    """Fetch a non-deleted module row from SQLite, joining domain metadata."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_module_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT m.*, d.domain_code, d.domain_name
        FROM module m
        LEFT JOIN domain d ON m.domain_id = d.id
        WHERE m.module_code = ? AND m.is_deleted = 0
    """, (code.strip(),))
    row = cur.fetchone()
    conn_sql.close()
    return dict(row) if row else None


def _fetch_data_type_row(root: Path, code: str) -> Optional[dict]:
    """Fetch a non-deleted data_type row from SQLite, joining connection metadata."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_data_type_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT t.*, c.connection_code, c.connection_name
        FROM data_type t
        LEFT JOIN connection c ON t.connection_id = c.id
        WHERE t.data_type_code = ? AND t.is_deleted = 0
    """, (code.strip().lower(),))
    row = cur.fetchone()
    conn_sql.close()
    return dict(row) if row else None


def domain_dir(root: Path, domain: str) -> Path:
    return edm_dir(root) / domain


def module_dir(root: Path, domain: str, module: str) -> Path:
    return domain_dir(root, domain) / module


def ddl_dir(root: Path, version: str) -> Path:
    """Central, versioned DDL output dir: .edm/ddl/<version>."""
    return edm_dir(root) / "ddl" / version


def entities_dir(root: Path, domain: str, module: str) -> Path:
    return module_dir(root, domain, module) / "entities"


def entity_domain_dir(root: Path) -> Path:
    return edm_dir(root) / "entity-domain"


def column_domain_dir(root: Path) -> Path:
    return edm_dir(root) / "column-domain"



def domain_index(root: Path, domain: str) -> Path:
    return domain_dir(root, domain) / f"_{domain}_index.md"


def module_index(root: Path, domain: str, module: str) -> Path:
    return module_dir(root, domain, module) / f"_{module}_index.md"


def global_index(root: Path) -> Path:
    return edm_dir(root) / "_index.md"


def entity_md(root: Path, domain: str, module: str, entity: str) -> Path:
    return entities_dir(root, domain, module) / f"{entity}.md"


def entity_aml(root: Path, domain: str, module: str, entity: str) -> Path:
    return entities_dir(root, domain, module) / f"{entity}.aml"


def domains_registry(root: Path) -> Path:
    return edm_dir(root) / "_domains.md"


def modules_registry(root: Path, domain: str) -> Path:
    return domain_dir(root, domain) / "_modules.md"


# --------------------------------------------------------------- registry table helpers

def read_registry_table(path: Path) -> tuple[dict, list[dict[str, str]]]:
    """Parse a registry markdown file (frontmatter + | Code | Name | Description | table)."""
    if not path.exists():
        return {}, []
    fm, body = read_frontmatter(path)
    rows = []
    headers = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|") or not line.endswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if not cells or all(re.match(r"^[-: ]+$", c) for c in cells):
            continue
        if not headers:
            headers = [c.lower() for c in cells]
            continue
        row = {}
        for idx, h in enumerate(headers):
            row[h] = cells[idx] if idx < len(cells) else ""
        if row.get("code"):
            rows.append(row)
    return fm, rows


def write_registry_table(path: Path, title: str, rows: list[dict[str, str]]) -> None:
    """Write frontmatter + markdown table (| Code | Name | Description |)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fm = {
        "title": title,
        "type": "registry",
        "status": "active",
    }
    lines = [
        f"# {title}\n",
        "| Code | Name | Description |",
        "|------|------|-------------|",
    ]
    for r in sorted(rows, key=lambda x: x.get("code", "").lower()):
        c = r.get("code", "")
        n = r.get("name", "")
        d = r.get("description", "")
        lines.append(f"| {c} | {n} | {d} |")
    body = "\n".join(lines) + "\n"
    write_md(path, fm, body)


def find_global_module_code(root: Path, code: str) -> Optional[str]:
    """Check if module code exists globally in SQLite module table. Returns domain name if found."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    ensure_module_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT COALESCE(d.domain_name, d.domain_code, '')
        FROM module m
        LEFT JOIN domain d ON m.domain_id = d.id
        WHERE m.module_code = ? AND m.is_deleted = 0
    """, (code.strip(),))
    row = cur.fetchone()
    conn_sql.close()
    return row[0] if row else None


# --------------------------------------------------------------- md helpers

def read_frontmatter(path: Path) -> tuple[dict, str]:
    """Split markdown into (frontmatter dict, body)."""
    if not path.exists():
        return {}, ""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError:
        return {}, text
    if not isinstance(fm, dict):
        fm = {}
    return fm, m.group(2)


def write_md(path: Path, fm: dict, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_text = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True)
    path.write_text(f"---\n{yaml_text}---\n{body}", encoding="utf-8")


def parse_columns(body: str) -> tuple[list[dict], list[dict]]:
    """Parse ## Columns + ## Foreign Keys sections from entity .md body."""
    columns, fks = [], []
    in_col, in_fk = False, False
    for line in body.splitlines():
        if line.startswith("## "):
            in_col = line.startswith("## Columns")
            in_fk = line.startswith("## Foreign Keys")
            continue
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        header = cells[0].lower() if cells else ""
        if not in_col and not in_fk:
            continue
        if header in ("column", "column name", "fk name", "fk"):
            continue
        if re.match(r"^[-: ]+$", cells[0]) and all(re.match(r"^[-: ]+$", c) for c in cells):
            continue
        if len(cells) < 2:
            continue
        if in_col:
            columns.append({
                "name": cells[0],
                "type": cells[1],
                "pk": cells[2].lower() == "yes" if len(cells) > 2 else False,
                "nullable": cells[3].lower() == "yes" if len(cells) > 3 else False,
                "default": cells[4] if len(cells) > 4 else "",
                "description": cells[5] if len(cells) > 5 else "",
                "unique": cells[6].lower() == "yes" if len(cells) > 6 else False,
            })
        elif in_fk:
            fks.append({
                "name": cells[0],
                "column": cells[1],
                "ref_entity": cells[2],
                "ref_column": cells[3],
            })
    return columns, fks


def render_columns(columns: list[dict], sources: dict = None) -> str:
    if not columns:
        return "_No columns defined._"
    sources = sources or {}
    # Column | Type | PK | Nullable | Default | Description | Source
    lines = ["| Column | Type | PK | Nullable | Default | Description | Unique | Source |",
             "|--------|------|----|----------|---------|-------------|--------|--------|"]
    for c in columns:
        source = sources.get(c["name"], "direct")
        lines.append(f'| {c["name"]} | {c["type"]} | '
                     f'{"Yes" if c["pk"] else ""} | {"Yes" if c["nullable"] else ""} | '
                     f'{c["default"]} | {c["description"]} | {"Yes" if c.get("unique") else ""} | {source} |')
    return "\n".join(lines)


def render_fks(fks: list[dict]) -> str:
    if not fks:
        return "_No foreign keys._"
    lines = ["| FK Name | Column | References Entity | References Column |",
             "|---------|--------|--------------------|--------------------|"]
    for f in fks:
        lines.append(f'| {f["name"]} | {f["column"]} | {f["ref_entity"]} | {f["ref_column"]} |')
    return "\n".join(lines)


# ------------------------------------------------------------ aml generator

def to_aml(name: str, columns: list[dict], fks: list[dict]) -> str:
    lines = [name]
    fk_by_col = {f["column"]: f for f in fks}
    for c in columns:
        parts = [c["name"]]
        if c["type"]:
            parts.append(c["type"])
        if c["pk"]:
            parts.append("pk")
        if c["nullable"]:
            parts.append("nullable")
        if c.get("unique"):
            parts.append("unique")
        if c["default"]:
            parts.append(f"={c['default']}")
        if c["name"] in fk_by_col:
            f = fk_by_col[c["name"]]
            parts.append(f"-> {f['ref_entity']}({f['ref_column']})")
        lines.append("  " + " ".join(parts))
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------- mermaid generator

def to_mermaid(name: str, columns: list[dict], fks: list[dict]) -> str:
    """Render an entity as a Mermaid classDiagram block."""
    lines = ["classDiagram", f"    class {name} {{"]
    for c in columns:
        pk = "PK " if c["pk"] else ""
        lines.append(f"        {pk}{c['name']} : {c['type']}")
    lines.append("    }")
    for f in fks:
        lines.append(f"    {f['ref_entity']} \"{f['name']}\" --> {name} : \"{f['column']}\"")
    return "\n".join(lines)


# --------------------------------------------------------------- DDL helpers

def sql_type_to_placeholder(t: str) -> str:
    t = t.lower().strip()
    if "int" in t or "number" in t or "bigint" in t:
        return "123"
    if "uuid" in t:
        return "uuid_generate_v7()"
    if "timestamp" in t or "datetime" in t or "date" in t:
        return "now()"
    if "boolean" in t:
        return "false"
    if "json" in t:
        return "'{}'"
    if "text" in t or "varchar" in t or "char" in t or "string" in t:
        import re
        m = re.search(r'\((\d+)\)', t)
        if m:
            length = int(m.group(1))
            val = "Sample Text"[:length]
            return f"'{val}'"
        return "'Sample Text'"
    if "decimal" in t or "float" in t or "double" in t or "numeric" in t:
        return "0.00"
    return "'sample'"


def generate_ddl(name: str, columns: list[dict], fks: list[dict], db: str, schema: str, root: Optional[Path] = None) -> str:
    """Generate PostgreSQL DDL from AML entity representation."""
    lines = [
        f"-- {name} DDL",
        f"-- database: {db}",
        f"-- schema: {schema}",
        "",
    ]
    col_defs = []
    for c in columns:
        pk = " PRIMARY KEY" if c["pk"] else ""
        null = "" if c["pk"] else (" NULL" if c["nullable"] else " NOT NULL")
        if c["default"]:
            default = f" DEFAULT {c['default']}"
        elif c["pk"] and "uuid" in c["type"].lower():
            default = " DEFAULT uuid_generate_v7()"
        else:
            default = ""
        col_defs.append(f'    "{c["name"]}" {c["type"]}{pk}{null}{default}')
    if fks:
        for f in fks:
            target_ent = f["ref_entity"]
            ref_schema = schema
            if root:
                import sqlite3
                p_db = edm_db_path(root)
                if p_db.exists():
                    try:
                        c_sql = sqlite3.connect(p_db)
                        cur = c_sql.cursor()
                        cur.execute('''
                            SELECT m.schema, m.module_code FROM entity e
                            JOIN module m ON e.module_id = m.id
                            WHERE (e.entity_code = ? OR e.entity_name = ?) AND e.is_deleted = 0
                            LIMIT 1
                        ''', (target_ent, target_ent))
                        r_target = cur.fetchone()
                        c_sql.close()
                        if r_target:
                            ref_schema = r_target[0] or (r_target[1].lower() if r_target[1] else schema)
                    except Exception:
                        pass
            col_defs.append(f'    CONSTRAINT "{f["name"]}" FOREIGN KEY ("{f["column"]}") REFERENCES "{ref_schema}"."{target_ent}"("{f["ref_column"]}")')
    for c in columns:
        if c.get("unique"):
            col_defs.append(f'    CONSTRAINT "ux_{name}_{c["name"]}" UNIQUE ("{c["name"]}")')
    lines.append(f'CREATE TABLE "{schema}"."{name}" (')
    lines.append(",\n".join(col_defs))
    lines.append(");")
    return "\n".join(lines)


def generate_samples(name: str, columns: list[dict], db: str, schema: str) -> str:
    """Generate sample INSERT statements for a table."""
    if not columns:
        return ""
    cols_no_pk = [c["name"] for c in columns if not c["pk"]]
    col_defs = ", ".join(f'"{c}"' for c in cols_no_pk)
    vals = ", ".join(sql_type_to_placeholder(c["type"]) for c in columns if c["name"] in cols_no_pk)
    return f'INSERT INTO "{schema}"."{name}" ({col_defs}) VALUES ({vals});'


# ------------------------------------------------------- entity-domain template helpers

def read_template(name: str, tmpl_dir: Path) -> tuple[dict, list[dict], list[dict]]:
    """Read template .md (legacy fallback), return (frontmatter, columns, fks)."""
    p = tmpl_dir / f"{name}.md"
    if not p.exists():
        sys.exit(f"error: template '{name}' not found in {tmpl_dir}")
    fm, body = read_frontmatter(p)
    cols, fks = parse_columns(body)
    return fm, cols, fks


def _fetch_template_row(root: Path, code: str, tmpl_type: str) -> Optional[dict]:
    """Fetch a non-deleted template row from SQLite entity_domain/column_domain table."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    table = "entity_domain" if tmpl_type == "entity-domain" else "column_domain"
    code_col = f"{table}_code"
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    if tmpl_type == "entity-domain":
        ensure_entity_domain_table(conn_sql)
    else:
        ensure_column_domain_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute(f"SELECT * FROM {table} WHERE {code_col} = ? AND is_deleted = 0", (code,))
    row = cur.fetchone()
    conn_sql.close()
    return dict(row) if row else None


def load_template_def(root: Path, tmpl_type: str, name: str) -> tuple[dict, list[dict], list[dict]]:
    """Load template definition (frontmatter, columns, fks). SQLite first, legacy file fallback."""
    table = "entity_domain" if tmpl_type == "entity-domain" else "column_domain"
    name_col = f"{table}_name"
    row = _fetch_template_row(root, name, tmpl_type)
    if row is not None:
        fm = {"title": row[name_col], "name": name, "type": tmpl_type,
              "entity": name, "description": row.get("template_desc") or "",
              "data_type": row.get("data_type") or ""}
        try:
            cols = json.loads(row.get("columns_json") or "[]")
        except Exception:
            cols = []
        if not fm["data_type"] and cols and isinstance(cols, list) and "type" in cols[0]:
            fm["data_type"] = cols[0]["type"]
        try:
            fks = json.loads(row.get("fks_json") or "[]")
        except Exception:
            fks = []
        return fm, cols, fks
    t_dir = entity_domain_dir(root) if tmpl_type == "entity-domain" else column_domain_dir(root)
    return read_template(name, t_dir)


def _resolve_module_id(root: Path, domain: str, module: str) -> Optional[int]:
    """Resolve domain and module name/code to module id in SQLite."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    ensure_domain_table(conn_sql)
    ensure_module_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT m.id
        FROM module m
        JOIN domain d ON m.domain_id = d.id
        WHERE (d.domain_code = ? OR d.domain_name = ?)
          AND (m.module_code = ? OR m.module_name = ?)
          AND m.is_deleted = 0 AND d.is_deleted = 0
    """, (domain.strip(), domain.strip(), module.strip(), module.strip()))
    row = cur.fetchone()
    conn_sql.close()
    return row[0] if row else None


def _fetch_entity_row(root: Path, domain: str, module: str, entity: str) -> Optional[dict]:
    """Fetch an entity row joining module and domain metadata."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_entity_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT e.*, m.module_code, m.module_name, m.schema AS module_schema,
               d.domain_code, d.domain_name,
               c.connection_code AS database_name
        FROM entity e
        JOIN module m ON e.module_id = m.id
        JOIN domain d ON m.domain_id = d.id
        LEFT JOIN connection c ON d.connection_id = c.id
        WHERE (d.domain_code = ? OR d.domain_name = ?)
          AND (m.module_code = ? OR m.module_name = ?)
          AND (e.entity_code = ? OR e.entity_name = ?)
          AND e.is_deleted = 0 AND m.is_deleted = 0 AND d.is_deleted = 0
    """, (domain.strip(), domain.strip(), module.strip(), module.strip(), entity.strip(), entity.strip()))
    row = cur.fetchone()
    conn_sql.close()
    return dict(row) if row else None


def _fetch_module_by_id(root: Path, mid: int) -> Optional[dict]:
    """Fetch a non-deleted module row (with domain metadata) by primary key."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_module_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT m.*, d.domain_code, d.domain_name
        FROM module m
        LEFT JOIN domain d ON m.domain_id = d.id
        WHERE m.id = ? AND m.is_deleted = 0
    """, (mid,))
    row = cur.fetchone()
    conn_sql.close()
    return dict(row) if row else None


def resolve_scope_meta(root: Path, domain: str, module: str) -> tuple[str, str]:
    """Resolve (database, schema) for a domain/module straight from SQLite.

    database := connection code linked to the domain ('' if unlinked);
    schema    := module.schema, falling back to LOWER(module_code).
    """
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    conn_sql = sqlite3.connect(db)
    ensure_module_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("""
        SELECT COALESCE(c.connection_code, '') AS database_name,
               COALESCE(m.schema, LOWER(m.module_code)) AS schema_name
        FROM module m
        JOIN domain d ON m.domain_id = d.id
        LEFT JOIN connection c ON d.connection_id = c.id
        WHERE (d.domain_code = ? OR d.domain_name = ?)
          AND (m.module_code = ? OR m.module_name = ?)
          AND m.is_deleted = 0 AND d.is_deleted = 0
    """, (domain.strip(), domain.strip(), module.strip(), module.strip()))
    row = cur.fetchone()
    conn_sql.close()
    if row is None:
        sys.exit(f"error: module '{module}' not found under domain '{domain}'")
    return str(row[0]), str(row[1])


def load_entity_def(root: Path, domain: str, module: str, entity: str) -> tuple[dict, list[dict], list[dict], dict]:
    """Load entity definition: (fm, columns, fks, sources). SQLite first, fallback to markdown."""
    row = _fetch_entity_row(root, domain, module, entity)
    if row is not None:
        try:
            cols = json.loads(row.get("columns_json") or "[]")
        except Exception:
            cols = []
        try:
            fks = json.loads(row.get("fks_json") or "[]")
        except Exception:
            fks = []
        try:
            ed_list = json.loads(row.get("entity_domains_json") or "[]")
        except Exception:
            ed_list = []
        try:
            cd_list = json.loads(row.get("column_domains_json") or "[]")
        except Exception:
            cd_list = []

        entity_schema = (row.get("schema") or "").strip()
        fm = {
            "title": row["entity_name"],
            "entity": row["entity_code"],
            "domain": row["domain_code"],
            "module": row["module_code"],
            "domain_name": row.get("domain_name") or row["domain_code"],
            "module_name": row.get("module_name") or row["module_code"],
            "database": row.get("database_name") or "",
            "schema": entity_schema or ((row.get("module_schema") or "").strip()
                                         or (row["module_code"] or "").lower()),
            "description": row.get("entity_desc") or "",
            "entity-domains": ed_list,
            "column-domains": cd_list,
        }
        sources = {}
        for r in ed_list:
            rname = r.get("name") or str(r)
            for c in r.get("columns", []):
                sources[c] = f"entity-domain:{rname}"
        for r in cd_list:
            rname = r.get("name") or str(r)
            for c in r.get("columns", []):
                sources[c] = f"column-domain:{rname}"
        return fm, cols, fks, sources

    # Legacy file fallback
    md = entity_md(root, domain, module, entity)
    if not md.exists():
        sys.exit(f"error: entity '{entity}' not found in {domain}/{module}")
    fm, body = read_frontmatter(md)
    cols, fks = parse_columns(body)
    sources = build_column_sources(fm)
    return fm, cols, fks, sources


def _get_entities_in_scope(root: Path, domain: Optional[str] = None, module: Optional[str] = None) -> list[dict]:
    """Return all non-deleted entities in scope joining module, domain, and connection."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return []
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_entity_table(conn_sql)
    where = ["e.is_deleted = 0", "m.is_deleted = 0", "d.is_deleted = 0"]
    params = []
    if domain:
        where.append("(d.domain_code = ? OR d.domain_name = ?)")
        params.extend([domain, domain])
    if module:
        where.append("(m.module_code = ? OR m.module_name = ?)")
        params.extend([module, module])
    query = f"""
        SELECT e.*, m.module_code, m.module_name, d.domain_code, d.domain_name,
               COALESCE(e.schema, m.schema, LOWER(m.module_code)) AS schema_name,
               COALESCE(c.connection_code, '') AS database_name
        FROM entity e
        JOIN module m ON e.module_id = m.id
        JOIN domain d ON m.domain_id = d.id
        LEFT JOIN connection c ON d.connection_id = c.id
        WHERE {' AND '.join(where)}
        ORDER BY d.domain_code, m.module_code, e.entity_code
    """
    rows = [dict(r) for r in conn_sql.execute(query, params).fetchall()]
    conn_sql.close()
    for r in rows:
        try:
            r["columns"] = json.loads(r.get("columns_json") or "[]")
        except Exception:
            r["columns"] = []
        try:
            r["fks"] = json.loads(r.get("fks_json") or "[]")
        except Exception:
            r["fks"] = []
    return rows


def _get_entity_code_index(root: Path) -> dict:
    """Map entity code -> candidate FK targets with their effective schema.

    Foreign keys store the target entity code only, so publishing needs a global
    index to place a relation in the target's own schema instead of the source's.
    """
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return {}
    conn_sql = sqlite3.connect(db)
    conn_sql.row_factory = sqlite3.Row
    ensure_entity_table(conn_sql)
    modules = {r["id"]: dict(r) for r in conn_sql.execute(
        """SELECT m.id, m.module_code, m.schema, m.parent_module_id, m.is_deleted,
                  d.domain_code
           FROM module m LEFT JOIN domain d ON m.domain_id = d.id""").fetchall()}
    rows = conn_sql.execute(
        "SELECT entity_code, schema AS entity_schema, module_id FROM entity WHERE is_deleted = 0"
    ).fetchall()
    conn_sql.close()

    def _is_lakehouse(module_id) -> bool:
        guard = 0
        while module_id is not None and guard < 32:
            mod = modules.get(module_id)
            if mod is None:
                return False
            if (mod.get("module_code") or "") == "DL":
                return True
            module_id = mod.get("parent_module_id")
            guard += 1
        return False

    index: dict = {}
    for r in rows:
        mod = modules.get(r["module_id"]) or {}
        if mod.get("is_deleted"):
            continue
        schema = ((r["entity_schema"] or "").strip()
                  or (mod.get("schema") or "").strip()
                  or (mod.get("module_code") or "").lower())
        index.setdefault(r["entity_code"], []).append({
            "schema": schema,
            "module_code": mod.get("module_code") or "",
            "domain_code": mod.get("domain_code") or "",
            "is_lakehouse": _is_lakehouse(r["module_id"]),
        })
    return index


def _resolve_ref_schema(index: dict, src_schema: str, src_domain: str, ref_code: str) -> tuple:
    """Resolve the schema of a FK target recorded by entity code only.

    Order: same schema -> unique candidate -> unique candidate in the same domain
    -> unique non-lakehouse candidate -> lowest schema name (deterministic).
    Returns (schema, rule); unknown codes fall back to the source schema.
    """
    candidates = index.get(ref_code) or []
    if not candidates:
        return src_schema, "unresolved"
    for cand in candidates:
        if cand["schema"] == src_schema:
            return src_schema, "same-schema"
    if len(candidates) == 1:
        return candidates[0]["schema"], "unique"
    same_domain = [c for c in candidates if c["domain_code"] == src_domain]
    if len(same_domain) == 1:
        return same_domain[0]["schema"], "same-domain"
    pool = [c for c in candidates if not c["is_lakehouse"]] or candidates
    if len(pool) == 1:
        return pool[0]["schema"], "non-lakehouse"
    return sorted(pool, key=lambda c: c["schema"])[0]["schema"], "tiebreak"


def _update_entity_json(root: Path, row: dict, cols: list, fks: list,
                        ed_list: list, cd_list: list, detail: str = "") -> None:
    """Persist entity columns/fks/template refs back to the SQLite entity table."""
    import sqlite3
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_entity_table(conn_sql)
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute("""
        UPDATE entity SET columns_json = ?, fks_json = ?,
            entity_domains_json = ?, column_domains_json = ?, version_id = ?, updated_time = ?
        WHERE id = ?
    """, (
        json.dumps(cols, ensure_ascii=False),
        json.dumps(fks, ensure_ascii=False),
        json.dumps(ed_list, ensure_ascii=False),
        json.dumps(cd_list, ensure_ascii=False),
        v_id, now, row["id"],
    ))
    record_change(conn_sql, "entity", row["id"], "M", detail or f"Updated entity {row.get('entity_code', '')}")
    conn_sql.commit()
    conn_sql.close()


def apply_template_to_entity(root, entity_name: str, domain: str, module: str,
                              tmpl_type: str, tmpl_name: str, target_col: Optional[str] = None) -> None:
    """Apply a template to an entity, merging columns and tracking module provenance ids."""
    import sqlite3
    import datetime
    row = _fetch_entity_row(root, domain, module, entity_name)
    if row is None:
        sys.exit(f"error: entity {entity_name} not found in {domain}/{module}")
    try:
        cols = json.loads(row.get("columns_json") or "[]")
    except Exception:
        cols = []
    try:
        fks = json.loads(row.get("fks_json") or "[]")
    except Exception:
        fks = []
    try:
        ed_list = json.loads(row.get("entity_domains_json") or "[]")
    except Exception:
        ed_list = []
    try:
        cd_list = json.loads(row.get("column_domains_json") or "[]")
    except Exception:
        cd_list = []

    fm, tmpl_cols, _ = load_template_def(root, tmpl_type, tmpl_name)
    tmpl_row = _fetch_template_row(root, tmpl_name, tmpl_type)
    tmpl_entity_id = tmpl_row.get("id") if tmpl_row and tmpl_type == "entity-domain" else None
    tmpl_column_id = tmpl_row.get("id") if tmpl_row and tmpl_type == "column-domain" else None

    if tmpl_type == "column-domain":
        tmpl_dt = fm.get("data_type") or (tmpl_cols[0].get("type") if tmpl_cols else "")
        applied_cols = []
        if target_col:
            found = False
            for c in cols:
                if c["name"] == target_col:
                    if tmpl_dt:
                        c["type"] = tmpl_dt
                    c["column_domain_id"] = tmpl_column_id
                    applied_cols.append(target_col)
                    found = True
                    break
            if not found:
                new_col = {"name": target_col, "type": tmpl_dt or "varchar",
                           "pk": False, "nullable": True, "default": "",
                           "description": "", "unique": False,
                           "entity_domain_id": None, "column_domain_id": tmpl_column_id}
                cols.append(new_col)
                applied_cols.append(target_col)
        existing_ref = next((r for r in cd_list if (r.get("name") if isinstance(r, dict) else r) == tmpl_name), None)
        if existing_ref:
            cur_cols = existing_ref.setdefault("columns", [])
            for ac in applied_cols:
                if ac not in cur_cols:
                    cur_cols.append(ac)
        else:
            cd_list.append({"name": tmpl_name, "column_domain_id": tmpl_column_id, "columns": applied_cols})

        _update_entity_json(root, row, cols, fks, ed_list, cd_list,
                            detail=f"Applied column-domain '{tmpl_name}' to {', '.join(applied_cols) if applied_cols else 'entity'}")
        print(f"Applied column-domain '{tmpl_name}' to {entity_name} ({domain}/{module}) "
              f"({len(applied_cols)} column(s): {', '.join(applied_cols) if applied_cols else 'none'})")
        return

    existing = {c["name"] for c in cols}
    added_cols = []
    new_cols_to_add = []
    style = get_naming_style(root)
    for tc in tmpl_cols:
        raw_name = tc.get("name", "")
        # Resolve <entity_name> placeholder honoring the configured naming style
        if "<entity_name>" in raw_name:
            suffix = raw_name.replace("<entity_name>", "").lstrip("_")
            if style == "C":
                resolved_name = to_camel_case(f"{entity_name} {suffix}")
            else:
                resolved_name = f"{to_snake_case(entity_name)}_{to_snake_case(suffix)}"
        else:
            resolved_name = format_by_naming_style(raw_name, style)

        if resolved_name in existing:
            continue
        new_col = dict(tc)
        new_col["name"] = resolved_name
        if new_col.get("description"):
            new_col["description"] = new_col["description"].replace("<entity_name>", entity_name)
        new_col.setdefault("entity_domain_id", None)
        new_col.setdefault("column_domain_id", None)
        new_col["entity_domain_id"] = tmpl_entity_id
        new_cols_to_add.append(new_col)
        added_cols.append(resolved_name)

    audit_indices = [i for i, c in enumerate(cols) if c["name"] in ("created_by", "is_deleted")]
    if audit_indices:
        insert_idx = min(audit_indices)
        for offset, nc in enumerate(new_cols_to_add):
            cols.insert(insert_idx + offset, nc)
    else:
        cols.extend(new_cols_to_add)

    existing_refs = {r.get("name") if isinstance(r, dict) else r for r in ed_list}
    if tmpl_name not in existing_refs:
        ed_list.append({"name": tmpl_name, "entity_domain_id": tmpl_entity_id, "columns": added_cols})

    _update_entity_json(root, row, cols, fks, ed_list, cd_list,
                        detail=f"Applied {tmpl_type} '{tmpl_name}'")
    print(f"Applied {tmpl_type} '{tmpl_name}' to {entity_name} ({domain}/{module}) "
          f"({len(added_cols)} column(s): {', '.join(added_cols) if added_cols else 'none-added'})")


def unapply_template_from_entity(root, entity_name: str, domain: str, module: str,
                                  tmpl_type: str, tmpl_name: str) -> None:
    """Remove a template's applied columns from an entity."""
    row = _fetch_entity_row(root, domain, module, entity_name)
    if row is None:
        sys.exit(f"error: entity {entity_name} not found in {domain}/{module}")
    try:
        cols = json.loads(row.get("columns_json") or "[]")
    except Exception:
        cols = []
    try:
        fks = json.loads(row.get("fks_json") or "[]")
    except Exception:
        fks = []
    try:
        ed_list = json.loads(row.get("entity_domains_json") or "[]")
    except Exception:
        ed_list = []
    try:
        cd_list = json.loads(row.get("column_domains_json") or "[]")
    except Exception:
        cd_list = []

    tmpl_row = _fetch_template_row(root, tmpl_name, tmpl_type)
    tmpl_id = tmpl_row.get("id") if tmpl_row else None

    if tmpl_type == "entity-domain":
        refs = ed_list
        prov_key = "entity_domain_id"
    else:
        refs = cd_list
        prov_key = "column_domain_id"

    removed_names = []
    new_refs = []
    for r in refs:
        rname = r.get("name") if isinstance(r, dict) else r
        rcols = (r.get("columns") if isinstance(r, dict) else []) if rname == tmpl_name else None
        if rname == tmpl_name and rcols:
            removed_names.extend(rcols)
        else:
            new_refs.append(r)
    if not removed_names:
        if tmpl_name in {(r.get("name") if isinstance(r, dict) else r) for r in refs}:
            print(f"template '{tmpl_name}' found entity but no columns tracked; removing ref.")
        else:
            sys.exit(f"error: template '{tmpl_name}' is not applied to {entity_name}")

    if tmpl_type == "entity-domain":
        ed_list = new_refs
    else:
        cd_list = new_refs

    rm = set(removed_names)
    filtered_cols = []
    for c in cols:
        if c["name"] in rm:
            continue
        if tmpl_id is not None and c.get(prov_key) == tmpl_id:
            continue
        filtered_cols.append(c)
    filtered_fks = [f for f in fks if f["column"] not in rm]

    _update_entity_json(root, row, filtered_cols, filtered_fks, ed_list, cd_list,
                        detail=f"Unapplied {tmpl_type} '{tmpl_name}'")
    print(f"Unapplied {tmpl_type} '{tmpl_name}' from {entity_name} ({domain}/{module}) "
          f"(removed {len(removed_names)} column(s): {', '.join(removed_names)})")


def build_column_sources(fm: dict) -> dict:
    """Map column name -> source string (template ref)."""
    sources = {}
    for list_key, prefix in (("entity-domains", "entity-domain"), ("column-domains", "column-domain")):
        refs = fm.get(list_key, []) or []
        for r in refs:
            rname = r["name"] if isinstance(r, dict) else r
            rcols = r.get("columns", []) if isinstance(r, dict) else []
            for c in rcols:
                sources[c] = f"{prefix}:{rname}"
    return sources


# ----------------------------------------------------------- rendered read

def entity_table(fm: dict, columns: list[dict], fks: list[dict], sources: dict = None) -> str:
    db = fm.get("database", "")
    schema = fm.get("schema", "")
    domain = fm.get("domain", "")
    module = fm.get("module", "")
    entity = fm.get("entity", "")
    out = [f"**{entity}**",
           "",
           f"| Database | Schema | Domain | Module | Entity |",
           f"|----------|--------|--------|--------|--------|",
           f"| {db} | {schema} | {domain} | {module} | {entity} |",
           "",
           "### Columns",
           "",
           render_columns(columns, sources),
           "",
           "### Foreign Keys",
           "",
           render_fks(fks)]
    return "\n".join(out)


def ensure_indexes(root: Path, domain: str, module: str) -> None:
    """No-op: domain/module folders are no longer created (SQLite is the source of truth)."""


# --------------------------------------------------------------- operations

def op_add_entity(root, args):
    import sqlite3
    import datetime
    module_id = _resolve_module_id(root, args.domain, args.module)
    if module_id is None:
        sys.exit(f"error: module '{args.module}' not found under domain '{args.domain}'. "
                 "Register domain/module first via register-domain / register-module.")

    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")

    style = get_naming_style(root)
    entity_code = format_by_naming_style(args.name, style)

    allowed = load_allowed_types(root)
    columns = []
    for n in args.column:
        parts = [s for s in n.split(" ") if s]
        name = format_by_naming_style(parts[0], style)
        type_str = parts[1] if len(parts) > 1 else "varchar"
        modifiers = [p.lower() for p in parts[2:]]
        is_pk = "pk" in modifiers or name == "id"
        is_nullable = "nullable" in modifiers
        is_unique = "unique" in modifiers
        is_valid, canonical = validate_column_type(type_str, allowed)
        if not is_valid:
            sys.exit(f"error: invalid PostgreSQL type '{type_str}' for column '{name}'. "
                     f"Allowed: {', '.join(sorted(allowed.values()))}")
        columns.append({"name": name, "type": canonical, "pk": is_pk,
                        "nullable": is_nullable, "default": "", "description": "",
                        "unique": is_unique,
                        "entity_domain_id": None, "column_domain_id": None})

    conn_sql = sqlite3.connect(db)
    ensure_entity_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("SELECT id FROM entity WHERE entity_code = ? AND module_id = ? AND is_deleted = 0",
                (entity_code, module_id))
    if cur.fetchone():
        conn_sql.close()
        sys.exit(f"error: entity '{entity_code}' already exists in {args.domain}/{args.module}")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sql)
    entity_schema = (getattr(args, "schema", None) or "").strip() or None
    cur.execute("""
        INSERT INTO entity (
            entity_code, entity_name, entity_desc, module_id, schema,
            columns_json, fks_json, entity_domains_json, column_domains_json,
            version_id, is_active, created_time, updated_time, is_deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
    """, (
        entity_code, entity_code, (args.description or "").strip(), module_id, entity_schema,
        json.dumps(columns, ensure_ascii=False), json.dumps([], ensure_ascii=False),
        "[]", "[]", v_id, now, now,
    ))
    rec_id = cur.lastrowid
    record_change(conn_sql, "entity", rec_id, "C", f"Added entity {entity_code} to {args.domain}/{args.module}")
    conn_sql.commit()
    conn_sql.close()
    print(f"added entity {entity_code} to {args.domain}/{args.module}")


def op_read_entity(root, args):
    fm, columns, fks, sources = load_entity_def(root, args.domain, args.module, args.name)
    print(entity_table(fm, columns, fks, sources))


def op_modify_entity(root, args):
    import sqlite3
    import datetime
    row = _fetch_entity_row(root, args.domain, args.module, args.name)
    if row is None:
        sys.exit(f"error: entity '{args.name}' not found in {args.domain}/{args.module}")
    try:
        columns = json.loads(row.get("columns_json") or "[]")
    except Exception:
        columns = []
    try:
        fks = json.loads(row.get("fks_json") or "[]")
    except Exception:
        fks = []
    try:
        ed_list = json.loads(row.get("entity_domains_json") or "[]")
    except Exception:
        ed_list = []
    try:
        cd_list = json.loads(row.get("column_domains_json") or "[]")
    except Exception:
        cd_list = []

    by_name = {c["name"]: c for c in columns}
    new_cols = []
    for spec in args.add_column:
        parts = [s for s in spec.split(" ") if s]
        name = parts[0]
        old = by_name.get(name, {})
        modifiers = [p.lower() for p in parts[2:]]
        col_obj = {
            "name": name,
            "type": parts[1] if len(parts) > 1 else "varchar",
            "pk": "pk" in modifiers or bool(old.get("pk", False)),
            "nullable": "nullable" in modifiers or bool(old.get("nullable", False)),
            "default": old.get("default", ""),
            "description": old.get("description", ""),
            "unique": "unique" in modifiers or bool(old.get("unique", False)),
            "entity_domain_id": old.get("entity_domain_id"),
            "column_domain_id": old.get("column_domain_id"),
        }
        if name in by_name:
            for i, c in enumerate(columns):
                if c["name"] == name:
                    columns[i] = col_obj
                    break
        else:
            new_cols.append(col_obj)
        by_name[name] = col_obj

    after_col = getattr(args, "after", None)
    if after_col and any(c["name"] == after_col for c in columns):
        idx = next(i for i, c in enumerate(columns) if c["name"] == after_col)
        for offset, nc in enumerate(new_cols):
            columns.insert(idx + 1 + offset, nc)
    else:
        columns.extend(new_cols)

    for name in args.drop_column:
        columns = [c for c in columns if c["name"] != name]
        if name in by_name:
            del by_name[name]
        fks = [f for f in fks if f["column"] != name]

    if args.set_type:
        col_to_set, new_type = args.set_type[0], args.set_type[1]
        for c in columns:
            if c["name"] == col_to_set:
                c["type"] = new_type
                break

    for col_spec in getattr(args, "set_col_desc", []) or []:
        cname, cdesc = col_spec[0], col_spec[1]
        for c in columns:
            if c["name"] == cname:
                c["description"] = cdesc
                break

    move_col = getattr(args, "move_col", None)
    if move_col and after_col:
        col_item = next((c for c in columns if c["name"] == move_col), None)
        if col_item and any(c["name"] == after_col for c in columns):
            columns = [c for c in columns if c["name"] != move_col]
            target_idx = next(i for i, c in enumerate(columns) if c["name"] == after_col)
            columns.insert(target_idx + 1, col_item)

    for cname in getattr(args, "set_nullable", []) or []:
        for c in columns:
            if c["name"] == cname:
                c["nullable"] = True
    for cname in getattr(args, "set_not_null", []) or []:
        for c in columns:
            if c["name"] == cname:
                c["nullable"] = False
    for cname in getattr(args, "set_unique", []) or []:
        for c in columns:
            if c["name"] == cname:
                c["unique"] = True

    for fk_spec in getattr(args, "add_fk", []) or []:
        if len(fk_spec) >= 3:
            col, ref_entity, ref_col = fk_spec[0], fk_spec[1], fk_spec[2]
            fk_name = fk_spec[3] if len(fk_spec) > 3 else f"fk_{args.name}_{ref_entity}"
            fks = [f for f in fks if f.get("name") != fk_name]
            fks.append({"name": fk_name, "column": col, "ref_entity": ref_entity, "ref_column": ref_col})
    for fk_name in getattr(args, "drop_fk", []) or []:
        fks = [f for f in fks if f.get("name") != fk_name]

    updates = ["columns_json = ?", "fks_json = ?", "version_id = ?", "updated_time = ?"]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    schema_arg = getattr(args, "schema", None)
    if schema_arg is not None:
        updates.append("schema = ?")
        params_schema = schema_arg.strip() or None
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_entity_table(conn_sql)
    v_id = get_active_version_id(conn_sql)
    params = [json.dumps(columns, ensure_ascii=False), json.dumps(fks, ensure_ascii=False), v_id, now]
    if schema_arg is not None:
        params.append(params_schema)
    if getattr(args, "description", None) is not None:
        updates.append("entity_desc = ?")
        params.append(args.description)
    conn_sql.execute(f"UPDATE entity SET {', '.join(updates)} WHERE id = ?", params + [row["id"]])
    record_change(conn_sql, "entity", row["id"], "M", f"Modified entity {args.name} in {args.domain}/{args.module}")
    conn_sql.commit()
    conn_sql.close()
    print(f"modified entity {args.name} in {args.domain}/{args.module}")


def op_delete_entity(root, args):
    import sqlite3
    import datetime
    row = _fetch_entity_row(root, args.domain, args.module, args.name)
    if row is None:
        sys.exit(f"error: entity '{args.name}' not found in {args.domain}/{args.module}")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_entity_table(conn_sql)
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute(
        "UPDATE entity SET is_deleted = 1, is_active = 0, version_id = ?, deleted_time = ? WHERE id = ?",
        (v_id, now, row["id"]))
    record_change(conn_sql, "entity", row["id"], "D", f"Soft-deleted entity {args.name}")
    conn_sql.commit()
    conn_sql.close()
    print(f"soft-deleted entity {args.name}")


def op_move_entity(root, args):
    import sqlite3
    import datetime
    row = _fetch_entity_row(root, args.from_domain, args.from_module, args.name)
    if row is None:
        sys.exit(f"error: entity '{args.name}' not found in {args.from_domain}/{args.from_module}")
    to_module_id = _resolve_module_id(root, args.to_domain, args.to_module)
    if to_module_id is None:
        sys.exit(f"error: module '{args.to_module}' not found under domain '{args.to_domain}'. "
                 "Register first via register-module.")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_entity_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("SELECT id FROM entity WHERE entity_code = ? AND module_id = ? AND is_deleted = 0",
                (args.name, to_module_id))
    if cur.fetchone():
        conn_sql.close()
        sys.exit(f"error: entity '{args.name}' already exists in {args.to_domain}/{args.to_module}")
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute(
        "UPDATE entity SET module_id = ?, version_id = ?, updated_time = ? WHERE id = ?",
        (to_module_id, v_id, now, row["id"]))
    record_change(conn_sql, "entity", row["id"], "M", f"Moved {args.name} from {args.from_domain}/{args.from_module} to {args.to_domain}/{args.to_module}")
    conn_sql.commit()
    conn_sql.close()
    print(f"moved {args.name} -> {args.to_domain}/{args.to_module}")


def op_add_domain(root, args):
    """Add a domain to the SQLite registry (no folders created)."""
    import sqlite3
    import datetime
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    code = kebab(args.name)
    name = args.title or args.name
    conn_ref = args.connection or ""
    conn_id = _resolve_connection_id(root, conn_ref) if conn_ref else None
    if conn_ref and conn_id is None:
        sys.exit(f"error: connection '{conn_ref}' does not exist in the connection table")
    conn_sql = sqlite3.connect(db)
    ensure_domain_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("SELECT id FROM domain WHERE domain_code = ? AND is_deleted = 0", (code,))
    if cur.fetchone():
        conn_sql.close()
        sys.exit(f"error: domain code '{code}' already registered; use register-domain --update")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sql)
    cur.execute("""
        INSERT INTO domain (domain_code, domain_name, domain_desc, connection_id,
                            version_id, is_active, created_time, updated_time, is_deleted)
        VALUES (?, ?, '', ?, ?, 1, ?, ?, 0)
    """, (code, name, conn_id, v_id, now, now))
    rec_id = cur.lastrowid
    record_change(conn_sql, "domain", rec_id, "C", f"Added domain {name} (code: {code})")
    conn_sql.commit()
    conn_sql.close()
    print(f"added domain {name} (code: {code}) to domain table")


def op_read_domain(root, args):
    import sqlite3
    d_row = _fetch_domain_row(root, args.name)
    if d_row is None:
        sys.exit(f"error: domain '{args.name}' does not exist")
    entities = []
    db = edm_db_path(root)
    if db.exists():
        conn_sql = sqlite3.connect(db)
        cur = conn_sql.cursor()
        cur.execute("""
            SELECT d.domain_code, m.module_code, e.entity_code
            FROM entity e
            JOIN module m ON e.module_id = m.id
            JOIN domain d ON m.domain_id = d.id
            WHERE d.id = ? AND e.is_deleted = 0 AND m.is_deleted = 0
            ORDER BY m.module_code, e.entity_code
        """, (d_row["id"],))
        entities = cur.fetchall()
        conn_sql.close()
    title = d_row["domain_name"]
    conn_code = d_row.get("connection_code") or ""
    print(f"# {title}  (conn: {conn_code})")
    print()
    print("| Domain | Module | Entity |")
    print("|--------|--------|--------|")
    for d, m, e in entities:
        print(f"| {d} | {m} | {e} |")


def op_modify_domain(root, args):
    import sqlite3
    import datetime
    row = _fetch_domain_row(root, args.name)
    if row is None:
        sys.exit(f"error: domain '{args.name}' does not exist in the domain table")
    new_code = ""
    code_arg = getattr(args, "code", None)
    if code_arg is not None:
        new_code = code_arg.strip()
        if not new_code:
            sys.exit("error: --code cannot be empty")
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", new_code):
            sys.exit("error: --code may contain only letters, digits, '-' and '_'")
        if new_code == row["domain_code"]:
            new_code = ""
    updates, params = [], []
    if new_code:
        updates.append("domain_code = ?")
        params.append(new_code)
    if getattr(args, "connection", None) is not None:
        conn_id = _resolve_connection_id(root, args.connection)
        if args.connection and conn_id is None:
            sys.exit(f"error: connection '{args.connection}' does not exist in the connection table")
        updates.append("connection_id = ?")
        params.append(conn_id)
    if getattr(args, "display_order", None) is not None:
        updates.append("display_order = ?")
        params.append(int(args.display_order))
    if getattr(args, "description", None) is not None:
        updates.append("domain_desc = ?")
        params.append(args.description)
    if getattr(args, "title", None):
        updates.append("domain_name = ?")
        params.append(args.title)
    if updates:
        conn_sql = sqlite3.connect(edm_db_path(root))
        ensure_domain_table(conn_sql)
        if new_code:
            clash = conn_sql.execute(
                "SELECT id FROM domain WHERE domain_code = ? AND is_deleted = 0", (new_code,)
            ).fetchone()
            if clash and clash[0] != row["id"]:
                conn_sql.close()
                sys.exit(f"error: domain code '{new_code}' is already in use")
        v_id = get_active_version_id(conn_sql)
        updates.append("version_id = ?")
        params.append(v_id)
        updates.append("updated_time = ?")
        params.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
        conn_sql.execute(f"UPDATE domain SET {', '.join(updates)} WHERE id = ?", params + [row["id"]])
        record_change(conn_sql, "domain", row["id"], "M", f"Modified domain {args.name}")
        conn_sql.commit()
        conn_sql.close()
    if new_code:
        print(f"modified domain {args.name} (code: {row['domain_code']} -> {new_code})")
    else:
        print(f"modified domain {args.name}")


def op_delete_domain(root, args):
    import sqlite3
    import datetime
    row = _fetch_domain_row(root, args.name)
    if row is None:
        sys.exit(f"error: domain '{args.name}' does not exist in the domain table")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_domain_table(conn_sql)
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute(
        "UPDATE domain SET is_deleted = 1, is_active = 0, version_id = ?, deleted_time = ? WHERE id = ?",
        (v_id, now, row["id"]))
    record_change(conn_sql, "domain", row["id"], "D", f"Soft-deleted domain {args.name}")
    conn_sql.commit()
    conn_sql.close()
    print(f"soft-deleted domain {args.name} (SQLite domain table)")


def op_add_module(root, args):
    """Add a module to the SQLite registry (no folders created)."""
    import sqlite3
    import datetime
    d_row = _fetch_domain_row(root, args.domain)
    if d_row is None:
        sys.exit(f"error: domain '{args.domain}' does not exist. Register it first via register-domain.")
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    code = kebab(args.name)
    name = args.title or args.name
    schema_val = (args.schema or kebab(name)).strip()
    repo_name = getattr(args, "repo_name", None)
    conn_sql = sqlite3.connect(db)
    ensure_module_table(conn_sql)
    cur = conn_sql.cursor()
    cur.execute("SELECT id FROM module WHERE module_code = ? AND is_deleted = 0", (code,))
    if cur.fetchone():
        conn_sql.close()
        sys.exit(f"error: module code '{code}' already registered; use register-module --code <c> --update")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sql)
    cur.execute("""
        INSERT INTO module (module_code, module_name, module_desc, repo_name, schema, domain_id,
                            version_id, is_active, created_time, updated_time, is_deleted)
        VALUES (?, ?, '', ?, ?, ?, ?, 1, ?, ?, 0)
    """, (code, name, repo_name, schema_val, d_row["id"], v_id, now, now))
    rec_id = cur.lastrowid
    record_change(conn_sql, "module", rec_id, "C", f"Added module {name} (code: {code})")
    conn_sql.commit()
    conn_sql.close()
    print(f"added module {name} (code: {code}) under {args.domain}")


def op_read_module(root, args):
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    module_id = _resolve_module_id(root, args.domain, args.name)
    if module_id is None:
        sys.exit(f"error: module '{args.name}' not found under domain '{args.domain}'")
    m = _fetch_module_by_id(root, module_id)
    if m is None:
        sys.exit(f"error: module '{args.name}' not found under domain '{args.domain}'")
    schema = (m.get("schema") or "").strip() or (m["module_code"] or args.name).lower()
    conn_sql = sqlite3.connect(db)
    cur = conn_sql.cursor()
    cur.execute("SELECT entity_code FROM entity WHERE module_id = ? AND is_deleted = 0 ORDER BY entity_code",
                (module_id,))
    ents = [r[0] for r in cur.fetchall()]
    conn_sql.close()
    print(f"# {m.get('module_name') or args.name}  (schema: {schema})")
    print()
    print(f"Entities: {', '.join(ents) if ents else 'none'}")


# ----------------------------------------------------------- domain & module registry

def op_register_domain(root, args):
    """Register a domain into the SQLite domain table, linking to connection(id)."""
    import sqlite3
    import datetime
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    conn_sql = sqlite3.connect(db)
    ensure_domain_table(conn_sql)

    code = args.code.strip()
    name = args.name.strip()
    desc = (args.description or "").strip()
    display_order = int(getattr(args, "display_order", 0) or 0)
    conn_ref = getattr(args, "connection", None)
    conn_id = _resolve_connection_id(root, conn_ref)
    if conn_ref and conn_id is None:
        sys.exit(f"error: connection '{conn_ref}' does not exist in the connection table")

    cur = conn_sql.cursor()
    cur.execute("SELECT id FROM domain WHERE domain_code = ? AND is_deleted = 0", (code,))
    existing = cur.fetchone()
    if existing and not getattr(args, "update", False):
        sys.exit(f"error: domain code '{code}' already registered (id {existing[0]}). Use --update to overwrite.")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sql)
    if existing:
        cur.execute("""
            UPDATE domain SET domain_name = ?, domain_desc = ?, connection_id = ?,
                display_order = ?, version_id = ?, updated_time = ? WHERE id = ?
        """, (name, desc, conn_id, display_order, v_id, now, existing[0]))
        record_change(conn_sql, "domain", existing[0], "M", f"Updated domain {name} (code: {code})")
    else:
        cur.execute("""
            INSERT INTO domain (domain_code, domain_name, domain_desc, connection_id,
                                display_order, version_id, is_active, created_time, updated_time, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (code, name, desc, conn_id, display_order, v_id, now, now))
        rec_id = cur.lastrowid
        record_change(conn_sql, "domain", rec_id, "C", f"Registered domain {name} (code: {code})")
    conn_sql.commit()
    conn_sql.close()
    print(f"registered domain '{name}' (code: {code}, connection_id: {conn_id}) in domain table")


def op_register_module(root, args):
    """Register a module into the SQLite module table, linking to domain(id)."""
    import sqlite3
    import datetime
    # Check domain exists in SQLite domain table
    d_row = _fetch_domain_row(root, args.domain)
    if d_row is None:
        sys.exit(f"error: domain '{args.domain}' does not exist. Register it first via register-domain.")
    domain_id = d_row["id"]

    code = args.code.strip()
    name = args.name.strip()
    desc = (args.description or "").strip()
    schema_val = (getattr(args, "schema", None) or kebab(name)).strip()
    repo_name = getattr(args, "repo_name", None)
    parent_ref = getattr(args, "parent_module", None)
    display_order = int(getattr(args, "display_order", 0) or 0)
    parent_id = None

    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    conn_sql = sqlite3.connect(db)
    ensure_module_table(conn_sql)
    if parent_ref and parent_ref.strip():
        p = conn_sql.execute(
            "SELECT id FROM module WHERE (module_code = ? OR module_name = ?) AND is_deleted = 0",
            (parent_ref.strip(), parent_ref.strip())).fetchone()
        if p is None:
            conn_sql.close()
            sys.exit(f"error: parent module '{parent_ref}' does not exist in the module table")
        parent_id = p[0]
        if parent_ref.strip().casefold() == code.casefold():
            conn_sql.close()
            sys.exit("error: a module cannot be its own parent")

    cur = conn_sql.cursor()
    cur.execute("SELECT id, domain_id FROM module WHERE module_code = ? AND is_deleted = 0", (code,))
    existing = cur.fetchone()
    if existing and not getattr(args, "update", False):
        cur.execute("SELECT domain_code, domain_name FROM domain WHERE id = ?", (existing[1],))
        cd = cur.fetchone()
        cd_name = cd[0] if cd else str(existing[1])
        sys.exit(f"error: module code '{code}' already registered in domain '{cd_name}' (id {existing[0]}). "
                 "Use --update to overwrite.")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sql)
    if existing:
        cur.execute("""
            UPDATE module SET module_name = ?, module_desc = ?, repo_name = ?, schema = ?, domain_id = ?,
                parent_module_id = ?, display_order = ?, version_id = ?, updated_time = ? WHERE id = ?
        """, (name, desc, repo_name, schema_val, domain_id, parent_id, display_order, v_id, now, existing[0]))
        record_change(conn_sql, "module", existing[0], "M", f"Updated module {name} (code: {code})")
    else:
        cur.execute("""
            INSERT INTO module (module_code, module_name, module_desc, repo_name, schema, domain_id,
                                parent_module_id, display_order, version_id, is_active, created_time, updated_time, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (code, name, desc, repo_name, schema_val, domain_id, parent_id, display_order, v_id, now, now))
        rec_id = cur.lastrowid
        record_change(conn_sql, "module", rec_id, "C", f"Registered module {name} (code: {code})")
    conn_sql.commit()
    conn_sql.close()
    print(f"registered module '{name}' (code: {code}, domain_id: {domain_id}) in module table")


def op_read_domains(root, args):
    """Print domains from the SQLite domain table, joined with connection metadata."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"no EDM database found at {db}")
    conn_sql = sqlite3.connect(db)
    ensure_domain_table(conn_sql)
    rows = conn_sql.execute("""
        SELECT d.domain_code, d.domain_name, d.domain_desc,
               COALESCE(c.connection_code, ''), d.display_order
        FROM domain d
        LEFT JOIN connection c ON d.connection_id = c.id
        WHERE d.is_deleted = 0
        ORDER BY d.display_order, d.domain_code
    """).fetchall()
    conn_sql.close()
    if not rows:
        print("no domains registered")
        return
    print(f"# Domains ({len(rows)} registered)")
    print()
    print("| Order | Code | Name | Description | Connection |")
    print("|-------|------|------|-------------|------------|")
    for code, nm, dsc, ccode, disp in rows:
        print(f"| {disp} | {code} | {nm} | {dsc or ''} | {ccode} |")


def op_read_modules(root, args):
    """Print modules as a hierarchical tree: each module followed by its submodules, then the next module."""
    import sqlite3
    from collections import defaultdict
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"no EDM database found at {db}")
    conn_sql = sqlite3.connect(db)
    ensure_module_table(conn_sql)
    domain_filter = getattr(args, "domain", None)
    if domain_filter:
        d_row = _fetch_domain_row(root, domain_filter)
        if not d_row:
            conn_sql.close()
            sys.exit(f"error: domain '{domain_filter}' not found")
        rows = conn_sql.execute("""
            SELECT m.module_code, m.module_name, m.module_desc,
                   COALESCE(m.repo_name, ''),
                   COALESCE(m.schema, ''),
                   COALESCE(d.domain_name, d.domain_code, ''),
                   COALESCE(c.connection_code, ''),
                   COALESCE(p.module_code, ''),
                   COALESCE(m.display_order, 0)
            FROM module m
            JOIN domain d ON m.domain_id = d.id
            LEFT JOIN connection c ON d.connection_id = c.id
            LEFT JOIN module p ON m.parent_module_id = p.id
            WHERE m.domain_id = ? AND m.is_deleted = 0
            ORDER BY m.display_order, m.module_code
        """, (d_row["id"],)).fetchall()
    else:
        rows = conn_sql.execute("""
            SELECT m.module_code, m.module_name, m.module_desc,
                   COALESCE(m.repo_name, ''),
                   COALESCE(m.schema, ''),
                   COALESCE(d.domain_name, d.domain_code, ''),
                   COALESCE(c.connection_code, ''),
                   COALESCE(p.module_code, ''),
                   COALESCE(m.display_order, 0)
            FROM module m
            JOIN domain d ON m.domain_id = d.id
            LEFT JOIN connection c ON d.connection_id = c.id
            LEFT JOIN module p ON m.parent_module_id = p.id
            WHERE m.is_deleted = 0
            ORDER BY m.display_order, m.module_code
        """).fetchall()
    conn_sql.close()
    if not rows:
        print("no modules registered")
        return

    info = {}
    parent_of = {}
    mod_order = {}
    for code, nm, dsc, repo, sc, dcode, conn_code, pid, disp in rows:
        info[code] = (nm, dsc, repo, sc, dcode, conn_code)
        parent_of[code] = pid
        mod_order[code] = disp
    children = defaultdict(list)
    roots = []
    for code in info:
        pcode = parent_of[code]
        if pcode in info:
            children[pcode].append(code)
        else:
            roots.append(code)
    for kids in children.values():
        kids.sort(key=lambda c: (mod_order.get(c, 0), c))
    roots.sort(key=lambda c: (mod_order.get(c, 0), c))

    title_suffix = f" - {domain_filter}" if domain_filter else ""
    print(f"# Modules{title_suffix} ({len(rows)} registered)")
    print()
    print("| Code | Name | Schema | Description | Domain | Connection |")
    print("|------|------|--------|-------------|--------|------------|")

    def walk(code, cont, is_last):
        nm, dsc, repo, sc, dcode, conn_code = info[code]
        if cont is None:
            lead = code
        else:
            lead = cont + ("\\-- " if is_last else "+-- ") + code
        print(f"| {lead} | {nm} | {sc or ''} | {dsc or ''} | {dcode} | {conn_code} |")
        kids = children.get(code, [])
        for i, kid in enumerate(kids):
            next_cont = "" if cont is None else (cont + ("    " if is_last else "|   "))
            walk(kid, next_cont, i == len(kids) - 1)

    for code in roots:
        walk(code, None, len(roots) == 1)


def op_modify_module(root, args):
    import sqlite3
    import datetime
    row = _fetch_module_row(root, args.name)
    domain_name = getattr(args, "domain", None)
    if not domain_name and row:
        domain_name = row.get("domain_code") or row.get("domain_name")
    if not domain_name:
        sys.exit(f"error: module '{args.name}' requires --domain or must exist in module table")

    if row:
        module_id = row["id"]
    else:
        module_id = _resolve_module_id(root, domain_name, args.name)
    if module_id is None:
        sys.exit(f"error: module '{args.name}' not found in module table")
    meta = _fetch_module_by_id(root, module_id)
    if meta is None:
        sys.exit(f"error: module '{args.name}' not found in module table")

    new_code = ""
    code_arg = getattr(args, "code", None)
    if code_arg is not None:
        new_code = code_arg.strip()
        if not new_code:
            sys.exit("error: --code cannot be empty")
        if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", new_code):
            sys.exit("error: --code may contain only letters, digits, '-' and '_'")
        if new_code == meta.get("module_code"):
            new_code = ""

    updates, params = [], []
    if new_code:
        updates.append("module_code = ?")
        params.append(new_code)
    if getattr(args, "schema", None) is not None:
        updates.append("schema = ?")
        params.append(args.schema.strip())
    if getattr(args, "repo_name", None) is not None:
        updates.append("repo_name = ?")
        params.append(args.repo_name.strip() if args.repo_name else None)
    if getattr(args, "display_order", None) is not None:
        updates.append("display_order = ?")
        params.append(int(args.display_order))
    if getattr(args, "description", None) is not None:
        updates.append("module_desc = ?")
        params.append(args.description)
    if getattr(args, "title", None):
        updates.append("module_name = ?")
        params.append(args.title)

    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_module_table(conn_sql)
    parent_ref = getattr(args, "parent_module", None)
    if parent_ref is not None:
        if parent_ref.strip() == "" or parent_ref.strip().casefold() == "none":
            updates.append("parent_module_id = ?")
            params.append(None)
        else:
            p = conn_sql.execute(
                "SELECT id FROM module WHERE (module_code = ? OR module_name = ?) AND is_deleted = 0",
                (parent_ref.strip(), parent_ref.strip())).fetchone()
            if p is None:
                conn_sql.close()
                sys.exit(f"error: parent module '{parent_ref}' does not exist in the module table")
            new_parent_id = p[0]
            if new_parent_id == module_id:
                conn_sql.close()
                sys.exit("error: a module cannot be its own parent")
            node = new_parent_id
            while node is not None:
                if node == module_id:
                    conn_sql.close()
                    sys.exit("error: parent assignment would create a cycle")
                prow = conn_sql.execute(
                    "SELECT parent_module_id FROM module WHERE id = ?", (node,)).fetchone()
                node = prow[0] if prow else None
            updates.append("parent_module_id = ?")
            params.append(new_parent_id)

    if updates:
        if new_code:
            clash = conn_sql.execute(
                "SELECT id FROM module WHERE module_code = ? AND is_deleted = 0", (new_code,)
            ).fetchone()
            if clash and clash[0] != module_id:
                conn_sql.close()
                sys.exit(f"error: module code '{new_code}' is already in use")
        v_id = get_active_version_id(conn_sql)
        updates.append("version_id = ?")
        params.append(v_id)
        updates.append("updated_time = ?")
        params.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
        conn_sql.execute(f"UPDATE module SET {', '.join(updates)} WHERE id = ?", params + [module_id])
        record_change(conn_sql, "module", module_id, "M", f"Modified module {meta.get('module_code') or args.name}")
        conn_sql.commit()
    conn_sql.close()
    if new_code:
        print(f"modified module {meta.get('module_code') or args.name} (code: {meta.get('module_code')} -> {new_code})")
    else:
        print(f"modified module {meta.get('module_code') or args.name}")


def op_delete_module(root, args):
    import sqlite3
    import datetime
    row = _fetch_module_row(root, args.name)
    domain_name = getattr(args, "domain", None)
    if not domain_name and row:
        domain_name = row.get("domain_code") or row.get("domain_name")
    if not domain_name:
        sys.exit(f"error: module '{args.name}' requires --domain or must exist in module table")

    module_id = row["id"] if row else _resolve_module_id(root, domain_name, args.name)
    if module_id is None:
        sys.exit(f"error: module '{args.name}' not found in module table")
    meta = _fetch_module_by_id(root, module_id)
    if meta is None:
        sys.exit(f"error: module '{args.name}' not found in module table")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_module_table(conn_sql)
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute(
        "UPDATE module SET is_deleted = 1, is_active = 0, version_id = ?, deleted_time = ? WHERE id = ?",
        (v_id, now, module_id))
    record_change(conn_sql, "module", module_id, "D", f"Soft-deleted module {meta.get('module_code') or args.name}")
    conn_sql.commit()
    conn_sql.close()
    print(f"soft-deleted module {meta.get('module_code') or args.name} (SQLite module table)")


def op_register_data_type(root, args):
    """Register a data type into the SQLite data_type table, linked to connection(id)."""
    import sqlite3
    import datetime
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    conn_sql = sqlite3.connect(db)
    ensure_data_type_table(conn_sql)

    code = args.code.strip().lower()
    name = args.name.strip()
    desc = (args.description or "").strip()
    category = (args.category or "").strip()
    aliases = (args.aliases or "").strip()
    conn_ref = getattr(args, "connection", None)
    conn_id = _resolve_connection_id(root, conn_ref)
    if conn_ref and conn_id is None:
        sys.exit(f"error: connection '{conn_ref}' does not exist in the connection table")

    cur = conn_sql.cursor()
    cur.execute("SELECT id FROM data_type WHERE data_type_code = ? AND is_deleted = 0", (code,))
    existing = cur.fetchone()
    if existing and not getattr(args, "update", False):
        sys.exit(f"error: data type code '{code}' already registered (id {existing[0]}). Use --update to overwrite.")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sql)
    if existing:
        cur.execute("""
            UPDATE data_type SET data_type_name = ?, data_type_desc = ?, category = ?,
                aliases = ?, connection_id = ?, version_id = ?, updated_time = ? WHERE id = ?
        """, (name, desc, category, aliases, conn_id, v_id, now, existing[0]))
        record_change(conn_sql, "data_type", existing[0], "M", f"Updated data type {name} (code: {code})")
    else:
        cur.execute("""
            INSERT INTO data_type (data_type_code, data_type_name, data_type_desc, category,
                                   aliases, connection_id, version_id, is_active, created_time, updated_time, is_deleted)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (code, name, desc, category, aliases, conn_id, v_id, now, now))
        rec_id = cur.lastrowid
        record_change(conn_sql, "data_type", rec_id, "C", f"Registered data type {name} (code: {code})")
    conn_sql.commit()
    conn_sql.close()
    print(f"registered data type '{name}' (code: {code}, connection_id: {conn_id}) in data_type table")


def op_read_data_types(root, args):
    """Print data types from the SQLite data_type table, joined with connection metadata."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"no EDM database found at {db}")
    conn_sql = sqlite3.connect(db)
    ensure_data_type_table(conn_sql)
    where = ["t.is_deleted = 0"]
    params = []
    if getattr(args, "category", None):
        where.append("t.category = ?")
        params.append(args.category)
    rows = conn_sql.execute(f"""
        SELECT t.data_type_code, t.data_type_name, t.category, t.aliases,
               COALESCE(c.connection_code, '')
        FROM data_type t
        LEFT JOIN connection c ON t.connection_id = c.id
        WHERE {' AND '.join(where)}
        ORDER BY t.category, t.data_type_code
    """, params).fetchall()
    conn_sql.close()
    if not rows:
        print("no data types registered")
        return
    print(f"# Data Types ({len(rows)} registered)")
    print()
    print("| Code | Name | Category | Aliases | Connection |")
    print("|------|------|----------|---------|------------|")
    for code, nm, cat, als, ccode in rows:
        print(f"| {code} | {nm} | {cat or ''} | {als or ''} | {ccode} |")


def op_modify_data_type(root, args):
    import sqlite3
    import datetime
    row = _fetch_data_type_row(root, args.code)
    if row is None:
        sys.exit(f"error: data type '{args.code}' does not exist in the data_type table")
    updates, params = [], []
    if getattr(args, "name", None):
        updates.append("data_type_name = ?")
        params.append(args.name)
    if getattr(args, "category", None) is not None:
        updates.append("category = ?")
        params.append(args.category)
    if getattr(args, "aliases", None) is not None:
        updates.append("aliases = ?")
        params.append(args.aliases)
    if getattr(args, "description", None) is not None:
        updates.append("data_type_desc = ?")
        params.append(args.description)
    if getattr(args, "connection", None) is not None:
        conn_id = _resolve_connection_id(root, args.connection)
        if args.connection and conn_id is None:
            sys.exit(f"error: connection '{args.connection}' does not exist in the connection table")
        updates.append("connection_id = ?")
        params.append(conn_id)
    if updates:
        conn_sql = sqlite3.connect(edm_db_path(root))
        ensure_data_type_table(conn_sql)
        v_id = get_active_version_id(conn_sql)
        updates.append("version_id = ?")
        params.append(v_id)
        updates.append("updated_time = ?")
        params.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
        conn_sql.execute(f"UPDATE data_type SET {', '.join(updates)} WHERE id = ?", params + [row["id"]])
        record_change(conn_sql, "data_type", row["id"], "M", f"Modified data type {args.code}")
        conn_sql.commit()
        conn_sql.close()
    print(f"modified data type {args.code}")


def op_delete_data_type(root, args):
    import sqlite3
    import datetime
    row = _fetch_data_type_row(root, args.code)
    if row is None:
        sys.exit(f"error: data type '{args.code}' does not exist in the data_type table")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    ensure_data_type_table(conn_sql)
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute(
        "UPDATE data_type SET is_deleted = 1, is_active = 0, version_id = ?, deleted_time = ? WHERE id = ?",
        (v_id, now, row["id"]))
    record_change(conn_sql, "data_type", row["id"], "D", f"Soft-deleted data type {args.code}")
    conn_sql.commit()
    conn_sql.close()
    print(f"soft-deleted data type {args.code}")


def _fetch_conn_row(root: Path, name: str) -> Optional[dict]:
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return None
    conn_sqlite = sqlite3.connect(db)
    conn_sqlite.row_factory = sqlite3.Row
    ensure_connection_table(conn_sqlite)
    cur = conn_sqlite.cursor()
    cur.execute("SELECT * FROM connection WHERE connection_code = ? AND is_deleted = 0", (name,))
    row = cur.fetchone()
    conn_sqlite.close()
    return dict(row) if row else None


def _decrypt_json(encrypted_str: str) -> dict:
    if not encrypted_str:
        return {}
    try:
        dec = _decrypt(encrypted_str)
        return json.loads(dec)
    except Exception:
        try:
            return json.loads(encrypted_str)
        except Exception:
            return {}


def op_add_conn(root, args):
    import sqlite3, datetime
    db = edm_db_path(root)
    conn_sqlite = sqlite3.connect(db)
    conn_sqlite.row_factory = sqlite3.Row
    ensure_connection_table(conn_sqlite)

    # Check if already exists (globally unique, including soft-deleted)
    cur = conn_sqlite.cursor()
    cur.execute("SELECT connection_code, is_deleted FROM connection WHERE connection_code = ?", (args.name,))
    existing = cur.fetchone()
    if existing:
        conn_sqlite.close()
        status_msg = " (currently soft-deleted)" if existing["is_deleted"] else ""
        sys.exit(f"error: connection '{args.name}' already exists in database{status_msg}")

    # Determine type flag
    if args.azimutt_server:
        flag = "Azimutt"
        payload = {
            "azimutt_server": args.azimutt_server,
            "auth_token": args.auth_token or "",
            "org": args.org or "",
            "project": args.project or "",
            "login_email": getattr(args, "login_email", None) or "",
            "login_password": getattr(args, "login_password", None) or "",
        }
        desc = getattr(args, "desc", None) or f"Azimutt server {args.azimutt_server}"
    else:
        flag = "DB"
        payload = {
            "type": args.type or "postgres",
            "url": args.url or "",
            "auth_token": args.auth_token or "",
        }
        desc = getattr(args, "desc", None) or f"{args.type or 'postgres'} database"

    encrypted = _encrypt(json.dumps(payload, ensure_ascii=False))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    v_id = get_active_version_id(conn_sqlite)

    cur = conn_sqlite.cursor()
    cur.execute("""
        INSERT INTO connection (
            connection_code, connection_name, connection_desc,
            connection_type_flag, connection_string, version_id,
            is_active, created_time, updated_time, is_deleted
        ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
    """, (args.name, args.name, desc, flag, encrypted, v_id, now, now))
    rec_id = cur.lastrowid
    record_change(conn_sqlite, "connection", rec_id, "C", f"Added connection {args.name} ({flag})")
    conn_sqlite.commit()
    conn_sqlite.close()
    print(f"added connection '{args.name}' ({flag}) to {db.name}")


def op_read_conn(root, args):
    row = _fetch_conn_row(root, args.name)
    if not row:
        sys.exit(f"error: connection '{args.name}' does not exist")
    payload = _decrypt_json(row["connection_string"])
    out = {
        "id": row["id"],
        "connection_code": row["connection_code"],
        "connection_name": row["connection_name"],
        "connection_desc": row["connection_desc"],
        "connection_type_flag": row["connection_type_flag"],
        "is_active": bool(row["is_active"]),
        "created_time": row["created_time"],
        "updated_time": row["updated_time"],
    }
    if getattr(args, "show_password", False):
        out["payload"] = payload
    else:
        masked = dict(payload)
        if masked.get("auth_token"):
            masked["auth_token"] = "*****"
        if masked.get("url"):
            masked["url"] = "*****"
        if masked.get("login_password"):
            masked["login_password"] = "*****"
        out["payload"] = masked
    print(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))


def op_modify_conn(root, args):
    import sqlite3, datetime
    row = _fetch_conn_row(root, args.name)
    if not row:
        sys.exit(f"error: connection '{args.name}' does not exist")
    payload = _decrypt_json(row["connection_string"])

    if args.type:
        payload["type"] = args.type
    if args.url is not None:
        payload["url"] = args.url
    if args.azimutt_server:
        payload["azimutt_server"] = args.azimutt_server
    if args.auth_token:
        payload["auth_token"] = args.auth_token
    if args.org is not None:
        payload["org"] = args.org
    if args.project is not None:
        payload["project"] = args.project
    if getattr(args, "login_email", None):
        payload["login_email"] = args.login_email
    if getattr(args, "login_password", None):
        payload["login_password"] = args.login_password

    flag = "Azimutt" if payload.get("azimutt_server") else "DB"
    encrypted = _encrypt(json.dumps(payload, ensure_ascii=False))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    db = edm_db_path(root)
    conn_sqlite = sqlite3.connect(db)
    v_id = get_active_version_id(conn_sqlite)
    conn_sqlite.execute("""
        UPDATE connection
        SET connection_type_flag = ?,
            connection_string = ?,
            version_id = ?,
            updated_time = ?
        WHERE connection_code = ? AND is_deleted = 0
    """, (flag, encrypted, v_id, now, args.name))
    record_change(conn_sqlite, "connection", row["id"], "M", f"Modified connection {args.name}")
    conn_sqlite.commit()
    conn_sqlite.close()
    print(f"modified connection '{args.name}' in {db.name}")


def op_delete_conn(root, args):
    """Soft delete the connection row following standard entity lifecycle."""
    import sqlite3, datetime
    row = _fetch_conn_row(root, args.name)
    if not row:
        sys.exit(f"error: connection '{args.name}' does not exist")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    db = edm_db_path(root)
    conn_sqlite = sqlite3.connect(db)
    v_id = get_active_version_id(conn_sqlite)
    conn_sqlite.execute("""
        UPDATE connection
        SET is_deleted = 1,
            is_active = 0,
            version_id = ?,
            deleted_time = ?
        WHERE connection_code = ?
    """, (v_id, now, args.name))
    record_change(conn_sqlite, "connection", row["id"], "D", f"Soft-deleted connection {args.name}")
    conn_sqlite.commit()
    conn_sqlite.close()
    print(f"deleted connection '{args.name}' (soft delete) in {db.name}")


def _resolve_org_id(server: str, token: str, org: str, headers: Optional[dict] = None, ssl_ctx=None) -> str:
    """Resolve an org name, slug, or id to the canonical UUID required by Azimutt API."""
    import uuid
    try:
        uuid.UUID(org)
        return org
    except (ValueError, TypeError, AttributeError):
        pass
    req_headers = headers if headers is not None else {"auth-token": token}
    req = Request(f"{server}/api/v1/organizations", headers=req_headers)
    try:
        with urlopen(req, timeout=15, context=ssl_ctx) as resp:
            orgs = json.loads(resp.read().decode("utf-8"))
        for o in orgs:
            if o.get("id") == org or o.get("slug") == org or o.get("name") == org:
                return o["id"]
    except Exception:
        pass
    return org


def op_test_azimutt_conn(root, args) -> None:
    conn_name = getattr(args, "conn", None) or getattr(args, "name", None)
    conn = load_conn(root, conn_name)
    server = (conn.get("azimutt_server") or "").rstrip("/")
    org = args.org or conn.get("org")
    if not server or not org:
        sys.exit(f"connection '{conn_name}' missing `azimutt_server`/`org`; use modify-conn --azimutt-server <url> --org <org>")
    token = conn.get("auth_token")
    if not token:
        sys.exit(f"connection '{conn_name}' missing `auth_token`; use modify-conn --auth-token <token>")

    org_id = _resolve_org_id(server, token, org)
    headers = {"Content-Type": "application/json", "auth-token": token}
    url = f"{server}/api/v1/organizations/{org_id}/projects"
    req = Request(url, headers=headers, method="GET")
    try:
        with urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8", "replace")
        projects = json.loads(body or "[]")
        print(f"OK: connection to {server} valid; found {len(projects)} project(s) in org '{org}' (id: {org_id})")
    except Exception as e:
        sys.exit(f"error: connection test failed: {e}")


def op_test_db_conn(root, args) -> None:
    """Test database connectivity by loading the connection and pre-flight probing."""
    conn_name = getattr(args, "conn", None) or getattr(args, "name", None)
    conn = load_conn(root, conn_name)
    url = conn.get("url")
    if not url:
        sys.exit(f"connection '{conn_name}' missing `url`; use add-conn --url <url>")
    password = conn.get("auth_token", "") or ""
    _preflight_conn(root, conn_name, url, password)
    print(f"OK: {conn_name} reachable")


def op_create_project(root, args) -> None:
    """Create a new project under an Azimutt organization via its REST API.

    Requires a connection with `azimutt_server` (base URL), `org`, and `auth_token`.
    """
    conn = load_conn(root, args.conn)
    server = conn.get("azimutt_server")
    org = args.org or conn.get("org")
    if not server or not org:
        sys.exit(f"connection '{args.conn}' missing `azimutt_server`/`org`; "
                 f"use add-conn --azimutt-server <url> --org <org>")
    token = conn.get("auth_token")
    if not token:
        sys.exit(f"connection '{args.conn}' missing `auth_token`; use add-conn --auth-token <token>")

    server = server.rstrip("/")
    org_id = _resolve_org_id(server, token, org)
    if args.no_schema:
        schema_content = ""

    payload = {
        "name": args.name,
        "description": args.description or "",
        "encoding_version": int(args.encoding_version) if str(args.encoding_version).isdigit() else 2,
        "storage_kind": args.storage_kind or "remote",
        "nb_sources": 0,
        "nb_tables": 0,
        "nb_columns": 0,
        "nb_relations": 0,
        "nb_types": 0,
        "nb_comments": 0,
        "nb_layouts": 0,
        "nb_notes": 0,
        "nb_memos": 0,
    }
    headers = {
        "Content-Type": "application/json",
        "auth-token": token,
    }

    print(f"Creating project '{args.name}' -> {server}/organizations/{org_id}/projects")
    req = Request(f"{server}/api/v1/organizations/{org_id}/projects", data=json.dumps(payload).encode("utf-8"),
                  headers=headers, method="POST")
    try:
        with urlopen(req, timeout=30) as resp:
            result = resp.read().decode("utf-8", "replace")
    except Exception as e:
        sys.exit(f"error: create project failed: {e}")
    created = json.loads(result or "{}")
    print(f"Created project '{created.get('name', args.name)}' (slug: {created.get('slug', '-')}) "
          f"id: {created.get('id', '-')}")
    if created.get("slug"):
        print(f"Open: {server}/organizations/{org}/{created['slug']}")

    # Auto-persist project name into the SQLite connection row for subsequent operations (e.g. deploy)
    row = _fetch_conn_row(root, args.conn)
    if row:
        try:
            payload = _decrypt_json(row["connection_string"])
            payload["project"] = created.get("slug") or args.name
            encrypted = _encrypt(json.dumps(payload, ensure_ascii=False))
            import sqlite3
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            _conn = sqlite3.connect(edm_db_path(root))
            _conn.execute("""
                UPDATE connection
                SET connection_string = ?, updated_time = ?
                WHERE connection_code = ?
            """, (encrypted, now, args.conn))
            _conn.commit()
            _conn.close()
            print(f"Stored project '{payload['project']}' in connection '{args.conn}'")
        except Exception as e:
            print(f"warning: could not update connection record: {e}")


def _resolve_project_id(server: str, token: str, org_id: str, proj: str, ssl_ctx=None) -> str:
    """Resolve a project name, slug, or id to the canonical UUID."""
    import uuid
    try:
        uuid.UUID(proj)
        return proj
    except (ValueError, TypeError, AttributeError):
        pass
    req = Request(f"{server}/api/v1/organizations/{org_id}/projects", headers={"auth-token": token})
    try:
        with urlopen(req, timeout=15, context=ssl_ctx) as resp:
            projects = json.loads(resp.read().decode("utf-8"))
        for p in projects:
            if p.get("id") == proj or p.get("slug") == proj or p.get("name") == proj:
                return p["id"]
    except Exception:
        pass
    return proj



def _compute_project_stats(p: dict) -> dict:
    """Compute the 9 stats fields required by Azimutt project update."""
    sources = p.get("sources", [])
    tables = [t for s in sources for t in s.get("tables", [])]
    columns_count = sum(len(t.get("columns", [])) for t in tables)
    relations_count = sum(len(s.get("relations", [])) for s in sources)
    types_count = sum(len(s.get("types", [])) for s in sources)
    comments_count = sum(1 for t in tables if t.get("comment")) + sum(
        sum(1 for c in t.get("columns", []) if c.get("comment")) for t in tables
    )
    layouts = p.get("layouts", {})
    memos_count = sum(len(l.get("memos", [])) for l in layouts.values())
    return {
        "nb_sources": len(sources),
        "nb_tables": len(tables),
        "nb_columns": columns_count,
        "nb_relations": relations_count,
        "nb_types": types_count,
        "nb_comments": comments_count,
        "nb_layouts": len(layouts),
        "nb_notes": 0,
        "nb_memos": memos_count,
    }


def _encode_multipart(fields: dict, file_field: str, filename: str, file_bytes: bytes) -> tuple:
    """Encode fields and a file into a multipart/form-data payload."""
    import uuid
    boundary = "----WebKitFormBoundary" + uuid.uuid4().hex
    crlf = b"\r\n"
    b_boundary = boundary.encode("utf-8")
    body = bytearray()
    for k, v in fields.items():
        if v is None:
            continue
        body.extend(b"--" + b_boundary + crlf)
        body.extend(('Content-Disposition: form-data; name="' + k + '"').encode("utf-8") + crlf + crlf)
        body.extend(str(v).encode("utf-8") + crlf)
    body.extend(b"--" + b_boundary + crlf)
    body.extend(('Content-Disposition: form-data; name="' + file_field + '"; filename="' + filename + '"').encode("utf-8") + crlf)
    body.extend(b"Content-Type: application/json" + crlf + crlf)
    body.extend(file_bytes)
    body.extend(crlf)
    body.extend(b"--" + b_boundary + b"--" + crlf)
    content_type = "multipart/form-data; boundary=" + boundary
    return bytes(body), content_type


def op_add_layout(root: Path, args) -> None:
    """Create a new layout in an Azimutt project via REST API."""
    import time
    ssl_ctx = _azimutt_ssl_context(args.insecure)
    conn = load_conn(root, args.conn)
    server = (conn.get("azimutt_server") or conn.get("url") or "").rstrip("/")
    org = args.org or conn.get("org")
    project = args.project or conn.get("project")
    if not server or not org or not project:
        sys.exit("error: connection " + args.conn + " missing azimutt_server, org, or project")
    token = conn.get("auth_token")
    if not token:
        sys.exit("error: connection " + args.conn + " missing auth_token")

    org_id = _resolve_org_id(server, token, org, ssl_ctx=ssl_ctx)
    project_id = _resolve_project_id(server, token, org_id, project, ssl_ctx=ssl_ctx)

    headers = {"auth-token": token}
    get_url = server + "/api/v1/organizations/" + org_id + "/projects/" + project_id + "?expand=content"
    req = Request(get_url, headers=headers)
    try:
        with urlopen(req, timeout=15, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        sys.exit("error: could not fetch project '" + project + "' from " + server + ": " + str(e))

    content_raw = data.get("content")
    if not content_raw:
        sys.exit("error: project '" + project + "' has no content")
    content = json.loads(content_raw) if isinstance(content_raw, str) else content_raw

    layouts = content.setdefault("layouts", {})
    if args.name in layouts and not args.force:
        sys.exit("error: layout '" + args.name + "' already exists; use --force to overwrite")

    source_tables = {}
    for s in content.get("sources", []):
        for t in s.get("tables", []):
            tid = str(t.get("schema")) + "." + str(t.get("table"))
            source_tables[tid] = t

    target_table_ids = args.tables or list(source_tables.keys())
    now_ms = int(time.time() * 1000)

    tables_payload = []
    x, y = 100, 100
    for tid in target_table_ids:
        t_meta = source_tables.get(tid)
        cols = [c["name"] for c in t_meta.get("columns", [])] if t_meta else []
        tables_payload.append({
            "id": tid,
            "color": args.color,
            "columns": cols,
            "position": {"left": x, "top": y},
            "size": {"height": max(160, min(600, 40 + len(cols) * 25)), "width": 280},
            "selected": False
        })
        x += 320
        if x > 1200:
            x = 100
            y += 400

    layouts[args.name] = {
        "createdAt": layouts.get(args.name, {}).get("createdAt", now_ms),
        "updatedAt": now_ms,
        "tables": tables_payload
    }

    stats = _compute_project_stats(content)
    file_bytes = json.dumps(content, ensure_ascii=False).encode("utf-8")
    fields = {
        "name": content.get("name", data.get("name", project)),
        "storage_kind": "remote",
        "encoding_version": content.get("version", 2),
        **stats
    }

    body, ctype = _encode_multipart(fields, "file", org_id + "-" + project + ".json", file_bytes)
    put_headers = {"auth-token": token, "Content-Type": ctype}
    put_url = server + "/api/v1/organizations/" + org_id + "/projects/" + project_id
    put_req = Request(put_url, data=body, headers=put_headers, method="PUT")
    try:
        with urlopen(put_req, timeout=30, context=ssl_ctx) as resp:
            json.loads(resp.read().decode("utf-8", "replace"))
        print("OK: Layout '" + args.name + "' created with " + str(len(tables_payload)) + " table(s) in project '" + project + "'")
        print("Open: " + server + "/organizations/" + org + "/" + project)
    except Exception as e:
        sys.exit("error: failed to update project layouts via API: " + str(e))




def _get_module_domain_map(root: Path) -> list:
    """Return active module->domain mappings (one row per distinct schema name),
    including entity-level schema overrides so tables published under an
    entity schema are attributed to the right module/domain. Each row also
    carries the module hierarchy (parent_module_id + parent names)."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        return []
    conn_sql = sqlite3.connect(db)
    rows = conn_sql.execute("""
        SELECT *
        FROM (
            SELECT m.module_code, m.module_name, m.id AS module_id,
                   COALESCE(m.schema, LOWER(m.module_code)) AS schema_name,
                   d.domain_code, d.domain_name, d.id AS domain_id,
                   m.parent_module_id AS parent_module_id,
                   p.module_code AS parent_code, p.module_name AS parent_name
            FROM module m
            JOIN domain d ON m.domain_id = d.id
            LEFT JOIN module p ON m.parent_module_id = p.id
            WHERE m.is_deleted = 0 AND d.is_deleted = 0
            UNION
            SELECT m.module_code, m.module_name, m.id AS module_id,
                   e.schema AS schema_name,
                   d.domain_code, d.domain_name, d.id AS domain_id,
                   m.parent_module_id AS parent_module_id,
                   p.module_code AS parent_code, p.module_name AS parent_name
            FROM entity e
            JOIN module m ON e.module_id = m.id
            JOIN domain d ON m.domain_id = d.id
            LEFT JOIN module p ON m.parent_module_id = p.id
            WHERE e.is_deleted = 0 AND m.is_deleted = 0 AND d.is_deleted = 0
              AND e.schema IS NOT NULL AND e.schema <> COALESCE(m.schema, LOWER(m.module_code))
        )
        ORDER BY domain_code, module_code
    """).fetchall()
    conn_sql.close()
    cols = ["module_code", "module_name", "module_id", "schema_name", "domain_code",
            "domain_name", "domain_id", "parent_module_id", "parent_code", "parent_name"]
    return [dict(zip(cols, r)) for r in rows]


def sync_project_layouts(root: Path, conn_name: str, org: str = "", project: str = "", insecure: bool = False) -> dict:
    """Create/refresh Azimutt layouts following the module hierarchy (parent_module_id):
    one layout per domain, one per module (named by module name path, e.g. `Platform Service/Security`),
    plus an `initial layout`; tables are positioned as nested blocks (submodule block beneath its parent)."""
    import time
    ssl_ctx = _azimutt_ssl_context(insecure)
    conn = load_conn(root, conn_name)
    server = (conn.get("azimutt_server") or conn.get("url") or "").rstrip("/")
    org = org or conn.get("org")
    project = project or conn.get("project")
    if not server or not org or not project:
        sys.exit("error: connection " + conn_name + " missing azimutt_server, org, or project")
    token = conn.get("auth_token")
    if not token:
        sys.exit("error: connection " + conn_name + " missing auth_token")

    module_defs = _get_module_domain_map(root)
    if not module_defs:
        sys.exit("error: no active modules registered in EDM; nothing to sync")

    org_id = _resolve_org_id(server, token, org, ssl_ctx=ssl_ctx)
    project_id = _resolve_project_id(server, token, org_id, project, ssl_ctx=ssl_ctx)
    headers = {"auth-token": token}

    get_url = server + "/api/v1/organizations/" + org_id + "/projects/" + project_id + "?expand=content"
    req = Request(get_url, headers=headers)
    try:
        with urlopen(req, timeout=15, context=ssl_ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        sys.exit("error: could not fetch project '" + project + "' from " + server + ": " + str(e))

    content_raw = data.get("content")
    if not content_raw:
        sys.exit("error: project '" + project + "' has no content")
    content = json.loads(content_raw) if isinstance(content_raw, str) else content_raw

    # Case-insensitive published table lookup: lower_tid -> actual_published_tid
    published = {}
    tid_columns = {}
    for s in content.get("sources", []):
        for t in s.get("tables", []):
            schema = str(t.get("schema", ""))
            table = str(t.get("table", ""))
            actual_tid = (schema + "." + table) if schema else table
            published[actual_tid.lower()] = actual_tid
            tid_columns[actual_tid.lower()] = [col["name"] for col in t.get("columns", [])]

    # schema(lower) -> module definitions, so we can attribute ANY published table to a module/domain
    schema_to_modules = {}
    mods_by_id = {}
    for r in module_defs:
        mods_by_id.setdefault(r["module_id"], r)
        key = (r["schema_name"] or r["module_code"]).lower()
        schema_to_modules.setdefault(key, []).append(r)

    module_name_of = {
        r["module_id"]: (r["module_name"] or r["module_code"]) for r in mods_by_id.values()
    }

    # Attribute published tables to modules via schema -> module
    tables_by_module = {}
    for actual_tid in published.values():
        schema_part = actual_tid.split(".")[0] if "." in actual_tid else ""
        mods = schema_to_modules.get(schema_part.lower(), [])
        if not mods:
            continue
        for r in mods:
            mid = r["module_id"]
            tables_by_module.setdefault(mid, []).append(actual_tid)

    # Module hierarchy tree (parent_module_id self-reference)
    parent_of = {}
    children_map = {}
    for mid, r in mods_by_id.items():
        parent_of[mid] = r.get("parent_module_id")
        if r.get("parent_module_id") in mods_by_id:
            children_map.setdefault(r["parent_module_id"], []).append(mid)
    roots = sorted(
        (mid for mid in mods_by_id if parent_of.get(mid) not in mods_by_id),
        key=lambda m: module_name_of.get(m, ""))
    for mids in children_map.values():
        mids.sort(key=lambda m: module_name_of.get(m, ""))
    child_lookup = children_map

    def module_path(mid: int) -> str:
        parts, cur, seen = [], mid, set()
        while cur in mods_by_id and cur not in seen:
            seen.add(cur)
            parts.append(module_name_of.get(cur, str(cur)))
            cur = parent_of.get(cur)
        return "/".join(reversed(parts))

    def place_subtree(mid: int, x: int, y: int, placements: dict) -> int:
        """Place a module's own tables as a block, then recurse into submodules beneath it.
        Returns the bottom offset of the placed subtree."""
        tids = tables_by_module.get(mid, [])
        cx, cy = x, y
        for i, tid in enumerate(tids):
            placements[tid.lower()] = (cx, cy)
            cx += 320
            if (i + 1) % 4 == 0:
                cx = x
                cy += 400
        own_bottom = (cy + 400) if tids else y
        child_x = x + 160
        next_child_y = own_bottom + 120
        bottom = own_bottom
        for ch in child_lookup.get(mid, []):
            child_bottom = place_subtree(ch, child_x, next_child_y, placements)
            next_child_y = child_bottom + 120
            bottom = max(bottom, child_bottom)
        return bottom

    def initial_positions() -> dict:
        placements = {}
        next_y = 100
        for rt in roots:
            next_y = place_subtree(rt, 100, next_y, placements) + 160
        return placements

    # Clean all existing layouts; rebuild from scratch using module hierarchy.
    content["layouts"] = {}
    layouts = content["layouts"]
    now_ms = int(time.time() * 1000)
    synced = []

    def subtree_tids(mid: int) -> list:
        tids = []
        stack = [mid]
        while stack:
            cur = stack.pop()
            tids.extend(tables_by_module.get(cur, []))
            if cur in child_lookup:
                stack.extend(child_lookup[cur])
        return list(dict.fromkeys(tids))

    def is_descendant(ancestor: int, mid: int) -> bool:
        cur = parent_of.get(mid)
        while cur is not None:
            if cur == ancestor:
                return True
            cur = parent_of.get(cur)
        return False

    # Leaf modules (own tables) get a layout named by their module path; the Azimutt layout menu
    # groups names by the leading "/" segment, so single children flatten to "Parent / Child".
    # For pure container modules with exactly one leaf descendant we also emit "<Parent>/Overview"
    # (the module's subtree) so the group holds >= 2 items and the leaf shows as a sub-menu entry.
    leaf_ids = sorted(
        (mid for mid in mods_by_id if tables_by_module.get(mid)),
        key=module_path)
    for mid in leaf_ids:
        name = module_path(mid)
        tids = subtree_tids(mid)
        subs = {}
        place_subtree(mid, 100, 100, subs)
        synced.append(_upsert_layout(layouts, name, tids, now_ms, tid_columns, positions=subs))
        print("Module layout: " + name + " -> " + str(len(tids)) + " table(s)")
    for cid in sorted(
            (mid for mid in mods_by_id if not tables_by_module.get(mid)),
            key=module_path):
        kids = [mid for mid in leaf_ids if is_descendant(cid, mid)]
        if len(kids) == 1:
            name = module_path(cid) + "/Overview"
            tids = subtree_tids(cid)
            subs = {}
            place_subtree(cid, 100, 100, subs)
            synced.append(_upsert_layout(layouts, name, tids, now_ms, tid_columns, positions=subs))
            print("Module layout: " + name + " -> " + str(len(tids)) + " table(s)")

    all_tids = [published[k] for k in published]
    if all_tids:
        synced.append(_upsert_layout(
            layouts, "initial layout", list(dict.fromkeys(all_tids)), now_ms, tid_columns,
            positions=initial_positions()))
        print("Initial layout -> " + str(len(dict.fromkeys(all_tids))) + " table(s)")

    stats = _compute_project_stats(content)
    file_bytes = json.dumps(content, ensure_ascii=False).encode("utf-8")
    fields = {
        "name": content.get("name", data.get("name", project)),
        "storage_kind": "remote",
        "encoding_version": content.get("version", 2),
        **stats
    }

    body, ctype = _encode_multipart(fields, "file", org_id + "-" + project + ".json", file_bytes)
    put_headers = {"auth-token": token, "Content-Type": ctype}
    put_url = server + "/api/v1/organizations/" + org_id + "/projects/" + project_id
    put_req = Request(put_url, data=body, headers=put_headers, method="PUT")
    try:
        with urlopen(put_req, timeout=30, context=ssl_ctx) as resp:
            json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as e:
        sys.exit("error: failed to push project layouts via API: " + str(e))

    print("OK: synced " + str(len(synced)) + " layout(s) into project '" + project + "'")
    print("Open: " + server + "/organizations/" + org + "/" + project)
    return {"synced": synced, "layouts": list(layouts.keys())}


def _upsert_layout(layouts: dict, name: str, table_ids: list, now_ms: int, tid_columns: dict, args_force: bool = False, positions: dict = None):
    """Build a new layout entry or refresh an existing one, preserving positions/colors/selection.

    `positions` optionally maps table ids (case-insensitive) to (left, top) defaults from the
    module-hierarchy plan; saved user positions still win over these defaults."""
    # Deduplicate table_ids case-insensitively, keeping the provided canonical case
    seen_lower = set()
    canonical_tids = []
    for tid in table_ids:
        t_low = tid.lower()
        if t_low not in seen_lower:
            seen_lower.add(t_low)
            canonical_tids.append(tid)

    pos_lookup = {k.lower(): v for k, v in (positions or {}).items()}
    grid = []
    x, y = 100, 100
    for tid in canonical_tids:
        if tid.lower() in pos_lookup:
            grid.append((tid, pos_lookup[tid.lower()][0], pos_lookup[tid.lower()][1]))
        else:
            grid.append((tid, x, y))
            x += 320
            if x > 1200:
                x = 100
                y += 400

    old = layouts.get(name, {})
    # Index old tables case-insensitively so old coordinates survive case variations
    old_tables = {t.get("id", "").lower(): t for t in old.get("tables", [])}
    table_payload = []
    for tid, gx, gy in grid:
        prev = old_tables.get(tid.lower(), {})
        t_columns = tid_columns.get(tid.lower())
        table_payload.append({
            "id": tid,
            "color": prev.get("color", "indigo"),
            "columns": list(t_columns) if t_columns is not None else prev.get("columns", []),
            "position": prev.get("position", {"left": gx, "top": gy}),
            "size": prev.get("size", {"height": 300, "width": 260}),
            "selected": prev.get("selected", False)
        })
    layout_entry = {
        "createdAt": old.get("createdAt", now_ms),
        "updatedAt": now_ms,
        "tables": table_payload
    }
    layouts[name] = layout_entry
    return name


def op_sync_layouts(root: Path, args) -> None:
    """Sync per-domain and per-module Azimutt layouts (standalone CLI)."""
    sync_project_layouts(root, args.conn, args.org, args.project, insecure=getattr(args, "insecure", False))


def op_delete_project(root, args) -> None:
    """Delete a project under an Azimutt organization via its REST API."""
    conn = load_conn(root, args.conn)
    server = conn.get("azimutt_server")
    org = args.org or conn.get("org")
    if not server or not org:
        sys.exit(f"connection '{args.conn}' missing `azimutt_server`/`org`; "
                 f"use add-conn --azimutt-server <url> --org <org>")
    token = conn.get("auth_token")
    if not token:
        sys.exit(f"connection '{args.conn}' missing `auth_token`; use add-conn --auth-token <token>")

    server = server.rstrip("/")
    org_id = _resolve_org_id(server, token, org)
    project_id = _resolve_project_id(server, token, org_id, args.name)

    headers = {
        "Content-Type": "application/json",
        "auth-token": token,
    }

    print(f"Deleting project '{args.name}' (id: {project_id}) from {server}/organizations/{org_id}/projects")
    req = Request(f"{server}/api/v1/organizations/{org_id}/projects/{project_id}",
                  headers=headers, method="DELETE")
    try:
        with urlopen(req, timeout=30) as resp:
            pass
        print(f"Deleted project '{args.name}' (id: {project_id}) successfully")
    except Exception as e:
        sys.exit(f"error: delete project failed: {e}")


def _extract_csrf(html: str) -> str:
    """Pull the Phoenix CSRF token from an Azimutt page (meta tag or hidden field)."""
    m = re.search(r'<meta[^>]+name=["\']csrf-token["\'][^>]+content=["\']([^"\']+)["\']', html)
    if m:
        return m.group(1)
    m = re.search(r'name=["\']_csrf_token["\'][^>]*value=["\']([^"\']+)["\']', html)
    return m.group(1) if m else ""


def _azimutt_owner_session(server: str, email: str, password: str):
    """Log into an Azimutt server with an Owner account; return (opener, csrf_token).

    The Azimutt REST API exposes no org-delete route (organizations are `only:
    [:index]`); deleting an organization goes through the session-authenticated
    browser route `DELETE /organizations/:id`, which requires a logged-in Owner.
    This helper performs `POST /login` (email/password + CSRF) and returns an
    opener whose cookie jar carries the session, plus a fresh CSRF token read
    from a post-login page.
    """
    from urllib.error import HTTPError

    base = server.rstrip("/")
    cj = http.cookiejar.CookieJar()
    opener = build_opener(HTTPCookieProcessor(cj))
    opener.addheaders = [("User-Agent", "Mozilla/5.0 (compatible; manage-edm)")]

    try:
        html = opener.open(Request(f"{base}/login"), timeout=30).read().decode("utf-8", "replace")
    except Exception as e:
        sys.exit(f"error: could not reach {base}/login: {e}")
    csrf = _extract_csrf(html)
    if not csrf:
        sys.exit("error: no CSRF token found on login page; is this an Azimutt server?")

    data = urlencode({"user[email]": email, "user[password]": password, "_csrf_token": csrf}).encode("utf-8")
    req = Request(f"{base}/login", data=data, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    req.add_header("X-CSRF-Token", csrf)
    try:
        resp = opener.open(req, timeout=30)
        body = resp.read().decode("utf-8", "replace")
    except HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        resp = None
    except Exception as e:
        sys.exit(f"error: login request failed: {e}")

    if resp is None or "Email or Password invalid" in body or resp.geturl().rstrip("/").endswith("/login"):
        reason = "invalid credentials" if "Email or Password invalid" in body else "reCAPTCHA or server error"
        sys.exit(f"error: Azimutt login failed ({reason}) for '{email}' on {base}")
    if "reCAPTCHA" in body and ("g-recaptcha" in body or "recaptcha" in body.lower()):
        sys.exit("error: this Azimutt instance enforces reCAPTCHA on login; owner-session automation is unsupported there")

    # Re-read the CSRF token from an authenticated page (the session may rotate it on login)
    try:
        html2 = opener.open(Request(f"{base}/home"), timeout=30).read().decode("utf-8", "replace")
    except Exception:
        html2 = body
    csrf2 = _extract_csrf(html2)
    return opener, (csrf2 or csrf)


def op_delete_org(root, args) -> None:
    """Delete an Azimutt organization via an Owner browser session.

    The Azimutt REST API has no org-delete route; deletion uses the browser
    route `DELETE /organizations/:id` and requires the logged-in user to be an
    Owner of the target organization. Credentials come from the connection
    (`login_email`/`login_password`) or `--email`/`--password`. Dry-run by
    default: lists the org's projects and stops; pass `--force` to delete.
    """
    conn = load_conn(root, args.conn)
    server = (conn.get("azimutt_server") or "").rstrip("/")
    if not server:
        sys.exit(f"connection '{args.conn}' missing `azimutt_server`; use add-conn --azimutt-server <url>")
    email = getattr(args, "email", None) or conn.get("login_email") or ""
    password = getattr(args, "password", None) or conn.get("login_password") or ""
    if not email or not password:
        sys.exit(f"connection '{args.conn}' missing owner login; "
                 f"set --login-email/--login-password via modify-conn, or pass --email/--password")

    opener, csrf = _azimutt_owner_session(server, email, password)

    try:
        with opener.open(Request(f"{server}/api/v1/users/current"), timeout=30) as resp:
            actor = json.loads(resp.read().decode("utf-8", "replace"))
        actor_email = actor.get("email", email)
    except Exception:
        actor_email = email

    try:
        with opener.open(Request(f"{server}/api/v1/organizations"), timeout=30) as resp:
            orgs = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as e:
        sys.exit(f"error: could not list organizations after login: {e}")

    org_id = None
    match = None
    for o in orgs:
        if o.get("id") == args.name or o.get("slug") == args.name or o.get("name") == args.name:
            org_id, match = o["id"], o
            break
    if not org_id:
        sys.exit(f"error: organization '{args.name}' not found on {server} (logged in as {actor_email})")
    org_label = match.get("name") or args.name

    try:
        with opener.open(Request(f"{server}/api/v1/organizations/{org_id}/projects"), timeout=30) as resp:
            projects = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        projects = []
    proj_names = [p.get("name") or p.get("slug") or p.get("id") for p in projects]

    if not getattr(args, "force", False):
        print(f"[dry-run] would delete organization '{org_label}' (id: {org_id}) from {server}")
        print(f"actor: {actor_email}")
        if proj_names:
            print("projects to be removed:")
            for n in proj_names:
                print(f"  - {n}")
        else:
            print("no projects in organization")
        print("note: deletion also removes layouts, notes, members, and access tokens. Pass --force to delete.")
        return

    print(f"Deleting organization '{org_label}' (id: {org_id}) from {server} (actor: {actor_email})")
    req = Request(f"{server}/organizations/{org_id}", method="DELETE")
    req.add_header("X-CSRF-Token", csrf)
    try:
        opener.open(req, timeout=40).read()
    except Exception as e:
        sys.exit(f"error: delete organization failed: {e}")

    try:
        with opener.open(Request(f"{server}/api/v1/organizations"), timeout=30) as resp:
            remaining = json.loads(resp.read().decode("utf-8", "replace"))
    except Exception:
        remaining = [{"id": org_id}]
    if any(o.get("id") == org_id for o in remaining):
        sys.exit(f"error: organization '{org_label}' is still present after delete; check Owner role on the account")
    print(f"Deleted organization '{org_label}' (id: {org_id}) successfully")


def _preflight_conn(root: Path, name: str, url: str, password: str = "") -> None:
    """Verify DB reachability + auth before launching Harlequin. Exit on failure."""
    try:
        import psycopg2
    except ImportError:
        print("warning: psycopg2 not installed; skipping connection pre-flight")
        return
    parsed = urlparse(url)
    user = parsed.username
    pwd = parsed.password or password or None
    dbname = parsed.path.lstrip("/") if parsed.path else None
    host = parsed.hostname
    port = parsed.port or 5432
    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=pwd,
                                dbname=dbname, connect_timeout=5)
        conn.close()
        print(f"connection ok: {name} ({host}:{port}/{dbname} as {user})")
    except Exception as e:  # noqa: BLE001
        sys.exit(f"error: cannot connect to {name}: {e}")


def op_explore(root, args):
    """Decrypt connection and launch Harlequin SQL IDE."""
    conn = load_conn(root, args.conn)
    url = conn["url"]
    password = conn.get("auth_token", "")
    if password:
        parsed = urlparse(url)
        netloc = f"{parsed.username}:{quote(password, safe='')}@{parsed.hostname}"
        if parsed.port:
            netloc += f":{parsed.port}"
        url = urlunparse(parsed._replace(netloc=netloc))
    if args.dry_run:
        print(f"[dry-run] Harlequin would launch with: {url}")
        return
    _preflight_conn(root, args.conn, conn["url"], password)
    import shutil
    harlequin = shutil.which("harlequin")
    if not harlequin:
        sys.exit("error: harlequin not installed. Install: pip install harlequin harlequin-psql")

    wmux = shutil.which("wmux") or (Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "wmux" / "resources" / "cli-bin" / "wmux.cmd" if os.name == "nt" else None)
    if os.environ.get("WMUX") == "1" or (wmux and Path(wmux).exists() and subprocess.run([str(wmux), "ping"], capture_output=True, text=True).stdout.strip() == "pong"):
        cmd_name = Path(harlequin).name if os.name == "nt" else harlequin
        cmd = f'& "{harlequin}" -a postgres --sslmode prefer "{url}"' if os.name == "nt" else f'{cmd_name} -a postgres --sslmode prefer "{url}"'
        res = subprocess.run([str(wmux), "agent", "spawn", "--cmd", cmd, "--label", f"Harlequin ({args.conn})"], capture_output=True, text=True)
        if res.returncode == 0:
            print(f"Launched Harlequin in new wmux tab for {args.conn}")
            return

    luvus = shutil.which("luvus") or (Path(os.environ.get("LOCALAPPDATA", "")) / "luvus" / "luvus.exe" if os.name == "nt" else None)
    if luvus and Path(luvus).exists() and os.environ.get("LUVUS_ENV"):
        # Inside Luvus: create a new tab and run Harlequin in its pane
        import time
        def lrun(*args):
            return subprocess.run([str(luvus), *args], capture_output=True, text=True)
        tab_res = lrun("tab", "new")
        tab_id = None
        try:
            tab_id = json.loads(tab_res.stdout).get("result", {}).get("tab")
        except Exception:
            pass
        if tab_id:
            lrun("tab", "focus", str(tab_id))
        time.sleep(0.5)
        # Find the pane in the newly focused tab
        pane_id = None
        try:
            plist = lrun("pane", "list")
            panes = json.loads(plist.stdout).get("result", {}).get("panes", [])
            if panes:
                pane_id = panes[0].get("pane")
        except Exception:
            pass
        cmd_name = Path(harlequin).name if os.name == "nt" else harlequin
        cmd = f'{cmd_name} -a postgres --sslmode prefer "{url}"'
        if pane_id:
            lrun("pane", "run", str(pane_id), cmd)
            print(f"Launched Harlequin in Luvus tab {tab_id} (pane {pane_id}) for {args.conn}")
        else:
            lrun("pane", "run", cmd)
            print(f"Launched Harlequin in new Luvus tab for {args.conn}")
        return

    if os.name == "nt":
        os.system(f'start "Harlequin" "{harlequin}" -a postgres --sslmode prefer "{url}"')
    else:
        subprocess.Popen([harlequin, "-a", "postgres", "--sslmode", "prefer", url])

def op_list(root, args):
    edm = edm_dir(root)
    if not edm.is_dir():
        sys.exit("error: no .edm/ corpus found")
    import sqlite3
    conns = []
    db = edm_db_path(root)
    if db.exists():
        try:
            _conn_sql = sqlite3.connect(db)
            ensure_connection_table(_conn_sql)
            for row in _conn_sql.execute("SELECT connection_code, connection_type_flag FROM connection WHERE is_deleted = 0 ORDER BY connection_code"):
                conns.append(f"{row[0]} ({row[1]})")
            _conn_sql.close()
        except Exception:
            pass
    print("| Domain | Module | Entity | Database | Schema |")
    print("|--------|--------|--------|----------|--------|")
    rows = _get_entities_in_scope(root)
    for e in rows:
        schema = e.get("schema_name") or e.get("module_code") or ""
        print(f"| {e['domain_code']} | {e['module_code']} | {e['entity_code']} | {e.get('database_name') or ''} | {schema} |")
    if conns:
        print()
        print(f"Connections: {', '.join(conns)}")


def op_view(root, args):
    """Combine entity AMLs -> .edm/_view.aml for `azimutt convert`."""
    rows = _get_entities_in_scope(root, args.domain, args.module)
    if not rows:
        sys.exit("no entities in scope")
    amls = [to_aml(e["entity_code"], e.get("columns") or [], e.get("fks") or []) for e in rows]
    out = edm_dir(root) / "_view.aml"
    out.write_text("\n".join(amls), encoding="utf-8")
    print(out)


# ----------------------------------------------------------- publish + deploy + render

def _azimutt_ssl_context(insecure: bool = False):
    """Return an SSL context; if *insecure*, skip certificate verification (useful for self-signed certs)."""
    if not insecure:
        return ssl.create_default_context()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def load_conn(root: Path, name: str) -> dict:
    """Load a connection from the SQLite connection table, decrypting its payload."""
    row = _fetch_conn_row(root, name)
    if not row:
        sys.exit(f"error: connection '{name}' not found; use add-conn")
    payload = _decrypt_json(row["connection_string"])
    data = {"name": row["connection_code"], "type_flag": row["connection_type_flag"]}
    data["display_name"] = row.get("connection_name") or row["connection_code"]
    data.update(payload)
    # legacy alias: consumers may still read `org`/`project` off the conn
    data["org"] = payload.get("org", "")
    data["project"] = payload.get("project", "")
    return data


def _azimutt_db_url(db_conn: dict) -> str:
    """Build the Azimutt DatabaseConnection url from an EDM connection payload.

    The password is injected (URL-encoded) when the stored url carries none, because
    the Azimutt gateway needs it to authenticate.
    """
    raw_url = db_conn.get("url") or "postgresql://localhost:5432/composync-db"
    password = str(db_conn.get("auth_token") or db_conn.get("password") or db_conn.get("login_password") or "")
    if password and "://" in raw_url:
        parsed = urlparse(raw_url)
        if not parsed.password:
            user = parsed.username or "composync"
            host = parsed.hostname or "localhost"
            port_str = f":{parsed.port}" if parsed.port else ""
            netloc = f"{user}:{quote(password, safe='')}@{host}{port_str}"
            raw_url = urlunparse(parsed._replace(netloc=netloc))
    return raw_url


def parse_sql_header(path: Path) -> dict:
    """Parse the `-- key: value` header of a generated DDL file into a dict."""
    meta = {}
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if not line.startswith("--"):
                    break
                m = re.match(r"--\s*([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*?)\s*$", line)
                if m:
                    meta[m.group(1).lower()] = m.group(2)
    except OSError:
        pass
    return meta


def op_generate(root, args):
    """Generate DDL and samples for an entity into .edm/ddl/<version>/<domain>-<module>-<entity>.sql."""
    fm, columns, fks, _ = load_entity_def(root, args.domain, args.module, args.name)
    entity = (fm.get("entity") or args.name).strip()
    domain = (fm.get("domain") or args.domain).strip()
    module = (fm.get("module") or args.module).strip()

    # Resolve DB/Schema: entity-level schema override takes precedence, then module.schema, else LOWER(module_code)
    db, schema = resolve_scope_meta(root, args.domain, args.module)
    fm_schema = (fm.get("schema") or "").strip()
    if fm_schema:
        schema = fm_schema
    if not db:
        db = fm.get("database", "")

    ddl = generate_ddl(entity, columns, fks, db, schema, root)
    samples = generate_samples(entity, columns, db, schema)

    version = load_version(root)
    out_dir = ddl_dir(root, version)
    out_dir.mkdir(parents=True, exist_ok=True)

    import datetime
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    stamp = now_utc.strftime("%Y-%m-%d %H:%M UTC")
    update_note = (args.title or f"regenerated for version {version}").strip()

    filename = f"{domain}-{module}-{entity}.sql"
    out_path = out_dir / filename

    content = (
        "-- ============================================================\n"
        "-- manage-edm generated DDL\n"
        f"-- entity:   {entity}\n"
        f"-- domain:   {domain}\n"
        f"-- module:   {module}\n"
        f"-- database: {db}\n"
        f"-- schema:   {schema}\n"
        f"-- version:  {version}\n"
        f"-- updated:  {stamp}\n"
        f"-- update:   {update_note}\n"
        "-- ============================================================\n"
        "\n"
        f"{ddl}\n"
        "\n"
        "-- samples\n"
        f"{samples}\n"
    )
    out_path.write_text(content, encoding="utf-8")
    print(f"Generated DDL ({version}): {out_path}")


def op_add_template(root, args):
    import sqlite3, datetime
    tmpl_type = "entity-domain" if args.type in ("entity", "entity-domain", "entity_domain") else "column-domain"
    table = "entity_domain" if tmpl_type == "entity-domain" else "column_domain"
    code_col = f"{table}_code"
    name_col = f"{table}_name"
    code = args.name.strip()
    name = args.title.strip() if args.title else code
    desc = (args.description or "").strip()

    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"error: EDM database not initialized: {db}")
    conn_sql = sqlite3.connect(db)
    if tmpl_type == "entity-domain":
        ensure_entity_domain_table(conn_sql)
    else:
        ensure_column_domain_table(conn_sql)

    cur = conn_sql.cursor()
    cur.execute(f"SELECT id FROM {table} WHERE {code_col} = ? AND is_deleted = 0", (code,))
    existing = cur.fetchone()
    if existing:
        conn_sql.close()
        sys.exit(f"error: {tmpl_type} template '{code}' already exists (id {existing[0]})")

    data_type_val = getattr(args, "data_type", None) or ""
    columns = []
    if tmpl_type == "column-domain":
        if not data_type_val and getattr(args, "column", None):
            first = args.column[0].strip()
            parts = [s for s in first.split(" ") if s]
            if len(parts) > 1 and parts[1] not in ("pk", "nullable"):
                data_type_val = parts[1]
            else:
                data_type_val = parts[0]
        cols_json = json.dumps([], ensure_ascii=False)
    else:
        if getattr(args, "column", None):
            for spec in args.column:
                parts = [s for s in spec.split(" ") if s]
                cname = parts[0]
                columns.append({"name": cname, "type": parts[1] if len(parts) > 1 else "varchar",
                                "pk": "pk" in parts, "nullable": "nullable" in parts,
                                "default": "", "description": "", "unique": False})
        cols_json = json.dumps(columns, ensure_ascii=False)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    fks_json = json.dumps([], ensure_ascii=False)
    v_id = get_active_version_id(conn_sql)
    if tmpl_type == "column-domain":
        cur.execute(f"""
            INSERT INTO column_domain (
                column_domain_code, column_domain_name, data_type, template_desc, columns_json, fks_json,
                version_id, is_active, created_time, updated_time, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (code, name, data_type_val, desc, cols_json, fks_json, v_id, now, now))
    else:
        cur.execute(f"""
            INSERT INTO entity_domain (
                entity_domain_code, entity_domain_name, template_desc, columns_json, fks_json,
                version_id, is_active, created_time, updated_time, is_deleted
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 0)
        """, (code, name, desc, cols_json, fks_json, v_id, now, now))
    rec_id = cur.lastrowid
    record_change(conn_sql, table, rec_id, "C", f"Added {tmpl_type} template {code}")
    conn_sql.commit()
    conn_sql.close()
    if tmpl_type == "column-domain":
        print(f"added column-domain template {code} (data type: {data_type_val}) to {table}")
    else:
        print(f"added {tmpl_type} template {code} to {table}")


def op_add_column_domain(root, args):
    """Add a column domain template with a designated data type."""
    args.type = "column"
    return op_add_template(root, args)


def op_read_template(root, args):
    tmpl_type = "entity-domain" if args.type in ("entity", "entity-domain", "entity_domain") else "column-domain"
    fm, cols, fks = load_template_def(root, tmpl_type, args.name)
    if tmpl_type == "column-domain":
        dt = fm.get("data_type") or (cols[0].get("type") if cols else "")
        print(f"**{fm.get('title') or args.name}** (Column Domain)")
        print()
        print("| Property | Value |")
        print("|----------|-------|")
        print(f"| Code | `{fm.get('name') or args.name}` |")
        print(f"| Name | {fm.get('title') or args.name} |")
        print(f"| Data Type | `{dt}` |")
        print(f"| Description | {fm.get('description') or ''} |")
    else:
        print(entity_table(fm, cols, fks))


def op_read_templates(root, args):
    """List templates from SQLite entity_domain/column_domain tables."""
    import sqlite3
    db = edm_db_path(root)
    if not db.exists():
        sys.exit(f"no EDM database found at {db}")
    conn_sql = sqlite3.connect(db)
    ensure_entity_domain_table(conn_sql)
    ensure_column_domain_table(conn_sql)
    total = 0
    shown = False
    req_type = getattr(args, "type", "all")
    if req_type in ("column", "column-domain", "column_domain"):
        kinds = (("column", "column_domain", "column_domain_code", "column_domain_name"),)
    elif req_type in ("entity", "entity-domain", "entity_domain"):
        kinds = (("entity", "entity_domain", "entity_domain_code", "entity_domain_name"),)
    else:
        kinds = (
            ("entity", "entity_domain", "entity_domain_code", "entity_domain_name"),
            ("column", "column_domain", "column_domain_code", "column_domain_name"),
        )
    for kind, table, code_col, name_col in kinds:
        if kind == "column":
            rows = conn_sql.execute(f"""
                SELECT {code_col}, {name_col}, coalesce(data_type, ''), template_desc, columns_json
                FROM {table}
                WHERE is_deleted = 0
                ORDER BY {code_col}
            """).fetchall()
            if not rows:
                continue
            total += len(rows)
            shown = True
            print(f"# {table} ({len(rows)} templates)")
            print()
            print("| Code | Name | Data Type | Description |")
            print("|------|------|-----------|-------------|")
            for code, nm, dt, desc, cols_json in rows:
                if not dt and cols_json:
                    try:
                        c_list = json.loads(cols_json)
                        if c_list and isinstance(c_list, list) and "type" in c_list[0]:
                            dt = c_list[0]["type"]
                    except Exception:
                        pass
                print(f"| {code} | {nm} | {dt or ''} | {desc or ''} |")
            print()
        else:
            rows = conn_sql.execute(f"""
                SELECT {code_col}, {name_col}, template_desc, columns_json
                FROM {table}
                WHERE is_deleted = 0
                ORDER BY {code_col}
            """).fetchall()
            if not rows:
                continue
            total += len(rows)
            shown = True
            print(f"# {table} ({len(rows)} templates)")
            print()
            print("| Code | Name | Description | Columns |")
            print("|------|------|-------------|---------|")
            for code, nm, desc, cols_json in rows:
                try:
                    ncols = len(json.loads(cols_json or "[]"))
                except Exception:
                    ncols = 0
                print(f"| {code} | {nm} | {desc or ''} | {ncols} |")
            print()
    conn_sql.close()
    if not shown:
        target = "column domain " if req_type in ("column", "column-domain", "column_domain") else "entity domain " if req_type in ("entity", "entity-domain", "entity_domain") else ""
        print(f"no {target}templates registered")


def op_read_column_domains(root, args):
    """List column domain templates from SQLite column_domain table."""
    args.type = "column"
    return op_read_templates(root, args)


def op_read_entity_domains(root, args):
    """List entity domain templates from SQLite entity_domain table."""
    args.type = "entity"
    return op_read_templates(root, args)


def op_modify_template(root, args):
    import sqlite3, datetime
    tmpl_type = "entity-domain" if args.type == "entity" else "column-domain"
    table = "entity_domain" if args.type == "entity" else "column_domain"
    code_col = f"{table}_code"
    name_col = f"{table}_name"
    code = args.name.strip()

    row = _fetch_template_row(root, code, tmpl_type)
    if row is None:
        sys.exit(f"error: {tmpl_type} template '{code}' not found in {table}")

    try:
        cols = json.loads(row.get("columns_json") or "[]")
    except Exception:
        cols = []
    try:
        fks = json.loads(row.get("fks_json") or "[]")
    except Exception:
        fks = []

    by_name = {c["name"]: c for c in cols}
    for spec in args.add_column:
        parts = [s for s in spec.split(" ") if s]
        cname = parts[0]
        by_name[cname] = {"name": cname, "type": parts[1] if len(parts) > 1 else "varchar",
                          "pk": "pk" in parts, "nullable": "nullable" in parts,
                          "default": "", "description": "", "unique": False}
    for cname in args.drop_column:
        if cname in by_name:
            del by_name[cname]
            fks = [f for f in fks if f["column"] != cname]
    if args.set_type:
        if args.set_type[0] in by_name:
            by_name[args.set_type[0]]["type"] = args.set_type[1]
    for col_spec in getattr(args, "set_col_desc", []) or []:
        cname, cdesc = col_spec[0], col_spec[1]
        if cname in by_name:
            by_name[cname]["description"] = cdesc
    columns = list(by_name.values())

    updates = ["columns_json = ?", "fks_json = ?", "updated_time = ?"]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    params = [json.dumps(columns, ensure_ascii=False), json.dumps(fks, ensure_ascii=False), now]
    if args.title:
        updates.append(f"{name_col} = ?")
        params.append(args.title)
    if getattr(args, "description", None) is not None:
        updates.append("template_desc = ?")
        params.append(args.description)

    conn_sql = sqlite3.connect(edm_db_path(root))
    v_id = get_active_version_id(conn_sql)
    updates.append("version_id = ?")
    params.append(v_id)
    conn_sql.execute(f"UPDATE {table} SET {', '.join(updates)} WHERE id = ?", params + [row["id"]])
    record_change(conn_sql, table, row["id"], "M", f"Modified {tmpl_type} template {code}")
    conn_sql.commit()
    conn_sql.close()
    print(f"modified {tmpl_type} template {code}")


def op_delete_template(root, args):
    import sqlite3, datetime
    tmpl_type = "entity-domain" if args.type == "entity" else "column-domain"
    table = "entity_domain" if args.type == "entity" else "column_domain"
    code = args.name.strip()

    row = _fetch_template_row(root, code, tmpl_type)
    if row is None:
        sys.exit(f"error: {tmpl_type} template '{code}' does not exist in {table}")

    if not args.force:
        applied = []
        refs_col = "entity_domains_json" if tmpl_type == "entity-domain" else "column_domains_json"
        conn_sql = sqlite3.connect(edm_db_path(root))
        rows = conn_sql.execute(f"""
            SELECT e.entity_code, COALESCE(d.domain_code, ''), COALESCE(m.module_code, ''),
                   e.{refs_col}
            FROM entity e
            LEFT JOIN module m ON e.module_id = m.id
            LEFT JOIN domain d ON m.domain_id = d.id
            WHERE e.is_deleted = 0
        """).fetchall()
        conn_sql.close()
        for ecode, dcode, mcode, refs_json in rows:
            try:
                refs = json.loads(refs_json or "[]")
            except Exception:
                refs = []
            ref_names = {r.get("name") if isinstance(r, dict) else r for r in refs}
            if code in ref_names:
                applied.append(f"{ecode} ({dcode}/{mcode})")
        if applied:
            sys.exit(f"error: template '{code}' is applied to: {', '.join(applied)}. Use --force to delete.")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn_sql = sqlite3.connect(edm_db_path(root))
    v_id = get_active_version_id(conn_sql)
    conn_sql.execute(f"UPDATE {table} SET is_deleted = 1, is_active = 0, version_id = ?, deleted_time = ? WHERE id = ?", (v_id, now, row["id"]))
    record_change(conn_sql, table, row["id"], "D", f"Soft-deleted {tmpl_type} template {code}")
    conn_sql.commit()
    conn_sql.close()
    print(f"soft-deleted {tmpl_type} template {code}")


def op_apply_template(root, args):
    apply_template_to_entity(root, args.name, args.domain, args.module,
                              "entity-domain" if args.type == "entity" else "column-domain",
                              args.template, getattr(args, "column", None))
    print(f"applied template {args.template} to {args.name}")


def op_unapply_template(root, args):
    unapply_template_from_entity(root, args.name, args.domain, args.module,
                                  "entity-domain" if args.type == "entity" else "column-domain",
                                  args.template)
    print(f"unapplied template {args.template} from {args.name}")


def op_publish(root: Path, args) -> None:
    """Push scope schema to an Azimutt server via its REST API."""
    ssl_ctx = _azimutt_ssl_context(args.insecure)
    conn = load_conn(root, args.conn)
    server = conn.get("azimutt_server")
    token = conn.get("auth_token")
    if not server or not token:
        sys.exit(f"connection '{args.conn}' missing `azimutt_server`/`auth_token`; "
                 f"use modify-conn --azimutt-server <url> --auth-token <token>")
    org = args.org or conn.get("org")
    proj = args.project or conn.get("project")
    if not org or not proj:
        sys.exit(f"connection '{args.conn}' missing `org`/`project`; "
                 f"use modify-conn --org <org> --project <project>")
    server = server.rstrip("/")

    org_id = _resolve_org_id(server, token, org, ssl_ctx=ssl_ctx)
    project_id = _resolve_project_id(server, token, org_id, proj, ssl_ctx=ssl_ctx)

    # Build Azimutt tables + relations directly from EDM entities in scope
    tables = []
    relations = []
    scope_entities = []
    rules: dict = {}

    rows = _get_entities_in_scope(root, args.domain, args.module)
    code_index = _get_entity_code_index(root)
    for e in rows:
        cols = e.get("columns") or []
        fks = e.get("fks") or []
        schema = (e.get("schema_name") or e.get("module_code") or "public")
        tname = e["entity_code"]
        source_cols = []
        pk_cols = []
        for c in cols:
            col_dict = {
                "name": c["name"],
                "type": c["type"],
                "nullable": bool(c.get("nullable", False)),
            }
            if c.get("default"):
                col_dict["default"] = str(c["default"])
            if c.get("description"):
                col_dict["comment"] = {"text": c["description"]}
            source_cols.append(col_dict)
            if c.get("pk"):
                pk_cols.append(c["name"])
        table_obj = {
            "schema": schema,
            "table": tname,
            "columns": source_cols,
        }
        if (e.get("entity_desc") or "").strip():
            table_obj["comment"] = {"text": e["entity_desc"].strip()}
        if pk_cols:
            table_obj["primaryKey"] = {
                "name": f"{tname}_pk",
                "columns": pk_cols
            }
        tables.append(table_obj)
        for fk in fks:
            ref_schema, rule = _resolve_ref_schema(
                code_index, schema, e.get("domain_code") or "", fk["ref_entity"])
            rules[rule] = rules.get(rule, 0) + 1
            relations.append({
                "name": fk["name"],
                "src": {"table": f"{schema}.{tname}", "column": fk["column"]},
                "ref": {"table": f"{ref_schema}.{fk['ref_entity']}", "column": fk["ref_column"]}
            })
        scope_entities.append(f"{e.get('domain_code')}/{e.get('module_code')}/{tname}")

    if not tables:
        sys.exit("error: no entities found in scope to publish")

    if relations:
        tally = ", ".join(f"{k} {v}" for k, v in sorted(rules.items()))
        print(f"relations: {len(relations)} ({tally})")

    scope = (args.domain or "_all") + ("/" + (args.module or "") if args.module else "")
    source_name = (getattr(args, "source_name", None) or "").strip() or f"edm-{scope.replace('/', '-')}"

    # Stage schema JSON in the OS temp dir for inspection; it is removed when publish ends.
    fd, tmp_json = tempfile.mkstemp(prefix="manage-edm_view_", suffix=".json")
    os.close(fd)
    json_path = Path(tmp_json)

    db_url = "postgresql://localhost:5432/composync-db"
    db_name = (rows[0].get("database_name") if rows else "") or "composync-db"
    try:
        db_conn = load_conn(root, db_name)
        db_url = _azimutt_db_url(db_conn)
        if not (getattr(args, "source_name", None) or "").strip():
            source_name = db_conn.get("display_name") or db_conn.get("name") or source_name
    except Exception as _e:
        print(f"warning: could not assemble database url credentials: {_e}")

    # All scopes share one source named after the EDM connection, so a scoped publish
    # would replace the whole model with the scope's tables only.
    if (args.domain or args.module) and not getattr(args, "force", False):
        sys.exit(f"error: scope {scope} would replace the shared source '{source_name}' "
                 f"with {len(tables)} table(s); re-run with --force to confirm")
    schema_payload = {
        "name": source_name,
        "kind": {"kind": "DatabaseConnection", "url": db_url},
        "enabled": True,
        "tables": tables,
        "relations": relations,
        "types": []
    }

    try:
        json_path.write_text(json.dumps(schema_payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Schema JSON ({len(tables)} table(s)) staged: {json_path}")
        for ent in scope_entities:
            print(f"  - {ent}")

        headers = {
            "Content-Type": "application/json",
            "auth-token": token,
        }

        # Query existing sources to determine whether to POST (create) or PUT (update)
        list_url = f"{server}/api/v1/organizations/{org_id}/projects/{project_id}/sources"
        existing_source_id = None
        existing_kind_url = ""
        try:
            req_list = Request(list_url, headers=headers, method="GET")
            with urlopen(req_list, timeout=15, context=ssl_ctx) as resp:
                existing_sources = json.loads(resp.read().decode("utf-8") or "[]")
            for s in existing_sources:
                if s.get("name") == source_name:
                    existing_source_id = s.get("id")
                    existing_kind_url = ((s.get("kind") or {}).get("url") or "").strip()
                    break
        except Exception:
            pass

        if existing_source_id:
            print(f"Source '{source_name}' exists (id: {existing_source_id}); updating via PUT...")
            if existing_kind_url and db_url and existing_kind_url != db_url:
                print(f"warning: source '{source_name}' connects with '{existing_kind_url}' "
                      f"but the EDM connection is '{db_url}'")
                print(f"warning: the Azimutt API cannot change a source connection; "
                      f"delete source '{source_name}' and re-publish to refresh it")
            update_url = f"{server}/api/v1/organizations/{org_id}/projects/{project_id}/sources/{existing_source_id}"
            update_payload = {"tables": tables, "relations": relations, "types": []}
            req = Request(update_url, data=json.dumps(update_payload).encode("utf-8"), headers=headers, method="PUT")
        else:
            print(f"Creating new source '{source_name}' via POST...")
            req = Request(list_url, data=json.dumps(schema_payload).encode("utf-8"), headers=headers, method="POST")

        print(f"Publishing to {server}/organizations/{org}/{proj} ...")
        try:
            with urlopen(req, timeout=30, context=ssl_ctx) as resp:
                body = resp.read().decode("utf-8", "replace") or "{}"
            print(f"OK: Published source '{source_name}' to {server}/organizations/{org}/{proj}")
            print(f"Open in browser: {server}/organizations/{org}/{proj}")
            try:
                print("Auto-syncing domain and module layouts...")
                sync_project_layouts(root, args.conn, org, proj, insecure=args.insecure)
            except Exception as _e:
                print(f"warning: layout auto-sync failed: {_e}")
        except Exception as e:  # noqa: BLE001
            print(f"Server error during publish: {e}")
            raise
    finally:
        try:
            os.unlink(json_path)
        except OSError:
            pass


def op_deploy(root: Path, args) -> None:
    """Deploy generated DDL SQL files to the target database."""
    try:
        import psycopg2
    except ImportError:
        sys.exit("error: psycopg2 not installed; required for database deployment")

    conn_data = load_conn(root, args.conn)
    url = conn_data.get("url", "")
    password = str(conn_data.get("auth_token") or conn_data.get("password") or conn_data.get("login_password") or "")
    if not url:
        sys.exit(f"error: connection '{args.conn}' has no database url configured")

    parsed = urlparse(url)
    user = parsed.username
    pwd = parsed.password or password or None
    dbname = parsed.path.lstrip("/") if parsed.path else None
    host = parsed.hostname
    port = parsed.port or 5432

    # Discover DDL files in scope (central .edm/ddl/<version>/*.sql)
    version = load_version(root)
    ddl_root = ddl_dir(root, version)
    sql_files = []
    if ddl_root.exists():
        for sql_file in sorted(ddl_root.glob("*.sql")):
            meta = parse_sql_header(sql_file)
            dom = meta.get("domain", "")
            mod = meta.get("module", "")
            ent = meta.get("entity", "")
            if not dom or not mod:
                continue
            if args.domain and args.domain not in (dom, meta.get("domain-name", "")):
                continue
            if args.module and args.module not in (mod, meta.get("module-name", "")):
                continue
            sql_files.append((dom, mod, ent, sql_file))

    if not sql_files:
        sys.exit(f"error: no generated DDL files found for version '{version}' in specified scope")

    # Dependency topological sort: entities referenced by foreign keys must be created first
    deps = {}
    for d_name, m_name, e_name, f in sql_files:
        content = f.read_text(encoding="utf-8")
        # Extract referenced tables from REFERENCES "schema"."Table" or REFERENCES "Table"
        import re
        refs = set(re.findall(r'REFERENCES\s+(?:"[^"]+"\.)?"([^"]+)"', content, re.IGNORECASE))
        deps[e_name] = refs

    sorted_files = []
    visited = set()
    file_map = {e_name: (d_name, m_name, e_name, f) for d_name, m_name, e_name, f in sql_files}

    def visit(ent):
        if ent in visited or ent not in file_map:
            return
        visited.add(ent)
        for ref in deps.get(ent, []):
            if ref != ent:
                visit(ref)
        sorted_files.append(file_map[ent])

    for d_name, m_name, e_name, f in sql_files:
        visit(e_name)

    sql_files = sorted_files

    print(f"Target: {host}:{port}/{dbname} (connection: {args.conn})")
    print(f"Found {len(sql_files)} DDL script(s) to deploy for version '{version}':")
    for d_name, m_name, e_name, f in sql_files:
        print(f"  - [{d_name}/{m_name}] {f.name}")

    if getattr(args, "dry_run", False):
        print("[dry-run] No changes applied to database.")
        return

    try:
        conn = psycopg2.connect(host=host, port=port, user=user, password=pwd,
                                dbname=dbname, connect_timeout=10)
        with conn:
            with conn.cursor() as cur:
                for d_name, m_name, e_name, f in sql_files:
                    sql = f.read_text(encoding="utf-8")
                    # Split schema DDL from sample inserts (separated by '-- samples')
                    parts = sql.split("-- samples")
                    ddl_sql = parts[0]
                    print(f"Executing DDL: {f.name} ({d_name}/{m_name})")
                    cur.execute(ddl_sql)
        conn.close()
        print(f"Successfully deployed {len(sql_files)} script(s) to {dbname}")
    except Exception as e:
        sys.exit(f"error: database deployment failed: {e}")


def op_export_image(root: Path, args) -> None:
    """Render current scope's ERD as PNG or SVG via mermaid-cli."""
    fmt = (args.format or "png").lower()
    if fmt not in ("png", "svg"):
        sys.exit(f"error: unsupported format '{fmt}'; use 'png' or 'svg'")
    npx_mmdc = shutil.which("npx")
    if not npx_mmdc:
        sys.exit("error: npx not found; install Node.js/npm")

    # Build a combined mermaid file from the scope
    rows = _get_entities_in_scope(root, args.domain, args.module)
    if not rows:
        sys.exit("no entities in scope to render")
    amls = [to_mermaid(e["entity_code"], e.get("columns") or [], e.get("fks") or []) for e in rows]
    mermaid_file = edm_dir(root) / "_view.mmd"
    mermaid_file.write_text("\n".join(amls), encoding="utf-8")
    out_file = edm_dir(root) / f"_view.{fmt}"
    cmd = f'npx --yes @mermaid-js/mermaid-cli -i "{mermaid_file}" -o "{out_file}"'
    print(f"Rendering ERD -> {out_file}")
    try:
        subprocess.run(cmd, check=True, shell=True, cwd=root, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"Mermaid error: {e.stderr}")
        sys.exit(1)
    if not out_file.exists():
        sys.exit("mermaid-cli finished without error but image file was not created")
    print(f"Image exported: {out_file}")


# ---------------------------------------------------------------- argparse

def P(name, help, **kw):
    return {"name": name, "help": help, **kw}


def build_parser():
    parser = argparse.ArgumentParser(prog="manage-edm")
    parser.add_argument("--root", help="project root containing .edm/ (default: nearest ancestor)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def entity_args(sp):
        sp.add_argument("name")
        sp.add_argument("--domain", required=True)
        sp.add_argument("--module", required=True)

    sp = sub.add_parser("add-entity", help="add entity (md + aml)")
    entity_args(sp); sp.add_argument("--column", action="append", default=[])
    sp.add_argument("--description"); sp.add_argument("--schema")

    sp = sub.add_parser("read", help="show entity as markdown table")
    entity_args(sp)

    sp = sub.add_parser("modify-entity", help="add/drop columns, set type")
    entity_args(sp)
    sp.add_argument("--add-column", action="append", default=[])
    sp.add_argument("--drop-column", action="append", default=[])
    sp.add_argument("--after", help="insert added column(s) or move after specified column")
    sp.add_argument("--move-col", help="column name to move after --after column")
    sp.add_argument("--set-type", nargs=2, metavar=("COL", "TYPE"))
    sp.add_argument("--set-col-desc", nargs=2, action="append", default=[], metavar=("COL", "DESC"), help="set description for a column")
    sp.add_argument("--set-nullable", action="append", default=[], metavar="COL", help="mark column nullable")
    sp.add_argument("--set-not-null", action="append", default=[], metavar="COL", help="mark column not nullable")
    sp.add_argument("--set-unique", action="append", default=[], metavar="COL", help="mark column unique")
    sp.add_argument("--add-fk", action="append", default=[], nargs="+", metavar="FK_SPEC", help="add foreign key: <col> <ref_entity> <ref_col> [<fk_name>]")
    sp.add_argument("--drop-fk", action="append", default=[], metavar="FK_NAME", help="drop foreign key by name")
    sp.add_argument("--description"); sp.add_argument("--schema")

    sp = sub.add_parser("delete-entity", help="delete entity")
    entity_args(sp)

    sp = sub.add_parser("move", help="move entity to another domain/module")
    sp.add_argument("name")
    sp.add_argument("--from-domain", required=True); sp.add_argument("--from-module", required=True)
    sp.add_argument("--to-domain", required=True); sp.add_argument("--to-module", required=True)

    sp = sub.add_parser("add-domain")
    sp.add_argument("name"); sp.add_argument("--title"); sp.add_argument("--database")
    sp.add_argument("--connection")

    sp = sub.add_parser("read-domain"); sp.add_argument("name")
    sp = sub.add_parser("modify-domain")
    sp.add_argument("name"); sp.add_argument("--title"); sp.add_argument("--database")
    sp.add_argument("--connection"); sp.add_argument("--description"); sp.add_argument("--code")
    sp.add_argument("--display-order", type=int)

    sp = sub.add_parser("delete-domain"); sp.add_argument("name"); sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("add-module")
    sp.add_argument("name"); sp.add_argument("--domain", required=True)
    sp.add_argument("--title"); sp.add_argument("--schema"); sp.add_argument("--connection")
    sp.add_argument("--repo-name")

    sp = sub.add_parser("read-module"); sp.add_argument("name"); sp.add_argument("--domain", required=True)
    sp = sub.add_parser("modify-module")
    sp.add_argument("name"); sp.add_argument("--domain")
    sp.add_argument("--title"); sp.add_argument("--schema"); sp.add_argument("--connection")
    sp.add_argument("--description"); sp.add_argument("--code")
    sp.add_argument("--repo-name"); sp.add_argument("--display-order", type=int)
    sp.add_argument("--parent-module", help="parent module code/name (use empty string to clear)")

    sp = sub.add_parser("delete-module"); sp.add_argument("name"); sp.add_argument("--domain")
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("register-domain", help="register a domain into SQLite domain table")
    sp.add_argument("name"); sp.add_argument("--code", required=True)
    sp.add_argument("--description", default="")
    sp.add_argument("--connection")
    sp.add_argument("--display-order", type=int, default=0)
    sp.add_argument("--update", action="store_true", help="overwrite existing entry with same code")

    sp = sub.add_parser("register-module", help="register a module into SQLite module table")
    sp.add_argument("name"); sp.add_argument("--domain", required=True)
    sp.add_argument("--code", required=True)
    sp.add_argument("--schema", help="DB schema name (default: kebab module name)")
    sp.add_argument("--description", default="")
    sp.add_argument("--repo-name")
    sp.add_argument("--parent-module", help="parent module code/name (optional)")
    sp.add_argument("--display-order", type=int, help="sort order within the domain (default: 0)")
    sp.add_argument("--update", action="store_true", help="overwrite existing entry with same code")

    sp = sub.add_parser("read-domains", help="print SQLite domain table registry")
    sp = sub.add_parser("read-modules", help="print SQLite module table registry")
    sp.add_argument("--domain")

    sp = sub.add_parser("register-data-type", help="register a data type into SQLite data_type table")
    sp.add_argument("name"); sp.add_argument("--code", required=True)
    sp.add_argument("--category"); sp.add_argument("--aliases"); sp.add_argument("--connection")
    sp.add_argument("--description", default="")
    sp.add_argument("--update", action="store_true", help="overwrite existing entry with same code")

    sp = sub.add_parser("read-data-types", help="print SQLite data_type table registry")
    sp.add_argument("--category")

    sp = sub.add_parser("modify-data-type")
    sp.add_argument("code"); sp.add_argument("--name"); sp.add_argument("--category")
    sp.add_argument("--aliases"); sp.add_argument("--connection"); sp.add_argument("--description")

    sp = sub.add_parser("delete-data-type"); sp.add_argument("code")

    sp = sub.add_parser("add-conn"); sp.add_argument("name"); sp.add_argument("--type"); sp.add_argument("--url")
    sp.add_argument("--azimutt-server"); sp.add_argument("--auth-token"); sp.add_argument("--org"); sp.add_argument("--project")
    sp.add_argument("--login-email"); sp.add_argument("--login-password")
    sp = sub.add_parser("read-conn"); sp.add_argument("name"); sp.add_argument("--show-password", action="store_true")
    sp = sub.add_parser("modify-conn"); sp.add_argument("name"); sp.add_argument("--type"); sp.add_argument("--url")
    sp.add_argument("--azimutt-server"); sp.add_argument("--auth-token"); sp.add_argument("--org"); sp.add_argument("--project")
    sp.add_argument("--login-email"); sp.add_argument("--login-password")
    sp = sub.add_parser("delete-conn"); sp.add_argument("name")

    sp = sub.add_parser("add-template", help="add entity-domain or column-domain template")
    sp.add_argument("name"); sp.add_argument("--type", choices=["entity", "column"], default="entity")
    sp.add_argument("--title"); sp.add_argument("--description")
    sp.add_argument("--data-type", help="data type for column-domain templates")
    sp.add_argument("--column", action="append", default=[])  # "col type pk nullable"

    sp = sub.add_parser("add-column-domain", help="add column-domain template with data type")
    sp.add_argument("name")
    sp.add_argument("--data-type", required=True, help="data type (e.g. decimal(17,2))")
    sp.add_argument("--title"); sp.add_argument("--description")

    sp = sub.add_parser("read-template", help="show template as markdown table")
    sp.add_argument("name"); sp.add_argument("--type", choices=["entity", "column"], default="entity")

    sp = sub.add_parser("read-templates", help="list templates from SQLite entity_domain or column_domain table")
    sp.add_argument("--type", choices=["entity", "column", "all", "column-domain", "column_domain", "entity-domain", "entity_domain"], default="all")

    sub.add_parser("read-column-domains", help="list column domain templates from SQLite column_domain table")
    sub.add_parser("read-entity-domains", help="list entity domain templates from SQLite entity_domain table")

    sp = sub.add_parser("modify-template", help="modify a template definition")
    sp.add_argument("name"); sp.add_argument("--type", choices=["entity", "column"], default="entity")
    sp.add_argument("--title"); sp.add_argument("--description")
    sp.add_argument("--add-column", action="append", default=[])
    sp.add_argument("--drop-column", action="append", default=[])
    sp.add_argument("--set-type", nargs=2, metavar=("COL", "TYPE"))
    sp.add_argument("--set-col-desc", nargs=2, action="append", default=[], metavar=("COL", "DESC"), help="set description for a column")

    sp = sub.add_parser("delete-template", help="delete a template")
    sp.add_argument("name"); sp.add_argument("--type", choices=["entity", "column"], default="entity")
    sp.add_argument("--force", action="store_true")

    sp = sub.add_parser("apply-template", help="apply a template to an entity")
    sp.add_argument("name"); sp.add_argument("--domain", required=True); sp.add_argument("--module", required=True)
    sp.add_argument("--template", required=True); sp.add_argument("--type", choices=["entity", "column"], default="entity")
    sp.add_argument("--column", help="target column in entity when applying a column domain")

    sp = sub.add_parser("unapply-template", help="remove a template from an entity")
    sp.add_argument("name"); sp.add_argument("--domain", required=True); sp.add_argument("--module", required=True)
    sp.add_argument("--template", required=True); sp.add_argument("--type", choices=["entity", "column"], default="entity")

    sp = sub.add_parser("explore", help="Launch Harlequin SQL IDE with decrypted connection")
    sp.add_argument("conn"); sp.add_argument("--dry-run", action="store_true")

    sub.add_parser("list", help="list domains/modules/entities")
    sp = sub.add_parser("view", help="concatenate scope .aml -> .edm/_view.aml")
    sp.add_argument("--domain"); sp.add_argument("--module")

    sp = sub.add_parser("generate", help="generate DDL to .edm/ddl/<version>/<domain>-<module>-<entity>.sql")
    sp.add_argument("name"); sp.add_argument("--domain", required=True); sp.add_argument("--module", required=True)
    sp.add_argument("--title"); sp.add_argument("--sql")

    sp = sub.add_parser("create-project", help="create a new project under an Azimutt organization")
    sp.add_argument("name"); sp.add_argument("--conn", required=True); sp.add_argument("--org", default="")
    sp.add_argument("--no-schema", action="store_true")
    sp.add_argument("--description"); sp.add_argument("--encoding-version", default="2")
    sp.add_argument("--storage-kind", choices=["local", "remote"], default="remote")

    sp = sub.add_parser("sync-layouts", help="automatically sync domain and module layouts in Azimutt")
    sp.add_argument("--conn", required=True, help="Azimutt connection name")
    sp.add_argument("--org", default="", help="override organization")
    sp.add_argument("--project", default="", help="override project")
    sp.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")

    sp = sub.add_parser("add-layout", help="create a new layout in an Azimutt project via API")
    sp.add_argument("name", help="layout name, e.g. portal-service")
    sp.add_argument("--conn", required=True, help="Azimutt connection name")
    sp.add_argument("--tables", nargs="+", default=[], help="tables to include, e.g. co.application_system")
    sp.add_argument("--color", default="indigo", help="color for tables on canvas")
    sp.add_argument("--force", action="store_true", help="overwrite layout if already exists")
    sp.add_argument("--org", default="", help="override organization")
    sp.add_argument("--project", default="", help="override project")
    sp.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")

    sp = sub.add_parser("delete-project", help="delete a project under an Azimutt organization")
    sp.add_argument("name"); sp.add_argument("--conn", required=True); sp.add_argument("--org", default="")

    sp = sub.add_parser("delete-org", help="delete an Azimutt organization via an Owner browser session")
    sp.add_argument("name", help="organization name, slug, or id")
    sp.add_argument("--conn", required=True, help="Azimutt connection name")
    sp.add_argument("--email", help="owner login email (default: connection `login_email`)")
    sp.add_argument("--password", help="owner login password (default: connection `login_password`)")
    sp.add_argument("--force", action="store_true",
                    help="actually delete (default is a dry run listing what would be removed)")

    sp = sub.add_parser("naming-style", help="read or set EDM entity and column naming style (S: snake_case, C: camelCase)")
    sp.add_argument("style", nargs="?", help="style to set: 'S'/'snake_case' or 'C'/'camelCase' (omit to read)")

    sp = sub.add_parser("set-version", help="set/read current EDM version (SQLite version table)")
    sp.add_argument("version", nargs="?", help="version to set (omit to print current)")
    sp.add_argument("--list", action="store_true", help="list all recorded versions")
    sp.add_argument("--force", action="store_true",
                    help="approve version increment (bypass version-bump gate)")

    sp = sub.add_parser("read-version-history", help="display audit change history from version_history table")
    sp.add_argument("--version", help="filter by version code or version id")
    sp.add_argument("--table", help="filter by table name (e.g. entity, domain, module)")
    sp.add_argument("--limit", type=int, default=50, help="limit entries (default: 50)")

    sp = sub.add_parser("init", help="create .edm/data/ + empty SQLite db (<project>-edm.db)")
    sp.add_argument("--force", action="store_true", help="recreate database if it exists")

    sp = sub.add_parser("test-conn", help="test Azimutt connection by listing projects")
    sp.add_argument("name"); sp.add_argument("--org")

    sp = sub.add_parser("test-db-conn", help="test PostgreSQL database connectivity")
    sp.add_argument("name", help="connection name")

    sp = sub.add_parser("publish", help="push scope schema JSON to an Azimutt server")
    sp.add_argument("--conn", required=True)
    sp.add_argument("--domain"); sp.add_argument("--module")
    sp.add_argument("--org"); sp.add_argument("--project")
    sp.add_argument("--source-name", help="override the source name (default: the EDM connection name)")
    sp.add_argument("--force", action="store_true", help="allow a scoped publish to replace the shared source")
    sp.add_argument("--insecure", action="store_true", help="skip TLS certificate verification")

    sp = sub.add_parser("deploy", help="deploy generated DDL SQL files to the target database")
    sp.add_argument("--conn", required=True, help="database connection name")
    sp.add_argument("--domain"); sp.add_argument("--module")
    sp.add_argument("--dry-run", action="store_true", help="preview SQL without applying")

    sp = sub.add_parser("export-image", help="render ERD as image (png/svg via mermaid-cli)")
    sp.add_argument("--domain"); sp.add_argument("--module")
    sp.add_argument("--format", choices=["png", "svg"], default="png")

    return parser


def main():
    args = build_parser().parse_args()
    root = find_root(getattr(args, "root", None))
    OPS = {
        "add-entity": op_add_entity, "read": op_read_entity,
        "modify-entity": op_modify_entity, "delete-entity": op_delete_entity,
        "move": op_move_entity,
        "add-domain": op_add_domain, "read-domain": op_read_domain,
        "modify-domain": op_modify_domain, "delete-domain": op_delete_domain,
        "add-module": op_add_module, "read-module": op_read_module,
        "modify-module": op_modify_module, "delete-module": op_delete_module,
"register-domain": op_register_domain, "register-module": op_register_module,
    "read-domains": op_read_domains, "read-modules": op_read_modules,
    "register-data-type": op_register_data_type, "read-data-types": op_read_data_types,
    "modify-data-type": op_modify_data_type, "delete-data-type": op_delete_data_type,
        "add-conn": op_add_conn, "read-conn": op_read_conn,
        "modify-conn": op_modify_conn, "delete-conn": op_delete_conn,
        "list": op_list, "view": op_view, "generate": op_generate,
    "add-template": op_add_template, "add-column-domain": op_add_column_domain,
    "read-template": op_read_template, "read-templates": op_read_templates,
    "read-column-domains": op_read_column_domains, "read-entity-domains": op_read_entity_domains,
    "modify-template": op_modify_template, "delete-template": op_delete_template,
    "apply-template": op_apply_template, "unapply-template": op_unapply_template,
        "publish": op_publish, "deploy": op_deploy, "test-conn": op_test_azimutt_conn, "test-db-conn": op_test_db_conn, "create-project": op_create_project, "sync-layouts": op_sync_layouts, "add-layout": op_add_layout, "delete-project": op_delete_project, "delete-org": op_delete_org, "export-image": op_export_image,
        "explore": op_explore, "naming-style": op_naming_style, "set-version": op_set_version, "read-version-history": op_read_version_history, "init": op_init,
    }
    OPS[args.cmd](root, args)


if __name__ == "__main__":
    main()