---
title: Plan Rules
project_indicator: AVRIG
indicator_status: frozen
created: 2026-11-19
owner: Architect
tags:
  - plan-ledger
  - governance
---

# Plan Rules

The rules that govern plan identity in this project, and the declaration of its indicator.

The numbered facts that used to sit in a ledger table beside these rules are now rows. The ledger is `plans/_plan.db`, a local SQLite database, and its committed archive is `plans/_plan.sql`, a deterministic text dump. Read a row with `plan-code.ps1 status`, or query either file directly. This document holds only the sentences that explain the rules; it deliberately holds no row data, so there is never a second copy of a number to disagree with the first.

## Project indicator

```yaml
project_indicator: AVRIG
indicator_status: frozen
```

- Shape: `^[A-Z][A-Z0-9]{1,9}$`. Two to ten characters, starting with a letter, with no hyphens or spaces.
- The value above is the declaration site. `plan-code.ps1` reads it from this frontmatter, validates it against the shape before the value reaches SQL, and `verify` asserts it equals the `project.indicator` row, so a mismatch between the document and the database is reported rather than tolerated.
- Status is `frozen`. Changing it requires an alias mapping every old code to its new code, recorded in the `indicator_alias` table (`old_code`, `new_code`, `migrated_on`). Existing filenames keep their original code.
- A linked worktree inherits this value from its main checkout and never proposes a different one.
- Other projects declare their own indicator. Two projects never share one.
- The indicator is uppercased in work items (`AVRIG-00001`) and lowercased in tag namespaces (`avrig/00001/rc.001`). Both forms derive from this single value.

## Allocation

The candidate number is the maximum over five sources, plus one, computed inside a single `BEGIN IMMEDIATE` transaction:

1. the local database, `plans/_plan.db`;
2. the local dump, `plans/_plan.sql`;
3. the dump as it stands on `origin/<default>`, read with `git show origin/<default>:plans/_plan.sql`;
4. filenames, from `git ls-tree -r --name-only origin/<default> -- plans/` plus local `plans/*.md` and `plans/done/**/*.md`;
5. branch names, from `git branch --all`.

A row that exists only on the remote still claims its number, through the remote dump and the remote filename scan. A claim that exists only on an unpushed branch is claimed by that checkout and is invisible to a clone that has never fetched it, which is not a gap to close but the reason the push is the cross-machine gate. Because the dump carries a row for every allocation it usually dominates the maximum, and sources 4 and 5 are what catch a claim whose dump was never exported.

Allocation runs at **approval**, and at no other time. Authoring a draft allocates nothing, so a draft has no number to hold and a discarded draft leaves no gap.

Run `git fetch origin <default>` immediately before reading the union. `origin/<default>` is a cached ref, so without a fetch a plan pushed from another clone is invisible and the number is reissued. The fetch and the recheck are one indivisible step. `<default>` is resolved with the four step contract in the plan, never from `origin/HEAD` alone.

**Filter to this project's indicator before taking the maximum.** Two codes can appear in one filename, and another project's plan may legitimately mention a code from this one. Compare with `-cmatch` and `-ceq`, never `-match` or `-eq`, because those are case insensitive and would accept a lowercase indicator the shape rule forbids.

| Input | Unfiltered match | Filtered to `AVRIG` |
|---|---|---|
| `2026-11-19-AVRIG-00007-real-plan.md` | `AVRIG-00007` | `AVRIG-00007` |
| `2026-11-19-WEB-00003-fix-PROJ-00099-regression.md` | `WEB-00003` | none |
| `2026-11-19-WEB-00009-mention-AVRIG-00442.md` | `WEB-00009` | none, the mention is in the slug, not the code position |

An unfiltered scan on the third row would read `AVRIG-00442` and permanently inflate the `AVRIG` series, because numbers are never renumbered.

Parse filenames with the anchored regex, which captures the code only at the start of an approved name:

```text
^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<date>\d{4}-\d{2}-\d{2})-(?<slug>.+)$
```

A plan has two filename states: while it is a draft it is dated and carries no code, and once approved it is renamed to put the code first. Match a branch name with `<type>/<CODE>-(?<num>\d{5})`, deliberately not anchored after the digits, because a plan branch carries a slug after it and a slice branch nests a path segment after that.

Three prohibitions, all required:

- Never split a filename at a hyphen to find the code. A slug contains hyphens, so the split yields garbage: applied to `AVRIG-00001-2026-11-19-agent-workflow-update.md` the last segment is `update.md`, not a number.
- Never scan loosely for any five digit run. A slug such as `migrate-to-20250-table` would be read as number `20250` and jump the series permanently.
- Never scan a raw dump for five digit runs. It carries years, timestamps, commit SHAs inside `candidate_tags`, and issue numbers, so it is queried through SQLite or not read at all.

Verified against real and hostile names:

| Input | Extracted |
|---|---|
| `AVRIG-00001-2026-11-19-agent-workflow-update.md` | `AVRIG-00001` |
| `AVRIG2-00042-2026-11-19-fix-v2-timeout-in-rc.2.md` | `AVRIG2-00042` |
| `AVRIG-00003-2026-11-19-migrate-to-20250-table.md` | `AVRIG-00003`, not `20250` |
| `2026-11-19-AVRIG-00045-draft-style-name.md` | no match, a draft carries no code |
| `2026-11-18-release-0.3.0-consolidated.md` | no match, legacy, exempt |

A filename with no matching token contributes nothing. It is never treated as number zero.

Numbers are never reused, renumbered, or reclaimed, including for abandoned plans. That is structural rather than a rule to remember: `DELETE` aborts, rekeying `number` or `indicator` aborts, and a `voided` row still counts toward the maximum, so a burned number cannot be handed out again while the database exists.

