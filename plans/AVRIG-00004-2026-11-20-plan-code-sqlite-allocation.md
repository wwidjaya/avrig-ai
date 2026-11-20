---
title: Plan Code Allocation via a SQLite Allocation Ledger
plan_id: AVRIG-00004
project_indicator: AVRIG
branch: feat/AVRIG-00004-plan-code-sqlite-allocation
candidate_tags: []
release_version:
status: in-progress
created: 2026-11-20
owner: Architect
tags:
  - governance
  - plan-ledger
  - tooling
  - sqlite
---

# Plan Code Allocation via a SQLite Allocation Ledger

## Goals and Objectives

Work-item codes are allocated today by reading four git sources by hand, taking the maximum, adding one, writing a ledger row, and pushing. The rule that makes this safe is prose: "recheck before writing the row, then write with nothing in between". No primitive enforces that sentence, and the actor executing it is a language model, so the rule is a hope rather than a lock. Two sessions that reach the same `max + 1` at the same moment both proceed, and the loser learns it lost only at `git push`, after it has already renamed a plan file and cut a branch.

This plan adds a real lock behind the prose: a per project SQLite database at `plans/_plan.db` that assigns the number inside a transaction at the moment of approval, with `BEGIN IMMEDIATE` serializing writers and a `UNIQUE` constraint refusing a duplicate even if serialization is bypassed.

Measurable outcomes:

- Two concurrent `assign` calls against one project produce two distinct codes, and the second is exactly one higher than the first. Under the 20 way concurrency test the same property becomes 20 distinct codes forming the contiguous run from `00004` to `00023`, measured by script rather than by inspection.
- A duplicate `(indicator, number)` insert is refused by the database with a non-zero exit and a named constraint, proven by test.
- A number that is explicitly voided after abandonment is never issued again by that database, and neither is one whose row is rekeyed or deleted, because both are refused outright, proven by test.
- `verify` detects drift between the database, the committed dump, and the git union in both directions, and exits non-zero under `--strict`.
- `export` is deterministic: two exports of one database are byte identical, and an export of an imported dump reproduces that dump byte for byte, so a committed dump diffs only when a row actually changed.
- `plans/PLAN-INDEX.md` is deleted, and no numbered fact survives outside the database: the ledger rows, the deferred defects, and the indicator aliases all live in tables, and the file's prose lives in `plans/PLAN-RULES.md`, so there is one record rather than a database shadowed by a hand-maintained table.
- Deleting `plans/_plan.db`, rebuilding it with `import` from `plans/_plan.sql`, and assigning again returns the same next number the dump implies.
- A wrong or unset payload path never produces a silent success: it exits `3` and writes no row, proven by test.

Non goal, stated plainly so it is not mistaken for one: this does not make numbering safe across machines. SQLite locks a file, and two machines hold two files. The git push rejection stays the cross machine compare and swap, and the git union stays an input to the candidate number so a stale local database jumps forward instead of reissuing. The database is a local lock and a fast index, never the archive. The archive is the committed dump, `plans/_plan.sql`, and its git history is the record.

This plan also deletes `plans/PLAN-INDEX.md` rather than maintaining it. The user's direction is that the markdown ledger is no longer needed once the database exists: keeping both would mean every allocation written twice, by two mechanisms, with the markdown as an unenforced copy. A second copy of a record is a future drift, not a backup, because the only time it is ever compared is when someone notices the numbers disagree.

## Context: what exists today

- `plans/PLAN-INDEX.md` holds the indicator (`AVRIG`), the allocation rules, the conventions, the deferred defects, and the ledger table with rows `AVRIG-00001` through `AVRIG-00004`. It is what this plan replaces and deletes: its tables become database tables, its prose becomes `plans/PLAN-RULES.md`, and its numbered rows become the seed of `plans/_plan.sql`.
- `.opencode/agents/Architect.md` holds the same rules in stage form. It is untracked in the Agentic repository (`git ls-files .opencode/agents` returns 0), a defect already deferred from `AVRIG-00003`.
- Agentic `AGENTS.md` holds the normative summary, and it is tracked.
- No allocation tooling exists anywhere. Verified: no `.ps1`, `.sh`, `.py`, `.ts`, or `.js` under `scripts/`, `tools/`, `bin/`, or `workflows/` mentions `PLAN-INDEX`, `project_indicator`, or allocation, and a `graphify` query for plan number allocation returns nothing relevant.
- `sqlite3` 3.51.2 is on `PATH` at `D:\miniconda3\envs\kb\Library\bin\sqlite3.exe`. Verified in this session: WAL mode engages, `BEGIN IMMEDIATE` works, a duplicate insert against the `UNIQUE (indicator, number)` constraint exits `1` with `UNIQUE constraint failed`.
- The DDL in this plan was executed as written against a scratch file: it applies clean, `PRAGMA integrity_check` returns `ok`, `user_version` reads `1`, all four triggers exist (`tr_allocation_event_no_update`, `tr_allocation_event_no_delete`, `tr_work_item_no_delete`, `tr_work_item_no_rekey`), and the indicator `CHECK` rejects `avrig`, `AVR IG`, `AVRIG-`, `AVRIGAVRIGAV` (12 characters) and `A` (1 character) with `CHECK constraint failed`. Amended constraints measured the same way: `ck_branch_carries_code` refuses `feat/AVRIG-00009-slug` on row `AVRIG-00001`; `created_on` refuses `20-11-2026`; a whitespace `actor_host` is refused; a `reserved` state value is refused because the vocabulary is `committed` and `voided` only; `DELETE FROM work_item` aborts with `work_item rows are permanent`, and updating either `number` or `indicator` aborts with `indicator and number are immutable once written`, while an ordinary `title` update still succeeds.
- The `assign` statement was executed exactly as written, extracted from this file with the `<temp payload path>` placeholder set and the `{code}` placeholder carried through to the statement: `git_max = 3` on an empty table produced `AVRIG-00004`, `git_max = 9` then jumped straight to `AVRIG-00010`, and after voiding `AVRIG-00010` a run with `git_max = 0` produced `AVRIG-00011`, so a burned number is never reissued and a stale database still moves forward. Both rows landed with a real branch and plan path (`feat/AVRIG-00004-plan-code-sqlite-allocation`, `plans/AVRIG-00004-2026-11-20-plan-code-sqlite-allocation.md`), no `{code}` token survived, and each call wrote one `assign` event carrying the `git_max` it used. The hostile title survived verbatim. A branch naming a code other than the one the row would receive is refused by `ck_branch_carries_code` and leaves **zero** rows written, which is why the check is worth having in the database rather than only in the wrapper.
- PostgreSQL exists (16.16 in WSL `avrig-ai`, `127.0.0.1:5432`). It was considered and rejected: numbering state is per project, the DB must live inside `plans/`, and a server dependency buys nothing a single file does not, given that neither option crosses machine boundaries.

## Key Detailed Design

### Two layers, and what each one owns

The first draft of this plan had three layers, with the markdown ledger as a rendered view of the database. The user deleted that layer: `plans/PLAN-INDEX.md` is removed, so there is nothing to render and no second copy to keep honest. Two layers remain.

| Layer | Artifact | Owns | Rebuildable |
|---|---|---|---|
| Durable archive | `plans/_plan.sql`, its git history, the approval push | truth, history, cross machine serialization | not applicable |
| Local lock | `plans/_plan.db` | assignment, contention, fast lookup | yes, from the archive via `import` |

The archive never depends on the local database. The local database is rebuilt from the archive at any time, and `verify` proves the two agree. That ordering is what keeps a lost or corrupt database from becoming a lost number.

Deleting the markdown layer deletes a class of failure rather than adding one. There is no longer a hand-editable copy that can disagree with the database, no render pass to run after every change, no marker block, and no scenario that has to prove a regeneration is byte identical to a table somebody typed by hand. What replaces it is one deterministic dump, and determinism is a property a test can assert with a hash.

The files that hold the record:

| Path | Tracked | Holds |
|---|---|---|
| `plans/_plan.sql` | yes | the whole database as plain text: schema, then one `INSERT` per row, then indexes and triggers |
| `plans/_plan.db` | no, ignored as `plans/_plan.db*` | the working database, rebuilt by `import` |
| `plans/PLAN-RULES.md` | yes | the prose that used to sit in `PLAN-INDEX.md`: indicator declaration, allocation rules, status vocabulary, conventions, reconciliation contract |

A text dump rather than the database file itself is deliberate. Git merges text, and a dump conflict is a handful of visible lines a reader can resolve; a binary database conflict cannot be resolved at all, and two branches that both allocate would produce one on every merge.

### Allocation algorithm

The candidate is `max(db_max, dump_max, remote_dump_max, filename_max, branch_max) + 1`, computed inside one `BEGIN IMMEDIATE` transaction, so a stale database whose rows lag the remote jumps forward instead of reissuing a number another machine already claimed. The payload carries that maximum as a single integer named `git_max`, because four of the five sources are read through git; the name is kept as it stands because the statement below was executed and verified under it.

1. Resolve the project root, read `project_indicator:` from the `plans/PLAN-RULES.md` frontmatter, and resolve the default branch with the four step contract below. The indicator is validated against `^[A-Z][A-Z0-9]{1,9}$` with a case sensitive match before it reaches SQL, and a value that fails exits `3` naming the offending value, because the `project` CHECK is a backstop that surfaces as a constraint error rather than as bad configuration.
2. `git fetch origin <default> --quiet` where an `origin` remote exists. A fetch that is attempted and fails exits `4` even without `--strict-git`, because `PLAN-RULES.md` makes the fetch and the recheck one indivisible step, and a stale `origin/<default>` is exactly how another machine's number gets reissued. A checkout with no `origin` remote at all, which is the shape of a fixture repository, is a warning by default and exit `4` under `--strict-git`. `--no-fetch` is the deliberate opt out, and it records that the union was read from cached refs.
3. Compute `git_max` from five sources: the database's own maximum, the local `plans/_plan.sql` maximum, the `origin/<default>` copy of `plans/_plan.sql`, the filenames in `git ls-tree -r --name-only origin/<default> -- plans/` plus local `plans/*.md` and `plans/done/**/*.md`, and `git branch --all --format=%(refname:short)`. Every source is filtered to codes whose indicator equals the declared indicator by case sensitive comparison. The dump is read exactly rather than scanned: `sqlite3 :memory: ".read '<dump>'" "SELECT MAX(number) FROM work_item WHERE indicator='<ind>';"`, and the remote copy is extracted with `git show origin/<default>:plans/_plan.sql` to a temp file first, because a dump on the remote is what another clone allocated and has not merged.
4. Write a BOM-free UTF-8 JSON payload to a temp file. The payload is a single element array whose one object carries indicator, title, branch, plan path, role, host, user, and `git_max`. The array is required rather than decorative: `json_each` over an object yields one row per member, and `json_extract` on a scalar string member then raises `malformed JSON`, so the object form fails and the one element array inserts exactly one row. The bytes must be BOM-free, because a PowerShell `-Encoding utf8` write produced a byte order mark and made the same statement fail with the same message.
5. Run one `sqlite3` invocation that inserts the assignment and selects the row it wrote.
6. Emit `code`, `number`, and `state` as machine readable output.

Step 5, in full, is the statement this plan is accountable for:

```sql
.bail on
.timeout 5000
.parameter set :payload '<temp payload path>'
PRAGMA busy_timeout = 5000;
BEGIN IMMEDIATE;

WITH payload AS (
  SELECT value AS v FROM json_each(readfile(:payload))
),
next_number AS (
  SELECT json_extract(v,'$.indicator') AS ind,
         (SELECT MAX(n) + 1 FROM (
            SELECT COALESCE((SELECT MAX(number) FROM work_item
                              WHERE indicator = json_extract(v,'$.indicator')), 0) AS n
            UNION ALL
            SELECT CAST(COALESCE(json_extract(v,'$.git_max'), 0) AS INTEGER) AS n)) AS num,
         v
    FROM payload
)
INSERT INTO work_item (indicator, number, title, state, owner_role, claiming_branch,
                       plan_path, committed_at, created_on, actor_host, actor_user)
SELECT ind, num,
       json_extract(v,'$.title'),
       'committed',
       json_extract(v,'$.role'),
       replace(json_extract(v,'$.branch'),    '{code}', ind || '-' || printf('%05d', num)),
       replace(json_extract(v,'$.plan_path'), '{code}', ind || '-' || printf('%05d', num)),
       strftime('%Y-%m-%dT%H:%M:%fZ','now'),
       strftime('%Y-%m-%d','now'),
       json_extract(v,'$.host'),
       json_extract(v,'$.user')
  FROM next_number;

INSERT INTO allocation_event (indicator, number, event, actor_role, actor_host, actor_user, detail)
SELECT indicator, number, 'assign', owner_role, actor_host, actor_user,
       'assigned at approval, git_max ' ||
       CAST(COALESCE(json_extract(readfile(:payload),'$[0].git_max'), 0) AS INTEGER)
  FROM work_item
 WHERE id = last_insert_rowid();

COMMIT;
SELECT code, number, state FROM work_item ORDER BY id DESC LIMIT 1;
```

Two properties matter here and both were measured in this session, not assumed:

- `BEGIN IMMEDIATE` takes the RESERVED lock at statement one, so writers serialize and a second writer waits rather than interleaving; it proceeds as soon as the first commits, and fails with `SQLITE_BUSY` only when the lock is still held when the 5 second timeout expires. The PowerShell wrapper maps that exit to code `2` with a "retry" message.
- `UNIQUE (indicator, number)` is the backstop if serialization is ever lost. Proven: the duplicate insert exits `1` with `UNIQUE constraint failed`. `UNIQUE (code)` is declared too, but `code` is generated from `(indicator, number)`, so that index cannot fire independently and buys a second index rather than a second guarantee.

Text never enters SQL as text. Titles and reasons travel as JSON values read with `readfile()` and lifted with `json_extract()`, which was verified to survive a title containing `It's a "quoted" title'; DROP TABLE p; --` with the table intact and the string stored verbatim. Integer fields are validated against `^\d{1,5}$` before serialization. This removes the escaping problem entirely rather than testing around it, and it is why `.parameter set` is used only for a tool generated temp path, never for user content. A tool generated path is still a CLI token rather than a safe string, though: `.parameter set` splits on whitespace, so a payload path containing a space is truncated or rejected, and a Windows temp directory under a profile whose name contains a space turns the run into an error. The payload therefore lives at a fixed space free path under the project's `plans/` folder, and the wrapper refuses any candidate path that does not match `^[^\s']+$` with exit `3`.

The payload read has one silent failure mode that must never be silent, and it was measured rather than predicted. `INSERT ... SELECT FROM json_each(readfile(:payload))` inserts nothing and exits `0` in three cases: the payload path is wrong, the parameter is unset, or the file is missing. An empty file, a BOM prefixed file, or any other malformed payload instead raises `malformed JSON` and exits `1`. A tool that trusted the exit code alone would report a successful assignment while writing no row at all. The wrapper therefore accepts an assignment only when the exit is `0` **and** stdout is exactly one `<INDICATOR>-<NNNNN>` token, and maps both the zero row outcome and the `malformed JSON` outcome to exit `3`, because both are input defects and neither is data corruption. `assign` also asserts the payload file exists before invoking `sqlite3`, and always writes it BOM free with `[IO.File]::WriteAllText($path, $json, [Text.UTF8Encoding]::new($false))`, since PowerShell `Set-Content -Encoding utf8` emits a BOM on Windows PowerShell and a BOM makes the payload invalid JSON.

`assign` is one transaction and one statement. There is no second phase: the number is written at approval, already bound to its branch and plan path, in the same `BEGIN IMMEDIATE` that computes it. A separate reservation step buys nothing once the code is only ever issued at approval, and it costs a lease, a reaper, a state transition, and a window where a number exists without a branch. `void` exists only for the deliberate abandonment case, where a committed row is marked `abandoned` with a reason and its number stays burned. `assign` accepts `{code}` inside `--branch` and `--plan-path`, and the statement replaces it with `indicator || '-' || printf('%05d', number)` before the `CHECK` runs. The placeholder is necessary rather than convenient: the number is computed inside the transaction, so the caller cannot know the code when it builds the argument, and without substitution `ck_branch_carries_code` would refuse every call and a concurrent run could never bind a branch at all. `assign` validates its inputs before it writes: `claiming_branch` must parse as `<type>/<CODE>-<NNNNN>-<slug>` with the same code the row is about to receive, optionally followed by a slice segment; `plan_path` must parse as `plans/<CODE>-<NNNNN>-<date>-<slug>.md` with the same code and no `..` segment; and `issue_number`, when supplied, must be a positive integer. Any mismatch exits `3` rather than reaching the database, because a row bound to a branch or path carrying another code is the traceability failure this ledger exists to prevent. Every state change also appends its own `allocation_event` row inside the same transaction, so the append-only table is the record the scenario table reads rather than a table nothing writes.

### Stated decisions

- Location: `plans/_plan.db`, per project, named as requested. The leading underscore sorts the binary ahead of the plan markdown rather than between two dated files. Tables carry no `project` dimension beyond a single row registry, because one project owns one database.
- Tracked or ignored: the database is ignored, the dump is tracked. `plans/_plan.db*` (including `-wal` and `-shm`) is added to `.gitignore` in the owning project, and `plans/_plan.sql` is committed. A binary file in git merges badly and a per machine lock has no business being distributed, while a text dump merges as lines a reader can resolve; `import` makes the database disposable. Confirmed by the user.
- Archive: `plans/_plan.sql`, a deterministic dump of the whole database. Committing the database file itself was considered and rejected for the same reason: two branches that both allocate would produce a binary conflict on every merge, and no human can resolve one.
- Sync caveat: `plans/` sits under OneDrive, which is not a friend of a live SQLite file. Mitigations are WAL, 5 second busy timeouts, transactions confined to a single statement plus a select, `PRAGMA integrity_check` inside `verify`, and `import` as the recovery path. `Infra` may additionally pin the file with `attrib +P` so OneDrive stops uploading it. The risk is accepted, not eliminated, and the design tolerates it because the file is rebuildable.
- Schema home: `shared/skills/plan-code/schema/001-plan.sql` in the Agentic repository, beside the tool. It is deliberately not placed in `.edm/ddl/`, which holds the platform PostgreSQL schema for `avrig_km_dev`; governance numbering is tooling state, not platform data, and filing it there would misrepresent ownership. `edm` still authors and validates the DDL.

### Schema

`PRAGMA user_version = 1` is the schema version marker, so no extra table is needed. There is deliberately no lease column. A number is written once, at approval, already bound to its branch and plan path, so there is no window in which a row exists without an owner and nothing to reap. `voided` is an explicit transition taken when a plan is abandoned, not a timeout, and the row keeps its number burned. `ck_branch_carries_code` pins the traceability rule in the database itself, so a row cannot be bound to a branch naming a different work item even by a hand written insert.

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA user_version = 1;

CREATE TABLE IF NOT EXISTS project (
  indicator      TEXT PRIMARY KEY
                 CHECK (length(indicator) BETWEEN 2 AND 10
                        AND substr(indicator,1,1) GLOB '[A-Z]'
                        AND indicator NOT GLOB '*[^A-Z0-9]*'),
  project_key    TEXT NOT NULL UNIQUE,
  repo_root      TEXT,
  frozen         INTEGER NOT NULL DEFAULT 0 CHECK (frozen IN (0,1)),
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS work_item (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator        TEXT    NOT NULL REFERENCES project(indicator) ON DELETE RESTRICT,
  number           INTEGER NOT NULL CHECK (number BETWEEN 1 AND 99999),
  code             TEXT    GENERATED ALWAYS AS (indicator || '-' || printf('%05d', number)) STORED,
  title            TEXT    NOT NULL CHECK (length(trim(title)) > 0),
  created_on       TEXT    CHECK (created_on IS NULL OR created_on GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  repos            TEXT,
  state            TEXT    NOT NULL CHECK (state IN ('committed','voided')),
  owner_role       TEXT    NOT NULL CHECK (length(trim(owner_role)) > 0),
  actor_host       TEXT    NOT NULL CHECK (length(trim(actor_host)) > 0),
  actor_user       TEXT    NOT NULL CHECK (length(trim(actor_user)) > 0),
  claiming_branch  TEXT,
  plan_path        TEXT,
  issue_number     INTEGER,
  issue_url        TEXT,
  evidence_path    TEXT,
  ledger_status    TEXT    CHECK (ledger_status IS NULL OR ledger_status IN
                     ('draft','under-review','awaiting-approval','approved','in-progress',
                      'testing','passed','release-version-decided','merged','deployed',
                      'released','abandoned')),
  candidate_tags   TEXT,
  release_version  TEXT,
  assigned_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  committed_at     TEXT,
  voided_at        TEXT,
  voided_reason    TEXT,
  CONSTRAINT uq_work_item_number UNIQUE (indicator, number),
  CONSTRAINT uq_work_item_code   UNIQUE (code),
  CONSTRAINT ck_committed_branch CHECK (state <> 'committed' OR claiming_branch IS NOT NULL),
  CONSTRAINT ck_committed_at     CHECK (state <> 'committed' OR committed_at IS NOT NULL),
  CONSTRAINT ck_voided_reason    CHECK (state <> 'voided'    OR voided_reason IS NOT NULL),
  CONSTRAINT ck_branch_carries_code
    CHECK (claiming_branch IS NULL
           OR instr(claiming_branch, indicator || '-' || printf('%05d', number)) > 0)
);

CREATE INDEX IF NOT EXISTS ix_work_item_state ON work_item (state);

CREATE TABLE IF NOT EXISTS allocation_event (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator  TEXT NOT NULL,
  number     INTEGER NOT NULL,
  event      TEXT NOT NULL CHECK (event IN ('assign','void','import','verify')),
  actor_role TEXT NOT NULL,
  actor_host TEXT NOT NULL,
  actor_user TEXT NOT NULL,
  detail     TEXT,
  at         TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- found_during holds a work item code such as AVRIG-00001 as text rather than
-- as a foreign key, because work_item.code is a generated column and SQLite
-- cannot point a foreign key at one. Do not "fix" this into a REFERENCES clause.
CREATE TABLE IF NOT EXISTS deferred_defect (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  found_during TEXT NOT NULL CHECK (length(trim(found_during)) > 0),
  defect       TEXT NOT NULL CHECK (length(trim(defect)) > 0),
  evidence     TEXT,
  at           TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS indicator_alias (
  old_code    TEXT PRIMARY KEY,
  new_code    TEXT NOT NULL,
  migrated_on TEXT
);

CREATE TRIGGER IF NOT EXISTS tr_allocation_event_no_update
BEFORE UPDATE ON allocation_event
BEGIN SELECT RAISE(ABORT, 'allocation_event is append-only'); END;

CREATE TRIGGER IF NOT EXISTS tr_allocation_event_no_delete
BEFORE DELETE ON allocation_event
BEGIN SELECT RAISE(ABORT, 'allocation_event is append-only'); END;

CREATE TRIGGER IF NOT EXISTS tr_work_item_no_delete
BEFORE DELETE ON work_item
BEGIN SELECT RAISE(ABORT, 'work_item rows are permanent; void the row instead of deleting it'); END;

CREATE TRIGGER IF NOT EXISTS tr_work_item_no_rekey
BEFORE UPDATE OF indicator, number ON work_item
BEGIN SELECT RAISE(ABORT, 'indicator and number are immutable once written'); END;
```

