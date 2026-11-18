#!/usr/bin/env python3
"""Append JSON rows to an Excel table, preserving row styles and backing up."""
import argparse
import json
import shutil
from copy import copy
from pathlib import Path

import openpyxl
from openpyxl.utils.cell import range_boundaries


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet", required=True)
    parser.add_argument("--table", required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--rows-json", help="JSON array of objects keyed by table headers")
    source.add_argument("--rows-json-file", type=Path, help="Path to a UTF-8 JSON array of row objects")
    parser.add_argument("--no-backup", action="store_true")
    args = parser.parse_args()

    path = args.workbook
    if not path.is_file():
        parser.error(f"Workbook not found: {path}")
    try:
        rows = json.loads(args.rows_json) if args.rows_json is not None else json.loads(args.rows_json_file.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        parser.error(f"Cannot read valid rows JSON: {exc}")
    if not isinstance(rows, list) or not rows or not all(isinstance(row, dict) for row in rows):
        parser.error("--rows-json must be a non-empty JSON array of objects")

    wb = openpyxl.load_workbook(path, data_only=False)
    if args.sheet not in wb.sheetnames:
        parser.error(f"Sheet not found: {args.sheet}")
    ws = wb[args.sheet]
    try:
        table = ws.tables[args.table]
    except KeyError:
        parser.error(f"Table {args.table!r} not found on sheet {args.sheet!r}")

    min_col, header_row, max_col, last_row = range_boundaries(table.ref)
    headers = [ws.cell(header_row, col).value for col in range(min_col, max_col + 1)]
    if any(not isinstance(header, str) for header in headers):
        parser.error("Table headers must all be text")
    for index, row in enumerate(rows, 1):
        missing = [header for header in headers if header not in row]
        extra = [key for key in row if key not in headers]
        if missing or extra:
            parser.error(f"Row {index}: missing columns={missing}; unknown columns={extra}")

    if not args.no_backup:
        backup = path.with_suffix(path.suffix + ".bak")
        if backup.exists():
            parser.error(f"Backup already exists; refusing to overwrite: {backup}")
        shutil.copy2(path, backup)

    template_row = last_row if last_row > header_row else header_row
    for offset, row in enumerate(rows, 1):
        target_row = last_row + offset
        for col, header in enumerate(headers, min_col):
            source = ws.cell(template_row, col)
            target = ws.cell(target_row, col)
            if template_row != header_row:
                if source.has_style:
                    target._style = copy(source._style)
                if source.number_format:
                    target.number_format = source.number_format
                if source.alignment:
                    target.alignment = copy(source.alignment)
                if source.protection:
                    target.protection = copy(source.protection)
            target.value = row[header]

    new_last_row = last_row + len(rows)
    table.ref = f"{ws.cell(header_row, min_col).coordinate}:{ws.cell(new_last_row, max_col).coordinate}"
    if table.autoFilter:
        table.autoFilter.ref = table.ref
    if ws.auto_filter.ref:
        af_min_col, af_min_row, af_max_col, af_max_row = range_boundaries(ws.auto_filter.ref)
        if (af_min_col, af_min_row, af_max_col) == (min_col, header_row, max_col):
            ws.auto_filter.ref = f"{ws.cell(header_row, min_col).coordinate}:{ws.cell(new_last_row, max_col).coordinate}"

    wb.save(path)
    wb.close()

    check = openpyxl.load_workbook(path, read_only=False, data_only=False)
    check_ws = check[args.sheet]
    check_table = check_ws.tables[args.table]
    if check_table.ref != table.ref or check_ws.max_row < new_last_row:
        check.close()
        raise RuntimeError("Post-save verification failed")
    for offset, row in enumerate(rows, 1):
        for col, header in enumerate(headers, min_col):
            if check_ws.cell(last_row + offset, col).value != row[header]:
                check.close()
                raise RuntimeError(f"Post-save value check failed at row {last_row + offset}, column {header}")
    print(f"Added {len(rows)} row(s) to {args.table}; range is now {check_table.ref}.")
    if not args.no_backup:
        print(f"Backup: {path.with_suffix(path.suffix + '.bak')}")
    check.close()


if __name__ == "__main__":
    main()
