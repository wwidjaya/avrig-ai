---
name: design-ocdf-structure
description: Document/synchronize OCDF metadata entities in Visual Paradigm .vpp files (table + column descriptions) and update the OCDF structure-design tracking notes from vault entity notes. Use when adding or updating entity/column documentation, mapping new EDM entities, or reconciling a vault entity note with the OJK EDM v2.0.1 vpp.
---

# design-ocdf-structure

Universal workflow for designing, documenting, and synchronizing OCDF metadata
entities in a Visual Paradigm `.vpp` project (a **SQLite 3** database) against
their canonical Obsidian vault notes and the `OCDF-Structure-Design.md` tracking
note. Reusable with **any** entity, not just the ones previously handled.

## 1. Source of Truth (Vault First)

Always start from the canonical entity note in the vault, e.g.
`02-projects/ojk/edm/data-model/entities/<domain>/<category>/<Entity>.md`.
Read it to get:

- the **table description** (the `## Description` bullets),
- the **column descriptions** (the `## Columns` table `Description` column),
- foreign-key relationships / references.

Cross-reference with `02-projects/ojk/ocdf/02-requirement-discovery/ocdf-questionnaire.md` (Section 3.8 / metadata object definitions) to map questionnaire attributes (e.g. name, code, type, frequency, status, version) to physical EDM columns or related format/requirement tables.

#### 1.2 Column Comparison (per-entity, required each run)

**Always, for every entity you process, compare the OCDF object's questionnaire attributes against the EDM entity columns** and record an attribute-to-column mapping table. This is a mandatory design step, not optional.

Steps:
1. For the target OCDF object (row `#`, `OCDF Object`, `OJK EDM Entity` in `OCDF-Structure-Design.md` §1), locate the entity note `02-projects/ojk/edm/data-model/entities/<domain>/<category>/<Entity>.md` and the matching `#### 2.x.3. Metadata Objects` section in `ocdf-questionnaire.md`.
2. Build the mapping table:

   | Questionnaire / OCDF attribute | EDM column(s) carrying that attribute | Notes |
   | --- | --- | --- |
   | `<attr>` | `<Column>` (+ linked table columns) | e.g. self-FK for hierarchies |

3. Produce one mapping table per entity and keep it with the entity note's documentation work (append or reference in the VPP `documentation_plain` / tracking note). Example for `report_section` → `RegulatoryReportFormatRow`:

   | Questionnaire attribute | RegulatoryReportFormatRow column(s) |
   | --- | --- |
   | Section code / name | `RegulatoryReportFormatRowCode`, `RegulatoryReportFormatRowName` |
   | Description | `RegulatoryReportFormatRowDesc` |
   | Sequence / display order | `DisplaySequenceNo` |
   | Parent section (hierarchy) | `ParentRegulatoryReportFormatRowID` |
   | Row data type | `RowDataTypeFlag` (S/N/D) |
   | Decimal digits | `RowDecimalDigit` |
   | Formula logic | `RowFormula` |
   | Aggregation (child→parent) | `RowAggregationFlag` (+/-/∼) |
   | Version association | `RegulatoryReportFormatVersionID` |
   | Report-format association | `RegulatoryReportFormatID` |
   | Status / lifecycle | `IsActiveFlag`, `IsDeletedFlag`, `CreatedAt`, `UpdatedAt`, `DeletedAt` |

4. This per-entity mapping justifies each `table_plain` and `cols` entry in the JSON spec.
Full mapping reference: `references/ocdf-mapping.md`.

Skip any table or column that is **already documented** in the vpp (probe first;
do not overwrite existing `documentation_plain=`).

Default vpp target:
`D:\Cloud\OneDrive\AI\Personal\vault\02-projects\ojk\ocdf\03-ocdf-design\2024.10.11 OJK EDM v2.0.1.vpp`

## 2. Safety Contract

- **Back up** the `.vpp` before writing (create `<file>.vpp.bak-<suffix>`).
- **Probe read-only first** — inspect the `DEFINITION` blob to learn the column
  count, existing documentation, and each column's block structure.
- Validate after writing: `PRAGMA integrity_check` → `ok`; braces balanced;
  column count unchanged; `type=\"text/css\"` (escaped) present and **no** plain
  `type="text/css"` bug.
- If the entity is a subtype with **one** column already documented, keep that
  column's existing `documentation_plain` intact.

## 3. Column Documentation Anchors

A `DBColumn` block falls into one of three shapes; use the matching anchor:

| Column shape | Anchor to insert `documentation_plain="..."` after |
| --- | --- |
| **Regular** (has `type=<code>;`, e.g. `type=27;`) | after `type=<code>;` |
| **Foreign key** (no `type=`, has `FromSimpleRelationships` + `foreignKeyConstraints`) | after `foreignKeyNamePattern="<...>";` (last field before `}`) |
| **Untyped / no datatype field** (neither above) | after the block's trailing `pmLastModified="<ms>";` field |

Use the reusable probe helper to classify every column automatically.

## 4. Table-Level Documentation

Insert both (missing) forms around the `dataModel=1;` anchor:

- **HTML** (`documentation="..."`) — insert **immediately before** `dataModel=1;`.
- **Plain** (`documentation_plain="..."`) — insert after `dataModel=1;` and
  before `Child=(`. **If a short tagline already exists** (e.g.
  `documentation_plain="Bulanan, Harian, Tahunan";`), keep it — only add the
  missing HTML block.

HTML template (note the escaped inner quotes — required, see `.opencode/references/vpp-schema.md`):

```
<head>
    <style type=\"text/css\">
      <!--
        body { color: #000000; font-family: Dialog; font-size: 12px }
      -->
    </style>
  </head>
  <body>
    <p><b>Description:</b>...plain text...</p>
  </body>
```

## 5. Reusable Tooling

This skill ships a single parameterized helper (`doc_entity.py`) that runs the
whole probe + patch + verify cycle for any entity, so **no per-entity script is
ever written**. Use it with the entity name and a small JSON spec.

```
python "$env:OPENCODE_CONFIG_DIR/shared/skills/design-ocdf-structure/doc_entity.py" --entity "<TableName>" [--db <path>] [--spec <path.json>] [--apply]
```

- Probe-only by default (prints the table's column list, existing docs, and
  anchor kinds; **writes nothing**).
- `--spec <path.json>`: supply `{ "table_plain": "...", "cols": { "ColName": "desc" } }`
  in advance; otherwise the script prints the extract-to-plain-text template so
  you can fill it in, or reads a generated `.<entity>.spec.json` next to itself.

The helper already encodes: backup-before-apply, anchor classification,
escaping-safe table HTML, tagline preservation, timestamp refresh, integrity +
brace + escaping verification, and a summary table of what changed.

## 6. Update the Tracking Note

After the vpp write, edit `OCDF-Structure-Design.md`:

1. Add the entity to the correct domain row of the **Proposed Metadata Objects**
   table (row 10 = `system_master`) as a wikilink: append `/ [[path\|Entity]]`
   in the entity column.
2. Append a descriptive sentence to the **Note (2026-08-27)** narrative:
   column count, key flags / hierarchies, and the references it participates in.

## 7. Verify

Re-run `doc_entity.py --entity "<Entity>"` (probe mode) and confirm:
- `integrity_check: ok`
- column count unchanged
- braces balanced, no plain `type="text/css"` bug
- each intended column now carries its `documentation_plain`; unintended columns
  and pre-existing docs are untouched.

Keep the backup until the file opens cleanly in Visual Paradigm.

### 7.3 Always Emit the Comparison Table at End of Execution

Following the per-entity column comparison required in **§1.2**, after verification completes, always **print a markdown table mapping the OCDF object's questionnaire attributes to the EDM entity columns** as the final output of the entity-execution session. Format:

| Questionnaire / OCDF attribute | EDM column(s) carrying that attribute | Notes |
| --- | --- | --- |
| `<attr>` | `<Column>` (+ linked table columns) | e.g. self-FK for hierarchies, mirrored total fields |

See `references/ocdf-mapping.md` for worked example (`report_section` → `RegulatoryReportFomatColumn`).

## Gotchas

- `.vpp` is SQLite; open the target `mode=ro` to probe and `mode=rw` only for the
  final write. Scope `UPDATE ... WHERE ID=?` (assert `rowcount==1`); never update
  without a `WHERE ID`.
- Escape every inner `"` as `\"` in `documentation=""`. A plain `"` in the HTML
  silently truncates the property and VP renders the table empty.
- Some untyped `DBColumn` blocks have neither `type=` nor
  `foreignKeyNamePattern`; the helper falls back to the `pmLastModified` end-of-
  block anchor.
- OneDrive file may be locked/syncing; back up and verify with the helper, and
  treat Visual Paradigm opening cleanly as the final validator.