Number permanence is now structural, not a rule to remember. Rows are never deleted, `tr_work_item_no_delete` aborts a `DELETE` outright, `tr_work_item_no_rekey` aborts any attempt to rewrite `indicator` or `number`, and `MAX(number)` includes `voided` rows, so a burned number cannot be handed out again while the database exists. A drift case in the scenario table may therefore not simulate a ledger-only row by deleting a database row; it must edit the ledger instead and let `verify` find the difference, which is what the real world produces anyway. Permanence still holds at the level the plan claims and no higher: deleting `plans/_plan.db` resets the local lock, and the git union seeds the next number back to where it was, which is why `import` exists and why the ledger stays the durable record.

### CLI surface

One script, `plan-code.ps1`, run from any project root. Every subcommand takes `--project <root>` defaulting to the current directory, and exits `0` ok, `1` verification or drift failure, `2` contention after the busy timeout, `3` invalid input or configuration, `4` git failure, a fetch that did not complete included. `assign` takes `--title`, `--branch`, `--plan-path`, and optional `--issue`. Both path arguments accept a `{code}` placeholder, because the number is computed inside the transaction and the caller cannot know it beforehand; the statement substitutes it before the `CHECK` runs, and a `--branch` or `--plan-path` that names a different code literally is still refused. There is no lease flag, because there is no reservation to expire.

| Subcommand | Purpose |
|---|---|
| `init` | create `plans/_plan.db`, apply the schema, set `user_version`, register the indicator |
| `import` | delete `plans/_plan.db` and load `plans/_plan.sql` into it, reporting the row counts |
| `assign` | compute `max(db_max, dump_max, remote_dump_max, filename_max, branch_max) + 1`, write the row already bound to its branch and plan path, with `--dry-run` printing the candidate and writing nothing |
| `void` | mark a committed row abandoned with a reason, burning the number without deleting the row |
| `status` | list rows, filterable by state, `--json` for machines |
| `verify` | cross check the database against the committed dump and the git union, `--strict` to fail on drift |
| `export` | write `plans/_plan.sql` deterministically from the database, `--check` to fail instead of writing |

`assign` self heals: when `plans/_plan.db` is absent it runs `import` first, so a fresh clone needs no ceremony and no number is skipped.

### The committed dump

`plans/_plan.sql` is the durable record: the whole database as plain text. `export` writes it, `import` loads it, and `verify` proves the two agree. The format is pinned so that a diff means a row changed and nothing else.

- Header: three `--` comment lines naming the project and the file, then `PRAGMA user_version = <n>;` taken from the database, then `BEGIN TRANSACTION;`.
- Schema: every `CREATE TABLE` from `sqlite_master` where `type = 'table'` and the name does not begin with `sqlite_`, ordered by name, emitted exactly as stored.
- Data: one `INSERT` per line, ordered so the order is stable (`project` by `indicator`, `indicator_alias` by `old_code`, `work_item` by `number`, `allocation_event` by `id`, `deferred_defect` by `id`), each with an explicit column list.
- Indexes and triggers last, ordered by name, so loading the file never fires an append-only trigger before the data is in.
- A closing `COMMIT;`.
- Values are emitted with SQLite's own `quote()`: integers bare, `NULL` bare, text single quoted with doubled quotes. Escaping is therefore SQLite's problem rather than the tool's, and a title containing a quote, a backslash, or a semicolon round trips unchanged.
- The column list comes from `PRAGMA table_info`, which omits generated columns, so `work_item.code` is never inserted. Measured on sqlite3 3.51.2: `table_info` does not return `code` at all, while `table_xinfo` returns it with `hidden = 3`, which is why the dumper uses `table_info`.
- No export timestamp appears anywhere in the file. Determinism is what makes the dump reviewable: two exports of one database are byte identical, and an export of an imported dump reproduces that dump exactly.
- No machine specific value appears either. The `project` row's `repo_root` is written as `NULL` rather than as the absolute path `init` was handed, because the dump is committed and an absolute path would differ on every clone, machine, and worktree while telling the file nothing it cannot derive. `project_key` stays, since the folder leaf is portable and identifies the project to a human reader.

Measured on the real repository, which is the only run that counts: `init` created the database and an empty dump, the migration seeded the four rows, and `export` wrote 118 lines. `export --check` then reported no change, `verify --strict` exited `0` agreeing across the database, the dump, `PLAN-RULES.md`, and the git union, and a full round trip (`import` to rebuild from the dump, then `export`) reproduced the dump byte for byte at SHA-256 `191ECE6B...E07C49F0`. So the determinism claim is a measured fact on this project's own data rather than only on a fixture.

Driving the dumper from `sqlite_master` rather than from a hardcoded table list means a future table dumps without a code change, which matters because this schema is version 1 and will not be the last. Adding `deferred_defect` and `indicator_alias` to it during this plan is the first demonstration: the dumper needed no edit to carry them.

The prose that used to live beside the ledger table does not belong in a dump, so it moves to `plans/PLAN-RULES.md`: the indicator declaration in its frontmatter, the allocation rules, the status vocabulary, the conventions, the pre-branch reconciliation contract, and the backfill notes. The database owns numbered facts; the rules document owns the sentences that explain them. Neither duplicates the other, which is the property the deleted markdown file lost by holding both.


`import` is the load side, and it is deliberately blunt: delete `plans/_plan.db` and its `-wal` and `-shm` siblings, then apply the dump. There is no merge, no diffing, and no idempotency question, because the dump is the record and the database is a cache; rebuilding a cache from its source is not a merge. `assign` self heals by importing first when the database is absent, and by running `init` when neither file exists, so a fresh clone needs no ceremony and no number is skipped.

`verify` is what keeps the two from drifting apart. It checks three things: that `export` would not change the dump on disk, that every number in the git union is present in the database, and that `PLAN-RULES.md`'s `project_indicator:` equals the `project.indicator` row. Under `--strict` any of the three exits `1`; otherwise it reports the drift and exits `0`, because a database that is merely behind a dump somebody else committed is not an error.

The first rows in the dump are the four that exist today, and they come from the file this plan deletes. Each of the ten ledger cells has a home: `Plan` is the generated `code`, `Created` is `created_on`, `Title` is `title`, `Repos` is `repos`, `Claiming branch` is `claiming_branch` holding the code-bearing token, `Status` is `ledger_status`, `Passing candidate tag` is `candidate_tags`, `Evidence path` is `evidence_path`, `Feature request` is `issue_number` and `issue_url`, and `Release version` is `release_version`. The one cell with no structured home is `AVRIG-00001`'s candidate tag text, which carries five tags with SHAs and pass counts; it lands in `candidate_tags` verbatim, because rewriting released evidence into a stricter shape would be the worse trade. The prose cells in `AVRIG-00002` and `AVRIG-00003` that read `none yet` and `pending` disappear with the table they were written for, since a null column says the same thing without a sentence that can go stale.

The four historical rows are inserted once, by a migration kept as evidence at `plans/evidence/AVRIG-00004/migrate-legacy-ledger.sql`, because `assign` only ever writes the maximum plus one and these four already hold `00001` to `00004`. That script is not shipped as a subcommand: it runs once against an empty database built from the schema, and then `export` writes the dump. Because there is no markdown left to parse, the earlier `import` rule that scanned a ledger cell for a code-bearing token disappears with it. Each historical row still needs a real `claiming_branch`, since `ck_committed_branch` is strict again, and all four rows in the file being deleted do carry one: `feat/AVRIG-00001-agent-workflow-update`, `feat/AVRIG-00002-landing-console-unslop-redesign`, `chore/AVRIG-00003-agent-desktop-uat-tooling`, and `feat/AVRIG-00004-plan-code-sqlite-allocation`.

### Git union computation

The filename and branch forms are unchanged from the deleted ledger's rules, because they were verified there. The ledger-cell form is gone with the cell it parsed, and the dump takes its place.

- Filename: `^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<date>\d{4}-\d{2}-\d{2})-(?<slug>.+)$`, anchored, so a draft name contributes nothing.
- Dump: queried, never scanned. Three copies exist and all three count: the local database, the local `plans/_plan.sql`, and `origin/<default>:plans/_plan.sql` extracted with `git show` to a temp file. Each is read as `sqlite3 :memory: ".read '<dump>'" "SELECT COALESCE(MAX(number),0) FROM work_item WHERE indicator = '<ind>';"`.
- Branch: `<type>/(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})`, deliberately unanchored after the digits so a slug and a slice segment both parse.
- Indicator comparison uses `-cmatch` and `-ceq`. Never split a filename at a hyphen, and never scan a raw dump for five digit runs: a dump carries years, timestamps, commit SHAs inside `candidate_tags`, and issue numbers, so a loose scan over it would read one of those and jump the series permanently. The dump is queried through SQLite or it is not read at all.

Measured on 2026-11-20 in `avrig-ai`, which is why the first number is `00004`: the `origin/main` tree carries `AVRIG-00001` (under `plans/done/`), `AVRIG-00002`, and `AVRIG-00003`; local `plans/*.md` carries `00002` and `00003`; local `plans/done/` carries `00001`; local and remote branches carry `00001`, `00002`, and `00003`; and the ledger rows are `AVRIG-00001` through `AVRIG-00003`. The union maximum is therefore `3`, and `max(db_max, 3) + 1` is `00004`. The same file's illustrative examples contain `AVRIG-00007`, `AVRIG-00045`, and `AVRIG-00442` inside prose and fenced fixtures; those are the exact case the anchored regex and the indicator filter exist to discard, and a naive scan would have jumped this project to `00443` permanently. The row this plan itself wrote is `AVRIG-00004`, which is the five-source maximum exactly one greater than the four sources that existed before it.

Re-measured after the dump landed, which is the state a later plan will actually see. `assign --dry-run` against the real checkout reports `{"code":"AVRIG-00005","number":5,"db_max":4,"dump_max":4,"remote_dump_max":0,"claim_max":4}` and exits `0`, so the local database and the committed dump agree on `4` and the next number is `00005`. `remote_dump_max` is `0` with the warning `origin/main has no plans/_plan.sql; that source contributed nothing`, which is exactly right while the dump exists only on this branch: the moment it is pushed, that source stops being empty and a stale clone on another machine jumps forward instead of reissuing. The dry run wrote nothing, confirmed by the row count staying at `4`. A `{code}` placeholder probe also proved the substitution boundary: `--branch feat/AVRIG-{code}-probe` was refused with exit `3` because it substitutes the whole code and yields `AVRIG-AVRIG-00005`, so the correct form is `feat/{code}-probe`.

### Default branch resolution record

| Repository | Resolved default | Deciding step | Evidence |
|---|---|---|---|
| `avrig-ai` | `main` | step 2, corroborated by step 3 | `origin/HEAD` resolves to `origin/main`, and local `main` exists and is checked out |
| Agentic | `master` | step 4, as recorded in `AGENTS.md` | no local `main`; `origin/master` strictly contains `origin/main` (`rev-list --count origin/main..origin/master` = 32, reverse = 0), and `origin/main` last moved 2026-08-25 against `origin/master` 2026-11-19 |

A literal re-run of the contract now stops at step 5 for the Agentic repository, because three local branches exist (`master`, `chore/AVRIG-00003-agent-desktop-uat-tooling`, `feat/AVRIG-00001-agent-workflow-update`). The recorded `master` resolution is used, and confirming it is an open item below rather than an assumption.

### Pre-branch reconciliation record

Measured 2026-11-20:

| Repository | Release tags tested | Result |
|---|---|---|
| `avrig-ai` | `0.2.0`, `0.2.1`, `0.3.0`, `0.4.0`, `0.5.0` | all ancestors of `refs/heads/main`, `--is-ancestor` returned 0 for each; no merge needed |
| Agentic | none | the repository carries no SemVer tags; trivially reconciled |

Candidate tags were enumerated and excluded by rule: `avrig/00001/rc.001` through `rc.005`, `avrig/00002/rc.001`, `avrig/00003/rc.001` through `rc.003`. The gate was re-run at branch creation time after `git fetch origin --tags --prune` in both repositories, with the same result: nothing to merge.

### Feature request and branch record

Allocated and published on 2026-11-20, after user approval:

