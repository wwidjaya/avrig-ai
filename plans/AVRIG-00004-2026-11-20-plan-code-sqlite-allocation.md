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
- A row's `plan_path` is checked in both directions rather than trusted. `verify` reports drift when a committed row names a file that is not there, and `update --plan-path` is the sanctioned repair, guarded to a relative path under `plans/` that carries the row's own code token and names a real file. This goal exists because the live ledger failed it: all four migrated rows pointed at their pre-approval names, and `verify --strict` called the ledger clean, so a pointer that rots silently was the one form of drift the tool could not see.
- A row written at assignment can be advanced afterwards without being re-keyed. `update` writes the six record fields (status, candidate tag, evidence, issue, issue URL, release version), refuses the six protected columns and a voided row by name with exit `3`, writes exactly one event per call, and leaves `verify --strict` to catch a skipped `export` as drift, proven by test. This goal exists because the ledger could otherwise be created and never advanced: stages 8, 12, 13, 14, and 16 each record something on a row that already exists, and without a writer those columns are decoration.

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
           OR instr(claiming_branch, indicator || '-' || printf('%05d', number) || '-') > 0)
);

CREATE INDEX IF NOT EXISTS ix_work_item_state ON work_item (state);

CREATE TABLE IF NOT EXISTS allocation_event (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  indicator  TEXT NOT NULL,
  number     INTEGER NOT NULL,
  event      TEXT NOT NULL CHECK (event IN ('assign','void','import','verify','update')),
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
| `update` | advance an existing row: `--code` plus any of `--status`, `--candidate-tag`, `--evidence`, `--issue`, `--release-version`, `--plan-path`, writing one `allocation_event` per call |
| `verify` | cross check the database against the committed dump and the git union, `--strict` to fail on drift |
| `export` | write `plans/_plan.sql` deterministically from the database, `--check` to fail instead of writing |

`assign` self heals: when `plans/_plan.db` is absent it runs `import` first, so a fresh clone needs no ceremony and no number is skipped.

`update` exists because the analyst asked why the ledger could be born but not advanced. Every delivery stage after assignment records something on a row already written: the candidate tag and its commit at stage 8, the verdict and the version decision at 12, the merge at 13, the release tag at 14, and the released version at 16. Without a writer those six columns (`ledger_status`, `candidate_tags`, `evidence_path`, `issue_number`, `issue_url`, `release_version`) are decoration, and the only alternative is a hand `UPDATE` against the database. Hand SQL was rejected for a concrete reason rather than tidiness: `tr_work_item_no_rekey` guards only `indicator` and `number`, so an ad hoc `UPDATE` could set `state = 'committed'` on a voided row and un-burn a number this design calls permanent, and it would write no event. So `update` allows exactly those six fields plus `--plan-path`, refuses `indicator`, `number`, `state`, `assigned_at`, `committed_at`, `voided_at`, and `voided_reason` by name, refuses a voided row outright, and records one event per call. It does not export automatically; `update` then `export` then `verify --strict` is the cycle, and skipping the middle step is exactly what `verify --strict` reports.

`--plan-path` is in that list because of a defect found on the live ledger during this plan's own Stage 7, and it is worth stating in full rather than folded into the paragraph above. All four migrated rows named a file that does not exist, every one of them carrying the pre-approval draft name, because the approval rename shortens the slug and the legacy markdown ledger was never corrected afterwards. `verify --strict` exited `0` on all four, since it checked only that a number claimed by a filename or a branch had a row and never checked the other direction. A path is metadata rather than identity: the identity of a row is `(indicator, number)`, so the repair belongs in the row and not in a file rename that would break the issue footer, the evidence folder, and every commit message pointing at the old name. `--plan-path` therefore refuses an absolute path, refuses a path outside `plans/`, refuses a path whose code token belongs to a different row, and refuses a path with no file behind it, accepting `plans/done/` because stage 16 archives the plan there. `update` and `verify` then check the pointer in both directions: a committed row whose `plan_path` names a file that is not there is drift, and the message names the repair.

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
- No structural column carries a machine path. The `project` row's `repo_root` is written as `NULL` rather than as the absolute path `init` was handed, because the dump is committed and an absolute path there would differ on every clone, machine, and worktree while telling the file nothing it cannot derive. `project_key` stays, since the folder leaf is portable and identifies the project to a human reader.
- Audit columns and free text do carry one, deliberately, and the distinction is worth stating because a casual reading of the bullet above would call them defects. `actor_host` and `actor_user` record the machine and the account that wrote each row, which is what an audit trail is for; `deferred_defect` rows 1 and 6 quote real paths from real findings, such as `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\`, and rewriting a defect description to hide the path it names would falsify the record. So the rule is narrow and checkable: structural columns are portable, and evidence keeps the words it was written with.

Measured on the real repository, which is the only run that counts: `init` created the database and an empty dump, the migration seeded the four rows, and `export` wrote 118 lines. `export --check` then reported no change, `verify --strict` exited `0` agreeing across the database, the dump, `PLAN-RULES.md`, and the git union, and a full round trip (`import` to rebuild from the dump, then `export`) reproduced the dump byte for byte at SHA-256 `359826FC...5B5AA9` (the dump was regenerated after the schema amendments in decisions 10 and 11, so the digest is the post-amendment one; the determinism claim was measured again on it rather than carried over. It moved once more to `E0C411CA...E218` at the stage 7 gate, after decision 12 repaired four stale plan paths and added four events, and the round trip was measured again there rather than assumed: `plans/evidence/AVRIG-00004/stage7-gate.md`). So the determinism claim is a measured fact on this project's own data rather than only on a fixture.

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

The body was regenerated from the plan at stage 7, and the reason is worth recording rather than hiding. The first version described the design as it stood at approval: three layers, with `plans/PLAN-INDEX.md` as the durable authority, the markdown ledger table as a rendered view, and `render` as the command that produced it. The user removed all three afterwards, so by stage 7 the published request was describing a design that no longer existed, down to a traceability line naming `PLAN-INDEX.md` as the ledger. It was rewritten from the current plan rather than patched, because the rule is that the body is generated from the plan and a hand-patched body would be a second document to maintain. The pre-edit body is kept at `plans/evidence/AVRIG-00004/issue6-before.md` so the correction is auditable. Four stale `render` references, three `PLAN-INDEX.md` references used as authority, and one sentence about `import` parsing a ledger cell, all gone.

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
| `shared/skills/plan-code/plan-code.ps1` | create | `be` | the allocator: five source union, SQLite transactions, eight subcommands |
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

### Stage 7, what the build gate means here

This plan ships no compiled target. `plan-code.ps1` is a single PowerShell script, `001-plan.sql` is a schema asset, and `Test-Allocation.ps1` is a test harness, so `cargo check` and `pnpm build` have nothing to say about it and a claimed workspace build would be theatre. The gate is four measured checks instead:

| Check | How | Pass |
|---|---|---|
| syntax | `[System.Management.Automation.Language.Parser]::ParseFile` over both `.ps1` files, collecting the error list rather than testing for a null | zero errors in both, with the token count reported as evidence that the file was actually parsed |
| schema asset | `sqlite3 <scratch> ".read schema/001-plan.sql"` | exit `0`, `PRAGMA integrity_check` returns `ok`, `user_version` reads `1`, and `sqlite_master` shows five tables, four triggers, and one index |
| dump round trip | `import` from `plans/_plan.sql`, then `export --check` | `export --check` exits `0`, and the regenerated dump is byte identical to the committed one |
| real ledger | `verify --strict` on the working checkout | exit `0`, with the row count it reports recorded |

The build id is `<CODE>-<NNNNN>-build.<NNN>` with `<NNN>` matching the candidate it precedes, and it lives in the evidence folder rather than as a Git tag, because there is no artifact to tag. A null check on the parser's error variable is not a substitute for the check itself: a parse that never ran leaves that variable unset, which reads as clean.

## Risks and Mitigations

- OneDrive touching a live SQLite file. Mitigated by WAL, short transactions, `integrity_check` in `verify`, and a rebuild path that makes corruption recoverable. Accepted, because the file is disposable by design.
- The database is mistaken for the archive. Mitigated in wording everywhere: `plans/_plan.sql` in git holds the record, the database holds the lock and the cache.
- Two machines still race. Mitigated by leaving the git push as the gate and by seeding the candidate from five sources including the remote dump, so a stale database jumps forward.
- A burned number from a losing race. Accepted: the existing rule already treats a failed push as the fail fast signal, and a gap is honest while a duplicate is not.
- An agent assigns without exporting. Mitigated by `verify`, whose first check is whether `export` would change the dump, so a database that is ahead of its record is reported immediately rather than at the next merge.
- The dump is edited by hand. Mitigated by the same check in the opposite direction, and by the fact that a hand edit is a line of SQL in a text diff rather than a silent database change nobody can see.
- A binary database is committed by mistake. Mitigated by `plans/_plan.db*` in `.gitignore` and by the fact that the file is regenerable, so committing it is a mistake with a one line fix rather than a corrupted history.
- Untracked agent definition. Mitigated by the SHA-256 manifest entry and by keeping the normative rule in tracked `AGENTS.md`.
- A pointer that rots while the ledger reports clean. This is not hypothetical: it had already happened to all four rows before stage 7, and `verify --strict` called them clean. Mitigated by checking the pointer in both directions and by `update --plan-path` as the repair, so the failure costs one command instead of a file rename that invalidates the issue, the evidence, and three commit messages.
- A record that can be created but never advanced. Mitigated by `update`, which is allowlisted to the six record fields, refuses the protected six and a voided row by name, and writes one event per call. This risk is listed rather than assumed away because the rejected alternative is the dangerous one: a hand `UPDATE` can set `state = 'committed'` on a voided row and un-burn a number this design calls permanent, and it leaves no event, so the habit would quietly defeat the whole record.

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

10. `update` becomes the eighth subcommand, on the analyst's blocking finding rather than on my initiative. The audit asked a question I had not: the ledger could be created but never advanced. Six columns (`ledger_status`, `candidate_tags`, `evidence_path`, `issue_number`, `issue_url`, `release_version`) had no writer at all, so stages 8, 12, 13, 14, and 16 each had to record something and none had a mechanism. The two rejected alternatives are worth naming: hand-editing the dump, which the dump's own header forbids, and a raw `UPDATE` against the database, which is unsafe for a specific reason rather than an aesthetic one, because `tr_work_item_no_rekey` guards only `indicator` and `number`, so ad hoc SQL could set `state = 'committed'` on a voided row and un-burn a number this design calls permanent, and it would write no event. So `update` takes `--code` plus the six allowlisted fields, refuses the protected ones by name, refuses a voided row outright, and writes one `allocation_event` per call. This also widens the event vocabulary to include `update`, which is an `edm` asset change and a `T02` amendment.

11. `ck_branch_carries_code` gains a trailing hyphen in its needle: `instr(claiming_branch, indicator || '-' || printf('%05d', number) || '-')`. Measured, not theorised: bare `instr` matched a prefix sibling, so a row for `AVRIG-00005` accepted `feat/AVRIG-000051-x`, whose code token is a different work item, and `edm` reproduced both behaviours side by side to prove the old expression accepted what the new one refuses. The consequence is deliberate and stated: a branch naming only `feat/AVRIG-00005` with no slug is now refused, which matches the rule that the slug is required. The same tightening is applied inside `assign`'s own guard, so the transaction refuses a mismatched branch before the session ends rather than only at the insert.

12. `update` gains `--plan-path` as a seventh field, and `verify` gains a check that the pointer resolves, both because the live ledger failed the check I had not written. The four migrated rows each named their pre-approval draft file, the approval rename having shortened every slug afterwards, and `verify --strict` reported the ledger clean on all four. The defect is one directional: the tool proved that every number claimed by a file or a branch had a row, and never that every row had a file. Keeping the path in the row rather than renaming four committed files is deliberate, because the row identity is `(indicator, number)` and a path is metadata, while a rename would invalidate the issue footer, the evidence folder, and three commit messages. The guard set is narrow on purpose: relative, under `plans/`, its file name beginning with the row's own code followed by a hyphen, and naming a real file, with `plans/done/` accepted because stage 16 archives the plan there. This was applied to the live ledger before the first candidate rather than deferred: `verify --strict` first reported four drift findings, four `update --code <CODE> --plan-path <real path>` calls then exited `0` and wrote one event each, `export` grew the dump to 122 lines, and `verify --strict` returned `ok`. `plans/evidence/AVRIG-00004/plan-path-repair.md` records the before and after listing. No file was renamed, because a rename would have invalidated the issue footer, the evidence folder names, and three commit messages to satisfy a metadata error.

## Test Specification and Validation Scenarios

The subject under test is the plan-code allocator, `shared/skills/plan-code/plan-code.ps1`, against its schema asset `shared/skills/plan-code/schema/001-plan.sql`. The runnable suite is `shared/skills/plan-code/tests/Test-Allocation.ps1`, and this section is its specification: every case named below exists in that file, and every assertion below is an assertion the file makes.

### What the contract is, and therefore what is graded

The design is dump backed. There is no markdown ledger, no marker block, and no `render`.

- Seven subcommands: `init`, `import`, `assign`, `void`, `status`, `verify`, `export`.
- Exit codes: `0` ok, `1` verification or drift, `2` contention, `3` invalid input or configuration, `4` git failure.
- `{code}` is a placeholder in `--branch` and `--plan-path`, substituted with the allocated code.
- The durable record is a deterministic plain text dump at `plans/_plan.sql`, written by `export`. The working database `plans/_plan.db` is disposable and is ignored by git.
- `import` deletes `plans/_plan.db` and applies `plans/_plan.sql`.
- `plans/PLAN-RULES.md` carries `project_indicator:` in its frontmatter, and that value must equal the `project.indicator` row.
- `work_item` has no `ledger_cells` column, `ck_committed_branch` is strict, and `deferred_defect` and `indicator_alias` exist.
- `status --json` emits one object per row with snake_case column names.

The suite grades that contract, never an internal detail: no case asserts on a function name, a private file layout, or a store shape. It asserts on exit codes, stored values, rendered rows, dump bytes, and filesystem effects.

### Runner contract

```powershell
pwsh -NoProfile -File shared/skills/plan-code/tests/Test-Allocation.ps1 `
  -Project <project root> -Out <evidence folder> -Tag <code-lower>/<NNNNN>/rc.<NNN>
```

- `-Case T03` (or `-Case T01,T02`) runs a subset. `-Keep` leaves the scratch tree for inspection. `-IncludeOneDrive` opts into the synced-folder concurrency variant.
- One `PASS` or `FAIL` line per case, each carrying the case id, the assertions passed over the assertions attempted, the candidate tag, the project commit SHA, and the tool checkout SHA, followed by a `ROLLUP n/21 PASS exit=n` line. A failing case makes the process exit non-zero.
- A missing subject is reported as `BLOCKED` with the reason and counted as a failing case, never skipped silently.
- Runner constants: `$PC` the allocator, `$DDL` the schema asset, `$PW` `pwsh`, `$SQL` `sqlite3`, `$TMP` a directory unique to the process, `$env:TEMP\opencode\plan-code\<pid>-<guid>` unless `-Scratch <dir>` names one, so two runs started at the same time cannot delete each other's fixtures. Every fixture, database, dump, payload, and race output lives under `$TMP`.
- Fixtures never touch the live checkout, its `plans/PLAN-RULES.md`, its `plans/_plan.sql`, or its `plans/_plan.db`.
- Every fixture is a real git repository with a bare `origin`, `core.autocrlf=false`, no commit signing, and `refs/remotes/origin/HEAD` set, because the default branch contract resolves through it.
- A fixture seeds its database by applying the shipped DDL, and produces `plans/_plan.sql` with the tool's own `export`. The dump is therefore always in the one format `verify` compares against, and a schema or export regression fails the fixture rather than passing quietly.
- A documented retry exists for exactly one case: exit `2` means the writer wrote nothing, so the same writer may be relaunched. Every other non-zero exit is a finding.
- Assertions are specific enough that a real defect fails them. No assertion is relaxed to make a case green.

### Scenario table

| ID | Threat | Gate |
|---|---|---|
| T01 | The schema asset and `init` disagree, or a retired column survives | 1 |
| T02 | A constraint that the design claims is structural is not enforced | 1 |
| T03 | Twenty concurrent writers collide, reuse, or skip a number | 3 |
| T04 | The git union does not seed the candidate upward | 4 |
| T05 | A foreign indicator or a number in prose inflates the series | 4 |
| T06 | An abandoned or killed allocation reissues its number | 5 |
| T07 | A title or reason injects SQL, or the payload shape is wrong | 5 |
| T08 | A deleted database cannot be rebuilt, or rebuild is not idempotent | 4 |
| T09 | The dump is not deterministic, or does not round trip | 6 |
| T10 | Drift between the dump and the database goes unreported or is unresolvable | 6 |
| T11 | A missing `sqlite3` is reported as something other than a configuration failure | 7 |
| T12 | `--dry-run` writes | 7 |
| T13 | `assign` writes a row without its audit event, or an event without a row | 2 |
| T14 | The approval runbook does not leave database, dump, plan file and branch in agreement | 8 |
| T15 | The exit code contract is not what the callers branch on | 7 |
| T16 | The database reaches git, or the dump is gitignored | 7 |
| T17 | `status` and `void` misreport state or lose the reason | 2 |
| T18 | `init` overwrites a durable record, a foreign project, or a newer schema | 1 |
| T19 | Goal 6 is ungraded: a numbered fact survives outside the database, or the archive carries the machine that made it | 1 |
| T20 | The delivery columns have no sanctioned writer, so stages 8, 12, 13, 14, and 16 have no mechanism | 2 |
| T21 | A row's `plan_path` is trusted rather than checked, so a pointer that rotted at the approval rename reports clean forever | 2 |

Gates run in that order. T14 runs last, on a clean scratch clone.

---

#### T01 Schema creation and integrity

Threat: `init` builds a database that is not the shipped schema, or a column retired with the markdown layer survives as dead weight.

Fixture: a coded fixture repository with no seed rows. The suite asserts `plans/_plan.db` is absent before `init`, then runs `init --indicator AVRIG`.

Assertions:

- `init` exits `0`, `user_version` is `1`, `integrity_check` is `ok`, `journal_mode` is `wal`.
- Tables are exactly `allocation_event,deferred_defect,indicator_alias,project,work_item`.
- Indexes are exactly `ix_work_item_state`, and it is on `state`.
- Triggers are exactly `tr_allocation_event_no_delete,tr_allocation_event_no_update,tr_work_item_no_delete,tr_work_item_no_rekey`.
- The `project` row carries `AVRIG`. `created_on` and `repos` exist as data columns. `ledger_cells` does not exist. No `lease_token`, `lease_expires_at`, or `reserved_at` exists.
- The generated `code` column is absent from `pragma_table_info` and reported `hidden=3` by `pragma_table_xinfo`, which is what a column list driven dumper depends on.
- `deferred_defect` columns are `id,found_during,defect,evidence,at`, and `indicator_alias` columns are `old_code,new_code,migrated_on`.
- The shipped DDL applies on its own to a scratch database, sets `user_version=1`, passes `integrity_check`, and creates the same five tables and four triggers. `init` therefore cannot hide a broken asset.

Pass: every assertion above holds. A hand rolled schema inside `init`, a stale column, or a broken `001-plan.sql` fails the case.

#### T02 Constraint proof, table driven

Threat: a constraint the design calls structural is only a convention, so a bad row lands.

Fixture: a fresh `init` database on an indicator-registering project, seeded with one legal committed row, its `assign` event, and one `indicator_alias` row so the duplicate and the append-only triggers have something to fire on.

Assertions, every refusal probed by direct SQL:

- `19` (SQLITE_CONSTRAINT) with the named refusal text for: duplicate `(indicator, number)`, retired `state` values `pending` and `reserved`, empty and whitespace-only `title`, `number` `0` and `100000`, a committed row with a null `claiming_branch`, a committed row with a null `committed_at`, a voided row with no reason, empty `owner_role`, empty `actor_host`, whitespace `actor_user`, a branch carrying another code, a `created_on` that is not `YYYY-MM-DD`, a foreign indicator that violates the `work_item` to `project` foreign key with `PRAGMA foreign_keys=ON`, a lowercase and a malformed indicator, `frozen` out of range, a second `assign` event on one number, an `UPDATE` and a `DELETE` of `allocation_event`, a `DELETE` of `work_item`, and an `UPDATE` of `work_item.number` and `work_item.indicator`.
- `19` with the named refusal for an empty `found_during`, a whitespace-only `defect`, and a duplicate `indicator_alias.old_code`.
- `uq_work_item_number` and `uq_work_item_code` are both declarable and present in the DDL, and the case records that the second cannot fire independently because `code` is generated from the pair.
- A committed row whose branch carries a prefix sibling, `feat/AVRIG-000051-x` on number `5`, is refused by `ck_branch_carries_code`, while `feat/AVRIG-00005-x` is accepted and a voided row with a `NULL` branch is still accepted. The needle ends in a hyphen so the code must be a full token; the earlier expression without it accepted the sibling, which is why it changed.
- `event='update'` is accepted by the event CHECK, and `event='reserve'` is still refused by it.
- After every refusal: exactly the seeded row and event and alias survive, no defect row landed, no retired state reached a row, no foreign indicator reached the registry, and `integrity_check` is `ok`.

Pass: all probes refuse, the probe count is not smaller than the set the case declares, and nothing partial survived.

#### T03 Twenty way concurrency

Threat: concurrent writers collide, so two owners receive one number, or a writer abandons a number it never recorded.

Fixture: a coded repository seeded with three committed rows, then twenty real `pwsh` processes launched together, each running `assign --branch 'feat/{code}-race-<i>' --plan-path 'plans/{code}-2026-11-20-race-<i>.md'`. Every record is prepared before launch so process start jitter cannot serialise the writers by accident. Exit `2` is retried once, because exit `2` means nothing was written.

Assertions:

- Every writer exits `0` after the documented retry. A failure is reported as one line naming the class counts (constraint, lock, other) and the first offending writer's stderr, so a partial run is characterised rather than hidden behind the first throw.
- No exception, native command error, or malformed JSON appears on stderr.
- The twenty returned codes are distinct, and the set equals `AVRIG-00004` to `AVRIG-00023`.
- The database holds twenty-three committed rows with twenty-three distinct codes, one `assign` event per row, no duplicate numbers, and a contiguous series from `4` to `23`.
- Every row carries its own code inside both `claiming_branch` and `plan_path`, which is what the `{code}` placeholder promises under a race.
- `integrity_check` is `ok` afterwards.
- With `-IncludeOneDrive`, the same assertion set runs against a synced folder path, and the folder is removed afterwards. The default run keeps every fixture under `$TEMP`, per the runner contract.

Pass: all of the above.

#### T04 Git union seeds the candidate upward

Threat: a number that exists only in git is reissued, or a number that exists only in the database is pulled backwards.

Fixture: a coded repository seeded with three committed rows. The case adds a coded plan file and a branch for `AVRIG-00011` without touching the database, then assigns.

Assertions:

- The candidate is `AVRIG-00012`, which is `git_max + 1`.
- The case then removes that plan file and branch from git and assigns again: the candidate is `AVRIG-00013`, so the database maximum wins and the union never regresses.

Pass: both candidates are exact.

#### T05 Indicator filtering

Threat: a foreign code, or a number that merely appears in prose or in a filename that is not a coded plan, inflates this project's series.

Fixture: a coded repository seeded with three committed rows, a `PLAN-RULES.md` whose prose names `WEB-00009`, `AVRIG-00442`, and `PROJ-00099`, plus `plans/WEB-00009-...md`, `plans/AVRIG-00003-2026-11-20-migrate-to-20250-table.md`, `plans/2026-11-20-AVRIG-00442-draft-style.md`, `plans/done/WEB-00021-...md`, a `feat/WEB-00021-foreign` branch, and a `feat/AVRIG-00003-slice/reporting` slice branch.

Assertions:

- The assigned code is exactly `AVRIG-00004`. Any of `00010`, `00021`, `00250`, `00442`, or `00443` would be a failure naming the source that leaked.
- No foreign indicator reached the database, and the row count is exactly the three seeded rows plus the one written.

Pass: the exact code and the exact row count.

#### T06 Void burns the number, and a killed assign is all or nothing

Threat: an abandoned plan hands its number to a second owner, or a killed `assign` leaves a row with no event or an event with no row.

Part a, the explicit abandonment transition, on a fixture with no seed row, no coded file, and no branch, so the git union is zero.

Assertions: `assign` gives `AVRIG-00001` and commits it; `void --code AVRIG-00001 --reason 'plan abandoned'` exits `0`, sets `state='voided'`, stores the reason verbatim, stamps `voided_at`, and writes exactly one `void` event, with two events in total; a second `assign` gives `AVRIG-00002`, and the voided row still exists, so the burn is recorded rather than hidden.

Part b, a real process kill. A live `assign` is stopped after roughly 250 milliseconds, and the suite waits for the `sqlite3` child to settle before asserting.

Assertions: `integrity_check` is `ok`. The outcome is one of exactly two shapes, and neither is a torn write: three rows and four events, with `AVRIG-00003` committed and its own event present; or two rows and three events, with no row and no event for `AVRIG-00003`. Any other shape fails the case. The next number is then strictly `max + 1`, and no number is duplicated.

Pass: one of the two allowed shapes, plus the monotonic continuation.

#### T07 Injection through the payload path

Threat: a title, a reason, or a payload envelope escapes the parameter path and either injects SQL or breaks allocation.

Fixture: a coded repository seeded with three committed rows and an `init` database. The title is `It's a "quoted" title'; DROP TABLE work_item; --` and the void reason is `push rejected; "non-fast-forward"`.

Assertions: both calls exit `0`, the stored title and reason are byte identical to the input, all three tables still exist, exactly one `void` event is written, and `integrity_check` is `ok`.

Part b pins the payload envelope and read shape as measured facts, so `be` cannot drift from them: a one element array parses and yields its title; the same array with a UTF-8 BOM still parses; a bare object envelope fails as `SQLITE_ERROR` with `malformed JSON` and exit `1`; an empty payload fails the same way. The case also asserts that `Set-Content -Encoding utf8` under `pwsh` 7 writes no BOM and `utf8BOM` does, so the fixture files are what the case says they are.

Pass: verbatim storage, surviving schema, one event, and the four envelope outcomes.

#### T08 Import rebuilds from the durable dump

Threat: the database is lost, accidentally or on another clone, and the record cannot be rebuilt, or a rebuild duplicates rows or moves bytes.

Fixture: a coded repository whose dump was produced by `export`, then one more `assign` and a fresh `export`, so the dump and the database hold four rows.

Assertions: the database files are deleted, `import --indicator AVRIG` exits `0`, and afterwards there are four rows with codes `AVRIG-00001` to `AVRIG-00004`, and the database maximum equals the pre-deletion maximum. A second `import` changes no row and writes no event, verified by a per-row digest, and the dump is byte identical before and after. A subsequent `assign` returns exactly pre-deletion maximum plus one, so deletion changes nothing about allocation.

Pass: identical digest, identical dump bytes, and the expected next code.

#### T09 Dump determinism and round-trip

Threat: the durable record is not reproducible, so every commit rewrites it, every `verify` reports drift, and a hand edited dump silently changes history.

Fixture: a fresh `init` project, then two assignments whose titles carry a single quote, a double quote, a backslash, a Windows path, and a `DROP TABLE` attempt. Both travel as JSON values.

Assertions:

- `export` writes `plans/_plan.sql`, BOM free, and a second `export` is byte identical by SHA-256.
- Both hostile titles are stored verbatim.
- With the database deleted, `import` rebuilds both rows, both titles survive unchanged, and an `export` of the rebuilt database reproduces the dump byte for byte.
- `verify --strict` exits `0` after the round trip, so a clean checkout is not drift.

Pass: equal hashes at both comparison points, verbatim strings, and a clean `verify`.

#### T10 Verify detects drift in both directions

Threat: the database and the durable record disagree and nobody is told, or one direction of drift cannot be resolved by the operation it calls for.

Fixture (a): a coded repository whose dump is current, a clean `verify --strict` baseline, then a legal row inserted directly into the database at `AVRIG-00007` so the database leads.

Assertions (a): `verify --strict` exits `1` and the finding is labelled `drift:` and names `_plan.sql`; `verify` without `--strict` exits `0` and still names the artifact; the database still holds five rows, so `verify` reported rather than repaired. `export` then carries `AVRIG-00007` into the dump and `verify --strict` exits `0`, which proves the remedy for this direction works.

Fixture (b): a coded repository with four rows whose `plans/_plan.sql` is replaced by the dump of a five row repository, so the dump leads. The dump is produced by `export`, never hand edited, so the case stays format agnostic.

Assertions (b): `verify --strict` exits `1` and names `_plan.sql`; the database is still four rows, so `verify` did not mutate it; `import` then recovers five rows including `AVRIG-00005`, leaves the dump byte identical, and `verify --strict` exits `0`.

Pass: both directions detected, both reported, neither destructive, and each resolved by its own operation.

#### T11 Missing sqlite3 is a configuration failure

Threat: a environment without `sqlite3` reports a data error, or writes a partial row before giving up.

Fixture: an `init` database on a coded repository, and a probe script that clears `PATH`, unsets any `AVRIG_SQLITE3` override, and runs `assign`.

Assertions: exit `3`, the message names `sqlite3`, and neither a row nor an event is written.

Pass: exit `3` with the binary named and the database untouched.

#### T12 Dry run writes nothing

Threat: a preview consumes a number.

Fixture: an `init` database on a coded repository with three coded files and branches, so the candidate is `AVRIG-00004`.

Assertions: `assign --dry-run` exits `0` and prints `AVRIG-00004`, the row count and the event count are unchanged, and a subsequent real `assign` still receives `AVRIG-00004`.

Pass: unchanged counts and an unchanged candidate.

#### T13 assign writes one row and one event

Threat: a row can exist without its audit event, an event without its row, or one call can write more than one of either.

Fixture: an `init` database on a coded repository with three coded files and branches.

Assertions: one `assign` with `--issue 42` writes exactly one row and exactly one `assign` event, no row lacks its own `assign` event, and the event count equals the row count. Then a refused `assign` whose branch names another code exits `3` and changes neither count, creates no row for the code its branch named, and leaves the earlier row untouched.

Pass: equal counts before and after the refusal, and no orphan on either side.

#### T14 Approval runbook end to end

Threat: the runbook the Architect follows leaves the database, the dump, the plan file, and the branch in disagreement, so approval ships an untraceable record.

Fixture: a coded repository with a seeded database and a current dump, plus an uncoded draft plan.

The runbook: `assign --branch 'feat/{code}-demo-task' --plan-path 'plans/{code}-2026-11-20-demo-task.md' --issue 123`, then `export`, then `git mv` the draft to the coded name, then create the claiming branch, then `verify --strict`.

Assertions: the code is `AVRIG-00004`; `verify --strict` exits `0`; the database holds one row for the code; the dump carries it; exactly one coded plan file exists; exactly one branch carries it. The approval commit carries both the coded plan file and `plans/_plan.sql`. A following `--dry-run` returns `AVRIG-00005`.

Pass: every one of those, with `verify --strict` green before the commit and the commit carrying both artifacts.

#### T15 Exit code contract

Threat: callers branch on the exit code, so a code that means something else costs a caller its safety.

Fixture: an `init` database on a coded repository; two further fixtures for the git cases.

Assertions, all `3`: empty `--title`; lowercase `--indicator`; an unknown flag; `void` for an unknown code; a branch carrying another code; a plan path outside `plans/`; a plan path that is not markdown; a non numeric `--issue`. Afterwards the ledger is empty, so no refusal wrote a row or an event.

Git cases:

- No `origin` remote at all: `assign` exits `0` with a `warn` line, and exits `4` under `--strict-git`, with only the lax run having written a row.
- `origin` configured but unreachable: `assign` exits `4` unconditionally and writes no row, while the same call with `--no-fetch` exits `0`.

`status --json` exits `0` and lists zero rows, which is the empty case the report path has to survive.

Pass: every code above, and no write from any refusal.

#### T16 The database never reaches git, and the dump is not ignored

Threat: a binary database is committed, or the durable dump is gitignored and never travels.

Fixture: the project tree under test, resolved from `-Project`. The gate note from the plan review applies: this case must run against the candidate tree, not the pre-merge default branch, or the rule is absent until after the case that gates it.

Assertions: `git check-ignore -v` exits `0` for `plans/_plan.db`, `plans/_plan.db-wal`, and `plans/_plan.db-shm`, each named by a `.gitignore` rule; `plans/_plan.sql` is not ignored; `git status --porcelain plans/` reports no database file; `git ls-files plans/` tracks no database file.

Pass: all six.

#### T17 Status and explicit void

Threat: the report shows a state the database does not hold, hides a burned number, or loses the reason a number was abandoned.

Fixture: a coded repository whose durable record was produced by `export` and then rebuilt by `import`, so the case also proves the dump is the seed source.

Assertions: `import` rebuilds the one seeded row; `assign` returns `AVRIG-00002`. `status --json` lists exactly two rows, the assigned row appears under its code, its `state` is `committed`, its `claiming_branch` is reported under that snake_case name, and `voided_reason` is null. `void --code AVRIG-00002 --reason 'push rejected'` exits `0`, sets `state='voided'`, stores the reason, and writes one `void` event; `status --json` then reports `voided` with that reason. A following `assign` returns `AVRIG-00003`, so the voided number is not reissued, and `status --json` lists three rows. Row lines are matched at column 0, so a detail line that echoes the code does not read as a second row: the committed view has no `AVRIG-00002` row and one `AVRIG-00003` row, and the voided view has one `AVRIG-00002` row and no `AVRIG-00003` row.

Pass: exact counts, exact field names, and both filtered views.

#### T18 init is idempotent and refuses a foreign or newer schema

Threat: `init` overwrites a durable record, registers a second project, or silently reapplies an older schema over a newer one.

Fixture: two `init` projects, one of them with an empty file at `plans/_plan.db`.

Assertions:

- A repeat `init` is safe: it may be a no-op or an explicit refusal that names the durable record, but it must leave one `project` row, `user_version=1`, and `integrity_check` `ok`.
- With the dump removed, so the durable-record guard is out of the way, `init --indicator WEB` exits `3`, and the `project` row and its count are unchanged.
- With `user_version` set to `99`, `init --indicator AVRIG` exits `3`, leaves `user_version` at `99`, and leaves the schema untouched. A newer database must never be silently marked with this tool's version.
- An empty file at the database path is initialised to `user_version=1`, which is the recovery path.

Pass: all four.

#### T19 The migration left nothing behind

Threat: goal 6 is asserted nowhere. A numbered fact survives in `plans/PLAN-INDEX.md`, the dump does not carry the four historical rows, a historical row loses its own code, or the committed archive embeds the machine that exported it, which is a diff on every clone.

Fixture: none. This is the only case that reads the candidate tree rather than a fixture, because its subject is that tree's leftovers. It is read only: the dump is applied to a scratch database, and `export --check` is the only command run against the tree, and it writes nothing.

Assertions:

- `plans/PLAN-INDEX.md` does not exist.
- `plans/PLAN-RULES.md` exists, opens with a frontmatter block, and that block carries `project_indicator:` and `indicator_status:`. The declared indicator matches `^[A-Z][A-Z0-9]{1,9}$`.
- `git ls-files --error-unmatch plans/_plan.sql` exits `0`, `git ls-files plans/_plan.db` is empty, and `git check-ignore -v plans/_plan.db` exits `0` with output naming a rule that matches `_plan.db*`.
- Applying the committed dump to a scratch database succeeds, and that database holds exactly `4` `work_item` rows, `6` `deferred_defect` rows, `0` `indicator_alias` rows, and `1` `project` row. The project indicator equals the declared one, and the four rows are numbers `1` to `4` with no gap.
- Each of the four rows satisfies `instr(claiming_branch, code || '-') > 0` and `instr(plan_path, code || '-') > 0`, and its `ledger_status` is one of the twelve vocabulary values rather than `NULL`.
- No column of `project` carries a drive letter or a `Users` fragment, and `repo_root` is `NULL`, because it is the only column an export could derive the machine from.
- The archive keeps its machine values where they are the record rather than a derivation: `actor_host` and `actor_user` hold the machine and account that wrote each row, and `deferred_defect` keeps the words a finding was written with. The case asserts that positively, so `deferred_defect` holds six rows and the `AVRIG-00003` row still names `.opencode/agents`. A later scrub is then caught as a change rather than passing silently, and a path in that text does not fail the case.
- The dump header says it is generated by `export` and must not be hand edited, and after `export --check` the file is byte identical. `export --check` may exit `0` or `1`; anything else is a configuration failure.

Pass: every assertion above, with the dump unchanged by the check.

The first draft of this case failed on a drive letter anywhere in the file, which flagged the `AVRIG-00003` deferred defect text. That was too broad: the plan permits machine values in the audit columns and in defect prose, and forbids them only where `export` derives them. The case grades the narrow claim and grades the three permitted sites positively, which is decision 12 and the bullet it sits beside.

#### T20 The `update` subcommand

Threat: six delivery columns have no writer at all, so stages 8, 12, 13, 14, and 16 of the delivery process have no sanctioned mechanism, or the writer they get reaches an immutable column, invents a version, or reports a refusal over a row it already committed.

Fixture: a coded repository seeded with three committed rows and an exported dump, then `assign` for `AVRIG-00004`, then `export`, so `verify --strict` is clean at the start. `--status` is proven on `AVRIG-00002`; the other fields are proven on `AVRIG-00004`.

Blocked path: the case probes `update --code AVRIG-00002 --status testing` first. If the allocator answers exit `3` with an unknown subcommand, the case reports `BLOCKED` with that output rather than failing or skipping. A missing subject is not evidence either way.

Assertions:

- `update --code AVRIG-00002 --status testing` exits `0`, sets `ledger_status` on that row, changes no other row, and writes exactly one `allocation_event` with `event='update'` whose `detail` names `status`.
- `--candidate-tag avrig/00004/rc.001` and `--evidence plans/evidence/AVRIG-00004/rc.001/` each write their column on `AVRIG-00004`.
- `--issue 6` writes `issue_number` `6`, and `issue_url` either ends `/issues/6` or stays empty, because a non GitHub origin yields no derivable URL and the column is not filled with a guess.
- After those calls and before `--release-version`, `release_version` is still empty: no other field invents a version.
- `--release-version 9.9.9` is accepted rather than refused, and stores the value verbatim.
- The allowlisted calls write exactly one event each, and every `update` event names a row that was actually updated.
- Refused with exit `3`, each proven separately: an unknown `--code`; `--indicator`, `--number`, `--state`, `--assigned-at`, `--committed-at`, `--voided-at`, and `--voided-reason`; and any update to a row whose `state` is `voided`. After each refusal the row count, the full row digest, and the event count are unchanged.
- An immutable column is unreachable even when a legal field is named in the same call, so `--status passed --indicator WXYZ --state voided` either runs or refuses and `indicator`, `number`, and `state` keep their stored values either way. Dropping the flag quietly is tolerated; writing it is not.
- A hostile string carrying a quote, a semicolon, a `--` comment, and in a second payload a newline lands verbatim in `evidence_path`, leaves all five tables present, drops no row, keeps `integrity_check` at `ok`, and exits `0`, because a value cannot be stored and reported as a refusal at the same time.
- `verify --strict` after an `update` with no `export` exits `1` and labels the finding as drift; `export` then `verify --strict` exits `0`, and the exported dump carries the candidate tag.

Pass: all of the above. `BLOCKED` is not a pass.

#### T21 The plan pointer is checked rather than trusted

Threat: a committed row names a plan file that is not there and the ledger still reports clean. This is not hypothetical: all four migrated rows named their pre-approval draft names, every one stale since the approval rename, and `verify --strict` passed them, so the one form of drift the tool could not see was the pointer. Decision 12 records it and the goals carry it.

Fixture: a coded repository seeded with three committed rows and an exported dump, each row naming a real file, `plans/done/` for row 1 so the archived shape is exercised from the start, and `plans/` for the rest. `verify --strict` is clean before the case begins.

Assertions:

- The baseline is clean: a ledger whose pointers resolve exits `0` under `verify --strict`.
- A committed row whose `plan_path` names a missing file makes `verify --strict` exit `1` with a `drift:` line naming the code and the path, and plain `verify` exits `0` while printing the same line. The probe state is written with SQL, because the writer refuses to create it, which is the point of the refusals below.
- An empty `plan_path` on a committed row is drift too, with its own message, and the finding names the row.
- The sanctioned repair is in place rather than a re-key: `update --code <row> --plan-path plans/<code>-<date>-<slug>.md` exits `0`, stores the pointer, writes exactly one `allocation_event` whose `detail` names `plan_path`, and `export` plus `verify --strict` then exits `0`.
- A voided row is exempt, because the check covers committed rows. Voiding a row whose pointer is empty removes the finding and `verify --strict` exits `0` with the pointer still empty, so the exemption passed it rather than a repair.
- A path under `plans/done/` is accepted, because stage 16 archives the plan there and the row follows it.
- Refused with exit `3`, each proven separately with the row count, the row digest, and the event count unchanged after: an absolute path; a path outside `plans/`; a basename carrying a different row's code, such as `plans/AVRIG-00005-x.md` on `AVRIG-00004`; and a path with no file behind it.
- Refused with exit `3` as well: a basename carrying the row's code with no hyphen after it, `plans/AVRIG-00004.md`, even when that file exists. The guard requires the basename to start with `<code>-`, which is the same set `instr(plan_path, code || '-')` accepts, so the writer cannot store a pointer that `T19` would then reject.

Pass: all of the above. Refusal messages are not graded, only the exit code and the unchanged ledger, because an invalid shape and a missing file are refused with the same code.
---

### Failure reporting

A failing case reports the case id, the assertion that failed, the expected and the actual value, and a root cause hypothesis owned by one specialist (`be`, `fe`, `edm`, `Infra`, or `build`), with reproduction steps and the relevant log excerpt. A case that cannot be executed because the subject is missing is `BLOCKED` with the reason, never `not applicable` and never silent.

### Attached suite and its first run

The suite above is not a specification that waits for implementation. `tester` wrote it as `shared/skills/plan-code/tests/Test-Allocation.ps1`, one `PASS` or `FAIL` line per case and a `ROLLUP n/m` summary with a non-zero exit on failure, and ran it against the tool commit `fd935c96` on 2026-11-20. The first result was `ROLLUP 16/18 PASS exit=1`.

Sixteen green on the first run was the useful part: schema creation and its integrity, the constraint proof, the git union raising the candidate, indicator filtering, void and killed `assign` durability, payload injection, import rebuilding from the dump, dump determinism by SHA-256, drift detection in both directions, the environment and exit code contracts, the record never reaching git, status and explicit void, and the approval runbook end to end, all exercised against the real tool rather than a description of it.

The two red cases were implementation defects rather than test gaps, both owned by `be`:

- `T03`, twenty way concurrency, lost 16 of 20 writers. The `{code}` placeholder was substituted client side from a candidate computed outside the write transaction, while the statement recomputed `MAX(number)+1` inside it, so under contention the written number exceeded the candidate and `ck_branch_carries_code` refused the row. A locked read also reported exit `1` instead of `2`, because one read path hardcoded the code.
- `T18`, schema downgrade, rewrote a `user_version` of `99` back to `1` and exited `0`, because the schema was applied before the guard that refuses a newer database, and the schema asset itself sets the marker.

A third finding was hardening rather than a gate: a shared temp payload directory that another process deletes turned into an unhandled exception instead of an exit code. The runner had the same class of defect from the other side, a hardcoded scratch root that let a concurrent run wipe another run's fixtures mid case and produce three false reds, which is why `-Scratch` exists and why the isolation is proven by running two copies at once rather than by reasoning about it.

The suite then grew with the plan rather than staying at eighteen. `T19` closed the analyst's blocking finding that goal 6 was ungraded. `T20` and `T21` came from two further findings: that the ledger could be created but never advanced, and that a row's plan pointer could rot while `verify` called the ledger clean, the second found on the live ledger at stage 7 rather than by any test.

The suite was then run three times rather than once, against the tool commit `827c4b6`, so that the claim is a measurement and not a hope. The single run reported `ROLLUP 21/21 PASS exit=0` with 495 assertions. Two further copies were then started at the same instant in separate scratch roots: both reported `ROLLUP 21/21 PASS exit=0`, and their per-case assertion counts matched the single run case for case, so the runner genuinely isolates rather than sharing state that happens to work when only one process is running.

Those are working-tree runs, and the plan says so rather than calling them evidence: no candidate tag existed when they were made, so they describe a commit and not a candidate. Stage 9 repeats the run at `avrig/00004/rc.001` and that result is the one that counts.

This is recorded because a plan that claimed a green suite before one existed would be false, and because the first two failures are the evidence that the constraint set works: a weaker `ck_branch_carries_code` would have let both writers claim the same number silently.

### Not applicable in this plan

| Surface | Verdict | Reason |
|---|---|---|
| Live browser UAT | not applicable | the plan ships a PowerShell CLI and a SQLite file, with no rendered page, no route, and no login journey to load |
| Desktop UAT through `agent-desktop` | not applicable | no native window, tray, dialog, or installer is started, clicked, or read; the ledger is a SQLite file queried by a CLI, not a surface the plan owns |
| `cargo check --workspace` and `pnpm build` as a code gate | not applicable | the artifacts are one PowerShell script, one SQL schema, three markdown documents, and a SQL dump. No Rust or TypeScript source changes, so a workspace build would exercise code this plan never touched. The equivalent gate for what did change is a PowerShell parse check of `plan-code.ps1`, a `.read` of the schema into a scratch database with `PRAGMA integrity_check`, and the tool's own scratch suite, all recorded under the execution order |

If a later stage adds a page or a window, these rows must be replaced by executed cases, not by silence.

### Execution order and gates

| Order | Cases | Gate |
|---|---|---|
| 1 | `T01`, `T02` | schema is real before anything is tested against it |
| 2 | `T12`, `T13`, `T17`, `T18`, `T20`, `T21` | single process behaviour before contention |
| 3 | `T03` | the only case that can leave 20 rows behind; runs on a clean fixture |
| 4 | `T04`, `T05`, `T08` | union and rebuild correctness |
| 5 | `T06`, `T07` | durability and injection |
| 6 | `T09`, `T10` | dump determinism and drift |
| 7 | `T11`, `T15`, `T16` | environment and contract edges |
| 8 | `T14` | the runbook, last, on a clean scratch clone |
| 9 | `T19` | the migration left nothing behind; the only case that reads the tree rather than a fixture | the tree is final only after every other case has run |

One command runs everything for a candidate:

```powershell
& $PW -NoProfile -File "$TOOL\shared\skills\plan-code\tests\Test-Allocation.ps1" `
  -Project $WT -Out "$WT\plans\evidence\<CODE>-<NNNNN>\rc.<NNN>"
```

### Evidence convention

- Results land in `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/`, one folder per candidate tag, keyed to the same candidate number as the build. `<CODE>`, `<NNNNN>`, and `<NNN>` are empty at Stage 3 and are filled at Stage 8, when the tag exists; nobody writes a version or a code before then.
- Contents: `RESULTS.md` (one line per case plus the rollup), `logs/T01.log` through `logs/T21.log` (stdout and stderr verbatim), `env.json` (`$PSVersionTable.PSVersion`, `sqlite3 --version`, `$TAG`, `$SHA`, `$TSHA`, and `git -C $TOOL status --porcelain -- shared/skills/plan-code` which must be empty), and `db/` (the fixture database copied after each destructive case, so a reviewer can re-run any query).
- No case output is paraphrased into `RESULTS.md`. The log is the record; the summary line only points at it.
- Each result line carries the tag, both commit SHAs, the verdict, the passing assertion count, and the evidence path. A line missing the tag or either SHA is treated as `BLOCKED`.
- No run may start against an untagged or moving tree. A green result on an older tag is not a pass for a newer tree, and a run in the working tree is not evidence at all.

### Rollup rule for the release trigger

The candidate passes only when all 21 cases report `PASS` with zero failed assertions and the runner exits `0`. At that point `tester` reports the passing tag, its `git rev-parse <tag>^{commit}` SHA, and a recommended increment: `minor` if the allocator ships as new capability with no change to any existing ledger row, `patch` if it only repairs an interface defect found during the run, `major` only if the ledger table shape or the exit code contract changes incompatibly after a previous release. No tag is created by `tester`; `build` owns the tag, the merge, and the push.

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

#### Re-audit, 2026-11-20, of the amended design

**Verdict: PASS WITH CHANGES.** The amended design is better than what it replaced: the dump is a real artifact whose measured hash reproduces, and the five source union is closed under the sanctioned approval sequence. Two blockers remain, one of them a capability the plan needs and does not have.

**R1 (blocking, owner `be`). The ledger can be created but not advanced.** Confirmed by reading the tool, not by inference. The only writes to an existing `work_item` row are `void` (state, `voided_at`, `voided_reason`) and the `--issue` UPDATE appended inside `assign`. Nothing writes `ledger_status`, `candidate_tags`, `evidence_path`, `issue_url`, or `release_version` after the migration, so `status --json` reports them as permanently null, `verify` compares none of them, and `SKILL.md` documents no cycle that would. Stages 8, 12, 13, 14 and 16 each have to record something on an existing row, so the stage mapping asserts a capability the plan does not specify. Both paths that exist today are wrong: hand editing `plans/_plan.sql`, which its own header line forbids, and raw SQL plus `export`.

Of the two options offered, take 1, a subcommand (for example `update`) over the same payload path. Option 2 is not merely ungainly, it is unsafe: `tr_work_item_no_rekey` guards `indicator` and `number` only, so a raw `UPDATE` can set `state = 'committed'` on a voided row and un-burn a number the whole design calls permanent, and it writes no event, so the append-only table stops being the record. Requirements for option 1: an explicit allowlist of the six mutable fields; refusal, by name and exit `3`, of `indicator`, `number`, `state`, `assigned_at`, `committed_at`, `voided_at`; selection by `--code` with exit `3` on an unknown code; exactly one `allocation_event` row per call; `export` left as a separate step so the diff stays reviewable. The event CHECK is currently exactly `('assign','void','import','verify')`, so it must gain the new event name, which is `edm`'s edit to `001-plan.sql` and a `tester` amendment to T02's vocabulary probe in the same pass. Closing evidence: a case that sets all six fields over two calls, asserts each of the six protected columns is refused by name, asserts one event per call, and asserts `export` then `verify --strict` exit `0`; plus one line in `SKILL.md`'s cycle and a stage 8, 12, 13, 14, 16 step in `Architect.md`.

**R2 (blocking, owner `tester`). The one goal the change rests on is ungraded.** Goal 6 claims no numbered fact survives outside the database, with the ledger rows, the six deferred defects, and the empty alias table landing in tables. T01 and T02 grade the tables and their columns, but nothing grades the migration: no case asserts that `plans/PLAN-INDEX.md` is absent, that the imported dump holds four work items, six defects and zero aliases, or that each historical row carries its own code in `claiming_branch`. Closing evidence: one read only case on the candidate tree, in the style of T16, asserting those five facts. Every other goal is graded: 1 by T03, 2 by T02, 3 by T06 and T17, 4 by T10, 5 by T09, 7 by T08, 8 by T07, T11 and T15.

**Accepted as designed.** The union is closed under the sanctioned sequence. Re-run on the live checkout: `verify --strict` exits `0` with four rows agreeing across database, dump, `PLAN-RULES.md` and the union, and the dump's SHA-256 is `191ECE6BFB0FA929BA483FF5523073A30F6BD4C7DDCD2570C99E1684E07C49F0`, matching the claim. `origin/main` carries no `plans/_plan.sql`, so `remote_dump_max = 0` is an accurate reading rather than a dead source. Two clones can still both be handed the same candidate, because nothing but the push compares them, and no interleaving gives one code two owners: the loser's push is rejected and it burns the number. That exposure is stated, and it is stated honestly. The two red cases are implementation defects and both diagnoses are correct. T03 substitutes `{code}` client side from a candidate read outside the write transaction, so the statement's own `replace()` is a noop and the written number can exceed the one the branch was validated against; the fix is to send the template and let SQL substitute. T18 applies the schema before the version guard, and the asset sets the marker itself. The locked read reporting `1` is also real: `Get-DbVersion` hardcodes that exit. A red suite naming its own defects is a better record than a green one that does not, and closing them needs `be`, not a rewrite. Deleting `PLAN-INDEX.md` lost no data: four work items, six defects, zero aliases in the dump, prose in `PLAN-RULES.md` with no row data. The dump's format matches its claims in the ways that matter: 118 lines, tables alphabetical, per table data order, generated `code` absent because `table_info` omits it, indexes and triggers after the data, `quote()` escaping, no export timestamp. I did not re-run the 18 case suite; I graded its recorded rollup and re-ran the read only claims instead. (Annotation added after this audit ran: the digest above is the pre-amendment dump. Decisions 10 and 11 changed the stored `CREATE TABLE` text, the dump was regenerated and re-verified at `359826FC...5B5AA9`, and the round trip was measured again rather than assumed to still hold.)

**Non blocking, six items.** The dump header overclaims: the three comment lines name the file and the tool but not the project, and line 3's `.read` recipe is not the `import` path, which deletes the database first. "No machine specific value appears" is overstated: `actor_host` (`WIRIANTO-ZB`) appears in the dump 8 times, and `project_key` comes from the checkout folder leaf at `init`; both are provenance or portability data and neither breaks clone to clone determinism, so the intent holds and the sentence should say "no machine specific path". `PLAN-RULES.md` under Allocation says a row that exists only on an unpushed branch still claims its number, which is false for a branch another machine has not pushed and this clone cannot see; say "a branch visible after a fetch". Goal 6 calls the database the home of the numbered facts while the layer table says the dump owns truth, and that inversion is what makes R1 read as a cache bug when it is an archive hole. The `## Architect Response to Review Findings` B2 paragraph still resolves the finding with `ledger_cells` and a markdown `import`, both deleted. The one-off migration sits under `plans/evidence/`, which is gitignored, so "generated rather than retyped" cannot be audited from the repository later; track it or say the derivation is gone with the file.

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