Single writer: allocation is serialized through the Architect role. `assign` performs the read, the maximum, and the insert inside one transaction, so a second writer waits or exits `2` rather than reading a number that is already taken. After writing, re-read and abort if the number appears twice. A racing session fails on non-fast-forward push, which is the intended fail-fast signal.

Approval commit: no code is assigned while a plan is a draft. A draft carries no `plan_id`, no database row, and no code in its filename. The single sanctioned commit on the default branch happens at approval instead: the number is claimed at that moment, the plan file is renamed to put the code first, the dump is regenerated, and only the renamed plan file and the regenerated dump are committed with a `docs(<CODE>-<NNNNN>):` message, before any implementation branch is cut. An abandoned draft therefore consumes no number and leaves no gap.

Worktree rule: a linked worktree inherits the indicator of its main checkout, detected with `git rev-parse --git-common-dir`, and never proposes one of its own. It merges or fast-forwards the default branch before allocating.

## Advancing a row

A row is written once, at approval, and advanced afterwards. The only sanctioned writer is `update`; a hand `UPDATE` against `plans/_plan.db` is prohibited, and for a concrete reason rather than tidiness. The triggers that make a number permanent guard `indicator` and `number`, so ad hoc SQL could set `state = 'committed'` on a voided row and un-burn a number this document calls permanent, and it would leave no audit event.

`update --code <CODE>` takes the six delivery fields, `--status`, `--candidate-tag`, `--evidence`, `--issue`, `--release-version`, and `--plan-path`, and writes one `allocation_event` per call. It refuses `indicator`, `number`, `state`, `assigned_at`, `committed_at`, `voided_at`, and `voided_reason` by name, refuses a voided row outright, and does not regenerate the dump. The cycle is `update`, then `export`, then `verify --strict`, and skipping the middle step is exactly the drift `verify --strict` reports.

`--plan-path` exists because a path rots and a record must be repairable without renaming a committed file. It accepts a relative path directly under `plans/` or `plans/done/` whose basename begins with the row's own code followed by a hyphen, and the file must exist. `verify` checks the same thing in the other direction: a committed row naming a file that is not there is drift, and the message names the repair.

## Status vocabulary

`draft`, `under-review`, `awaiting-approval`, `approved`, `in-progress`, `testing`, `passed`, `release-version-decided`, `merged`, `deployed`, `released`, `abandoned`.

## Pre-branch reconciliation

Before a plan branch is cut, every release tag (`X.Y.Z`) must be proven an ancestor of the repository's default branch:

```text
git fetch origin --tags --prune
git merge-base --is-ancestor refs/tags/<X.Y.Z> refs/heads/<default>
```

A non-zero exit means released content is stranded off the default branch. Merge it with `git merge --no-ff <X.Y.Z>` on the default branch before branching, so the plan branch is never cut from stale code.

Never merge a candidate tag (`<code-lower>/<NNNNN>/rc.<NNN>`) into a default branch, and never move or force a tag to make it an ancestor. Either action bypasses UAT and the release path.

Measured on 2026-11-19: all release tags in `avrig-ai`, `avrig-api`, `avrig-lib` and `avrig-ui` are reachable from `main` (four tags each, latest `0.4.0`), and every default branch is in sync with its remote. The Agentic configuration repository carries no SemVer tags. So no reconciliation merge is needed today, and the gate exists for the case where one is.

## Conventions

| Identifier | Shape | Example |
|---|---|---|
| Work item | `<CODE>-<NNNNN>` | `AVRIG-00001` |
| Branch | `<type>/<CODE>-<NNNNN>-<slug>` | `feat/AVRIG-00001-document-version-comparison` |
| Slice branch | `<type>/<CODE>-<NNNNN>-<slug>/<slice>` | `feat/AVRIG-00001-document-version-comparison/reporting` |
| Build id | `<CODE>-<NNNNN>-build.<NNN>` | `AVRIG-00001-build.001` |
| Candidate tag | `<code-lower>/<NNNNN>/rc.<NNN>` | `avrig/00001/rc.001` |
| Release tag | `X.Y.Z` | `1.1.0` |

A work-item code never implies a release version. The release version is recorded only after deployment succeeds, at stage 16. A null value is the honest state, because no version exists until a release is approved.

`plans/_plan.db` is a runtime artifact, not a committed one. It is ignored as `plans/_plan.db*`, which covers the `-wal` and `-shm` siblings that WAL mode creates, and the leading underscore sorts it ahead of every plan markdown in a directory listing. Deleting it loses nothing that is not recoverable: `import` reloads it from `plans/_plan.sql`, and `assign` self heals by importing first when the file is absent. The database must never be committed, because a binary would conflict on every concurrent branch and would turn a local cache into a second source of truth.

## Backfill

Plans authored before the ledger existed have no code and keep their legacy filenames, so existing cross-references stay valid. They are exempt from the filename rule and are never retro-numbered:

- `2026-11-18-release-0.3.0-consolidated.md`
- `2026-11-19-fix-0.3.0-plan-audit-findings.md`
- `2026-11-19-gateway-opencode-header-passthrough.md`
- every uncoded file under `plans/done/`

A coded plan also moves to `plans/done/` once it is released, and it keeps its code and its row there permanently. So `plans/done/` holds two kinds of file: legacy plans from before this ledger, which are uncoded and exempt, and released coded plans, which keep the code-first filename they were approved under. The bullet above refers only to the first kind.

Archived coded plans: `plans/done/AVRIG-00001-2026-11-19-agent-workflow-update.md`.

Deferred defects and indicator aliases are rows, not prose: `deferred_defect` and `indicator_alias` in the database. Read them with `plan-code.ps1 status --json`, or query the dump.