| Item | Value |
|---|---|
| Work item | `AVRIG-00004` |
| Approval commit on `main` | `8a5e5db`, carrying only the renamed plan file and `plans/PLAN-INDEX.md`, pushed as `415650d..8a5e5db` |
| Feature request | [#6](https://github.com/wwidjaya/avrig-ai/issues/6), title `AVRIG-00004 Plan Code Allocation via a SQLite Allocation Ledger`, label `enhancement` |
| `avrig-ai` branch | `feat/AVRIG-00004-plan-code-sqlite-allocation` from `main`, created and linked through `gh issue develop`, tracking `origin` |
| Agentic branch | `feat/AVRIG-00004-plan-code-sqlite-allocation` from `master`, created and linked through `gh issue develop --branch-repo`, tracking `origin` |

The issue was created before either branch, so both were created already linked. `gh issue develop --list 6` reports both, one per repository, which is the state that a branch created first with `git switch -c` could never reach. The issue body carries the plan's goals, scope, target files, and measurable outcomes, with a traceability footer whose release version line is present and deliberately empty.

The Agentic checkout was on `chore/AVRIG-00003-agent-desktop-uat-tooling`, which holds zero commits beyond `master`, so switching to the new branch was tree-neutral and its 21 tracked modifications and 75 untracked files carried across untouched. That matters because `.opencode/agents/Architect.md` is untracked and exists nowhere else, so the implementation has to happen in this checkout rather than in a clean worktree.

### Failure modes and recovery

| Failure | Symptom | Response |
|---|---|---|
| Second writer still blocked when the 5 second timeout expires | `SQLITE_BUSY` | exit `2`, caller retries; nothing was written |
| Process killed during `assign` | nothing, because the transaction either committed or rolled back | `verify` decides; a committed row is a real assignment, a rolled back one left no trace |
| Push rejected as non-fast-forward | the row is committed locally but the remote already holds the number | `void` with reason `push rejected`, then `assign` again with the refreshed remote dump in the union; the loser burns a number by design |
| Database deleted, corrupt, or stale | `verify` reports rows missing or `integrity_check` fails | delete the file, `import` reloads it from `plans/_plan.sql` |
| Database ahead of the dump | `export --check` exits `1`, `verify --strict` exits `1` | run `export` and commit the dump with the plan |
| Dump edited by hand, or another clone's dump not merged | `verify --strict` exits `1` naming the code | `import` to adopt the dump, or `export` to overwrite it, depending on which side was right |
| `sqlite3` not on `PATH` | exit `3` naming the binary | install path or `AVRIG_SQLITE3` override, reported as a setup defect not a data defect |
| Payload path wrong, unset, or file missing | `sqlite3` exits `0` having inserted nothing | wrapper requires one `<INDICATOR>-<NNNNN>` token on stdout; zero rows maps to exit `3` and the caller must not proceed |
| Payload empty, BOM prefixed, or malformed | `malformed JSON`, exit `1` | mapped to exit `3` as an input defect; the transaction did not commit |

## Target Program Files (Mandatory)

Agentic repository (default branch `master`):

| Path | Action | Owner | Purpose |
|---|---|---|---|
| `shared/skills/plan-code/SKILL.md` | create | `be` | skill body: when to allocate, the approval runbook, the exit code contract, the assign then export cycle |
| `shared/skills/plan-code/plan-code.ps1` | create | `be` | the allocator: five source union, SQLite transactions, seven subcommands |
| `shared/skills/plan-code/schema/001-plan.sql` | create | `edm` | the DDL above, five tables, four triggers, `PRAGMA user_version` |
| `shared/skills/plan-code/tests/Test-Allocation.ps1` | create | `tester` | concurrency, duplicate, injection, void, import, export determinism |
| `AGENTS.md` | edit | `be` | the allocation paragraph names the tool as the local lock, and the ledger reference moves from `PLAN-INDEX.md` to `PLAN-RULES.md` plus the dump |
| `.opencode/agents/Architect.md` | edit | `be` | stage 4 calls `assign` then `export` instead of describing a manual maximum scan, and the six `PLAN-INDEX.md` references move to `PLAN-RULES.md` |
| `.opencode/agents/analyst.md` | edit | `be` | its single `PLAN-INDEX.md` reference moves to `PLAN-RULES.md` |
| `.opencode/agents/plan.md` | edit | `be` | its single `PLAN-INDEX.md` reference moves to `PLAN-RULES.md` |
| `.opencode/agents/tester.md` | edit | `be` | its single `PLAN-INDEX.md` reference moves to `PLAN-RULES.md` |

`avrig-ai` repository (default branch `main`):

| Path | Action | Owner | Purpose |
|---|---|---|---|
| `plans/PLAN-RULES.md` | create | `Architect` | the prose from the deleted ledger: indicator declaration in its frontmatter, allocation rules, status vocabulary, conventions, reconciliation contract, backfill notes |
| `plans/_plan.sql` | create | `Architect` | the committed dump: schema, the four historical rows, and this plan's own row |
| `plans/PLAN-INDEX.md` | delete | `Architect` | replaced by the database, the dump, and `PLAN-RULES.md` |
| `.gitignore` | edit | `be` | add `plans/_plan.db*` |
| `plans/_plan.db` | runtime artifact, never committed | `be` | created by `init`, loaded by `import`, written by `assign` |
| `plans/evidence/AVRIG-00004/migrate-legacy-ledger.sql` | create | `Architect` | the one-off insert of the four historical rows, and of the six deferred defect rows, generated from the deleted table rather than retyped. `plans/evidence/**` is ignored in this repository, so it is scaffolding rather than a tracked artifact: the seeded rows are reviewable in the dump itself, and the mapping is recoverable from the file's git history |

`.opencode/agents/Architect.md` is untracked in the Agentic repository, the defect deferred from `AVRIG-00003`. The edit is therefore not reviewable through git. It is recorded with a SHA-256 manifest at `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json`, written once stage 4 assigns the code, with a `.bak-<timestamp>` sibling beside every edited instruction file, so the content is pinned and can be restored. The normative rule also lands in the tracked `AGENTS.md`, so a lost agent file degrades convenience rather than correctness.

## Parallel Execution Plan

| Stream | Owner | Scope | Depends on | Mode |
|---|---|---|---|---|
| S1 schema | `edm` | `schema/001-plan.sql`, constraint and trigger validation query set | none | starts immediately |
| S2 allocator | `be` | `plan-code.ps1`, `SKILL.md`, `.gitignore`, `AGENTS.md` | S1 for the final DDL, proceeds against the DDL in this plan meanwhile | overlaps S1, gates on it |
| S3 ledger replacement | `Architect` | `plans/PLAN-RULES.md`, deletion of `plans/PLAN-INDEX.md`, `plans/_plan.sql`, the migration evidence | the CLI contract frozen in this plan | parallel with S1 and S2 |
| S4 tests | `tester` | `tests/Test-Allocation.ps1`, `## Test Specification and Validation Scenarios`, evidence under `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/` | S4 authoring parallel, execution after S1 to S3 | author parallel, run last |
| S5 build and candidates | `build` | build gate, build id, candidate tags and pushes | S1 to S4 | sequential after S4 |
| S6 wiring | `be` | the ten `PLAN-INDEX.md` references across `AGENTS.md` and the four `.opencode/agents` definitions, rewritten to name `PLAN-RULES.md` and the tool; the Architect stage 4 runbook now calls `assign` then `export` | S2, S3 | sequential after S3 |

Sequential constraints: S1 before S2's final schema check, and S1 through S3 all complete before S4 executes. S3 and S2 are independent because the CLI contract is fully specified above, which is the point of settling it in the plan.

Stage mapping: this is Stage 1 output now, then Stage 2 analyst review and Stage 3 test scenarios in parallel, Stage 4 approval, Stage 5a reconciliation (nothing to merge, recorded above), 5b issue, 5c branches in both repositories, Stage 6 implementation on the plan branch, Stage 7 build gate, Stage 8 candidate tag `avrig/<NNNNN>/rc.001`, Stage 9 test at the tagged commit, Stage 10 remediation with a fresh tag per fix, 11 resync, 12 UAT and version decision, 13 ancestry assertion and merge, 14 release tag, 15 deployment, 16 publication and archival.

## Risks and Mitigations

- OneDrive touching a live SQLite file. Mitigated by WAL, short transactions, `integrity_check` in `verify`, and a rebuild path that makes corruption recoverable. Accepted, because the file is disposable by design.
- The database is mistaken for the archive. Mitigated in wording everywhere: `plans/_plan.sql` in git holds the record, the database holds the lock and the cache.
- Two machines still race. Mitigated by leaving the git push as the gate and by seeding the candidate from five sources including the remote dump, so a stale database jumps forward.
- A burned number from a losing race. Accepted: the existing rule already treats a failed push as the fail fast signal, and a gap is honest while a duplicate is not.
- An agent assigns without exporting. Mitigated by `verify`, whose first check is whether `export` would change the dump, so a database that is ahead of its record is reported immediately rather than at the next merge.
- The dump is edited by hand. Mitigated by the same check in the opposite direction, and by the fact that a hand edit is a line of SQL in a text diff rather than a silent database change nobody can see.
- A binary database is committed by mistake. Mitigated by `plans/_plan.db*` in `.gitignore` and by the fact that the file is regenerable, so committing it is a mistake with a one line fix rather than a corrupted history.
- Untracked agent definition. Mitigated by the SHA-256 manifest entry and by keeping the normative rule in tracked `AGENTS.md`.

## Out of Scope

- A server backed numbering authority shared across machines; a later plan if it is ever wanted.
- Changing any project indicator, and the alias mechanism.
- A Rust or TypeScript implementation of the allocator.
- Generating the ledger prose sections, which stay hand written.
- Publishing the feature request differently, or altering the release and candidate tag rules.
- Fixing the untracked `.opencode/agents/` defect, which needs its own governance plan.

## Decisions Taken at Stage 4

1. Agentic default branch is `master`, confirmed by the user. Resolution step 4 applies: the checkout is `master` while `origin/HEAD` advertises `origin/main`, no local `main` exists, and `origin/master` is 32 commits ahead of `origin/main` with nothing flowing the other way, so `main` is stale rather than parallel.
2. `plans/_plan.db` is ignored by git as `plans/_plan.db*`, confirmed. The database is a local lock and a fast index; the committed dump `plans/_plan.sql` is the durable record.
3. There is no reservation lease. The user's direction is that no reservation is needed because a number is assigned once, at approval. The design therefore writes the row already committed and already bound to its branch and plan path, in one `BEGIN IMMEDIATE`, and drops the lease columns, the reaper, the `reserved` state, the `reap` event, and the `--lease` flag. `voided` remains, but only as the explicit abandonment transition, never a timeout.
4. `.opencode/agents/Architect.md` is edited while untracked, confirmed, with a SHA-256 manifest at `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json` and `.bak-<timestamp>` siblings standing in for review. The normative rule also lands in tracked `AGENTS.md`.
5. `assign` accepts a `{code}` placeholder in `--branch` and `--plan-path`, and the statement substitutes the computed code before the `CHECK` runs. The tester raised this as a contract element the design did not state; without it a concurrent `assign` cannot satisfy `ck_branch_carries_code`, because the caller cannot know the number the transaction is about to allocate. Substitution is verified: two calls produced `feat/AVRIG-00004-...` and `feat/AVRIG-00010-...` with zero `{code}` survivors, while a literal branch naming another code is still refused.
6. **Withdrawn by decision 7.** `import` used to parse the ledger's `Claiming branch` cell for a code-bearing branch token rather than copying it, storing `NULL` when the cell carried none, and `ck_committed_branch` was widened to accept a `ledger_cells` snapshot in place of a branch. The tester raised it as a gap: today's cells all carry their code, but a historical cell reading only `main` is a legal ledger line that `ck_branch_carries_code` would refuse. It was verified at the time, and it stays here as history rather than as a rule, because there is no markdown ledger left to parse and no snapshot column left to widen.

7. `plans/PLAN-INDEX.md` is deleted at the user's direction, because the database makes the markdown ledger a second copy of the same facts and the only time a second copy is ever compared is when someone notices the numbers disagree. The ledger rows, the deferred defects, and the indicator aliases move into tables; the prose moves to `plans/PLAN-RULES.md`; the durable record becomes `plans/_plan.sql`, a deterministic text dump that git can diff and merge. Consequences: `render` is replaced by `export`, markdown `import` is replaced by "load the dump", `ledger_cells` is dropped, `ck_committed_branch` returns to its strict form, and decision 6 disappears with the mechanism it described. The dump was chosen over committing the database file because a binary conflict between two branches that both allocate cannot be resolved by a human, while a text conflict is a few visible lines.

8. `deferred_defect` and `indicator_alias` are added to the schema now rather than in a later plan, because the markdown tables that held them are being deleted in this same change and leaving their content without a home would lose it. `found_during` stores a work item code as text rather than as a foreign key, because `work_item.code` is a generated column and SQLite cannot point a foreign key at one.

9. The schema file is amended in place at `user_version = 1` instead of gaining a `002-plan.sql`. It has never shipped: it exists only on this plan branch, so a second version would record a migration that no release ever experienced. The first shipped version is therefore version 1 with five tables, and a future change is what introduces version 2.

## Test Specification and Validation Scenarios

Authored by `tester` in Stage 3. Owner of execution: `tester` at Stage 9, against a candidate tag. Eighteen cases, `T01` through `T18`. Every case names the threat it covers, the fixture it needs, the exact command, and a pass criterion a script decides without reading prose.

### Subject under test, and the tag rule

- Subject: `shared/skills/plan-code/plan-code.ps1`, `shared/skills/plan-code/schema/001-plan.sql`, `shared/skills/plan-code/SKILL.md` in the Agentic repository, plus `plans/PLAN-INDEX.md` and `.gitignore` in `avrig-ai`. The plan spans two repositories, so two SHAs are recorded and neither is inferred from the other.
- **No case may run against a working tree.** At Stage 9 the runner resolves the candidate in the repository that carries it, and tests named commits only:

```powershell
$TAG  = 'avrig/<NNNNN>/rc.<NNN>'                        # filled at Stage 8, carried by avrig-ai
$SHA  = git -C $LIVE rev-parse "$TAG^{commit}"           # a mutable tag ref is not evidence
$WT   = Join-Path $env:TEMP "opencode\plan-code\wt\$SHA"
git -C $LIVE worktree add --detach $WT $SHA
if ((git -C $WT describe --exact-match) -ne $TAG) { throw 'HEAD is not the candidate tag' }

$TOOL = 'D:\Cloud\OneDrive\AI\Agentic'                   # the tool repository
$TSHA = git -C $TOOL rev-parse HEAD                      # recorded, not assumed to match $SHA
```

- Every result line names `$TAG`, `$SHA`, and `$TSHA`. A run whose evidence folder does not name all three is not evidence, whatever its exit code. A tool checkout that is dirty (`git -C $TOOL status --porcelain -- shared/skills/plan-code` non empty) is `BLOCKED`, because the files under test would then not correspond to either SHA.

### Resolved environment, used verbatim below

| Fact | Value | Consequence for these scenarios |
|---|---|---|
| Shell | `pwsh` 7.7.0, Windows | `Start-Process -ArgumentList` quoting is reliable at 7.3 and above, so parallel launches need no manual quote repair |
| `sqlite3` | 3.51.2, `D:\miniconda3\envs\kb\Library\bin\sqlite3.exe`, on `PATH` | constraint and trigger proofs can call `sqlite3` directly, no driver needed |
| Test module | Pester 3.4.0 is installed but never used | Pester 5 syntax is unavailable, so the harness carries its own assertions and imports no Pester at all; the 3.4.0 module is neither required nor referenced |
| `avrig-ai` default | `main` | fixture repos are initialised with `git init -b main` |
| Agentic default | `master` | the tool's own repo skills are not exercised by these scenarios, only its `plan-code.ps1` |
| `avrig-ai` git union max | `AVRIG-00003` | a correct first allocation from the live tree is `AVRIG-00004` |
| Temp root | `$env:TEMP` = `C:\Users\wwidj\AppData\Local\Temp` | fixtures live under `$env:TEMP\opencode\plan-code`, never under OneDrive |
| BOM hazard as stated in the plan | claimed to make `json_each(readfile())` fail with `malformed JSON` | it does not reproduce on this host; see C3. The actual failure is the query shape, C1 | T07 pins the measured behaviour instead of the claimed one |

### Measured corrections to the plan, found while validating the fixtures

These were run in `$env:TEMP\opencode\plan-code\validate` against `sqlite3` 3.51.2 and `pwsh` 7.7.0 before these scenarios were written. Each one contradicts a statement in this plan, so a test written from the plan text would fail on correct software. `be` and `edm` must settle them in S1 and S2; `analyst` folds them into `## Review Findings`.

| # | Plan says | Measured | Consequence |
|---|---|---|---|
| C1 | `json_extract(value,'$.indicator') ... FROM json_each(readfile(:payload))` with an object payload | succeeds with a single element array `[{...}]`, exit `0`. With an object `{...}` it fails, `Runtime error near line 3: malformed JSON`, exit `1`, because `json_each` returns one row per member and each `value` is then parsed as JSON alone | resolved in the design by requiring the array payload; verified. The scenario table pins the array and asserts the object form fails, so nobody reintroduces it |
| C2 | a constraint violation exits `1` | exits `19`, `SQLITE_CONSTRAINT`. Exit `1` is `SQLITE_ERROR`, which is syntax and `malformed JSON` | T02 asserts `19` for constraints and `1` for the error class, so neither is confused with the other |
| C3 | a BOM prefixed payload raises `malformed JSON`, per the failure modes table | measured: `[{...}]` with a leading `239,187,191` parses and returns its title, exit `0`. An **empty** file raises `malformed JSON` at exit `1`, which is a different row | the BOM row of that table is wrong as written and needs amending to "empty, truncated, or malformed". Writing BOM free stays the rule, and T07 asserts what actually happens rather than the claim |
| C4 | dot commands can be issued inside one `sqlite3` invocation alongside SQL | passing `.bail on`, `.parameter set`, and SQL as a single argument fails with `Usage: .bail on|off`, because an argument is one statement | the allocator must write a `.sql` file and use `.read`, or pipe the script on stdin; both were verified to work |

### Harness contract

One file, `shared/skills/plan-code/tests/Test-Allocation.ps1`, authored by `tester`, no Pester dependency.

```powershell
param(
  [string]$Project = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ai',
  [string]$Out     = 'plans/evidence/<CODE>-<NNNNN>/rc.<NNN>',
  [string[]]$Case  = @('T01','T02','T03','T04','T05','T06','T07','T08',
                       'T09','T10','T11','T12','T13','T14','T15','T16','T17','T18')
)
```

Runner constants, fixed for every case:

```powershell
$TOOL = 'D:\Cloud\OneDrive\AI\Agentic'
$PC   = "$TOOL\shared\skills\plan-code\plan-code.ps1"
$DDL  = "$TOOL\shared\skills\plan-code\schema\001-plan.sql"
$PW   = Join-Path $PSHOME 'pwsh.exe'
$SQL  = 'D:\miniconda3\envs\kb\Library\bin\sqlite3.exe'
$TMP  = Join-Path $env:TEMP 'opencode\plan-code'
$LIVE = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ai'
```

Invocation wrapper, because `& $PC` runs a `.ps1` in process and `exit 3` would kill the runner:

```powershell
function Invoke-Pc([string]$Proj, [string[]]$Arg) {
  $o = & $PW -NoProfile -File $PC @Arg --project $Proj 2>&1
  [pscustomobject]@{ Exit = $LASTEXITCODE; Out = (@($o) -join "`n") }
}
function Assert-Equal($Expected, $Actual, [string]$What) {
  if ("$Expected" -cne "$Actual") { throw "$What : expected [$Expected] got [$Actual]" }
}
function Assert-Match([string]$Text, [string]$Pattern, [string]$What) {
  if ($Text -notmatch $Pattern) { throw "$What : no match for /$Pattern/ in [$Text]" }
}
function Get-Code([string]$Out) {
  $m = [regex]::Match($Out, '"code"\s*:\s*"(?<c>[A-Z][A-Z0-9]{1,9}-\d{5})"')
  if (-not $m.Success) { throw "no code in output: $Out" }
  $m.Groups['c'].Value
}
```

Output contract, machine readable, one line per case plus a rollup:

```text
T01 PASS 13/13  tag=avrig/<NNNNN>/rc.<NNN> sha=<SHA> tsha=<TSHA>
T03 FAIL 4/7  tag=... sha=... tsha=... reason=distinct codes 19 of 20
ROLLUP 17/18 PASS exit=1
```

The runner exits `0` only when every selected case is `PASS` with zero failed assertions. Any `FAIL` exits `1`. A case that throws before its first assertion counts as `FAIL 0/n`, never as skipped.

### CLI contract these scenarios assume

The plan fixes seven subcommands, `init`, `import`, `assign`, `void`, `status`, `verify`, `render`, together with `--project`, `--dry-run`, `--json`, `--strict`, `--check`, `--no-fetch`, `--strict-git`, and the exit codes. There is no `reserve`, no `commit`, no reaper, no `--lease`, and no `--lease-token`: a number is written once, at approval, already `committed` and already bound to its branch and plan path, inside one `BEGIN IMMEDIATE`. The cases below additionally assume these flags. They are pinned here so the harness and `be` agree before execution; a deviation is a contract defect reported before the run, never silently adapted inside the harness.

| Flag | Subcommand | Meaning |
|---|---|---|
| `--indicator <CODE>` | `init`, `import`, `assign` | declare or confirm the indicator; must equal the ledger's `project_indicator` |
| `--title <text>` | `assign` | work item title, untrusted |
| `--role <text>` | `assign` | owner role |
| `--branch <ref>` | `assign` | claiming branch; must carry the code the row receives; the literal token `{code}` is substituted with that code inside the transaction |
| `--plan-path <path>` | `assign` | repo relative plan path under `plans/`, ending `.md`, carrying the same code; `{code}` as above |
| `--issue <n>` | `assign` | feature request number, a positive integer |
| `--dry-run` | `assign` | print the candidate and write nothing |
| `--code <IND-NNNNN>` | `void` | target row |
| `--reason <text>` | `void` | untrusted void reason |
| `--state <s>` | `status` | filter rows by state |

The `{code}` token is not decoration. `assign` computes the number inside its own transaction, so a caller that binds a branch cannot know it in advance, and `ck_branch_carries_code` refuses a row bound to a branch naming a different work item. `assign` substitutes the token, then validates the substituted branch and path against the number it just computed, and the database check verifies the result a second time. T03 and T14 use the token, because neither can know the number beforehand; T04, T05, T08, T13, and T15 pass a literal code, so the substitution is never the only form proven. A `be` implementation that rejects the token makes T03 and T14 `BLOCKED` at Stage 9 rather than silently unexecutable, and the report must say so.

`void` carries no token and no lease. It moves one `committed` row to `voided` with a reason and burns the number, and it never runs on a timer. The retired event names `reserve`, `commit`, and `reap` are not writable at all, because the `state` vocabulary is `committed` and `voided` and the event vocabulary is `assign`, `void`, `import`, and `verify`.

`status --json` emits one object per row with the column names the table uses, snake case, so `code`, `number`, `state`, `claiming_branch`, `plan_path`, and `voided_reason` are read back under those names, and `voided_reason` is `null` on a live row. T15 and T17 assert those names, so a camel case renderer fails there rather than inside a reviewer's head.

### Fixture builder

Every case that must be deterministic uses a fresh fixture, never the live repo, so no real number is consumed.

```powershell
function New-FixtureRepo([string]$Path, [int]$LedgerMax = 3) {
  Remove-Item -Recurse -Force $Path -ErrorAction SilentlyContinue
  New-Item -ItemType Directory -Force (Join-Path $Path 'plans\done') | Out-Null
  $origin = "$Path-origin.git"
  Remove-Item -Recurse -Force $origin -ErrorAction SilentlyContinue
  git init -q --bare $origin
  git -C $Path init -q -b main
  git -C $Path config user.email t@example.invalid
  git -C $Path config user.name tester
  git -C $Path remote add origin $origin

  # the Claiming branch cell carries the row's own code, because import lifts that cell
  # into claiming_branch and ck_branch_carries_code applies to imported rows as well
  $rows = @()
  for ($n = 1; $n -le $LedgerMax; $n++) {
    $rows += ('| AVRIG-{0:D5} | 2026-11-20 | Fixture {0} | avrig-ai | feat/AVRIG-{0:D5}-fixture | approved | none yet | pending | pending | empty |' -f $n) }
  $md = @(
    '---',
    'title: Plan Index',
    'project_indicator: AVRIG',
    '---',
    '# Plan Index',
    '',
    '<!-- BEGIN GENERATED LEDGER -->',
    '| Plan | Created | Title | Repos | Claiming branch | Status | Passing candidate tag | Evidence path | Feature request | Release version |',
    '|---|---|---|---|---|---|---|---|---|---|'
  ) + $rows + @('<!-- END GENERATED LEDGER -->', '')
  [IO.File]::WriteAllText((Join-Path $Path 'plans\PLAN-INDEX.md'), ($md -join "`n"), [Text.UTF8Encoding]::new($false))

  for ($n = 1; $n -le $LedgerMax; $n++) {
    if ($n -eq 1) { $p = Join-Path $Path 'plans\done\AVRIG-00001-2026-11-20-fixture-one.md' }
    else          { $p = Join-Path $Path ('plans\AVRIG-{0:D5}-2026-11-20-fixture-{0}.md' -f $n) }
    [IO.File]::WriteAllText($p, "# fixture $n`n", [Text.UTF8Encoding]::new($false)) }
  [IO.File]::WriteAllText((Join-Path $Path 'plans\2026-11-20-uncoded-draft.md'), "# draft`n",
                          [Text.UTF8Encoding]::new($false))
  git -C $Path add -A; git -C $Path commit -q -m fixture; git -C $Path push -q -u origin main
  if ($LedgerMax -ge 1) {
    git -C $Path branch ("feat/AVRIG-{0:D5}-fixture-branch" -f $LedgerMax) | Out-Null
    git -C $Path push -q origin ("feat/AVRIG-{0:D5}-fixture-branch" -f $LedgerMax) }
}
```

Baseline state: ledger rows `AVRIG-00001..0000N`, coded filenames for the same numbers, one plan branch, one uncoded draft, a bare `origin` on disk so `fetch` succeeds offline. Union max equals `$LedgerMax`, so the first allocation is `AVRIG-{LedgerMax+1}`. Every case below starts from `New-FixtureRepo $repo 3` and therefore expects `AVRIG-00004` unless it says otherwise. `New-FixtureRepo $repo 0` yields no ledger row, no coded file, and no branch, so `git_max` is `0`; T06 uses it to prove that a voided number is not reissued from a zero union. The `Claiming branch` cell names the row's own code, because `import` lifts that cell into `claiming_branch` and `ck_branch_carries_code` applies to an imported row exactly as it does to an assigned one.

### Scenario table

#### T01 Schema creation and integrity

Threat: `init` ships an incomplete schema, so a later constraint proof passes vacuously because the constraint was never created.

Fixture: `$repo = "$TMP\t01"; New-FixtureRepo $repo 3`.

```powershell
$repo = "$TMP\t01"; New-FixtureRepo $repo 3
$db = "$repo\plans\_plan.db"
Assert-Equal 0 (Invoke-Pc $repo @('init','--indicator','AVRIG')).Exit 'init exit'
Assert-Match ([IO.File]::ReadAllText($DDL)) 'PRAGMA user_version\s*=\s*1' 'the shipped DDL declares version 1'
Assert-Equal 1 (& $SQL -noheader $db 'PRAGMA user_version;') 'user_version'
Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity_check'
Assert-Equal 'wal' (& $SQL -noheader $db 'PRAGMA journal_mode;') 'journal_mode'
$t = (& $SQL -noheader $db "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;") -join ','
Assert-Equal 'allocation_event,project,work_item' $t 'tables'
$i = (& $SQL -noheader $db "SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name;") -join ','
Assert-Equal 'ix_work_item_state' $i 'indexes'
Assert-Equal 'state' (& $SQL -noheader $db "SELECT name FROM pragma_index_info('ix_work_item_state');") 'the one index is on state, not on an expiry column'
$g = (& $SQL -noheader $db "SELECT name FROM sqlite_master WHERE type='trigger' ORDER BY name;") -join ','
Assert-Equal 'tr_allocation_event_no_delete,tr_allocation_event_no_update,tr_work_item_no_delete,tr_work_item_no_rekey' $g 'triggers'
Assert-Equal 'AVRIG' (& $SQL -noheader $db 'SELECT indicator FROM project;') 'project row'
Assert-Equal 3 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name IN ('created_on','repos','ledger_cells');")) 'render source columns exist'
Assert-Equal 1 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name='assigned_at';")) 'assigned_at exists'
Assert-Equal 0 ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM pragma_table_info('work_item') WHERE name IN ('lease_token','lease_expires_at','reserved_at');")) 'no lease column survived the design change'
```

Pass: 13 assertions green, `exit 0`, `user_version` exactly `1`, `integrity_check` exactly `ok`, exactly one user index, `ix_work_item_state`, whose only column is `state`, all four triggers present by name, one `project` row carrying `AVRIG`, the three render source columns present, `assigned_at` present, and `lease_token`, `lease_expires_at`, and `reserved_at` all absent. That last assertion is the column level statement of the no reservation decision: a reservation column that crept back in fails here before any behavioural case can be written against it. Fixture: the database file is absent before the call. A green T01 does not prove the constraints work, only that they exist; T02 does that.

#### T02 Constraint proof, table driven

Threat: a `CHECK` or `UNIQUE` is written in a form SQLite accepts but never fires, so invalid state reaches the durable ledger.

Fixture: `$repo = "$TMP\t02"`, `New-FixtureRepo`, `init`, then one valid `project` row, one valid `committed` `work_item` row with `number = 4`, and one `assign` event on that row. Each probe runs in its own `sqlite3` call so one failure does not mask the next. `PRAGMA foreign_keys` is a per connection setting, so case (m) is the one probe that runs with `-cmd 'PRAGMA foreign_keys=ON;'`; every other case runs without it. The baseline row is a full `committed` row, bound to `feat/AVRIG-00004-baseline` and `plans/AVRIG-00004-2026-11-20-baseline.md` with `committed_at` and `created_on` set, because the two committed checks and `ck_branch_carries_code` leave no legal partially filled shape to seed. The event row is seeded for one reason only: `tr_allocation_event_no_update` and `tr_allocation_event_no_delete` fire per row, so an `UPDATE` or `DELETE` over an empty table exits `0` and would grade a trigger that never ran. Every insert probe names its own `number`, so no probe is silently graded against `uq_work_item_number` instead of the constraint it names; case (a) is the one duplicate by design.

| # | Insert or update | Must be refused by | Expected text |
|---|---|---|---|
| a | second row `('AVRIG',4,...)` | `uq_work_item_code`, measured, see note | `UNIQUE constraint failed` |
| b | assert both `uq_work_item_number` and `uq_work_item_code` appear in the stored `work_item` DDL | structural, see note | both names present in `sqlite_master.sql` |
| c | `state = 'pending'`, `number = 5` | `work_item.state` CHECK | `CHECK constraint failed` |
| c2 | `state = 'reserved'`, `number = 6`, the value the design dropped | the same CHECK, which admits `committed` and `voided` only | `CHECK constraint failed` |
| d | `title = ''`, `number = 7` | `work_item.title` CHECK | `CHECK constraint failed` |
| e | `title = '   '`, `number = 8` | same CHECK via `trim` | `CHECK constraint failed` |
| f | `number = 0` | `number BETWEEN 1 AND 99999` | `CHECK constraint failed` |
| g | `number = 100000` | same CHECK | `CHECK constraint failed` |
| h | `indicator = 'avrig'` on `project` | `substr(indicator,1,1) GLOB '[A-Z]'` | `CHECK constraint failed` |
| i | `indicator = 'AVR IG'` on `project` | `NOT GLOB '*[^A-Z0-9]*'` | `CHECK constraint failed` |
| j | `indicator = 'AVRIG-'` on `project` | same | `CHECK constraint failed` |
| k | `indicator = 'AVRIG123456'` (11 chars) on `project` | `length BETWEEN 2 AND 10` | `CHECK constraint failed` |
| l | `indicator = 'A'` (1 char) on `project` | same | `CHECK constraint failed` |
| m | work item with `indicator = 'WEB'` absent from `project` | foreign key, for this probe only, because `PRAGMA foreign_keys` is per connection | `FOREIGN KEY constraint failed` |
| n | `state = 'committed'` with `claiming_branch IS NULL`, `number = 9` | `ck_committed_branch` | `CHECK constraint failed` |
| o | `state = 'committed'` with a branch carrying its own code but `committed_at IS NULL`, `number = 10` | `ck_committed_at` | `CHECK constraint failed` |
| p | `state = 'voided'` with `voided_reason IS NULL`, `number = 11` | `ck_voided_reason` | `CHECK constraint failed` |
| q | `project.frozen = 2` | `frozen IN (0,1)` | `CHECK constraint failed` |
| r | `allocation_event.event = 'reserve'`, a retired name | `event IN ('assign','void','import','verify')` | `CHECK constraint failed` |
| s | `UPDATE allocation_event SET detail='x'` | `tr_allocation_event_no_update` | `allocation_event is append-only` |
| t | `DELETE FROM allocation_event` | `tr_allocation_event_no_delete` | same text |
| u | `DELETE FROM work_item WHERE number=4` | `tr_work_item_no_delete` | `work_item rows are permanent` |
| v | `UPDATE work_item SET number=5 WHERE number=4` | `tr_work_item_no_rekey` | `indicator and number are immutable` |
| w | `UPDATE work_item SET indicator='AVRIH' WHERE number=4` | same trigger, because `UPDATE OF indicator, number` covers both | `indicator and number are immutable` |
| z1 | `owner_role = ''`, `number = 12` | `owner_role` non-empty CHECK | `CHECK constraint failed` |
| z3 | `actor_host = ''`, `number = 13` | `actor_host` non-empty CHECK | `CHECK constraint failed` |
| z4 | `actor_user = '  '`, `number = 14` | `actor_user` non-empty CHECK | `CHECK constraint failed` |
| aa | `number = 15`, `state='committed'`, branch `feat/AVRIG-00009-other`, `committed_at` set | `ck_branch_carries_code`, because the branch names a code other than `AVRIG-00015` | `CHECK constraint failed` |
| ab | `created_on = '20-11-2026'`, `number = 16` | the `created_on` GLOB CHECK | `CHECK constraint failed` |

```powershell
$repo = "$TMP\t02"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
& $SQL -bail $db @"
INSERT INTO project (indicator,project_key) VALUES ('AVRIG','avrig-ai');
INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,committed_at,created_on,actor_host,actor_user)
VALUES ('AVRIG',4,'baseline','committed','Architect','feat/AVRIG-00004-baseline',
        'plans/AVRIG-00004-2026-11-20-baseline.md','2026-11-20T00:00:00.000Z','2026-11-20','h','u');
