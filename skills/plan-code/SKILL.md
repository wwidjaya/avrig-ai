---
name: plan-code
description: Allocate, void, and audit avrig-ai plan codes (<CODE>-<NNNNN>) against the committed SQLite dump at plans/_plan.sql. Use before a plan branch is cut, when a draft plan is renamed to carry its code, at release, and whenever the dump, the working database, and git are suspected of disagreeing.
---

# plan-code

`plans/_plan.sql` is the durable record: a deterministic SQL dump committed to git.
`plans/_plan.db` is a local working copy, ignored by git, rebuilt from the dump.
`plans/PLAN-RULES.md` is hand written and declares `project_indicator:` in its frontmatter.

The database is a local lock and a fast index. Git stays the authority: a number exists
once its row is in a committed dump.

## Cycle

    import  ->  assign  ->  export  ->  verify

`import` loads the dump into a fresh database, `assign` adds one row, `export` rewrites
the dump, `verify` proves the three records agree.

After assignment, the row is advanced with `update`, which is its own short cycle:

    update  ->  export  ->  verify --strict

`update` never rewrites the dump itself, so the diff stays reviewable: skipping the
`export` is exactly the drift that `verify --strict` reports.

## Allocating a code at approval

Run from the project root, with `plan-code.ps1` taken from this skill directory.

1. Preview, and confirm the code is the next free one:

       pwsh -NoProfile -File plan-code.ps1 assign --dry-run --project <root> `
         --title "<plan title>" --branch "feat/{code}-<slug>" `
         --plan-path "plans/{code}-<YYYY-MM-DD>-<slug>.md"

2. The same command without `--dry-run`. It prints one JSON line carrying the code,
   the number, and the sources it consulted. Add `--issue <n>` once the feature
   request exists.

3. Rename the draft so the code comes first:

       git mv plans/<draft>.md plans/<CODE>-<NNNNN>-<date>-<slug>.md

4. Create the branch through the issue, so the two are linked:

       gh issue develop <n> --name feat/<CODE>-<NNNNN>-<slug> --base <default>

5. Record it, then prove it, then commit:

       pwsh -NoProfile -File plan-code.ps1 export --project <root>
       pwsh -NoProfile -File plan-code.ps1 verify --strict --project <root>
       git add plans/_plan.sql && git commit

`--branch` and `--plan-path` accept `{code}`, which is replaced only after the number
is chosen. Both are validated against that number before any row is written, so a
branch naming a different code or a different number fails with exit 3 and writes
nothing. The substitution is applied again inside the write transaction, against the
number the row actually receives, so a writer that loses a race still stores its own
code rather than a stale one.

## Recording delivery progress

`update` advances a row that already exists. It takes `--code` plus any of
`--status`, `--candidate-tag`, `--evidence`, `--issue`, `--release-version`, `--plan-path`,
and it writes one `allocation_event` per call. Fields you do not name are left alone. It
refuses `indicator`, `number`, `state`, `assigned_at`, `committed_at`, `voided_at`,
and `voided_reason` by name with exit 3, refuses an unknown code with exit 3, and
refuses a voided row outright, because a burned number is permanent.

`--plan-path` is the repair for a row whose path went stale when the approval rename
shortened the filename. The value must be relative and name a file directly under
`plans/` or `plans/done/`, must carry the row's own code as a full token, and must name
a file that exists, each checked with exit 3 before anything is written. `assign` has
no existence check on purpose: at assignment the file has not been renamed yet, so the
final name legitimately does not exist at that moment.

The delivery stages that use it:

| Stage | Call |
|---|---|
| 8, candidate tag | `update --code <C> --candidate-tag "<code-lower>/<NNNNN>/rc.<NNN>" --evidence plans/evidence/<CODE>-<NNNNN>/rc.<NNN> --status testing` |
| 12, UAT and version decision | `update --code <C> --status release-version-decided` (the decision, not the version: `--release-version` stays unset) |
| 13, merge | `update --code <C> --status merged` |
| 14, release tag | no `update`: no column holds a release tag, `release_version` already carries `X.Y.Z` from stage 12 and the tag is that same string, so the check is `status --json`, not a write |
| 15, deployment | `update --code <C> --status deployed` |
| 16, publication and archival | `update --code <C> --release-version <X.Y.Z> --status released`, then close the feature request |

