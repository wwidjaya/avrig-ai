---
name: write-vpp
description: Create/update Visual Paradigm .vpp project files (SQLite 3) — tables, columns, foreign keys, domains, and diagram placement. Write-capable. Use when asked to add or change a .vpp data model. Always backs up first and dry-runs by default.
---

# write-vpp

Create and update model elements in Visual Paradigm `.vpp` project files. A `.vpp`
is a **SQLite 3 database**; this skill's tool opens it **read-write** and rewrites
`DEFINITION` blobs in VP's text format.

Shared format reference (tables, DEFINITION format, type codes, relationship
kinds, **write patterns**): **`.opencode/references/vpp-schema.md`**. Read it
before writing — especially the "Write patterns" section.

## Safety contract (non-negotiable)

- **`--backup` is required** before any write. The tool refuses `--apply` without
  it (unless `--force`, which is discouraged). Creates a timestamped sibling copy
  `<file>.vpp.bak-<ts>`.
- **Dry-run is the default.** Without `--apply`, the tool prints the SQL +
  `DEFINITION` changes and writes nothing.
- **Never** edit `LAST_*` mirror tables, `sqlite_sequence`, `USER_ID_FORMAT`, or
  `PROJECT_INFO` (except root-level element creation). VP manages these.
- **Dual timestamps:** row `CREATE_AT`/`LAST_MOD_AT` in seconds; `DEFINITION`
  `lastModifiedTime`/`pmCreateDateTime`/`pmLastModified` as 13-digit-ms strings.
- **Diagram shape blobs are derived** (in `PROJECT_FILE`). `diagram add-table`
  updates `DIAGRAM.DEFINITION` + `DIAGRAM_ELEMENT` but NOT the gzip shape blobs;
  it always prints a warning. VP regenerates them on open.
- **Validate after writing:** re-read with the `read-vpp` ops and confirm the
  change is visible; keep the backup until the file opens cleanly in VP.

## Invocation (Windows)

```
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py <op> [args] [--db <path>] [--backup] [--apply]
```