INSERT INTO allocation_event (indicator,number,event,actor_role,actor_host,actor_user,detail)
VALUES ('AVRIG',4,'assign','Architect','h','u','baseline row');
"@
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'baseline row seeded'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'baseline event seeded, so the append-only triggers have a row to fire on'

# a legal committed row, mutated by the named field, so every probe is graded on one constraint
function Sql-Row([int]$Number, [hashtable]$Over = @{}) {
  $f = [ordered]@{
    Indicator = 'AVRIG'; Title = "probe $Number"; State = 'committed'; Role = 'Architect'
    Branch    = ('feat/AVRIG-{0:D5}-probe' -f $Number)
    PlanPath  = ('plans/AVRIG-{0:D5}-2026-11-20-probe.md' -f $Number)
    CommittedAt = '2026-11-20T00:00:00.000Z'; CreatedOn = '2026-11-20'; Host = 'h'; User = 'u' }
  foreach ($k in $Over.Keys) { $f[$k] = $Over[$k] }
  $vals = @($f.Indicator, $Number, $f.Title, $f.State, $f.Role, $f.Branch, $f.PlanPath,
            $f.CommittedAt, $f.CreatedOn, $f.Host, $f.User) |
          ForEach-Object { if ($null -eq $_) { 'NULL' } elseif ($_ -is [int]) { "$_" } else { "'" + ($_ -replace "'","''") + "'" } }
  'INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,' +
  'committed_at,created_on,actor_host,actor_user) VALUES (' + ($vals -join ',') + ');'
}

$rows = @(
  @{ Id='02a';  Number=4;      Over=@{} }
  @{ Id='02c';  Number=5;      Over=@{ State='pending' } }
  @{ Id='02c2'; Number=6;      Over=@{ State='reserved' } }
  @{ Id='02d';  Number=7;      Over=@{ Title='' } }
  @{ Id='02e';  Number=8;      Over=@{ Title='   ' } }
  @{ Id='02f';  Number=0 }
  @{ Id='02g';  Number=100000 }
  @{ Id='02n';  Number=9;      Over=@{ Branch=$null } }
  @{ Id='02o';  Number=10;     Over=@{ CommittedAt=$null } }
  @{ Id='02p';  Number=11;     Over=@{ State='voided'; Branch=$null; CommittedAt=$null } }
  @{ Id='02z1'; Number=12;     Over=@{ Role='' } }
  @{ Id='02z3'; Number=13;     Over=@{ Host='' } }
  @{ Id='02z4'; Number=14;     Over=@{ User='  ' } }
  @{ Id='02aa'; Number=15;     Over=@{ Branch='feat/AVRIG-00009-other' } }
  @{ Id='02ab'; Number=16;     Over=@{ CreatedOn='20-11-2026' } }
  @{ Id='02m';  Number=1;      Over=@{ Indicator='WEB'; Branch='feat/WEB-00001-fk'
                                       PlanPath='plans/WEB-00001-2026-11-20-fk.md' }
                                Extra=@('-cmd','PRAGMA foreign_keys=ON;') }
) | ForEach-Object {
  $_.Sql  = (Sql-Row $_.Number $_.Over)
  $_.Text = if ($_.Id -eq '02a') { 'UNIQUE constraint failed' }
            elseif ($_.Id -eq '02m') { 'FOREIGN KEY constraint failed' }
            else { 'CHECK constraint failed' }
  $_ }

$statements = @(
  @{ Id='02h'; Sql="INSERT INTO project (indicator,project_key) VALUES ('avrig','k-h');" }
  @{ Id='02i'; Sql="INSERT INTO project (indicator,project_key) VALUES ('AVR IG','k-i');" }
  @{ Id='02j'; Sql="INSERT INTO project (indicator,project_key) VALUES ('AVRIG-','k-j');" }
  @{ Id='02k'; Sql="INSERT INTO project (indicator,project_key) VALUES ('AVRIG123456','k-k');" }
  @{ Id='02l'; Sql="INSERT INTO project (indicator,project_key) VALUES ('A','k-l');" }
  @{ Id='02q'; Sql='UPDATE project SET frozen = 2;' }
  @{ Id='02r'; Sql="INSERT INTO allocation_event (indicator,number,event,actor_role,actor_host,actor_user) VALUES ('AVRIG',4,'reserve','Architect','h','u');" }
  @{ Id='02s'; Sql="UPDATE allocation_event SET detail = 'x';" }
  @{ Id='02t'; Sql='DELETE FROM allocation_event;' }
  @{ Id='02u'; Sql='DELETE FROM work_item WHERE number = 4;' }
  @{ Id='02v'; Sql='UPDATE work_item SET number = 5 WHERE number = 4;' }
  @{ Id='02w'; Sql="UPDATE work_item SET indicator = 'AVRIH' WHERE number = 4;" }
) | ForEach-Object {
  $_.Text = if ($_.Id -in @('02s','02t')) { 'allocation_event is append-only' }
            elseif ($_.Id -eq '02u') { 'work_item rows are permanent' }
            elseif ($_.Id -in @('02v','02w')) { 'indicator and number are immutable' }
            else { 'CHECK constraint failed' }
  $_ }

# (b) both unique constraints are structural: code is generated from (indicator, number)
Assert-Equal 2 ([int](& $SQL -noheader $db "SELECT (sql LIKE '%uq_work_item_number%') + (sql LIKE '%uq_work_item_code%') FROM sqlite_master WHERE type='table' AND name='work_item';")) 'both unique constraints present in the DDL'

foreach ($c in @($rows) + @($statements)) {
  $sa = @('-bail') + @($c.Extra | Where-Object { $_ }) + @($db, $c.Sql)
  $o = (& $SQL @sa 2>&1) -join "`n"
  if ($LASTEXITCODE -ne 19) { throw "$($c.Id) : sqlite3 exit $LASTEXITCODE, expected 19 (SQLITE_CONSTRAINT): $o" }
  if ($o -notmatch [regex]::Escape($c.Text)) { throw "$($c.Id) : expected [$($c.Text)] in [$o]" }
}
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'only baseline row survives'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'only baseline event survives'
Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE state NOT IN ('committed','voided');") 'no retired state value reached a row'
Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after refusals'
```

Pass: 28 refusal probes each exit `19` with their expected text, plus one structural check on the stored DDL, `work_item` still holds exactly the one baseline row and `allocation_event` exactly one row, no row carries a state outside `committed` and `voided`, and `integrity_check` is still `ok`. Case (c2) is the one that pins the design change: `reserved` is not a state any more, so a design that quietly kept the lease vocabulary fails here rather than at the first assignment. Note on (a) and (b): `code` is `GENERATED ALWAYS ... STORED` from `(indicator, number)`, so the two unique constraints are logically redundant and neither can fire alone. Measured: the duplicate insert fails on `work_item.code`, so `uq_work_item_number` never appears in an error message. The scenario table therefore asserts both constraint names in the stored DDL plus one real `UNIQUE` failure, which is the honest maximum, rather than pretending each fires independently.

#### T03 Twenty way concurrency

Threat: two sessions reach the same `max + 1`; the loser discovers it after renaming a plan file and cutting a branch. This is the case the whole plan exists for.

Fixture: `$repo = "$TMP\t03"`, `New-FixtureRepo $repo 3`, `init`, then 20 records prepared before launch so process start jitter does not serialize the writers.

```powershell
$repo = "$TMP\t03"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"; $out = "$TMP\t03\out"; New-Item -ItemType Directory -Force $out | Out-Null

