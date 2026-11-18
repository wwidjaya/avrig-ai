#!/usr/bin/env python3
"""List workbook sheets, tables, defined names, and data validations."""
import argparse
import json
from pathlib import Path

import openpyxl


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    args = parser.parse_args()
    if not args.workbook.is_file():
        parser.error(f"Workbook not found: {args.workbook}")

    wb = openpyxl.load_workbook(args.workbook, read_only=False, data_only=False)
    result = {"workbook": str(args.workbook.resolve()), "sheets": []}
    for ws in wb.worksheets:
        tables = []
        for name in ws.tables:
            table = ws.tables[name]
            tables.append({
                "name": table.name,
                "range": table.ref,
                "columns": [column.name for column in table.tableColumns],
                "autofilter": table.autoFilter.ref if table.autoFilter else None,
            })
        result["sheets"].append({
            "name": ws.title,
            "tables": tables,
            "validations": [
                {"type": dv.type, "formula": dv.formula1, "ranges": str(dv.sqref)}
                for dv in ws.data_validations.dataValidation
            ],
        })
    result["defined_names"] = [
        {"name": name, "reference": defined_name.attr_text}
        for name, defined_name in wb.defined_names.items()
    ]
    print(json.dumps(result, indent=2, ensure_ascii=False))
    wb.close()


if __name__ == "__main__":
    main()