Default target: the same OJK EDM v2.0.0 file used by `read-vpp`. Pass `--db <path>`
for any other `.vpp`. **Always test on a throwaway copy first** (e.g. in
`C:\Users\wwidj\AppData\Local\Temp\opencode\`).

## Operations

| Op | Command | Purpose |
|---|---|---|
| backup | `backup` | create a timestamped backup copy |
| table create | `table create <package_id> <name>` | new DBTable + standard columns (ID/Code/Name/Desc/audit/flags) |
| table rename | `table rename <old> <new>` | rename a table (NAME + DEFINITION header) |
| column add | `column add <table> <name> [--type --length --not-null --pk --default]` | add a DBColumn to a table |
| column update | `column update <table> <name> [--type --length --not-null --pk --default]` | edit a column block |
| column rename | `column rename <table> <old> <new>` | rename a column (+ domain rel address) |
| fk add | `fk add <table> <column> <ref_table> <ref_column> [--label]` | DBForeignKey + child `foreignKey=` wiring |
| domain assign | `domain assign <table>|<table.column> <domain>` | DBTableDomain / DBColumnDomainRelationship |
| diagram add-table | `diagram add-table <diagram> <table>` | place table on diagram (guarded) |
| style apply | `style <table_or_id> --style-name "<name>"` | apply visual style (e.g. "Logical Entity") to a shape (creates style in StyleSetContainer if absent) |
| verify | `verify [name]` | read-back integrity check |

## Visual Style Application (e.g., "Logical Entity")

To apply a predefined VP visual style (like "Logical Entity") to a shape programmatically:

VP stores visual styles as `Style` elements inside a `StyleSetContainer` MODEL_ELEMENT
(singleton `Model` → `StyleSetContainer` named `"StyleSet"`). A style's full reference
is `<StyleSetContainerID$StyleID>`. The `StyleSetContainer.Child` list holds
`{<StyleID>:"<StyleName>":Style { ... }}` blocks.

### How VP applies a style via the GUI (observed in Test v1.0.1.vpp)

Applying a style in VP writes **two** things:

1. **DIAGRAM_ELEMENT.DEFINITION** gets:
   - a `style=<ContainerID$StyleID>;` line, plus
   - resolved appearance attributes folded in: `@transparency=<fillColorTransparency>;`,
     `_fillColor`, `background`, `foreground`, `_lineModel` color.
2. The `Style` element's `_styleViews=(...)` list gets a `StyleView` entry:
   ```text
   {<StyleViewID>:"View":StyleView {
       view="<DIAGRAM_ELEMENT_ID>";
       styleContainer=<DIAGRAM_ID>;
   }}
   ```

**Critical:** applying a NEW style via the GUI **creates the `Style` element inside the
`StyleSetContainer`** if it does not already exist. The "Logical Entity" style is NOT a
built-in; it was created by VP GUI when first applied. Its defining properties (from
Test v1.0.1.vpp):

```text
{uAqXigWGAqAkBAjK:"Logical Entity":Style {
    borderColor=-65536;
    foreground=-16777216;
    endArrowSize=2;
    fontSize=11;
    beginArrowSize=2;
    background2=-16777216;
    borderWeight=1.0;
    compartmentFontName=NULL;
    fontName="Dialog";
    background=-8728587;
    _modelEditable=T;
    fillColorTransparency=100;
}}
```

### Steps to read/apply programmatically

1. **Find `StyleSetContainer` + `Style` ID**:
   - Query `MODEL_ELEMENT` where `MODEL_TYPE='StyleSetContainer'`; parse its `Child=(...)`
     for `{<StyleID>:"<Name>":Style {`.
   - Style ref = `<ContainerID$StyleID>` (e.g. `<SJHYCgWGAqAkBCIb$uAqXigWGAqAkBAjK>`).
2. **If the style name is absent**, create the `Style` element (append block into the
   `StyleSetContainer` `Child=(...)`) with the appearance attributes above, since VP
   treats it as a user-defined style.
3. **Update `DIAGRAM_ELEMENT.DEFINITION`**: add `style=<ContainerID$StyleID>;` and fold
   in the resolved appearance attributes.
4. **Update the `Style`'s `_styleViews=(...)`** with a `StyleView` pointing at the
   diagram element's ID.

The `vpp_write.py` `style` op wraps steps 1-4 (dry-run by default, `--backup` required).

**No helper op exists for entity/column descriptions** (`documentation=`). Set them with a
targeted script that rewrites the table's `DEFINITION` blob — see the schema reference's
"Entity & column descriptions" + "Renaming a table" write patterns for the exact position
of `documentation=`/`documentation_plain=` and the `\"` escaping rule (a plain `"` in the
HTML makes VP render the table empty).

## Examples

```powershell
# Back up first
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py backup --db "C:\path\to\model.vpp"

# Create a table (dry-run first, then --apply with --backup)
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py table create <package_id> "NewTable" --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py table create <package_id> "NewTable" --backup --apply --db "C:\path\to\model.vpp"

# Add / update / rename a column
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py column add NewTable Email --type 27 --length 150 --backup --apply --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py column update NewTable Email --length 255 --backup --apply --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py column rename NewTable Email EmailAddress --backup --apply --db "C:\path\to\model.vpp"

# Add a foreign key
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py fk add NewTable CountryID Country ID --label "located in" --backup --apply --db "C:\path\to\model.vpp"

# Assign domains
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py domain assign NewTable.Email EmailAddress --backup --apply --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py domain assign NewTable Standard --backup --apply --db "C:\path\to\model.vpp"

# Place on a diagram (guardrail: shape blobs left for VP to regenerate)
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py diagram add-table "01-01-02" NewTable --backup --apply --db "C:\path\to\model.vpp"

# Apply a visual style (e.g., "Logical Entity")
python $env:OPENCODE_CONFIG_DIR/shared/skills/write-vpp/vpp_write.py style NewTable --style-name "Logical Entity" --backup --apply --db "C:\path\to\model.vpp"

# Verify the result via read-vpp
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py table NewTable --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py fk NewTable --db "C:\path\to\model.vpp"
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py mainview NewTable --db "C:\path\to\model.vpp"
```

## Finding a package/model id

`table create` needs a `PARENT_ID` — a Package or Model element. Resolve it first:

```
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py search <package-name>
python $env:OPENCODE_CONFIG_DIR/shared/skills/read-vpp/vpp_query.py rootmodels        # top-level models
```

## Gotchas

- **Mandatory backup + dry-run default** are enforced by the tool; do not bypass
  with `--force` unless the user explicitly accepts the risk.
- Table/column names with trailing spaces or quotes must be quoted on the command
  line.
- A `.vpp` on OneDrive may be locked or syncing; verify with `verify` and keep the
  backup until the file opens cleanly in Visual Paradigm — VP is the real validator.
- The tool intentionally does **not** rewrite derived `PROJECT_FILE` shape blobs;
  after `diagram add-table`, open the file in VP once to regenerate them.
- Only the target `.vpp` is written; the source model and `read-vpp` skill are
  never modified.
- **Always scope raw `UPDATE`s to `WHERE ID=<row>`** (then assert `rowcount==1`).
  A `UPDATE ... SET DEFINITION=?` without `WHERE` clones one blob into every row —
  a real incident wiped all 881 tables and was only recoverable from the pre-write
  backup. When in doubt, restore the backup and re-apply the change carefully.
- **Description escaping:** when writing `documentation="..."`, escape every inner
  `"` as `\"` (e.g. `type=\"text/css\"`). Plain `"` inside the HTML silently truncates
  the property and VP renders the affected table **empty** (while `read-vpp` still
  reads it — trust VP, not the regex query, as the validator).
- **DEFINITION brace balance (fixed 2026-08-29):** `col_block()` closed with `f'}}'`
  (single `}`) leaving every column missing a closing brace → imbalanced `Child=(...)`;
  VP silently drops the whole element (table invisible, and in the worst case the
  parent package stops expanding). Always sanity-check `open-brace count == close-brace
  count` on the DEFINITION after `table create`/`column add`. The updated tool closes
  with `f'}}}}'`.
- **Package tree visibility requires a Child ref.** `table create` sets `PARENT_ID` but
  does **not** insert `<model:parent:pkg:table>` into the package's `Child=(...)` block.
  Without it the table exists in SQL but is invisible in VP's project browser. After
  `table create`, must manually append the Child ref (format
  `<ModelID:ParentModelID:PkgID:TableID>`, comma-separated, no trailing stray comma) —
  `diagram add-table` alone is insufficient for the browser tree.
- **Package Child ref mistakes corrupt the package.** When editing a package
  `Child=(...)` block, keep every entry comma-separated and the last entry bare (no
  trailing comma). A missing comma between two refs, or a stray trailing comma, makes
  VP unable to parse the package → `cannot expand package` in the UI. Restore from
  backup and re-append carefully.
- **`vpp_write.py` table/column ops cannot safely materialize tables (verified 2026-08-30).**
  Their output is missing VP-required `FromSimpleRelationships` row refs and uses
  non-alphanumeric IDs — VP silently drops / blank-renders the table in the browser.
  **Do not rely on `table create` + `column add` for visible entities.** Use the
  **VP-format clone recipe** below.

## VP-format clone recipe (working, 2026-08-30)

Replicate VP's own structure by cloning an existing visible table in the same model/diagram.

1. Read the full `DEFINITION` of a visible template table for field order / column
   block format.
2. Generate purely alphanumeric IDs (VP pattern): table ID + diagram-element ID +
   ModelView key ID + one per column — avoid `$`/`.` where possible.
3. Insert `MODEL_ELEMENT` DBTable row under the target model/package.
4. `DEFINITION` layout:
   ```text
   <tblId>:"<Name>":DBTable {
       _modelEditable=T;
       _masterViewId="<diagElemId>";
       primaryKeyConstraintNamePattern="";
       pmAuthor="wwidj";
       lastModifiedTime=<ms>;
       pmCreateDateTime="<ms>";
       _modelViews=(
           {<viewKey>:"View":ModelView {container=<diagId>; view="<diagElemId>";}}
       );
       dataModel=1;
       Child=(
           {<colId>:"Col":DBColumn { _modelEditable=T; length=...; nullable=...; type=...; }},
       );
       pmLastModified="<ms>";
   }
   ```
5. Insert `DIAGRAM_ELEMENT` with `MODEL_ELEMENT_ID=<tableId>`.
6. Append `<modelId:tableId>` to the parent MODEL_ELEMENT `Child=(...)`.
7. Append `<diagId:diagElemId>` to the DIAGRAM `Child=(...)`.
8. Back up first. Brace balance must be 0. VP validates the result on open.

## Entity shape size formula & attribute rendering (verified 2026-08-30)

VP sizes a DBTable canvas shape by column count. Calibrated from Test v1.0.0.vpp
correctly-sized entities (n = number of columns):

| n (cols) | shape width | shape height |
|---|---|---|
| 1 | 140 | 41 |
| 4 | 230 | 95 |
| 5 | 259 | 113 |
| 6 | 290 | 131 |
| 8 | 350 | 167 |

**Height fits exactly**: `height = 41 + (columns-1) * 18` (41 = title + caption + ID
row; +18 per additional column row). Verified n=1,4,5,6,8.

**Width default**: `width = 140 + (columns-1) * 30` (base 140 caption width + ~30/col).
Width is not strictly linear — VP fits to the widest column, so allow manual override.

### Proven Working Python Entity Generator

To ensure attributes render immediately AND prevent diagram corruption:

```python
def entity_size(ncols):
    width  = 140 + (ncols - 1) * 30
    height = 41  + (ncols - 1) * 18
    return width, height

# 1. DIAGRAM_ELEMENT DEFINITION pattern (must include _captionUIModel & _lineModel):
shape_defn = f"""{shape}:"{name}":DBTable {{
	_fillColor=( @gradientStyle=1;, @transparency=0;, @type=1;, @color1=( 245, 182, 122, 255 ); );
	background=( 122, 207, 245, 255 );
	width={w};
	creatorDiagramType="ERDiagram";
	_captionUIModel=( @x=0;, @y=0;, @width={w};, @height=15;, @side=12;, @visible=T;, @internalWidth=-2147483648;, @internalHeight=-2147483648; );
	_elementFont=( @name="Dialog";, @color=( 0, 0, 0, 255 );, @size=11;, @style=0; );
	metaModelElement=<{model_id}:{tid}>;
	foreground=( 0, 0, 0, 255 );
	y={y};
	overrideAppearanceWithStereotypeIcon=T;
	x={x};
	_lineModel=( @cap=0;, @transparency=0;, @weight=1.0;, @color=( 0, 0, 0, 255 );, @hasStroke=T; );
	height={h};
}}"""

# 2. Child append pattern (Model & Diagram must be strictly comma-separated):
# Model: <model_id:tid>
# Diagram: <diag_id:shape_id>
# Always assert count('{') == count('}') and count('(') == count(')') after writing!
```
Place new shape at a spare (x, y) region; keep ≥30px from existing shape bounds.

## Column-block validation

To prevent corruption in `Child=(...)` trees:

1. **Validate each column block independently:**
   - Verify `{` and `}` count match per column block.
   - Verify each block ends with `}},`. A missing closure merges adjacent blocks.
2. **Back up before modifying.**

### Clean revert of an inserted entity

To remove an inserted entity cleanly without full restore:
1. `DELETE FROM DIAGRAM_ELEMENT WHERE ID = ?`
2. `DELETE FROM MODEL_ELEMENT WHERE ID = ?`
3. Strip child references (`<parent_id:child_id>`) from parent `MODEL_ELEMENT` and `DIAGRAM` definitions.

## Placement & Collision Prevention

Place shapes using 2D bounding-box checks (gap ≥ 30px).
When parsing existing coordinates from DEFINITION strings, use `(?<!@)\bx=(\d+);` and `(?<!@)\by=(\d+);` to avoid matching nested `@x=`/`@y=` in `_captionUIModel`.
ws = re.findall(r'width=(\d+);', s)       # width/height never @-prefixed
hs = re.findall(r'height=(\d+);', s)
x, y, w, h = int(xs[-1]), int(ys[-1]), int(ws[-1]), int(hs[-1])
```

