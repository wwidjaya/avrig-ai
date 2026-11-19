---
title: Plan Index
project_indicator: AVRIG
indicator_status: frozen
created: 2026-11-19
owner: Architect
tags:
  - plan-ledger
  - governance
---

# Plan Index

Running-number ledger and indicator declaration for every plan in this project.

## Project indicator

```yaml
project_indicator: AVRIG
indicator_status: frozen
```

- Shape: `^[A-Z][A-Z0-9]{1,9}$`. Two to ten characters, starting with a letter, with no hyphens or spaces.
- Status was `pending-user-confirmation` at authoring. The user confirmed `AVRIG`, so it is now `frozen`, and the declaration and this artifact agree.
- Once frozen, changing it requires an alias table, kept in the `## Aliases` table below, mapping every old code to its new code. Existing filenames keep their original code.
- A linked worktree inherits this value from its main checkout and never proposes a different one.
- Other projects declare their own indicator. Two projects never share one. Enforcement is manual until a workspace registry exists.
- The indicator is uppercased in work items (`AVRIG-00001`) and lowercased in tag namespaces (`avrig/00001/rc.001`). Both forms derive from this single value.

## Allocation

Take the maximum from the union of four sources: `git ls-tree -r --name-only origin/<default> -- plans/`, the local `plans/*.md`, the local `plans/done/**/*.md`, and every coded branch name in `git branch --all`. The next number is the highest extracted number, plus one. A row that exists only on the remote, or only on an unpushed branch, still claims its number.

Allocation runs at **approval**, and at no other time. Authoring a draft allocates nothing, so a draft has no number to hold and a discarded draft leaves no gap. Because drafts are not numbered, these four sources are not the only evidence: a draft approved in another clone appears as a ledger row and an approved filename, and both are already in the union, so nothing is missed.

Run `git fetch origin <default>` immediately before reading the union. `origin/<default>` is a cached ref, so without a fetch a plan pushed from another clone is invisible and the number is reissued. Verified in a fresh clone: a pushed plan was absent from `git ls-tree origin/main -- plans/` until `git fetch` ran. The fetch and the recheck below are one indivisible step.

`<default>` is resolved with the four step contract in the plan, never from `origin/HEAD` alone, and indicators are compared case sensitively with `-ceq`. See the plan's default branch contract for why a single command is not sufficient.

**Filter to this project's indicator before taking the maximum.** This is mandatory, not an optimization. Two codes can appear in one filename, and another project's plan may legitimately mention a code from this one. Verified:

| Input | Unfiltered match | Filtered to `AVRIG` |
|---|---|---|
| `2026-11-19-AVRIG-00007-real-plan.md` | `AVRIG-00007` | `AVRIG-00007` |
| `2026-11-19-WEB-00003-fix-PROJ-00099-regression.md` | `WEB-00003` | none |
| `2026-11-19-WEB-00009-mention-AVRIG-00442.md` | `WEB-00009` | none, the mention is in the slug, not the code position |

An unfiltered scan on the third row would read `AVRIG-00442` and permanently inflate the `AVRIG` series, because numbers are never renumbered.

Parse with the anchored filename regex, which captures the code only at the start of an approved name:

```text
^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<date>\d{4}-\d{2}-\d{2})-(?<slug>.+)$
```

A plan has two filename states. While it is a draft it is dated and carries no code, so it contributes nothing here and its number is claimed by its ledger row instead. Once approved it is renamed to put the code first. That is why the ledger is read alongside the tree rather than replaced by it.

Match a ledger cell with `^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})$` and a branch name with `<type>/<CODE>-(?<num>\d{5})`. The branch pattern is deliberately not anchored after the number, because a plan branch carries a slug after it (`feat/AVRIG-00001-agent-workflow-update`) and a slice branch nests a path segment after that (`feat/AVRIG-00001-agent-workflow-update/reporting`). Parsing stops at the five digits, so both forms yield the same code and number. In every form the captured indicator must equal this ledger's `project_indicator`, or the match is discarded.