function Start-Assign([int]$i) {
  $a = @('-NoProfile','-File',$PC,'assign','--title',"concurrent $i",'--role','Architect',
         '--branch',"feat/{code}-race-$i",'--plan-path',"plans/{code}-2026-11-20-race-$i.md",
         '--project',$repo)
  Start-Process -FilePath $PW -ArgumentList $a -PassThru -WindowStyle Hidden `
    -RedirectStandardOutput "$out\$i.out" -RedirectStandardError "$out\$i.err"
}
$procs = 1..20 | ForEach-Object { Start-Assign $_ }
$procs | ForEach-Object { $_.WaitForExit(); $_.WaitForExit() }   # second call lets redirected streams flush

# documented retry: exit 2 means nothing was written, so re-running is safe
$retries = 0
foreach ($p in $procs) {
  if ($p.ExitCode -eq 2) {
    $retries++
    $i = [array]::IndexOf($procs, $p) + 1
    $again = Start-Assign $i; $again.WaitForExit(); $again.WaitForExit()
    if ($again.ExitCode -ne 0) { throw "T03 : pid $i retried to exit $($again.ExitCode)" }
  } elseif ($p.ExitCode -ne 0) { throw "T03 : pid exit $($p.ExitCode)" }
}
$stderr = (Get-ChildItem "$out\*.err" | Get-Content -Raw) -join "`n"
if ($stderr -match 'Exception|NativeCommandError|malformed JSON') { throw "T03 : stderr carries an exception: $stderr" }
if ($stderr -match 'SQLITE_BUSY') { 'T03 : SQLITE_BUSY printed on stderr, retries=' + $retries }

# {code} is substituted inside the transaction, so each process could bind a branch it could
# not have known before the race, and every row is still bound to a branch naming itself
$codes = Get-ChildItem "$out\*.out" | ForEach-Object {
  $m = [regex]::Match((Get-Content $_ -Raw), '"code"\s*:\s*"(?<c>[A-Z][A-Z0-9]{1,9}-\d{5})"')
  if ($m.Success) { $m.Groups['c'].Value } } | Sort-Object -Unique
$want = 4..23 | ForEach-Object { 'AVRIG-{0:D5}' -f $_ }
Assert-Equal 20 $codes.Count 'distinct codes'
Assert-Equal 0 (Compare-Object $codes $want).Count 'set equals 00004..00023'
Assert-Equal 20 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE state='committed';") 'committed rows'
Assert-Equal 20 (& $SQL -noheader $db 'SELECT COUNT(DISTINCT code) FROM work_item;') 'distinct codes in db'
Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE instr(claiming_branch, code) = 0;') 'every row carries its own code in its branch'
Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE instr(plan_path, code) = 0;') 'every row carries its own code in its plan path'
Assert-Equal 20 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign';") 'one assign event per row'
Assert-Equal '4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23' `
  ((& $SQL -noheader $db 'SELECT group_concat(number) FROM (SELECT number FROM work_item ORDER BY number);') -replace "`n",'') 'contiguous series'
Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after concurrency'
"{0}" -f "T03 retries=$retries"
```

Pass: all 20 processes end at exit `0`, retries allowed only for exit `2` and recorded in the result line, the distinct code set equals `AVRIG-00004` through `AVRIG-00023` exactly once each, all 20 rows are `committed`, each row's `claiming_branch` and `plan_path` carry that row's own code, there are exactly 20 `assign` events and no other, numbers are contiguous with no gap and no duplicate, `integrity_check` is `ok`, and no `SQLITE_BUSY` reaches a caller as an unhandled exception. The `{code}` token is what makes this case expressible at all: without it, a process would have to name the code before the lock decided it, and `ck_branch_carries_code` would refuse every row but the winner's.

Part b, OneDrive file path. Same script, `$repo = 'D:\Cloud\OneDrive\AI\Agentic\plan-code-t03'`, torn down with `Remove-Item -Recurse -Force` at the end. This is the same assertion set run against a synced folder, because the plan accepts that hazard rather than eliminating it. Pass requires the same result; a failure here is reported as an accepted-risk finding naming the retry count, not as a silent pass.

#### T04 Git union seeds the candidate upward

Threat: a stale local database reissues a number another clone already pushed, and the loss surfaces only at `git push`.

Fixture: `$repo = "$TMP\t04"`, `New-FixtureRepo $repo 3`, `init`, then a coded plan file and branch for `AVRIG-00011` pushed to `origin`.

```powershell
$repo = "$TMP\t04"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
[IO.File]::WriteAllText("$repo\plans\AVRIG-00011-2026-11-20-forced.md", "# forced`n", [Text.UTF8Encoding]::new($false))
git -C $repo add -A; git -C $repo commit -q -m 'forced 11'
git -C $repo branch feat/AVRIG-00011-forced | Out-Null
git -C $repo push -q origin main feat/AVRIG-00011-forced

Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'the database holds no row before the first assign'
$a = Invoke-Pc $repo @('assign','--title','after git seed','--role','Architect',
                      '--branch','feat/AVRIG-00012-seeded','--plan-path','plans/AVRIG-00012-2026-11-20-seeded.md')
Assert-Equal 0 $a.Exit 'assign exit'
Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00012"' 'candidate is git_max + 1'

# reverse: db ahead of git must not be pulled backwards
git -C $repo rm -q "plans/AVRIG-00011-2026-11-20-forced.md"; git -C $repo commit -q -m 'drop 11'
git -C $repo push -q origin main; git -C $repo branch -D feat/AVRIG-00011-forced | Out-Null
git -C $repo push -q origin --delete feat/AVRIG-00011-forced
$b = Invoke-Pc $repo @('assign','--title','db ahead','--role','Architect',
                      '--branch','feat/AVRIG-00013-ahead','--plan-path','plans/AVRIG-00013-2026-11-20-ahead.md')
Assert-Equal 0 $b.Exit 'second assign exit'
Assert-Match $b.Out '"code"\s*:\s*"AVRIG-00013"' 'db max wins when git union regresses'
```

Pass: the database is empty, the git union names `AVRIG-00011`, so the first assignment is `AVRIG-00012`; after the union regresses to `AVRIG-00003` the next assignment is `AVRIG-00013` because `MAX(number)` already holds `12`, proving `max(db_max, git_max) + 1` in both directions. Both calls pass a literal code rather than `{code}`, so the substitution is not the only branch binding form exercised.

#### T05 Indicator filtering

Threat: a foreign code, or a slug containing five digits, permanently inflates the series; numbers are never renumbered, so the inflation is forever.

Fixture: `$repo = "$TMP\t05"`, `New-FixtureRepo $repo 3`, `init`, then hostile glyphs in every union source.

```powershell
$repo = "$TMP\t05"; New-FixtureRepo $repo 3
$u = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText("$repo\plans\WEB-00009-2026-11-20-foreign.md", "# foreign`n", $u)
[IO.File]::WriteAllText("$repo\plans\AVRIG-00003-2026-11-20-migrate-to-20250-table.md", "# five digits`n", $u)
[IO.File]::WriteAllText("$repo\plans\2026-11-20-AVRIG-00442-draft-style.md", "# draft`n", $u)
[IO.File]::WriteAllText("$repo\plans\done\WEB-00021-2026-11-20-foreign-done.md", "# done`n", $u)
$md = Get-Content "$repo\plans\PLAN-INDEX.md" -Raw
$md = $md -replace '(?m)^# Plan Index$',
  "# Plan Index`n`nProse mentions WEB-00009 and AVRIG-00442 and PROJ-00099 and must contribute nothing."
[IO.File]::WriteAllText("$repo\plans\PLAN-INDEX.md", $md, $u)
git -C $repo add -A; git -C $repo commit -q -m hostile; git -C $repo push -q origin main
git -C $repo branch feat/WEB-00021-foreign | Out-Null
git -C $repo branch feat/AVRIG-00003-fixture-branch/reporting | Out-Null
git -C $repo push -q origin feat/WEB-00021-foreign feat/AVRIG-00003-fixture-branch/reporting

Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$a = Invoke-Pc $repo @('assign','--title','filtered','--role','Architect',
                      '--branch','feat/AVRIG-00004-filtered','--plan-path','plans/AVRIG-00004-2026-11-20-filtered.md')
Assert-Equal 0 $a.Exit 'assign exit'
Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00004"' 'no inflation from WEB, 20250, 00442, 00021'
Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE indicator <> 'AVRIG';") 'no foreign indicator reached the ledger'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'exactly one row written'
```

Pass: the candidate is exactly `AVRIG-00004` and exactly one row is written, carrying `AVRIG`. Any of `AVRIG-00010`, `AVRIG-00022`, `AVRIG-00043`, `AVRIG-00250`, or `AVRIG-00443` is a FAIL naming the source that leaked. `verify` is deliberately not asserted here: the fixture has never imported its three ledger rows, so strict mode would fail on a drift this case does not create, and T10 owns drift. Case sensitivity is implied by the fixture's `WEB-` and `web-` shapes; a lowercase indicator argument (`--indicator avrig`) is refused as invalid input in T15.

#### T06 Void burns the number

Threat: an abandoned plan hands its number to a second owner, or a killed `assign` leaves a number with no row and no audit record. A burned number is honest, a reused or untraceable one is not, and there is no lease and no reaper to hide behind either failure.

Part a, the explicit abandonment transition. `void` is the only way a number leaves service, it never runs on a timer, and the number stays spent.

```powershell
$repo = "$TMP\t06"; New-FixtureRepo $repo 0     # no ledger row, no coded file, no branch: git_max is 0
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$a = Invoke-Pc $repo @('assign','--title','to be abandoned','--role','Architect',
                      '--branch','feat/AVRIG-00001-abandoned','--plan-path','plans/AVRIG-00001-2026-11-20-abandoned.md')
Assert-Equal 0 $a.Exit 'assign exit'
Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00001"' 'git_max 0 gives the first number'
Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=1;') 'a number is committed at the moment it is assigned'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign' AND number=1;") 'one assign event'

$v = Invoke-Pc $repo @('void','--code','AVRIG-00001','--reason','plan abandoned')
Assert-Equal 0 $v.Exit 'void exit'
Assert-Equal 'voided' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=1;') 'state voided'
Assert-Equal 'plan abandoned' (& $SQL -noheader $db 'SELECT voided_reason FROM work_item WHERE number=1;') 'reason stored verbatim'
Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE voided_at IS NULL;') 'voided_at stamped'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='void' AND number=1;") 'exactly one void event'
Assert-Equal 2 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'one assign and one void, nothing else'

$b = Invoke-Pc $repo @('assign','--title','after void','--role','Architect',
                      '--branch','feat/AVRIG-00002-after-void','--plan-path','plans/AVRIG-00002-2026-11-20-after-void.md')
Assert-Equal 0 $b.Exit 'assign after void'
Assert-Match $b.Out '"code"\s*:\s*"AVRIG-00002"' 'git_max is still 0, and the voided number is not reissued'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item WHERE state='voided';") 'the voided row still exists, so the burn is recorded rather than hidden'
```

Part b, a real process kill during `assign`. The transaction is one `BEGIN IMMEDIATE` that writes the row and its `assign` event before it commits, so the only two allowed outcomes are both written or neither. There is no lease to advance and nothing to reap, so whatever survived is the answer.

```powershell
$p = Start-Process -FilePath $PW -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-File',$PC,'assign','--title','kill me','--role','Architect',
  '--branch','feat/{code}-kill','--plan-path','plans/{code}-2026-11-20-kill.md','--project',$repo)
Start-Sleep -Milliseconds 250; Stop-Process -Id $p.Id -Force; $p.WaitForExit()
Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity after the kill'
$rows = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
$ev   = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')
$n3   = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE number = 3;')
$e3   = [int](& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign' AND number = 3;")
if ($rows -eq 3) {
  Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number = 3;') 'the surviving row is committed'
  Assert-Equal 4 $ev 'three events before the kill plus the one committed with the row'
  Assert-Equal 1 $n3 'the row of the killed assign exists'
  Assert-Equal 1 $e3 'the event of the killed assign was committed with it'
} elseif ($rows -eq 2) {
  Assert-Equal 3 $ev 'no event without its row'
  Assert-Equal 0 $n3 'the killed assign left no row'
  Assert-Equal 0 $e3 'the killed assign left no event'
} else { throw "T06 : unexpected row count $rows" }

# the next number continues from whatever survived, never backwards and never duplicated
$before = [int](& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0) FROM work_item;')
$d = Invoke-Pc $repo @('assign','--dry-run','--title','after kill','--role','Architect',
                       '--branch','feat/{code}-after','--plan-path','plans/{code}-2026-11-20-after.md')
Assert-Equal 0 $d.Exit 'dry run after the kill'
Assert-Match $d.Out ('"code"\s*:\s*"AVRIG-{0:D5}"' -f ($before + 1)) 'strictly increasing after the kill'
Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) - COUNT(DISTINCT number) FROM work_item;') 'no duplicate numbers'
```

Pass: part a leaves a row that is `committed` at assignment and `voided` with the exact reason after `void`, with `voided_at` stamped and exactly one `void` event beside the one `assign` event; a following `assign` against a `git_max` of `0` returns `AVRIG-00002`, not the voided `AVRIG-00001`, and the voided row still exists to prove the burn is recorded. Part b yields `integrity_check` `ok` and exactly one of two shapes: three rows with four events, the survivor `committed` with its own `assign` event present, or two rows with three events and neither a row nor an event for `AVRIG-00003`. Either way the next candidate is strictly greater than the surviving maximum and no number repeats.

#### T07 Injection through the JSON payload path

Threat: a title or reason terminates the statement, or the payload is read in a shape SQLite rejects so every assignment fails.

```powershell
$repo = "$TMP\t07"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$title  = "It's a `"quoted`" title'; DROP TABLE work_item; --"
$reason = 'push rejected; "non-fast-forward"'
$a = Invoke-Pc $repo @('assign','--title',$title,'--role','Architect',
                      '--branch','feat/AVRIG-00004-inject','--plan-path','plans/AVRIG-00004-2026-11-20-inject.md')
Assert-Equal 0 $a.Exit 'assign exit'
$stored = & $SQL -noheader $db 'SELECT title FROM work_item ORDER BY number DESC LIMIT 1;'
Assert-Equal $title $stored 'title verbatim'
Assert-Equal 3 (& $SQL -noheader $db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name IN ('project','work_item','allocation_event');") 'tables survive'
Invoke-Pc $repo @('void','--code','AVRIG-00004','--reason',$reason) | Out-Null
Assert-Equal $reason (& $SQL -noheader $db "SELECT voided_reason FROM work_item WHERE number=4;") 'reason verbatim'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='void' AND number=4;") 'one void event, with no injected text in its own statement'
Assert-Equal 'ok' (& $SQL -noheader $db 'PRAGMA integrity_check;') 'integrity'
Assert-Equal 0 (Invoke-Pc $repo @('verify')).Exit 'verify without --strict reports the unrendered row without failing'
```

Pass for part a: `assign` exits `0`, the stored title is byte identical to the input, all three tables still exist, `void` stores the reason byte identical and writes one `void` event, `integrity_check` is `ok`, and `verify` without `--strict` exits `0`. A `DROP TABLE` that succeeded would fail the table count, and a mangled quote would fail the string comparison. `verify --strict` is deliberately not asserted here: this fixture holds one assigned row that has never been rendered, so strict mode would report a drift this case does not create, and T10 and T14 own that assertion.

Part b. The payload envelope and read shape are pinned here. The design requires a one element array envelope (B1) and the invocation shape is stdin with `.bail on` (Architect response, non blocking 4). Both are measured facts, so this case is what `be` must satisfy, and part a is the same path end to end through `assign`.

```powershell
$d = "$TMP\t07"; $db = "$d\plans\_plan.db"
$json = '[{"indicator":"AVRIG","title":"bom probe"}]'   # one element array, B1
$obj  = '{"indicator":"AVRIG","title":"bom probe"}'     # the shape that must fail
$plain = "$d\plain.json"; $bom = "$d\bom.json"; $objf = "$d\obj.json"
[IO.File]::WriteAllText($plain, $json, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText($objf,  $obj,  [Text.UTF8Encoding]::new($false))
Set-Content -Path "$d\ps7-plain.json" -Value $json -Encoding utf8
Set-Content -Path $bom -Value $json -Encoding utf8BOM

Assert-Equal 123 ([IO.File]::ReadAllBytes("$d\ps7-plain.json")[0]) 'pwsh 7 utf8 writes no BOM'
Assert-Equal 239 ([IO.File]::ReadAllBytes($bom)[0]) 'utf8BOM writes the BOM'

# adopted invocation: stdin, dot commands on their own lines (C4, Architect response)
function Run-Payload([string]$Path) {
  $script = ".bail on`n.timeout 5000`n.parameter set :payload '$Path'`n" +
            "SELECT json_extract(value,'`$.title') FROM json_each(readfile(:payload));`n"
  $o = ($script | & $SQL -noheader $db 2>&1) -join "`n"
  [pscustomobject]@{ Exit = $LASTEXITCODE; Out = $o }
}
$ok = Run-Payload $plain
Assert-Equal 0 $ok.Exit 'array envelope is accepted'
Assert-Equal 'bom probe' $ok.Out 'array envelope yields the title'
$b = Run-Payload $bom
Assert-Equal 0 $b.Exit 'BOM prefixed array still parses (C3)'
Assert-Equal 'bom probe' $b.Out 'BOM is tolerated by SQLite'

# the object envelope must be refused, so it cannot be reintroduced (B1)
$bad = Run-Payload $objf
Assert-Equal 1 $bad.Exit 'object envelope is SQLITE_ERROR'
Assert-Match $bad.Out 'malformed JSON' 'object envelope fails as measured'

# an empty payload is the malformed case, not the silent zero row case
[IO.File]::WriteAllText("$d\empty.json", '', [Text.UTF8Encoding]::new($false))
$em = Run-Payload "$d\empty.json"
Assert-Equal 1 $em.Exit 'empty payload is SQLITE_ERROR'
Assert-Match $em.Out 'malformed JSON' 'empty payload message'
```

Pass: the array envelope exits `0` and yields `bom probe`; the BOM prefixed array also exits `0` and yields `bom probe`, which records that SQLite tolerates a BOM rather than claiming it fails; the object envelope exits `1` with `malformed JSON`; and an empty payload exits `1` with `malformed JSON`. The wrapper still maps every non `0` and every zero row outcome to exit `3` before an assignment is accepted, which T11 and T12 exercise through the CLI.

#### T08 Import rebuilds from the durable layer

Threat: the local database becomes the archive, so deleting or corrupting it loses numbers.

```powershell
$repo = "$TMP\t08"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$a = Invoke-Pc $repo @('assign','--title','before delete','--role','Architect',
                      '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.md','--issue','99')