**Find a free spot** (scans in y-major then x-major, 30px gap on both axes):

```python
def find_spot(existing, new_w, new_h, gap=30):
    for y in range(101, 3000, 60):
        for x in range(88, 3000, 60):
            nx1, nx2 = x, x + new_w
            ny1, ny2 = y, y + new_h
            if all(nx1 > ex2 + gap or nx2 < ex1 - gap or
                   ny1 > ey2 + gap or ny2 < ey1 - gap
                   for (ex1, ey1, ew, eh) in existing):
                return x, y
    raise RuntimeError("no free spot")
```

Where `existing` = list of `(x, y, w, h)` for every shape already on the diagram.
`gap=30` keeps shapes ≥30px apart (matches the "keep ≥30px from existing shape
bounds" sizing rule). A candidate is free only if it is clear on the **x-axis AND
y-axis** for every existing box — checking only one axis is what caused the
`DataExchangeMethod`/`DataExchangeFormat` overlap at (300,550) vs (500,550).

## Text overflow / under-sized width (real incident, fixed 2026-08-30)

A numeric bounding-box gap does **not** guarantee a visual gap. If an existing
shape's stored `width` is less than the formula width for its column count, its
attribute-name text renders **outside** the drawn box and bleeds over the neighbor.

Real case: `PeriodAccumulationType` (5 cols) stored `width=200`, but formula width
is `140+(5-1)*30 = 260`. Column names like `PeriodAccumulationTypeCode` overflowed
past x=467 and visually collided with `ReportTransmissionMode` placed at x=508 —
even though `508 > 467` on paper.

**Two rules that prevent this:**

1. **Use max(stored, formula) as the effective width when checking placement** —
   do not trust a shape's stored `width`. In the `existing` list, normalize:
   ```python
   # ncols = column count of that shape (from its DBTable DEFINITION)
   existing = [(x, y, max(w, 140 + (ncols - 1) * 30), h) for (x, y, w, h, ncols) ...]
   ```
   Best practice: also just **fix the stored width** to the formula value so the
   shape itself stops overflowing (VP re-renders clean).

2. **Use a wider x-gap for side-by-side shapes on the same row** (`gap=50` vs `30`).
   On high-DPI / different fonts, even a formula-correct width can render a few px
   wider. 50px horizontal gap absorbs that; keep 30px only for y (font height is
   fixed by `@size=11`).