`--issue <n>` also records the issue URL when `origin` is a GitHub remote; with any
other origin the stored URL is left as it was. After any successful `update` the dump
is stale, so run `export`, then `verify --strict`, then commit the dump.

## Commands

| Command | Purpose |
|---|---|
| `init --indicator <CODE>` | create the database, register the indicator, write the first dump. Refuses when `plans/_plan.sql` already exists. |
| `import` | delete the database and rebuild it from `plans/_plan.sql`. Exits 3 when the dump is absent: a project with no dump has never allocated anything. |
| `export [--check]` | rewrite the dump from the database. `--check` writes nothing and exits 1 when the file would change. |
| `assign` | allocate the next number. Self healing: a missing database is imported, and a project with no dump is initialised. |
| `void --code <IND-NNNNN> --reason <text>` | retire a number. The row stays, the number is never reissued. |
| `update --code <IND-NNNNN> [--status\|--candidate-tag\|--evidence\|--issue\|--release-version\|--plan-path]` | advance an existing row through the delivery stages. Refuses a voided row and every protected column. Run `export` afterwards. |
| `status [--state committed\|voided] [--json]` | list work items. `--json` emits snake_case keys. |
| `verify [--strict]` | check that the dump matches the database, that every number claimed by a plan file or a branch has a row, that every committed row's `plan_path` names a file under `plans/` or `plans/done/`, and that `PLAN-RULES.md` agrees with the database. `--strict` turns drift into exit 1. |

## Exit codes

| 0 | ok |
|---|---|
| 1 | verification or drift failure (`verify --strict`, `export --check`) |
| 2 | contention: the write lock was not acquired within the busy timeout |
| 3 | invalid input or configuration |
| 4 | git failure, including a fetch that was attempted and did not complete |

## Guarantees

- The candidate is `max(database, dump, remote dump, plan filenames, branch names) + 1`,
  filtered to the project indicator with case sensitive comparison. Branch names have
  their remote prefix removed before matching. A repository with no `origin` produces a
  warning, not a wrong number, unless `--strict-git` is given.
- Untrusted text never reaches SQL as interpolation. Titles, branches, plan paths, and
  reasons travel as a one element JSON array in a BOM free temp file, read with
  `json_each(readfile(:payload))` and lifted with `json_extract`.
- One assignment writes exactly one `work_item` row and one `allocation_event` row in a
  single `BEGIN IMMEDIATE` transaction. A refused or failed assignment writes nothing.
- One `update` writes one `allocation_event` row per call and can only reach the six
  delivery columns; the identity columns and the void columns are refused by name, and a
  voided row is never touched, so an ad hoc `UPDATE` cannot un-burn a number.
- An allocation that silently wrote zero rows is turned into exit 3, because success is
  only reported when stdout carries exactly one `<INDICATOR>-<NNNNN>` token.
- The dump is deterministic: comments, `PRAGMA user_version`, `BEGIN TRANSACTION`,
  tables ordered by name, one `INSERT` per row with an explicit column list, indexes and
  triggers last, `COMMIT`. Column lists come from `table_info`, so the generated
  `work_item.code` column is never inserted. Two exports of one database are byte
  identical, and an export after `import` reproduces the dump byte for byte.
- `--no-fetch` reads cached refs; the default fetches the default branch and treats a
  failed fetch as exit 4.

## Recovery

| Symptom | Action |
|---|---|
| `plans/_plan.db is absent` | `import` |
| `plans/_plan.sql does not match plans/_plan.db` | `export`, then commit the dump |
| a number is claimed by a file or branch but has no row | the claim was made by hand; rename the file to the allocated number, then `export` |
| `database is locked` | another allocation holds the write lock; retry |
| `init` refuses because the dump exists | run `import`; never delete a dump to re-initialise |
| `sqlite3 was not found on PATH` | install sqlite3, or set `AVRIG_SQLITE3` to the binary |

## Scope

The schema in `schema/001-plan.sql` is owned by the `edm` agent. Do not edit it here.
The tool only reads `PLAN-RULES.md`; the Architect writes it.
