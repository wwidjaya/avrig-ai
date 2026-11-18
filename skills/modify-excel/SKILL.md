---
name: modify-excel
description: Inspect and safely modify Excel .xlsx workbooks with Python and openpyxl. Use for workbook sheets, named tables, lookup rows, styles, and data validation tasks.
---

# Modify Excel workbooks

Use the scripts here for quick inspection and table-row additions. Install `openpyxl` if needed (`python -m pip install openpyxl`).

## Safe workflow

1. Resolve and verify the workbook path before editing. Inspect workbook features before saving; `openpyxl` may not preserve every Excel-specific feature.
2. Run `inspect_workbook.py` to review sheets, named tables and ranges, defined names, and validations. Converted Markdown may omit workbook metadata.
3. Make only the requested change. Back up before saving. For table additions, extend both table and autofilter ranges and copy an existing row's styles.
4. Reopen the saved workbook and verify the changes and relevant workbook structure.

## Scripts

```powershell
python scripts/inspect_workbook.py "budget.xlsx"
python scripts/add_table_rows.py "budget.xlsx" --sheet references --table ExpenseItemType --rows-json-file "rows.json"
```

`rows.json` is an array of objects keyed by every table column header. `add_table_rows.py` creates a `.bak` copy unless `--no-backup` is provided. Review workbook integrity after changes, especially files containing macros, external links, pivots, or embedded objects.