Assert-Equal 0 $a.Exit 'assign exit'
Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00004"' 'pre-deletion candidate'
Invoke-Pc $repo @('render') | Out-Null
git -C $repo add -A; git -C $repo commit -q -m 'approval commit'
$expected = (& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0)+1 FROM work_item;')

Remove-Item -Force $db, "$db-wal", "$db-shm" -ErrorAction SilentlyContinue
Assert-Equal 0 (Invoke-Pc $repo @('import','--indicator','AVRIG')).Exit 'import exit'
$rows = (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
Assert-Equal 4 $rows 'row count after import'
Assert-Equal 'AVRIG-00001,AVRIG-00002,AVRIG-00003,AVRIG-00004' `
  ((& $SQL -noheader $db 'SELECT group_concat(code) FROM (SELECT code FROM work_item ORDER BY number);') -replace "`n",'') 'codes match ledger and git union'
Assert-Equal 4 ([int](& $SQL -noheader $db 'SELECT COALESCE(MAX(number),0) FROM work_item;')) 'db max matches git union'

# idempotency: a second import changes no row, writes no event, and moves no rendered byte
Invoke-Pc $repo @('render') | Out-Null
$digest = (& $SQL -noheader $db "SELECT group_concat(code||'|'||number||'|'||state||'|'||COALESCE(committed_at,'')||'|'||COALESCE(ledger_cells,''),';') FROM (SELECT * FROM work_item ORDER BY number);")
$events = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')
$rendered = (Get-FileHash "$repo\plans\PLAN-INDEX.md").Hash
Invoke-Pc $repo @('import','--indicator','AVRIG') | Out-Null
Assert-Equal $digest (& $SQL -noheader $db "SELECT group_concat(code||'|'||number||'|'||state||'|'||COALESCE(committed_at,'')||'|'||COALESCE(ledger_cells,''),';') FROM (SELECT * FROM work_item ORDER BY number);") 'second import changed no row'
Assert-Equal $events ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')) 'second import wrote no event'
Invoke-Pc $repo @('render') | Out-Null
Assert-Equal $rendered ((Get-FileHash "$repo\plans\PLAN-INDEX.md").Hash) 'second import and render produced no output change'
$b = Invoke-Pc $repo @('assign','--title','after import','--role','Architect',
                      '--branch','feat/AVRIG-00005-y','--plan-path','plans/AVRIG-00005-2026-11-20-y.md')
Assert-Equal 0 $b.Exit 'assign after import'
Assert-Match $b.Out ('"code"\s*:\s*"AVRIG-{0:D5}"' -f [int]$expected) 'allocation unchanged by deletion'
```

Pass: after deletion and `import` the database holds exactly `AVRIG-00001..00004`, a second `import` changes no row digest, writes no `allocation_event`, and a following `render` leaves the ledger hash identical, and the next candidate equals the pre-deletion value (`AVRIG-00005`).

#### T09 Render, idempotency, check gate, escaping

Threat: the generated table is not byte stable, so every run produces a review diff; or a cell escapes wrongly and corrupts the markdown table.

Part a, reproduce the ledger byte for byte, graded against a post-marker fixture after `import`. The live file has no markers yet, so the fixture inserts them, `import` snapshots the ten original cell texts into `ledger_cells`, and `render` resolves each cell as structured column, then snapshot text, then empty (B2). The live checkout is never written to.

```powershell
$repo = "$TMP\t09"; New-FixtureRepo $repo 3
$raw = [IO.File]::ReadAllText("$WT\plans\PLAN-INDEX.md")
$nl  = if ($raw -match "`r`n") { "`r`n" } else { "`n" }
$raw = $raw -replace '(?m)^(\| Plan \| Created \|)', ('<!-- BEGIN GENERATED LEDGER -->' + $nl + '$1')
$raw = [regex]::Replace($raw, '(?m)^(\| AVRIG-\d{5} \|[^\r\n]*)(\r?\n)(?!\| AVRIG-)',
                        ('$1$2<!-- END GENERATED LEDGER -->$2'))
Assert-Equal 2 ([regex]::Matches($raw, 'GENERATED LEDGER').Count) 'both markers inserted once'
[IO.File]::WriteAllText("$repo\plans\PLAN-INDEX.md", $raw, [Text.UTF8Encoding]::new($false))
foreach ($f in Get-ChildItem "$WT\plans" -Filter 'AVRIG-*.md') { Copy-Item $f.FullName "$repo\plans\" -Force }
git -C $repo add -A; git -C $repo commit -q -m 'markered live ledger'; git -C $repo push -q origin main

Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo @('import','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
Assert-Equal 3 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'three rows imported'
Assert-Equal 3 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE ledger_cells IS NOT NULL;') 'ten cells snapshotted per row'
Assert-Equal 0 (Invoke-Pc $repo @('render')).Exit 'render exit'
git -C $repo diff --exit-code -- plans/PLAN-INDEX.md; Assert-Equal 0 $LASTEXITCODE 'render reproduces the markered ledger byte for byte'
$h1 = (Get-FileHash "$repo\plans\PLAN-INDEX.md").Hash
Invoke-Pc $repo @('render') | Out-Null
Assert-Equal $h1 (Get-FileHash "$repo\plans\PLAN-INDEX.md").Hash 'second render byte identical'
git -C $repo add -A; git -C $repo commit -q -m 'render baseline'
Assert-Equal 0 (Invoke-Pc $repo @('render','--check')).Exit 'check clean'
(Get-Content "$repo\plans\PLAN-INDEX.md") -replace '(\| AVRIG-00002 \| \d{4}-\d{2}-\d{2} \| )[^|]+', '${1}EDITED BY HAND' |
  Set-Content "$repo\plans\PLAN-INDEX.md" -Encoding utf8NoBOM
$c = Invoke-Pc $repo @('render','--check')
Assert-Equal 1 $c.Exit 'check fails on a manual edit'
Assert-Match $c.Out 'AVRIG-00002' 'check names the drifted row'
Assert-Match (Get-Content "$repo\plans\PLAN-INDEX.md" -Raw) 'EDITED BY HAND' 'check did not rewrite the file'
```

Part b, escaping. Assign a title containing a pipe and assert `\|` in the output.

```powershell
$repo2 = "$TMP\t09b"; New-FixtureRepo $repo2 3
Invoke-Pc $repo2 @('init','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo2 @('import','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo2 @('assign','--title','a | b','--role','Architect',
                   '--branch','feat/{code}-pipe','--plan-path','plans/{code}-2026-11-20-pipe.md') | Out-Null
Invoke-Pc $repo2 @('render') | Out-Null
$line = Select-String -Path "$repo2\plans\PLAN-INDEX.md" -Pattern 'AVRIG-00004' | ForEach-Object Line
Assert-Match $line 'a \\\| b' 'pipe escaped as backslash pipe'
$sep = ($line -split '(?<!\\)\|').Count - 1
Assert-Equal 11 $sep 'eleven unescaped separators, ten columns'
Assert-Equal 1 ([regex]::Matches($line, '\\\|').Count) 'exactly one escaped pipe'
```

Pass: the markers are inserted exactly once, three rows import with `ledger_cells` populated, `render` reproduces the markered live ledger with an empty `git diff`, a second render is hash identical, `render --check` exits `0` clean and `1` naming `AVRIG-00002` after a hand edit while leaving that edit in place, and a pipe is written as `\|` without changing the column count of ten. No cell source is invented: `Created` and `Repos` come from `created_on` and `repos`, and the legacy prose cells come from `ledger_cells`.

#### T10 Verify detects drift in both directions

Threat: an agent assigns a number and never renders it, or edits the ledger by hand, and the two records silently disagree. Drift is simulated by editing the ledger, never by deleting or rekeying a database row, because `tr_work_item_no_delete` and `tr_work_item_no_rekey` make those operations impossible and a case that tried them would grade the trigger instead of drift (B5).

```powershell
# (a) database row that the ledger does not carry
$repo = "$TMP\t10a"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo @('import','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo @('render') | Out-Null
Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'clean baseline'
$db = "$repo\plans\_plan.db"
& $SQL -bail $db "INSERT INTO work_item (indicator,number,title,state,owner_role,claiming_branch,plan_path,committed_at,actor_host,actor_user) VALUES ('AVRIG',7,'only in db','committed','Architect','feat/AVRIG-00007-only-in-db','plans/AVRIG-00007-2026-11-20-only-in-db.md','2026-11-20T00:00:00.000Z','h','u');"
$v = Invoke-Pc $repo @('verify','--strict')
Assert-Equal 1 $v.Exit 'strict fails on db-only row'
Assert-Match $v.Out 'AVRIG-00007' 'message names the code'
$w = Invoke-Pc $repo @('verify')
Assert-Equal 0 $w.Exit 'non strict reports without failing'
Assert-Match $w.Out 'AVRIG-00007' 'non strict still names the code'

# (b) ledger row that the database does not carry: edit the ledger, touch no row
$repo = "$TMP\t10b"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo @('import','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo @('render') | Out-Null
$raw = [IO.File]::ReadAllText("$repo\plans\PLAN-INDEX.md")
$raw = $raw -replace '(?m)^(<!-- END GENERATED LEDGER -->)',
  ('| AVRIG-00008 | 2026-11-20 | ledger only | avrig-ai | feat/AVRIG-00008-ledger-only | approved | none yet | pending | pending | empty |' + "`n" + '$1')
[IO.File]::WriteAllText("$repo\plans\PLAN-INDEX.md", $raw, [Text.UTF8Encoding]::new($false))
Assert-Equal 3 ((& $SQL -noheader "$repo\plans\_plan.db" 'SELECT COUNT(*) FROM work_item;')) 'database still holds three rows'
$v = Invoke-Pc $repo @('verify','--strict')
Assert-Equal 1 $v.Exit 'strict fails on ledger-only row'
Assert-Match $v.Out 'AVRIG-00008' 'message names the code'
```

Pass: the clean baseline exits `0`; a database-only row yields exit `1` under `--strict` and exit `0` without it, both naming `AVRIG-00007`; a ledger-only row yields exit `1` under `--strict` naming `AVRIG-00008`, and the database row count is unchanged at three throughout, which proves the drift was detected from the ledger rather than caused by a database mutation.

#### T11 Missing sqlite3 is a configuration failure

Threat: a missing binary is mistaken for a data problem, or the tool degrades into writing a partial row.

```powershell
$repo = "$TMP\t11"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"; $before = (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
$cmd = @"
`$env:PATH = 'C:\Windows\System32;C:\Windows'
Remove-Item Env:AVRIG_SQLITE3 -ErrorAction SilentlyContinue
& '$PW' -NoProfile -File '$PC' assign --title t --role Architect --branch 'feat/{code}-t' --plan-path 'plans/{code}-2026-11-20-t.md' --project '$repo'
exit `$LASTEXITCODE
"@
[IO.File]::WriteAllText("$TMP\t11\probe.ps1", $cmd, [Text.UTF8Encoding]::new($false))
$o = (& $PW -NoProfile -File "$TMP\t11\probe.ps1" 2>&1) -join "`n"
Assert-Equal 3 $LASTEXITCODE 'exit 3 on missing binary'
Assert-Match $o 'sqlite3' 'message names the binary'
Assert-Equal $before (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'no row written'
Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'no event written'
```

Pass: exit `3`, stderr names `sqlite3`, and both `work_item` and `allocation_event` counts are unchanged. `AVRIG_SQLITE3` is unset so the override cannot mask the failure.

#### T12 Dry run writes nothing

Threat: a preview assigns a number and burns it, so the dry run silently costs the series a slot.

```powershell
$repo = "$TMP\t12"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$before = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
$ev = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')
$d = Invoke-Pc $repo @('assign','--dry-run','--title','preview','--role','Architect',
                       '--branch','feat/{code}-preview','--plan-path','plans/{code}-2026-11-20-preview.md')
Assert-Equal 0 $d.Exit 'dry run exit'
Assert-Match $d.Out '"code"\s*:\s*"AVRIG-00004"' 'candidate printed'
Assert-Equal $before ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')) 'row count unchanged'
Assert-Equal $ev ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;')) 'event count unchanged'
$a = Invoke-Pc $repo @('assign','--title','real','--role','Architect',
                       '--branch','feat/AVRIG-00004-real','--plan-path','plans/AVRIG-00004-2026-11-20-real.md')
Assert-Equal 0 $a.Exit 'real assign exit'
Assert-Match $a.Out '"code"\s*:\s*"AVRIG-00004"' 'the real assign still gets the same number'
```

Pass: exit `0`, the printed candidate equals `AVRIG-00004`, both counts are identical before and after the dry run, and the following real assignment returns the same number rather than `AVRIG-00005`.

#### T13 `assign` writes one row and one event, or neither

Threat: the row and its audit event land in separate transactions, so a number reaches the ledger with no record of who assigned it, or a refused assignment leaves a half written row. No other case states the one to one ratio outside contention, and `verify` cannot explain a row that has no `assign` event.

```powershell
$repo = "$TMP\t13"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$a = Invoke-Pc $repo @('assign','--title','one row','--role','Architect',
                      '--branch','feat/AVRIG-00004-one','--plan-path','plans/AVRIG-00004-2026-11-20-one.md','--issue','42')
Assert-Equal 0 $a.Exit 'assign exit'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE number=4;') 'exactly one row'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign' AND number=4;") 'exactly one assign event'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'the call wrote one row and no more'
Assert-Equal 0 (& $SQL -noheader $db "SELECT COUNT(*) FROM work_item w WHERE NOT EXISTS (SELECT 1 FROM allocation_event e WHERE e.event='assign' AND e.indicator=w.indicator AND e.number=w.number);") 'every row carries its own assign event'
$rows = [int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')
$ev   = [int](& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign';")
Assert-Equal $rows $ev 'one assign event per row, no more'

# a refused assign writes neither, and the row that already exists is untouched
$bad = Invoke-Pc $repo @('assign','--title','refused','--role','Architect',
                         '--branch','feat/AVRIG-00009-other','--plan-path','plans/AVRIG-00009-2026-11-20-other.md')
Assert-Equal 3 $bad.Exit 'a branch naming another code is refused'
Assert-Equal $rows ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;')) 'refused assign wrote no row'
Assert-Equal $ev ([int](& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='assign';")) 'refused assign wrote no event'
Assert-Equal 0 ([int](& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item WHERE number=9;')) 'no row exists for the code the branch named'
Assert-Equal 'committed' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=4;') 'the earlier row is untouched'
```

Pass: one call writes exactly one row and exactly one `assign` event, the invariant "one `assign` event per row" holds with no extras, and a refused call exits `3` writing neither row nor event while leaving the earlier row `committed`. Two refusal routes are both acceptable and both must end at exit `3` with zero rows: the wrapper pre-checks the branch before it reaches SQL, or it passes the branch through and `ck_branch_carries_code` aborts the insert inside the transaction. Measured, the constraint route is live and leaves zero rows, which is the transaction doing its job rather than a wrapper catching a typo.

#### T14 Approval runbook end to end

Threat: the documented sequence does not actually produce one ledger row and one code, so the runbook is prose that has never been run.

```powershell
$repo = "$TMP\t14\scratch"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
Invoke-Pc $repo @('import','--indicator','AVRIG') | Out-Null
[IO.File]::WriteAllText("$repo\plans\2026-11-20-demo-task.md", "# demo`n", [Text.UTF8Encoding]::new($false))
git -C $repo add -A; git -C $repo commit -q -m 'draft'

# 1. assign: one call claims the number and binds it to the branch and the plan path
$a = Invoke-Pc $repo @('assign','--title','Demo Task','--role','Architect',
                       '--branch','feat/{code}-demo-task','--plan-path','plans/{code}-2026-11-20-demo-task.md',
                       '--issue','123')
Assert-Equal 0 $a.Exit 'assign'
$code = Get-Code $a.Out
Assert-Equal 'AVRIG-00004' $code 'assigned code'

# 2. rename the draft to the code first name the row already points at, and cut the branch
git -C $repo mv "plans/2026-11-20-demo-task.md" "plans/$code-2026-11-20-demo-task.md"
git -C $repo branch "feat/$code-demo-task" | Out-Null

# 3. render the ledger from the database
Assert-Equal 0 (Invoke-Pc $repo @('render')).Exit 'render'

# 4. cross check database, ledger, and git union
Assert-Equal 0 (Invoke-Pc $repo @('verify','--strict')).Exit 'verify after runbook'

Assert-Equal 1 (Select-String -Path "$repo\plans\PLAN-INDEX.md" -Pattern "\| $code \|").Count 'one ledger row for the code'
Assert-Equal 1 (Get-ChildItem "$repo\plans" -Filter "$code-*.md").Count 'one coded plan file'
Assert-Equal 1 (git -C $repo branch --format='%(refname:short)' | Where-Object { $_ -match [regex]::Escape($code) }).Count 'one claiming branch'
git -C $repo add -A; git -C $repo commit -q -m "docs($code): allocate"
$touched = git -C $repo show --name-only --format= HEAD
Assert-Equal 1 (@($touched | Where-Object { $_ -like "plans/$code-*.md" }).Count) 'approval commit carries the coded plan'
Assert-Equal 1 (@($touched | Where-Object { $_ -eq 'plans/PLAN-INDEX.md' }).Count) 'approval commit carries the ledger'
$n = Invoke-Pc $repo @('assign','--dry-run','--title','Next','--role','Architect',
                       '--branch','feat/{code}-next','--plan-path','plans/{code}-2026-11-20-next.md')
Assert-Equal 0 $n.Exit 'dry run exit'
Assert-Match $n.Out '"code"\s*:\s*"AVRIG-00005"' 'next code advances'
```

Pass: `assign` returns `AVRIG-00004`, and the plan file, the ledger row, and the claiming branch all carry that one code, `verify --strict` exits `0` after `render`, the approval commit contains the renamed plan and the ledger, and the following candidate is `AVRIG-00005`. The documented sequence has no `commit` step: `assign`, then the rename and the branch cut, then `render`, then `verify --strict`. The rename sits between `assign` and `render` because the coded filename only exists once `assign` has returned the code that the row was already bound to. Scratch clone path is `$env:TEMP\opencode\plan-code\t14\scratch`, never under OneDrive.

#### T15 Exit code contract

Threat: callers branch on exit codes, so a wrong code silently turns a hard failure into a success.

| Probe | Command | Expected |
|---|---|---|
| invalid title | `assign --title ''` with a legal branch and plan path | `3` |
| invalid indicator | `assign --indicator avrig` | `3` |
| unknown flag | `assign --nonsense 1` | `3` |
| unknown work item | `void --code AVRIG-09999 --reason x` | `3` |
| branch carrying another code | `assign --branch feat/AVRIG-00009-other --plan-path plans/AVRIG-00009-2026-11-20-other.md` | `3` |
| plan path outside `plans/` | `assign --plan-path other/AVRIG-00004-2026-11-20-x.md` | `3` |
| plan path not ending in `.md` | `assign --plan-path plans/AVRIG-00004-2026-11-20-x.txt` | `3` |
| non numeric issue | `assign --issue abc` | `3` |
| no `origin` remote, no `--strict-git` | `assign` | `0`, warning recorded |
| no `origin` remote, `--strict-git` | `assign --strict-git` | `4`, no row written |
| fetch attempted and failed | `assign` with an `origin` URL that does not resolve | `4`, no row written, no `--strict-git` needed |
| clean success | `status --json` on a clean db | `0` |

```powershell
$repo = "$TMP\t15"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
# a complete legal bind for AVRIG-00004, the number this fixture would issue
$ok4 = @('--title','t','--role','Architect',
         '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.md')

Assert-Equal 3 (Invoke-Pc $repo (@('assign','--title','','--role','Architect',
  '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.md'))).Exit 'empty title'
Assert-Equal 3 (Invoke-Pc $repo (@('assign','--indicator','avrig') + $ok4)).Exit 'lowercase indicator'
Assert-Equal 3 (Invoke-Pc $repo @('assign','--nonsense','1')).Exit 'unknown flag'
Assert-Equal 3 (Invoke-Pc $repo @('void','--code','AVRIG-09999','--reason','nope')).Exit 'unknown code'

# the input refusals assign now has: the branch, the plan path, and the issue number
Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','t','--role','Architect',
  '--branch','feat/AVRIG-00009-other','--plan-path','plans/AVRIG-00009-2026-11-20-other.md')).Exit 'branch carrying another code'
Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','t','--role','Architect',
  '--branch','feat/AVRIG-00004-x','--plan-path','other/AVRIG-00004-2026-11-20-x.md')).Exit 'plan path outside plans'
Assert-Equal 3 (Invoke-Pc $repo @('assign','--title','t','--role','Architect',
  '--branch','feat/AVRIG-00004-x','--plan-path','plans/AVRIG-00004-2026-11-20-x.txt')).Exit 'plan path not markdown'
Assert-Equal 3 (Invoke-Pc $repo (@('assign') + $ok4 + @('--issue','abc'))).Exit 'non numeric issue'

Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM work_item;') 'no refusal wrote a row'
Assert-Equal 0 (& $SQL -noheader $db 'SELECT COUNT(*) FROM allocation_event;') 'no refusal wrote an event'

# case A: no origin remote configured, a warning unless --strict-git is asked for
$gorp = "$TMP\t15\noorigin"; New-FixtureRepo $gorp 3
git -C $gorp remote remove origin
Invoke-Pc $gorp @('init','--indicator','AVRIG') | Out-Null
$gdb = "$gorp\plans\_plan.db"
$r = Invoke-Pc $gorp @('assign','--title','no origin','--role','Architect',
  '--branch','feat/AVRIG-00004-no-origin','--plan-path','plans/AVRIG-00004-2026-11-20-no-origin.md')
Assert-Equal 0 $r.Exit 'no origin is a warning by default'
Assert-Match $r.Out 'warn' 'warning recorded'
$s = Invoke-Pc $gorp @('assign','--title','no origin strict','--role','Architect',
  '--branch','feat/AVRIG-00005-no-origin','--plan-path','plans/AVRIG-00005-2026-11-20-no-origin.md','--strict-git')
Assert-Equal 4 $s.Exit 'no origin under --strict-git'
Assert-Equal 1 (& $SQL -noheader $gdb 'SELECT COUNT(*) FROM work_item;') 'only the lax run wrote a row'

# case B: origin configured but the fetch fails, which is exit 4 with no flag at all
$forp = "$TMP\t15\badremote"; New-FixtureRepo $forp 3
Invoke-Pc $forp @('init','--indicator','AVRIG') | Out-Null
git -C $forp remote set-url origin "$TMP\t15\missing-origin.git"
git -C $forp update-ref -d refs/remotes/origin/main
$f = Invoke-Pc $forp @('assign','--title','bad remote','--role','Architect',
  '--branch','feat/AVRIG-00004-bad-remote','--plan-path','plans/AVRIG-00004-2026-11-20-bad-remote.md')
Assert-Equal 4 $f.Exit 'attempted fetch failure is exit 4 unconditionally'
Assert-Equal 0 (& $SQL -noheader "$forp\plans\_plan.db" 'SELECT COUNT(*) FROM work_item;') 'failed fetch wrote no row'
$n = Invoke-Pc $forp @('assign','--title','bad remote nofetch','--role','Architect',
  '--branch','feat/AVRIG-00004-bad-remote-nofetch','--plan-path','plans/AVRIG-00004-2026-11-20-bad-remote-nofetch.md','--no-fetch')
Assert-Equal 0 $n.Exit '--no-fetch bypasses the fetch and succeeds'

$j = Invoke-Pc $repo @('status','--json')
Assert-Equal 0 $j.Exit 'status exit'
Assert-Equal 0 (@($j.Out | ConvertFrom-Json)).Count 'every refusal left the ledger empty'
```

Pass: each probe returns exactly the exit code in the table; no refusal writes a `work_item` row or an `allocation_event` row, and `status --json` on that fixture parses to an empty array, which is the same fact stated through the CLI; the branch, plan path, and issue refusals all exit `3` without a row, because a row bound to a branch or path carrying another code is the traceability failure the ledger exists to prevent; a checkout with no `origin` warns and exits `0` by default while `--strict-git` turns it into exit `4`; an `origin` that exists but cannot be fetched exits `4` with no flag, and `--no-fetch` lets the same fixture succeed. `status --json` with rows is covered by T17, because this fixture deliberately holds none.

#### T16 The database never reaches git

Threat: a binary lock file is committed and merged by hand, or shows up as an untracked artifact in every status.

```powershell
Push-Location $WT
git check-ignore -v plans/_plan.db;      Assert-Equal 0 $LASTEXITCODE 'db ignored'
git check-ignore -v plans/_plan.db-wal;  Assert-Equal 0 $LASTEXITCODE 'wal ignored'
git check-ignore -v plans/_plan.db-shm;  Assert-Equal 0 $LASTEXITCODE 'shm ignored'
Assert-Equal 0 ((git status --porcelain plans/) -match '_plan\.db').Count 'not reported by status'
Assert-Equal 0 (git ls-files plans/ | Select-String '_plan\.db').Count 'never tracked'
Pop-Location
```

Pass: all three `check-ignore` calls exit `0` and name a `.gitignore` rule, `git status` reports nothing matching `_plan.db`, and `git ls-files` lists no database file. Read only; the case creates nothing and consumes no number. The same three `check-ignore` calls are repeated against the live checkout in post-merge smoke, where the rule exists only after the Stage 13 merge; running them there earlier would grade a rule that has not landed yet.

#### T17 Status and explicit void

Threat: a committed number cannot be inspected or released by hand, so a closed issue or a rejected push leaves the series in an unknown state and nobody can tell which numbers are live. T06 owns the burn itself; this case owns what `status` reports about it.

```powershell
$repo = "$TMP\t17"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$a = Invoke-Pc $repo @('assign','--title','void me','--role','Architect',
                      '--branch','feat/AVRIG-00004-void-me','--plan-path','plans/AVRIG-00004-2026-11-20-void-me.md')
Assert-Equal 0 $a.Exit 'assign exit'
$s = ((Invoke-Pc $repo @('status','--json')).Out | ConvertFrom-Json)   # throws if not valid JSON
Assert-Equal 1 (@($s).Count) 'one row listed'
Assert-Equal 'committed' (@($s)[0].state) 'state reported'
Assert-Equal 'AVRIG-00004' (@($s)[0].code) 'code reported'
Assert-Equal 'feat/AVRIG-00004-void-me' (@($s)[0].claiming_branch) 'claiming branch reported, so the row can be traced from the CLI'
Assert-Equal 0 (Invoke-Pc $repo @('void','--code','AVRIG-00004','--reason','push rejected')).Exit 'void exit'
Assert-Equal 'voided' (& $SQL -noheader $db 'SELECT state FROM work_item WHERE number=4;') 'state voided'
Assert-Equal 'push rejected' (& $SQL -noheader $db 'SELECT voided_reason FROM work_item WHERE number=4;') 'reason stored'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM allocation_event WHERE event='void' AND number=4;") 'one void event'
$s2 = ((Invoke-Pc $repo @('status','--json')).Out | ConvertFrom-Json)
Assert-Equal 'voided' (@($s2)[0].state) 'status reports the transition rather than the assignment'
Assert-Equal 'push rejected' (@($s2)[0].voided_reason) 'status carries the reason'
Assert-Equal 1 (([regex]::Matches((Invoke-Pc $repo @('status','--state','voided')).Out,'AVRIG-00004')).Count) 'state filter lists the voided row'
Assert-Equal 0 (([regex]::Matches((Invoke-Pc $repo @('status','--state','committed')).Out,'AVRIG-00004')).Count) 'state filter excludes it from the committed view'
$b = Invoke-Pc $repo @('assign','--title','after void','--role','Architect',
                      '--branch','feat/AVRIG-00005-after-void','--plan-path','plans/AVRIG-00005-2026-11-20-after-void.md')
Assert-Equal 0 $b.Exit 'assign after void exit'
Assert-Equal 'AVRIG-00005' (Get-Code $b.Out) 'the voided number is not reissued'
$s3 = ((Invoke-Pc $repo @('status','--json')).Out | ConvertFrom-Json)
Assert-Equal 2 (@($s3).Count) 'the voided row and its successor are both listed'
Assert-Equal 0 (([regex]::Matches((Invoke-Pc $repo @('status','--state','committed')).Out,'AVRIG-00004')).Count) 'the burned number stays out of the committed view after a successor exists'
```

Pass: `status --json` parses and reports one `committed` row with its code and claiming branch; `void` moves it to `voided` with the exact reason and one `void` event; `status --json` then reports the same row as `voided` carrying that reason; `--state voided` lists it while `--state committed` does not; a following `assign` returns `AVRIG-00005`; and both rows are listed, with the burned number still absent from the committed view. The burn is asserted here only as a visibility fact, because T06 is where it is proved against `git_max=0`.

#### T18 Init is idempotent and refuses a foreign or newer schema

Threat: `init` re-applies or migrates over a live database, silently switching the project indicator or downgrading a schema version, so the local lock answers for a project it does not belong to.

```powershell
$repo = "$TMP\t18"; New-FixtureRepo $repo 3
Invoke-Pc $repo @('init','--indicator','AVRIG') | Out-Null
$db = "$repo\plans\_plan.db"
$a = Invoke-Pc $repo @('init','--indicator','AVRIG')
Assert-Equal 0 $a.Exit 'same indicator is idempotent'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM project;') 'exactly one project row'
Assert-Equal 1 (& $SQL -noheader $db 'PRAGMA user_version;') 'version still 1'

$b = Invoke-Pc $repo @('init','--indicator','WEB')
Assert-Equal 3 $b.Exit 'second indicator refused'
Assert-Equal 'AVRIG' (& $SQL -noheader $db 'SELECT indicator FROM project;') 'project row unchanged'
Assert-Equal 1 (& $SQL -noheader $db 'SELECT COUNT(*) FROM project;') 'no second project row'

# a newer or unknown user_version is refused rather than silently applied
& $SQL -bail $db 'PRAGMA user_version=99;'
$c = Invoke-Pc $repo @('init','--indicator','AVRIG')
Assert-Equal 3 $c.Exit 'unknown newer user_version refused'
Assert-Equal 99 (& $SQL -noheader $db 'PRAGMA user_version;') 'refused init did not rewrite the version'
Assert-Equal 1 (& $SQL -noheader $db "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='project';") 'refused init did not touch the schema'

# an empty file at the database path is initialised, which is the recovery path
$fresh = "$TMP\t18\fresh"; New-FixtureRepo $fresh 3
New-Item -ItemType Directory -Force "$fresh\plans" | Out-Null
[IO.File]::WriteAllBytes("$fresh\plans\_plan.db", [byte[]]@())
$d = Invoke-Pc $fresh @('init','--indicator','AVRIG')
Assert-Equal 0 $d.Exit 'empty database file is initialised'
Assert-Equal 1 (& $SQL -noheader "$fresh\plans\_plan.db" 'PRAGMA user_version;') 'initialised to version 1'
```

Pass: the same indicator re-runs at exit `0` with one `project` row and `user_version` `1`; a different indicator exits `3` and leaves the `project` row untouched at count 1; `user_version` `99` makes `init` exit `3` with both the version and the schema unchanged; and an empty file at `plans/_plan.db` is initialised to `user_version` `1` at exit `0`.

### Not applicable in this plan

| Surface | Verdict | Reason |
|---|---|---|
| Live browser UAT | not applicable | the plan ships a PowerShell CLI and a SQLite file, with no rendered page, no route, and no login journey to load |
| Desktop UAT through `agent-desktop` | not applicable | no native window, tray, dialog, or installer is started, clicked, or read; the ledger is a SQLite file queried by a CLI, not a surface the plan owns |
| `cargo check --workspace` and `pnpm build` as a code gate | not applicable | the artifacts are one PowerShell script, one SQL schema, three markdown documents, and a SQL dump. No Rust or TypeScript source changes, so a workspace build would exercise code this plan never touched. The equivalent gate for what did change is a PowerShell parse check of `plan-code.ps1`, a `.read` of the schema into a scratch database with `PRAGMA integrity_check`, and the tool's own scratch suite, all recorded under the execution order |

If a later stage adds a page or a window, these two rows must be replaced by executed cases, not by silence.

### Execution order and gates

| Order | Cases | Gate |
|---|---|---|
| 1 | `T01`, `T02` | schema is real before anything is tested against it |
| 2 | `T12`, `T13`, `T17`, `T18` | single process behaviour before contention |
| 3 | `T03` | the only case that can leave 20 rows behind; runs on a clean fixture |
| 4 | `T04`, `T05`, `T08` | union and rebuild correctness |
| 5 | `T06`, `T07` | durability and injection |
| 6 | `T09`, `T10` | ledger rendering and drift |
| 7 | `T11`, `T15`, `T16` | environment and contract edges |
| 8 | `T14` | the runbook, last, on a clean scratch clone |

One command runs everything for a candidate:

```powershell
& $PW -NoProfile -File "$TOOL\shared\skills\plan-code\tests\Test-Allocation.ps1" `
  -Project $WT -Out "$WT\plans\evidence\<CODE>-<NNNNN>\rc.<NNN>"
```

### Evidence convention

- Results land in `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/`, one folder per candidate tag, keyed to the same candidate number as the build. `<CODE>`, `<NNNNN>`, and `<NNN>` are empty at Stage 3 and are filled at Stage 8, when the tag exists; nobody writes a version or a code before then.
- Contents: `RESULTS.md` (one line per case plus the rollup), `logs/T01.log` through `logs/T18.log` (stdout and stderr verbatim), `env.json` (`$PSVersionTable.PSVersion`, `sqlite3 --version`, `$TAG`, `$SHA`, `$TSHA`, and `git -C $TOOL status --porcelain -- shared/skills/plan-code` which must be empty), and `db/` (the fixture database copied after each destructive case, so a reviewer can re-run any query).
- No case output is paraphrased into `RESULTS.md`. The log is the record; the summary line only points at it.
- Each result line carries the tag, both commit SHAs, the verdict, the passing assertion count, and the evidence path. A line missing the tag or either SHA is treated as `BLOCKED`.
- No run may start against an untagged or moving tree. A green result on an older tag is not a pass for a newer tree, and a run in the working tree is not evidence at all.

### Rollup rule for the release trigger

The candidate passes only when all 18 cases report `PASS` with zero failed assertions and the runner exits `0`. At that point `tester` reports the passing tag, its `git rev-parse <tag>^{commit}` SHA, and a recommended increment: `minor` if the allocator ships as new capability with no change to any existing ledger row, `patch` if it only repairs an interface defect found during the run, `major` only if the ledger table shape or the exit code contract changes incompatibly after a previous release. No tag is created by `tester`; `build` owns the tag, the merge, and the push.

### Post-merge smoke, after the Stage 13 merge

The three `.gitignore` paths can only be asserted against a checkout that carries the rule, and the live checkout carries it only after the merge. This runs then, on the default branch, and is never a substitute for a candidate case.

```powershell
Push-Location $LIVE
$def = (git symbolic-ref --short refs/remotes/origin/HEAD) -replace '^origin/',''
git switch $def; git pull --ff-only
foreach ($f in '_plan.db','_plan.db-wal','_plan.db-shm') {
  git check-ignore -q "plans/$f"; Assert-Equal 0 $LASTEXITCODE "$f ignored on the default branch"
}
Assert-Equal 0 (git ls-files plans/ | Select-String '_plan\.db').Count 'no database file tracked on the default branch'
Pop-Location
```

Pass: all three paths are ignored on the resolved default branch, nothing matching `_plan.db` is tracked, and the smoke writes no file, because `check-ignore` and `ls-files` are read only. A failure here after a green T16 means the merge dropped the rule, not that the rule was wrong.

## Review Findings

**Addendum, 2026-11-20, after approval.** The user deleted the markdown ledger from the design after this review closed: `plans/PLAN-INDEX.md` is gone, the durable record is now the committed dump `plans/_plan.sql`, and `render` is `export`. Findings B2, B5, and B9 graded the markdown rendering, the ledger-cell snapshots, and the `PLAN-INDEX.md` filenames respectively, so their subject matter no longer exists; the design that replaced them is recorded under `## Decisions Taken at Stage 4` as decisions 7, 8, and 9. The verdict below stands as written, because rewriting a completed audit to match a later design would make it a worse record than an out of date one. A fresh audit of the amended design is required before Stage 7, and it is recorded in `## Architect Response to Review Findings` as the addendum entry.

**Verdict: PASS WITH CHANGES.** The design is sound: the three layer split is honest about what SQLite can and cannot guarantee, the trust boundary is real rather than decorative, and the approach needs no rework. Stage 4 must not open until Blocking B1 to B9 are closed, and B2 and B6 need a decision from `Architect` and `tester` rather than a wording fix. The document changed twice while this audit ran: the database and DDL filenames were rewritten, then the test matrix arrived and was revised. Every finding therefore names the text as it stood at the end of the review.

Plan identity is correct for a draft: `plan_id:` is empty, the filename is still `2026-11-20-plan-code-sqlite-allocation.md` with no code, `project_indicator: AVRIG` equals the ledger's declared value by case sensitive comparison, `status: under-review` is in the vocabulary, and no SemVer appears anywhere. Nothing was allocated, and the ledger still ends at `AVRIG-00003`.

### Blocking

**B1. The reserve statement does not run against the payload the plan specifies, and T07b proves it.**
Measured on sqlite3 3.51.2. With an object payload, `json_each` returns one row per member and `json_extract(value,'$.title')` raises `malformed JSON` at exit 1, so the whole statement fails. With a one element array `[{...}]` the identical statement inserts exactly one row and the `SELECT` returns it. T07b uses the object form at `$json = '{"indicator":"AVRIG","title":"bom probe"}'` and asserts the good path parses to `bom probe`, which fails by construction, so the case cannot pass as written.
Changed (Allocation algorithm step 4): "Write a JSON payload to a temp file: indicator, title, ..." is now "Write a BOM-free UTF-8 JSON payload to a temp file. The payload is a single element array whose one object carries ...", with the measured reason and the BOM requirement stated in place.
Required of `tester`: T07b's `$json` becomes `'[{"indicator":"AVRIG","title":"bom probe"}]'`.

**B2. `render` cannot reproduce the current ledger, yet the fifth goal and T09 assert that it can.**
The ten columns and their order are right, but three have no source in the schema. `Created` and `Repos` have no column at all, and today's `Passing candidate tag`, `Feature request`, and `Release version` cells carry bold text, backticked tags, a commit SHA, issue links, and the literal words `empty until deployment`, none of which a bare `candidate_tags`, `issue_number`, or `release_version` value reproduces. T09 compounds this: it copies the live ledger, which has no markers yet, and then asserts `git diff --exit-code` is empty, so it fails whether or not markers are expected.
Changed (Goals, fifth outcome): "render reproduces ... exactly ... so the change is additive rather than a rewrite" now adds "That is only measurable once the render section defines a source for every existing cell, and today `Created`, `Repos`, and the two `empty until deployment` release cells have none."
Changed (Ledger rendering): "... leaves a blank cell for an unset `release_version`." now continues into the BOM-free UTF-8 and preserved line ending rule, the no-write guarantee for `--check`, and a statement that the two cell sources above are blocking rather than cosmetic.
Not changed, because it is a design decision: the plan needs either a `plan_date` and `repos` column plus a defined cell format for prose-free rendering, or a narrowed goal that compares only the rows the schema can express. `Architect` and `tester` must settle it together, and T09 must assert against a post-marker fixture.

**B3. Lease expiry is compared as text but never constrained, and `--lease` had no bounds.**
Measured: `Nov 20 2026 10:00` sorts after every `2026-` timestamp and is therefore never reaped, and `2026-11-20T10:00:00.000+07:00` is seven hours wrong while comparing as live. The reaper and the lease are the entire safety mechanism for a killed process, so a shape that never expires silently converts a crash into a permanent reservation.
Changed (Schema, opening sentence): "`PRAGMA user_version = 1` is the schema version marker, so no extra table is needed." now also requires a `CHECK` pinning the fixed width UTC shape on `lease_expires_at`, with both failure modes named.
Changed (CLI surface, first paragraph): exit `4` is now "git failure, a fetch that did not complete included", and the paragraph adds `--lease <hh:mm:ss>` with a `00:30:00` default refused when unparsable, zero, negative, or over 24 hours.

**B4. Untrusted identity fields reached the row unvalidated, and the branch never had to agree with the code.**
`claiming_branch`, `plan_path`, `issue_number`, `issue_url`, and the indicator read from the plan frontmatter all entered through `commit` with no shape rule, so a row could bind a branch carrying a different code and break the traceability the ledger exists to provide. The indicator's shape was enforced only by the `project` CHECK, which surfaces as exit 1, a data error, rather than exit 3, bad configuration.
Changed (Allocation algorithm step 1): "Resolve the project root and its default branch ..." now reads the indicator from the ledger frontmatter, validates it case sensitively before SQL, and exits `3` naming the value.
Changed (reserve/commit paragraph): "`reserve` is transactional and short. `commit` is a second short transaction ..." now continues into the branch, plan path, issue number and issue URL rules, all exiting `3` on mismatch, and into the event writes required by B7.

**B5. Number permanence was claimed as structural and is not, and the obvious fix collides with T10.**
`MAX(number)` does include `voided` rows, so a burned number is not reissued while its row exists. Nothing refuses `DELETE FROM work_item` or an `UPDATE` of `indicator` and `number`; the append-only triggers cover `allocation_event` only, and T10 itself deletes a `work_item` row to simulate a ledger-only row.
Changed (paragraph after the schema): "Number permanence is structural rather than a rule to remember: rows are never deleted ..." is now "Number permanence holds for a row that still exists ... It is not yet structural against removal ... The same pair of triggers must be added to `work_item` ... That requirement collides with the drift case in the matrix, which deletes a `work_item` row ...".
Open: `edm` adds the trigger pair, and `tester` reworks T10 so drift is simulated without deleting a database row.

**B6. T16 cannot pass at Stage 9.**
It runs `git check-ignore -v plans/_plan.db` after `Push-Location $LIVE`, but `$LIVE` is the main checkout on `main`, and the `.gitignore` rule is added on the plan branch. The rule is therefore absent until the merge at Stage 13, after the case that is meant to gate it.
Not changed, because matrix content belongs to `tester`: T16 must run against the candidate worktree, or assert the rule from the candidate tree and leave the live check to post-merge smoke.

**B7. `allocation_event` was declared append-only and never written, while grading cases require rows in it.**
The published reserve statement inserts no event, yet T06 asserts a `reap` event, T13 a `commit` event, T17 a `void` event, and T11 asserts the table stays empty on failure.
Changed (reserve/commit paragraph, final sentence): now requires every state change to append its own event inside the same transaction, naming `reserve`, `reap`, `commit`, and `void`.

**B8. The instruction manifest pointed at the plan body rather than the evidence path, and required no backup sibling.**
`Architect.md` is untracked, so a manifest plus a read-back is the only proof that a local edit landed with a plan. The convention already used in this repository is `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json` with `.bak-<timestamp>` siblings, as AVRIG-00001 and AVRIG-00003 both did.
Changed (untracked file paragraph): "It is recorded with a SHA-256 manifest entry in this plan ..." is now "It is recorded with a SHA-256 manifest at `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json`, written once stage 4 assigns the code, with a `.bak-<timestamp>` sibling beside every edited instruction file ...".
Changed (Open Item 4): "with a SHA-256 manifest entry standing in for review" now names the same path and the backup siblings.

**B9. The database and DDL names were rewritten mid audit, contradicting the user's instruction and the matrix.**
The body was changed to `plans/_plan.db` and `schema/001-plan.sql` while every fixture in the matrix still expects `plans/_plan.db` and `001-plan.sql`. The database filename was given by explicit user instruction, so it is not the plan's to rename, and a half applied rename leaves the runbook and the harness pointing at two different files.
Changed (whole document): restored `plans/_plan.db` in 11 places and `schema/001-plan.sql` in 3, so the body, the target file table, and all 20 plus fixture lines agree. If the user has since asked for `_plan.db`, the matrix must be renamed in the same edit rather than left behind.

### Non blocking

- `UNIQUE (code)` is redundant rather than wrong. `code` is generated from `(indicator, number)`, the indicator CHECK forbids a hyphen, and `number` is always five digits, so the mapping is injective and that index cannot fire independently. T02 already concedes this. Kept, with the claim corrected in the backstop bullet named below rather than removed.
- `project.frozen`, `project_key`, and `repo_root` are declared with no behaviour. No subcommand reads or sets `frozen`, so the "proposed, then confirmed, then frozen" rule stays unenforced and the column implies a guarantee it does not make. Either `init` refuses a second indicator and refuses to change a frozen one, or drop the columns.
- `CREATE TABLE IF NOT EXISTS` with an unconditional `PRAGMA user_version = 1` makes schema drift invisible and would stamp version 1 over a future version 2. `init` should refuse an unknown `user_version`, and `verify` should assert the expected columns exist.
- `.read` is never constrained. `init` applies the schema somehow; state that `sqlite3` reads only the tool's own schema asset at a path fixed relative to the script, never a path derived from `--project` or from user input.
- The sqlite3 invocation shape is unspecified: stdin, `-cmd`, or a temp `.sql` file. If a temp `.sql` file is used it is another tool owned path and must satisfy the same space free rule.
- `owner_role`, `actor_host`, and `actor_user` are free text with no emptiness check, unlike `title`.
- Ownership has one overlap and one question. `AGENTS.md` appears in both S2 and S6 scope, and `.opencode/agents/Architect.md` appears in the target table under `be` but in no stream except S6. Assigning the PowerShell CLI to `be` is defensible for a transactional CLI, but `Infra` owns host scripting here, so say why it is `be`.
- S2 may "proceed against the DDL in this plan meanwhile" while S1 owns the final DDL, which is how two schemas start to diverge. Make S1 the only DDL author and S2 read the file.
- This plan's own Stage 4 approval precedes the tool it installs, so its number must come from the manual procedure and then be backfilled by `import`. Say so, or the first run of the runbook is a chicken and egg problem in disguise.
- `verify` without `--strict` exits `0` on drift while exit `1` is defined globally as "verification or drift failure". T10 confirms the intended behaviour, so the exit code table should say it.
- T15's two "git failure" rows now mean "no `origin` remote", which is the warning case, while an attempted fetch that fails keeps exit `4`. Relabel the rows.
- "Pester 3.4.0 only" in the environment table contradicts "no Pester dependency" in the harness paragraph.
- The `Architect` assignment for `plans/PLAN-INDEX.md` is legal. The Architect's edit permission allows `plans/**` and `**/plans/**`, so S3 does not breach its write scope, which is worth stating because it looks like a breach at a glance.

Wording corrections made in place, each naming its section and the sentence it changed:

- Context, fourth bullet: "a duplicate insert against a `UNIQUE (code, num)` constraint exits `1`" is now "against the `UNIQUE (indicator, number)` constraint exits `1`", because the schema declares no `(code, num)` constraint and the defect under test must be named correctly.
- Allocation algorithm step 2: "`git fetch origin <default> --quiet`, unless `--no-fetch`. A failed fetch is a recorded warning, and a hard failure only under `--strict-git`." is now split into an attempted fetch that fails (exit `4` even without `--strict-git`) and a checkout with no `origin` remote at all (warning by default, exit `4` under `--strict-git`), which is what T15 actually probes and what `PLAN-INDEX.md` requires of an indivisible fetch and recheck.
- Goals, second outcome: "Measured by a scripted 20 way concurrency test, not by inspection." is now the stated property, 20 distinct codes forming the contiguous run from `00004` to `00023`, because "the second is exactly one higher than the first" has no subject once twenty writers contend.
- Goals, third outcome: "A reservation survives a process kill, is reaped after its lease, and its number is never issued again, proven by test." is now "A killed process leaves a `reserved` row that is reaped after its lease, and the number is never issued again by that database, proven by test.", because a surviving row and a reaped row were described as one outcome and the guarantee is per database file.
- Backstop bullet under the statement: "`UNIQUE (indicator, number)` and `UNIQUE (code)` are the backstop if serialization is ever lost." is now "`UNIQUE (indicator, number)` is the backstop ... `UNIQUE (code)` is declared too, but ... cannot fire independently", which is the same thing T02 records.
- Failure modes, first row: "Second writer arrives" is now "Second writer still blocked when the 5 second timeout expires", so the row no longer implies that an ordinary second writer fails rather than proceeding after the first commits.

### Verified

- Indicator CHECK, executed against 3.51.2 with 12 values. `AB`, `AVRIG`, `AVRIG2`, and `ABCDEFGHIJ` are accepted. `A`, `abcdef`, `Abcde`, `AVRIG-1`, `AVRIG_1`, `1AVRIG`, `ABCDEFGHIJK`, and `AVR IG` are all rejected with `CHECK constraint failed`. Length 2 to 10, first character `[A-Z]` by case sensitive GLOB, and no character outside `[A-Z0-9]` is exactly `^[A-Z][A-Z0-9]{1,9}$`, and as a column CHECK it cannot be bypassed by the tool.
- Generated column: `GENERATED ALWAYS AS (indicator || '-' || printf('%05d', number)) STORED` is legal on 3.51.2 (the 3.31 requirement is met) and produced `AVRIG-00007`; `printf` is deterministic, so `STORED` is allowed.
- `max(db_max, git_max) + 1` behaves as claimed. With a stale `git_max` of 3 the statement allocated `00004`, then `00005` on a second run against the same stale payload, so the database maximum wins when the union lags.
- The silent payload failure is real and the plan's guard is right. A wrong, unset, or missing payload path inserts nothing and exits `0`, so requiring exactly one `<INDICATOR>-<NNNNN>` token on stdout before a reservation is accepted is the correct defence, because the exit code alone lies.
- `render --check` fails rather than rewriting, and now also writes nothing.
- Default branch and reconciliation records are true as measured. `avrig-ai` resolves to `main`; tags `0.2.0`, `0.2.1`, `0.3.0`, `0.4.0`, and `0.5.0` each return 0 from `git merge-base --is-ancestor` against `refs/heads/main`; the Agentic repository carries zero SemVer tags and three local branches, so its recorded step 4 stop is accurate rather than convenient.
- `.opencode/agents` is untracked (`git ls-files` count 0) and `.bak-<timestamp>` siblings already exist there, so B8 is a process fix rather than a new convention.
- Trust boundary on text is sound. Titles and reasons travel as JSON and are never interpolated into SQL, `.parameter set` carries only a tool owned path, and T07 already exercises an injection title and a quoted reason.
- Identifier taxonomy holds. Candidate tags are excluded from reconciliation by rule, release tags are bare `X.Y.Z`, `avrig/<NNNNN>/rc.001` is the Stage 8 tag, and nothing maps a work-item code to a version.
- Scope honesty holds. There is no UI in this plan, so `unslop` and `modern-web-guidance` are correctly absent, and applying either to a PowerShell and SQLite tooling plan would be the opposite error.
- Writing rules: zero occurrences of U+2014 and U+2013 in the file, measured before and after the edits.

## Architect Response to Review Findings

The verdict is accepted. Every blocking finding is resolved below, either in the design or by a decision recorded here, and every resolution that belongs to the matrix is written as an instruction to `tester` rather than left implicit.

**B1, payload shape.** Accepted, and the array envelope the analyst measured is now the requirement. Current proof: an object payload returns one row per member and `json_extract(value,'$.title')` raises `malformed JSON`; `[{"indicator":...}]` inserts exactly one row. T07b must use `$json = '[{"indicator":"AVRIG","title":"bom probe"}]'`. A simpler `INSERT ... VALUES` form with single quote doubling was also built and measured end to end during this session (four allocations, `00004`, `00005`, `00010` after a git jump, `00011` against a lagging git, hostile title stored verbatim, duplicate refused at exit `19`). It was rejected in favour of the analyst verified payload path for one reason: the matrix and the harness contract are already built around the payload, and swapping the mechanism now would invalidate a freshly validated suite for a stylistic gain. The measurement stands in this plan so a later optimisation has a starting point.

**B2, render fidelity.** Resolved as design, not wording. `created_on` and `repos` are columns with a shape check on the date; `ledger_cells` stores the ten original cell texts as JSON at `import`; and rendering resolves each cell as structured column, then snapshot text, then empty. That makes byte equality reachable without rewriting released evidence, and it keeps the two legacy `empty until deployment` cells as they shipped. T09 must grade against a post-marker fixture after `import`, not against an unmigrated copy.

**B3, lease shape and bounds.** Moot at Stage 4, and superseded by a decision rather than a fix. The user directed that no reservation exists at all, because a number is assigned once, at approval. There is therefore no `lease_expires_at`, no `--lease`, no reaper, and no `reserved` state, so the shape the analyst measured cannot be misused: the column does not exist. The finding was correct about the design as it stood, and the honest resolution is deletion rather than a `CHECK` that guards a mechanism nobody needs.

**B4, identity validation.** Shapes are now enforced at two levels. `owner_role`, `actor_host`, and `actor_user` carry non-empty checks; `claiming_branch` must contain the row's own `code`, enforced as `ck_branch_carries_code`, so a branch that carries a different work item cannot be bound to the row at all, and this was measured: the insert is refused and zero rows are written; and the indicator is validated case sensitively in the tool before it reaches SQL, exiting `3` naming the offending value. `plan_path` is validated as a repo relative path ending in `.md`, and `issue_number` as a positive integer, both exiting `3`.

**B5, permanence.** Resolved structurally and the collision with the matrix is resolved in favour of permanence. `tr_work_item_no_delete` aborts `DELETE`, `tr_work_item_no_rekey` aborts an `UPDATE` of `indicator` or `number`, and the matrix simulates ledger-only drift by editing the ledger rather than by deleting a database row. Permanence is claimed for the file, not beyond it, and the plan says so.

**B6, T16.** Accepted as a matrix defect. T16 must run against the candidate worktree, where the `.gitignore` rule exists, and the live checkout check moves to post-merge smoke after Stage 13.

**B7, events.** The statement itself now writes them, in the same transaction: one `assign` event bound to `last_insert_rowid()` and carrying the `git_max` used, and `void` writes its own `void` event. `import` and `verify` write their own where applicable. The event vocabulary is exactly `('assign','void','import','verify')` and the CHECK refuses anything else, so a test can no longer grade an event the design cannot produce. Measured: inserting a `reap` event fails the CHECK.

**B8, instruction manifest.** Accepted as written. The manifest is `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json` with `.bak-<timestamp>` siblings beside every edited instruction file.

**B9, naming.** Resolved toward the user's latest explicit instruction, which is `plans/_plan.db`, with the DDL asset at `schema/001-plan.sql`. The analyst restored `_plan_index.db` from an instruction that had already been superseded twice, so the body and the matrix are renamed together in one pass: 31 occurrences of the database name and 7 of the DDL name. A half applied rename is the defect, not the rename.

**Stage 4 amendment, no reservation lease.** After the review closed, the user directed that no reservation exists, because a number is assigned once at approval. The design was simplified rather than patched: `assign` replaces `reserve` plus `commit`, the row is written already `committed` and already bound to its branch and plan path, and `lease_token`, `lease_expires_at`, `reserved_at`, the `reserved` state, the `reap` event, and `--lease` are deleted. `voided` survives as the explicit abandonment transition only. B3 and B7 are re-resolved above on that basis, and the whole amended DDL and the whole `assign` statement were executed again from this file, not paraphrased: `00004`, then `00010` when git was ahead, then `00011` after voiding `00004`, each writing exactly one `assign` event, with a foreign-code branch refused and zero rows written.

Non blocking items are settled as follows, so none becomes a later surprise:

- `frozen` gains behaviour instead of being dropped: `init` refuses a second indicator, refuses any change to a frozen one, and exits `3`.
- `init` refuses an unknown `user_version` rather than stamping `1` over it, and `verify` asserts the expected columns exist.
- `sqlite3` reads only the tool's own schema asset at a path fixed relative to the script; no path derived from `--project` or from user input is ever opened with `.read`.
- The invocation shape is stdin, with `.bail on` and `.timeout 5000`, so no temp `.sql` file exists to inherit a path rule.
- `S1` is the only DDL author and `S2` reads the asset; `AGENTS.md` is owned by `S6` alone; `.opencode/agents/Architect.md` belongs to `S6`. The CLI is assigned to `be` because it is a transactional application with SQL semantics rather than host provisioning, and `Infra` owns only the OneDrive pinning step.
- This plan's own code comes from the manual procedure, because the tool does not exist yet. The first `import` then backfills its row, which is recorded here so the sequence is not mistaken for a gap.
- `verify` exits `0` without `--strict` on drift by design, `1` under `--strict`; the exit table says so explicitly.

Matrix corrections required before Stage 9, addressed to `tester` in a follow up: T07b array payload, T09 post-marker fixture after `import`, T10 drift by ledger edit rather than row deletion, T16 against the candidate worktree, T15 rows relabelled for "no `origin` remote" versus "attempted fetch failed", the Pester contradiction resolved, every fixture renamed to `plans/_plan.db` and `001-plan.sql`, plus new cases for the branch-code check, the delete and rekey triggers, and the event writes. A second pass after the Stage 4 amendment converts T06 from lease reaping to explicit `void`, drops T13's lease guard, removes every `--lease` bound from T15, removes the lease shape rows from T02, deletes the `Get-LeaseToken` helper, and rewrites every `reserve` then `commit` sequence as a single `assign`.

