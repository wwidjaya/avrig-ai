---
name: read-vpp
description: Read/query Visual Paradigm .vpp project files (SQLite 3) — tables, columns, foreign keys, diagrams, and model elements. Read-only. Use when asked to inspect a .vpp data model or to verify claims about its tables/columns/FKs.
---

# read-vpp

Inspect Visual Paradigm `.vpp` files. A `.vpp` is a **SQLite 3 database** whose
core table is `MODEL_ELEMENT` (columns: ID, MODEL_TYPE, PARENT_ID, NAME,
DEFINITION, ...) plus `DIAGRAM`, `DIAGRAM_ELEMENT`, and `PROJECT_INFO`. Table
definitions and their columns are serialized inside the `DEFINITION` column in
Visual Paradigm's text format.

**Read-only:** the tool opens the file with `mode=ro` and never writes.

## Invocation (Windows)

```
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py <op> [args] [--db <path>]
```

Default target: `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\ojk\edm\data-model\2024.10.11 OJK EDM v2.0.0.vpp`.
Pass `--db <path>` to query any other `.vpp`.

## Operations

| Op | Command | Purpose |
|---|---|---|
| project | `project` | project name, DB/project version, build |
| tables | `tables` | list all DBTable elements (count + names) |
| table | `table <name>` | columns (type/length/PK/nullable) + FK constraints |
| columns | `columns <name>` | compact comma-separated column list |
| fk list | `fk` | all foreign keys (source → target table) |
| fk table | `fk <name>` | foreign keys touching a table |
| diagrams | `diagrams` | list diagrams (name, type, element count) |
| search | `search <text>` | find model elements by name (tables, columns, packages) |
| types | `types` | MODEL_TYPE distribution |
| rootmodels | `rootmodels` | top-level Model elements (PARENT_ID is null) |
| mainview | `mainview <table>` | main view (diagram) of a table + all its diagram views flagged MAIN/AUX |
| domains | `domains [name]` | database domains (entity + flat) with types, aliases, usage counts |

## Checking each type of information

"What do I want to know?" → which command (or raw query) to run:

| You want to check… | Command | Notes |
|---|---|---|
| Project name / version | `project` | name, DB version, build |
| All tables / columns of one | `tables` / `table <name>` / `columns <name>` | `columns` = compact names only |
| A table's columns in detail | `table <name>` | type code, length, PK, nullability + column-level FKs |
| Foreign keys (all / one table) | `fk` / `fk <name>` | self-FK may undercount by 1; cross-check DEFINITION |
| Diagrams (names + types) | `diagrams` | 3rd column is `DIAGRAM_TYPE` |
| Element type counts | `types` | MODEL_TYPE distribution (DBTable, DBForeignKey, …) |
| Root/top-level models | `rootmodels` | `MODEL_TYPE='Model' AND PARENT_ID IS NULL` |
| Main view of an entity | `mainview <table>` | flags `[MASTER]` vs `[AUX]` per diagram |
| Package enclosing an entity | `mainview` chain → walk `PARENT_ID` | `DBTable → Package → Model → Model`; package names are not unique |
| Relations of an entity + labels | `fk <table>` + `FromSimpleRelationships` | label = `DBForeignKey.NAME`; domain links have no label |
| Diagram's drawn title | resolve `Child=(...)` → TextBox `plainText` | distinct from `DIAGRAM.NAME` |
| Shape geometry/colours | `DIAGRAM_ELEMENT.DEFINITION` | x, y, width, height, background, foreground, fill |
| Database domains | `domains` / `domains <name>` | entity + flat domains, types, aliases, usage |
| Position of an entity in a diagram | `DIAGRAM_ELEMENT.DEFINITION` | join `MODEL_ELEMENT_ID` → table id |
| Main vs aux of each table in a package | compare `DIAGRAM_ELEMENT.ID` to `_masterViewId` | per table in the package's `ContainedDiagramElements` |
| Full detail of a diagram | `DIAGRAM.DEFINITION` + resolve `Child=(...)` | metadata, parent model, children, title, per-shape geometry |

Raw SQL equivalents for the non-trivial rows live in the schema reference
(`.opencode/references/vpp-schema.md`).

## Examples

```powershell
# Project metadata
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py project

# Every table
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py tables

# One table's full definition
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py table <table>
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py columns <table>

# Foreign keys
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py fk            # all
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py fk <table>    # only those touching <table>

# Diagrams
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py diagrams

# Find elements by name
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py search <text>

# Model type counts
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py types

# Root models (top-level domains)
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py rootmodels

# Main view of an entity + every diagram that shows it
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py mainview <table>

# Database domains: all entity domains + flat column domains
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py domains
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py domains <domain>   # one entity domain + its tables

# A different file (--db after the subcommand)
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py tables --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py project --db "C:\path\to\model.vpp"
```

## Reading the output

- **Columns**: each table row shows `type` (numeric VP type code; `-` = no data
  type assigned), `length`, `PK` (primary key), and nullability. A column with
  `type=-` has **no explicit type assigned** — it inherits the project default
  column type (`ProjectDiagramOptions_DefaultColumnType`, e.g. `integer(10)`),
  so it is NOT "missing a type"; the ID/PK columns conventionally carry no `type=`.
- **FKs**: `source -> target (relationship name)`. The FK `toModel`/`fromModel`
  addresses are colon-joined paths whose last component is the referenced table
  ID, resolved to names by the tool.

## Schema reference

The `.vpp` file format, underlying tables, and the raw SQL for every check above
(plus type codes and relationship kinds) live in the shared reference:

- **`.opencode/references/vpp-schema.md`** — file format, read patterns, type-code
  map, domain relationships. Read it when you need a check that the ops don't cover
  (e.g. geometry/colours, diagram detail properties, raw SQL equivalents).

The `rootmodels` and `mainview` ops wrap the schema's raw queries; use them when you
need the underlying objects directly.

## Gotchas

- This tool is **read-only**. For modifications, use the `write-vpp` skill.
- `search` matches table/column/package **names** only (not definition text).
- Table names may contain trailing spaces — quote them: `table "Table Name "`.
- A `.vpp` from Visual Paradigm is a SQLite file; opening it with any SQLite
  client works, but the `DEFINITION` format is VP-specific — prefer this tool.