Two prohibitions, both required:

- Never split a filename at a hyphen to find the code. A slug contains hyphens, so the split yields garbage: applied to `AVRIG-00001-2026-11-19-agent-workflow-update.md` the last segment is `update.md`, not a number.
- Never scan loosely for any five digit run. A slug such as `migrate-to-20250-table` would be read as number `20250` and jump the series permanently, and numbers are never renumbered.

Verified against real and hostile names:

| Input | Extracted |
|---|---|
| `AVRIG-00001-2026-11-19-agent-workflow-update.md` | `AVRIG-00001` |
| `AVRIG2-00042-2026-11-19-fix-v2-timeout-in-rc.2.md` | `AVRIG2-00042` |
| `AVRIG-00003-2026-11-19-migrate-to-20250-table.md` | `AVRIG-00003`, not `20250` |
| `2026-11-19-AVRIG-00045-draft-style-name.md` | no match, a draft carries no code |
| `2026-11-18-release-0.3.0-consolidated.md` | no match, legacy, exempt |

A filename with no matching token contributes nothing. It is never treated as number zero.

Numbers are never reused, renumbered, or reclaimed, including for abandoned plans.

Single writer: allocation is serialized through the Architect role. Recheck before writing the row, then write with nothing in between. After writing, re-read the ledger and abort if the number appears twice. A racing session fails on non-fast-forward push, which is the intended fail-fast signal.

Approval commit: no code is assigned while a plan is a draft. A draft carries no `plan_id`, no ledger number row, and no code in its filename, because a number claimed before anyone approved the work reserves a slot for something that may never happen. The single sanctioned commit on the default branch happens at approval instead: the number is claimed at that moment, the plan file is renamed to put the code first, the ledger row is written, and only the renamed plan file and this ledger are committed with a `docs(<CODE>-<NNNNN>):` message, before any implementation branch is cut. That commit is what makes the reservation visible to every checkout and worktree. An abandoned draft therefore consumes no number and leaves no gap in the series.

Worktree rule: a linked worktree inherits the indicator of its main checkout, detected with `git rev-parse --git-common-dir`, and never proposes one of its own. It merges or fast-forwards the default branch before allocating.

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

A work-item code never implies a release version. The Release version column stays blank through review, approval, implementation, testing, UAT, merge and deployment, and is filled with the released tag only after deployment succeeds, at stage 16. A blank cell is the honest state, because no version exists until a release is approved.

## Aliases

Empty. Populated only if the indicator ever changes after freezing.

| Old code | New code | Migrated |
|---|---|---|
| none | none | n/a |

## Ledger

| Plan | Created | Title | Repos | Claiming branch | Status | Passing candidate tag | Evidence path | Feature request | Release version |
|---|---|---|---|---|---|---|---|---|---|
| AVRIG-00001 | 2026-11-19 | Architect and Tester Workflow: Universal Plan Codes, Analyst-First Review, Branch and Candidate Tag Gate | Agentic, avrig-ai | main (approval), feat/AVRIG-00001-agent-workflow-update | passed | **`avrig/00001/rc.004` @ `a908c7e` PASS 20/20**; `rc.003` @ `5ebede4` FAIL 19/20; `rc.002` @ `d23a7aa` FAIL 19/20; `rc.001` @ `d100017` FAIL 15/20 | `plans/evidence/AVRIG-00001/rc.004/` | [#3](https://github.com/wwidjaya/avrig-ai/issues/3), branch linked | blank until deployment |

## Backfill

Plans authored before this ledger existed have no code and keep their legacy filenames, so existing cross-references stay valid. They are exempt from the filename rule and are never retro-numbered:

- `2026-11-18-release-0.3.0-consolidated.md`
- `2026-11-19-fix-0.3.0-plan-audit-findings.md`
- `2026-11-19-gateway-opencode-header-passthrough.md`
- everything under `plans/done/`

New work in this project starts at `AVRIG-00001`.
