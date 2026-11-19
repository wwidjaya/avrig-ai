---
title: "Architect and Tester Workflow: Universal Plan Codes, Analyst-First Review, Branch and Candidate Tag Gate"
plan_id: AVRIG-00001
project_indicator: AVRIG
indicator_status: pending-user-confirmation
status: approved
created: 2026-11-19
owner: Architect (authoring), analyst (review and findings), tester (test matrix and live browser verification), be (config file writes), build (branch, candidate tags, merge, release), Infra (deploy), km (retrospective)
branch: feature/AVRIG-00001
repos:
  - avrig-ai (default main)
  - Agentic (default master)
default_branches_resolved: true
instruction_files_tracked: false
candidate_tags: []
release_version: undecided until the user approves a version at stage 12
version_target: none, project codes never imply a SemVer
resolved_decisions: 3 (default branch per repo, instruction files local only, plans committed)
tags:
  - agent-workflow
  - plan-lifecycle
  - branching
  - tagging
  - browser-testing
  - release-governance
---

# Architect and Tester Workflow: Universal Plan Codes, Analyst-First Review, Branch and Candidate Tag Gate

## Goals and Objectives

1. Give every plan a permanent work-item key shaped `<CODE>-<NNNNN>`, where `<CODE>` is the project indicator and `<NNNNN>` a five digit zero padded running number. The indicator is never baked into instruction text: each project declares its own, so a second project can use `WEB`, `API`, or `PAY` and the rules hold unchanged.
2. Make the indicator permanent and provable. It is declared once per project in the plan ledger, it is frozen only after the user confirms it, and any later change requires a documented alias mapping so old codes never break.
3. Separate the six identifiers so they can never be confused: work items identify work, branches identify active development, build ids identify produced artifacts, candidate tags identify testable artifacts, release tags identify released software, and slice branches identify one part of one work item.
4. Reorder the Architect stages so an authored plan goes straight to `analyst` review with no intervening gate, the test matrix is attached before the user is asked anything, and the Architect then confirms findings and open clarifications with the user.
5. Bind execution to a branch cut after explicit approval from a default branch that has first been reconciled with every release tag, named `<type>/<CODE>-<NNNNN>`, cut in every repository the plan touches, with the default branch resolved per repository rather than assumed to be `main`, and make those branches the only place development and fixes happen.
6. Guarantee the plan branch is never cut from stale code. Before branching, every release tag must be proven an ancestor of the default branch, so released content that never reached it is merged first instead of being silently absent from the work.
7. Bind every test run to an immutable candidate tag created before the test starts, so the tester verifies an exact tagged tree instead of a moving working directory.
8. Make each remediation cycle produce a fresh candidate tag and a matching build, so the artifact promoted to production is provably the artifact that passed.
9. Assign SemVer only at release approval, from the content that actually passed, and make the released artifact provably the tested artifact: the version bump is candidate tested, the merge is guarded by an ancestry assertion and a tree-equality assertion, and the release tag is placed on the merged default branch tip whose tree equals the passing candidate.
10. Let concurrent plans finish independently. A later plan never blocks an earlier one, and a long-running branch resynchronizes with its repository's default branch before its final candidate, guarded by an ancestry assertion.
11. Require the `tester` subagent to run real live browser testing of the running application, not only API calls and unit suites, with evidence retained per candidate tag.
12. Close the drift this plan exists to remove: the plan file list covers every live document that still carries the old workflow, not just the two primary ones.

Measurable outcomes:

| Objective | Pass condition |
|---|---|
| Universal indicator | The fenced instruction text destined for `Architect.md` and `tester.md` contains no user project's actual indicator outside an Example column, and describes the shape by regex `^[A-Z][A-Z0-9]{1,9}$` |
| Indicator declared per project | `plans/PLAN-INDEX.md` frontmatter carries `project_indicator:` and states the freeze-after-confirmation rule |
| Plan codes, forward only | Every plan file created at or after this one matches `plans/YYYY-MM-DD-<CODE>-<NNNNN>-<slug>.md` and its code extracts by token regex. Legacy files are exempt by recorded exception |
| Allocation is collision safe | The allocation rule reads the union of the fetched remote tree, the local tree, and all branch names, filters to this project's indicator, parses with the anchored filename regex rather than a hyphen split, rechecks before writing, and asserts no duplicate after writing |
| Identifier separation | Policy text names all six identifier kinds and states that a work-item code never implies a SemVer |
| Analyst-first stage | `Architect.md` lists `analyst` as the immediate successor of plan authoring, with the test matrix attached before the approval stage |
| Branch gate | `Architect.md` states the branch is cut from the repository's resolved default branch in every affected repository, only after user approval, in the pattern `<type>/<CODE>-<NNNNN>`, and only after every release tag is confirmed an ancestor of that default branch |
| Candidate tag gate | `Architect.md` states a candidate tag and its build exist before the first test and that every fix produces the next numbered pair |
| Release integrity | `Architect.md` states the bump happens on the plan branch and is itself candidate tested, the ancestry assertion and tree-equality assertion guard the merge, the merge precedes the tag, and the tag is created by hand at the tested commit because the publisher can only tag a branch head |
| Live browser test | `tester.md` names the Playwright harness and the `wmux browser` fallback with its real call forms, plus evidence storage per candidate tag |
| Default branch per repo | No stage assumes `main`; every stage resolves the default branch with the four step contract in the design section and records the resolved name plus the step that decided it |
| Local-only files verified | A SHA-256 instruction manifest exists under `plans/evidence/AVRIG-00001/`, and each edited instruction file has a `.bak-` sibling |
| No production drift | Baseline captured before implementation, then one `git diff --stat` per affected repository with absolute paths; the after-minus-before delta contains no path outside `plans/`, the two `AGENTS.md` files, and `.gitignore`. Pre-existing drift is subtracted, not tolerated, because both repositories already carry unrelated modifications |

Non-goals: backfilling codes into plans authored before this one, changing `release.ps1` internals, and building a CI artifact registry.

## Key Detailed Design

### Program Design

This plan edits instruction documents plus one ledger. There is no service contract, Axum route, or crate module change. The design work is the identifier scheme, the state machine, and the precision of the words describing both.

#### Measured state of the workspace

Verified on 2026-11-19, because three of the blockers turn on these facts:

| Project root | Repository kind | Default branch | Plans folder | Working branch |
|---|---|---|---|---|
| `avrig-ai` | own repo | `main` | present | `main` |
| `avrig-ai-gateway-oauth` | linked worktree of `avrig-ai` | inherits `main` | own `plans/` checkout | `feat/gateway-opencode-oauth` |
| `avrig-api` | own repo | `main` | absent | `main` |
| `avrig-lib` | own repo | `main` | absent | `main` |
| `avrig-ui` | own repo | `main` | absent | `main` |
| `api` | own repo | resolve at runtime | absent | resolve at runtime |
| `web` | own repo | resolve at runtime | absent | resolve at runtime |
| `TripoSR` | own repo | resolve at runtime | absent | resolve at runtime |
| `Agentic` (config root) | own repo | **`master`**, while `origin/HEAD` points at `origin/main` | absent | `master` |

That is seven own repositories plus one worktree, eight working trees in total. Default branches are resolved per repository, not assumed: the Agentic configuration repository works on `master` while the four `avrig-*` product repositories use `main`.

Two measured facts drive the design, plus a third that changes how resolution must work:

1. **Default branches are not uniform.** The Agentic configuration repository has no local `main`; its checkout is `master`, `origin/main` exists, and `origin/master` matches `master`. So `git switch main` aborts in the repository that owns the agent instruction files.
2. **`.opencode/agents/` is entirely untracked in the Agentic repository.** Verified: `git ls-files .opencode/agents/` returns nothing, `git check-ignore` exits 1, and `git status` reports the whole directory as `??`. Resolved by decision 2: the files stay local only, and the plan states plainly that a candidate tag cannot cover them, with a backup and a checksum manifest as the mitigation.
3. **Remote HEAD and local default branch disagree in the Agentic repository.** Measured on 2026-11-19: `git symbolic-ref --short refs/remotes/origin/HEAD` returns `origin/main`, local `main` does not exist (`git rev-parse --verify --quiet main` exits 1), the only local branch is `master`, and `git rev-list --left-right --count master...origin/main` reports `28 0`, so `master` is 28 commits ahead of `origin/main` and level with `origin/master`.

Fact 3 breaks the obvious resolution rule. Resolving the default branch by reading `origin/HEAD` yields `main` in the Agentic repository, and `git switch main` then fails there, which is exactly the failure this plan set out to remove. So resolution cannot be a single command. The rule below is the resolution contract, and it is what the instruction text must carry:

```text
resolve_default_branch(repo):
  1. if the current branch tracks a remote and that branch is the repo's
     only long-lived branch, the current branch is the default
  2. else read  git symbolic-ref --short refs/remotes/origin/HEAD
     strip the remote prefix -> candidate
  3. if candidate exists locally, it is the default
  4. else if exactly one local branch exists, that branch is the default,
     and record the origin/HEAD disagreement in the plan
  5. else stop and ask the user; never guess
```

Step 1 exists because the Agentic repository is developed on `master` while its remote still advertises `main`, and step 4 is what makes this repository resolvable rather than a hard stop. Applied here: `avrig-ai` and the three product repositories resolve to `main` by step 3; the Agentic repository resolves to `master` by step 4, with the `origin/main` disagreement recorded.

The resolution result and its step number are recorded in the plan before any branch is cut, so a later reader can see how each repository was decided instead of inferring it.

The worktree case has a consequence worth stating: because `avrig-ai-gateway-oauth` shares `avrig-ai`'s object store, a ledger row committed on the default branch is not visible while that worktree sits on its feature branch. The ledger therefore lives in the checked-out branch, and allocation reads the ledger, the filenames it can see, and the archived `plans/done/` tree. A worktree that cannot see the newest plans must merge or fast-forward its default branch before allocating.

#### The indicator contract

| Property | Rule |
|---|---|
| Shape | `^[A-Z][A-Z0-9]{1,9}$`, so 2 to 10 characters, first character a letter, no hyphens, no spaces |
| Parse rule | Extract by token regex `([A-Z][A-Z0-9]{1,9})-([0-9]{5})`, searched anywhere in the filename or ledger cell. Never split at a hyphen |
| Non-matching files | A filename with no matching token contributes nothing to allocation. It is never treated as number zero |
| Scope | One indicator per project root, one independent number series per indicator |
| Source of truth | `plans/PLAN-INDEX.md` frontmatter `project_indicator:` |
| New project | Propose from the folder name, present to the user at stage 3, write only the confirmed value. Never adopt a proposal silently |
| Permanence | Frozen only after user confirmation. Any later change requires an alias table mapping old codes to new, and existing filenames keep their original code |
| Collision avoidance | Two projects never share an indicator. A workspace registry is optional and deferred |
| Case | Uppercase in work items, lowercase in tag namespaces, both derived from the one declared value |

The parse rule is a token regex rather than a hyphen split because the hyphen split is provably broken. Measured: applying the split to the real filename `2026-11-19-AVRIG-00001-agent-workflow-update.md` gives a right side of `update.md`, so the ledger cannot read its own first entry and the next author reissues `00001`. The token regex returns `AVRIG-00001` from that filename, `AVRIG2-00042` from `2026-11-19-AVRIG2-00042-fix-v2-timeout-in-rc.2.md`, and no match from `2026-11-18-release-0.3.0-consolidated.md`, which is exactly the required behaviour for legacy files.

#### The identifier taxonomy

| Identifier | Shape | Example | Owner |
|---|---|---|---|
| Work item | `<CODE>-<NNNNN>` | `AVRIG-00002` | Architect |
| Branch | `<type>/<CODE>-<NNNNN>` | `feature/AVRIG-00002` | build |
| Slice branch | `<type>/<CODE>-<NNNNN>-<slice>` | `feature/AVRIG-00002-reporting` | be, fe |
| Build id | `<CODE>-<NNNNN>-build.<NNN>` | `AVRIG-00002-build.003` | build, artifact space only |
| Candidate tag | `<code-lower>/<NNNNN>/rc.<NNN>` | `avrig/00002/rc.002` | build |
| Release tag | `X.Y.Z` | `1.1.0` | build |

Six identifiers, where `<type>` is one of `feature`, `fix`, `chore`, `docs`, `refactor`, `perf`. A slice branch is a branch subtype, not a seventh kind.

Hard rules:

- A work-item code never implies a SemVer and never reserves one.
- The version is assigned only at release approval, from content: `major` breaking, `minor` backward-compatible functionality, `patch` backward-compatible fix.
- Build ids live in the artifact space, not as Git tags.
- Candidate tags are immutable, and each carries its own build cut from the same commit, aligned as `build.<NNN>` with `rc.<NNN>`.
- Candidate tags are lowercase because Git refs are case insensitive on Windows file systems.
- Release tags are bare `X.Y.Z`. This is settled by tooling, not preference: `release.ps1` anchors `$SemVerRegex` at `^(0|[1-9]\d*)`, so a `v`-prefixed tag cannot match and is impossible through the only publisher that exists.
- One commit can carry several identifiers, but only one release version.

#### Release construction under the retained `release.ps1`

The script cannot tag an arbitrary commit, and the plan does not modify it. Measured behaviour: it rewrites `avrig-ai/Cargo.toml`, `apps/web/package.json`, and `avrig-api/Cargo.toml`, refreshes both lockfiles, commits with `git add -A`, then tags HEAD of whatever branch is checked out. So tagging the passing candidate directly would place the tag on a commit that never contained the bumped manifests, and the manifests would then be bumped on the default branch afterwards, which means the tested tree and the released tree differ.

The sequence that keeps rule 7 and rule 8 true without touching the script. Note the critical detail: `build` creates the release tag itself, at the candidate SHA, before invoking the script. The script has no target-commit parameter, so it would otherwise tag the merge commit:

```text
1. passing candidate exists           avrig/00002/rc.003
2. decide the version                 user approves 1.1.0
3. bump manifests ON THE PLAN BRANCH  make bump-version 1.1.0
4. commit the bump on the branch      chore(release): 1.1.0
5. cut and test rc.004                the bump is now part of the tested tree
6. ancestry assert, then merge        git merge-base --is-ancestor <default> <candidate>
                                      git merge --no-ff avrig/00002/rc.004
                                      assert tree(<default>) == tree(rc.004)
7. create the release tag BY HAND      git tag -a 1.1.0 <merge sha> -m "avrig 1.1.0"
   at the merged default tip            (the assertion just proved its tree equals rc.004)
8. run the publisher with -SkipBump    release.ps1 1.1.0 -SkipBump
```

Step 7 is required and step 8 depends on it. Measured: `release.ps1` accepts only `$Target`, `$Message`, `$NoPush`, `$SkipBump`, `$Force`, `$Range`, and `$RangeTag`, so it has no way to tag an arbitrary commit. Its tagging line is `git tag -a $new -m "avrig $new"` with no commit argument, which tags HEAD. If step 7 were omitted, `-SkipBump` at step 8 would find no existing tag, take the create path, and place `1.1.0` on whatever commit the default branch has advanced to, which may be later than the merged candidate. With step 7 done, the script instead reaches its reuse path: measured, it prints "Tag $new already exists locally, reusing" when `git tag --list $new` finds the tag, and that path never uses `--force`, so it pushes without moving the tag.

The tag sits on the merge commit, not on the candidate commit, and that is correct. A `--no-ff` merge always creates a new commit, so commit identity cannot survive the merge. What survives is the tree, which step 6 asserts. Reproduced: candidate `420ee5b`, merge `af5bed9`, same commit False, tree equal True. Every identity claim in this plan is therefore stated on the tree, never on the commit.

Step 8 also pushes every repository in `$RepoOrder`. For the three repositories that received no tag by hand, the script takes the create path and tags their current HEAD, which is the correct behaviour for repositories that carry no plan change.

Two hard preconditions fall out of the script's behaviour:

- The script must run with the repository's default branch checked out, never a feature branch. It reads `git rev-parse --abbrev-ref HEAD` and pushes that branch, so running it from a feature branch publishes an unmerged, untested tree. `build` must assert the checked-out branch equals the resolved default branch and that the tree is clean before invoking it.
- The release set is all four repositories in `$RepoOrder`, not only the ones a plan touched. The policy wording must match the tool, or the tool must be filtered, and filtering is out of scope.

#### State machine, with QA and UAT defined

`QA` and `UAT` appear in the illustration, so they are defined here rather than left as floating terms.

- **QA** is the automated matrix plus live browser pass at stage 9, owned by `tester`, evidenced under `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/`.
- **UAT** is the user's explicit approval at stage 12, recorded in the plan and in the ledger row, with the passing candidate tag and commit SHA named. It is a human decision, not an automated one, and it is the only thing that authorizes a version number.

| State | Owning assignee | Entry condition |
|---|---|---|
| `draft` | Architect | Plan file and ledger row created with an allocated code |
| `under-review` | analyst | Architect hands the plan over immediately after writing it |
| `awaiting-approval` | Architect | Analyst has recorded `## Review Findings`, the test matrix is attached, and open questions are presented |
| `approved` | primary | User approves execution, which cuts branches |
| `in-progress` | be, fe, edm | Branches exist in every affected repository |
| `testing` | tester | A candidate tag and its matching build exist on the branch head |
| `passed` | tester | QA passes against that specific candidate tag |
| `release-version-decided` | build, primary | UAT passed: user approved a version, and the bump is committed and re-tested |
| `merged` | build | Ancestry assertion passed, merge completed, tree equality asserted |
| `deployed` | Infra | The artifact built for the passing candidate is running |
| `released` | build | Release tag published on the merged default branch tip, whose tree equals the passing candidate, through `release.ps1 -SkipBump` |
| `abandoned` | Architect | User abandons the plan; the code and row remain |

#### End-to-end illustration

Two projects, two independent series. Project `AVRIG` has one released version, project `WEB` has its own unrelated line:

```text
AVRIG project                     WEB project
main                              main
  |
  +--- 1.0.0                      +--- 3.4.1
```

Three independent plans start, and no version is guessed:

```text
AVRIG-00001
AVRIG-00002
WEB-00001
```

Deliberately undecided at this point:

```text
AVRIG-00001 = 1.1.0 ?
AVRIG-00002 = 1.2.0 ?
no
```

Branches are cut from each project's default branch, after approval:

```text
AVRIG main                        WEB main
 |                                 |
 +--- feature/AVRIG-00001          +--- feature/WEB-00001
 |
 +--- feature/AVRIG-00002
```

A plan spanning several slices may branch further, but the plan branch remains the release candidate branch:

```text
feature/AVRIG-00001
    +--- feature/AVRIG-00001-user-profile
    +--- feature/AVRIG-00001-reporting
    +--- feature/AVRIG-00001-validation
```

Iteration 1 on `AVRIG-00001`:

```text
main @ 1.0.0
   |
   +--- feature/AVRIG-00001
            +--- commit A
            +--- commit B
            +--- commit C
```

The build produces an artifact id, which is not a software version:

```text
AVRIG-00001-build.001
```

Iteration 2 adds work, and the build number advances with it:

```text
feature/AVRIG-00001
       +--- commit A
       +--- commit B
       +--- commit C
       +--- commit D
       +--- commit E
```

```text
AVRIG-00001-build.002
```

Testing finds bugs, fixed on the same branch:

```text
feature/AVRIG-00001
       +--- ...
       +--- fix F
       +--- fix G
```

```text
AVRIG-00001-build.003
```

Meanwhile `AVRIG-00002` moves faster, which is normal:

```text
main @ 1.0.0
   |
   +--- feature/AVRIG-00001
   |       +--- iteration 1
   |       +--- iteration 2
   |
   +--- feature/AVRIG-00002
           +--- iteration 1
           +--- iteration 2
           +--- iteration 3
```

```text
AVRIG-00002-build.001
AVRIG-00002-build.002
AVRIG-00002-build.003
AVRIG-00002-build.004
```

Ready for formal testing, a candidate is cut. The production version is still unassigned:

```text
feature/AVRIG-00002
             |
             v
       test candidate
             |
             v
avrig/00002/rc.001  +  AVRIG-00002-build.005
```

Each candidate carries its own build from the same commit, so the pair is always aligned.

Test iteration 1 finds bugs. The tag is never overwritten:

```text
avrig/00002/rc.001
        |
        +--- bugs found
                |
                v
       fix on feature branch
                |
                v
       avrig/00002/rc.002
```

Test iteration 2 finds one more problem, and the trail grows:

```text
avrig/00002/rc.001
avrig/00002/rc.002
avrig/00002/rc.003
```

All three stay immutable, which is what makes the audit trail usable later.

`AVRIG-00002` finishes QA first while `AVRIG-00001` is still testing:

```text
AVRIG-00001   still testing
AVRIG-00002   QA passed
```

UAT for `AVRIG-00002` is the user approving a version. `AVRIG-00001` does not block it. If the content is backward-compatible functionality:

```text
AVRIG-00002 -> 1.1.0
```

```text
1.0.0
   |
   +----------------------------------+
                                      |
                        AVRIG-00002 --+
                                      v
                                   1.1.0
```

The commit tagged `1.1.0` is the same commit that passed QA and UAT, because the manifest bump was itself candidate tested as `rc.004` before the merge.

`AVRIG-00001` continues independently, but `main` has moved:

```text
main
1.0.0
   |
   v
1.1.0
```

So `AVRIG-00001` synchronizes with `main` before its next candidate. Merge rather than rebase, because it preserves history and is safer for a long-running agent branch:

```bash
git switch feature/AVRIG-00001
git merge main
```

Work continues on top of the synchronized branch:

```text
main
 |
 +--- 1.1.0
       |
       +--- feature/AVRIG-00001
              +--- iteration 3
              +--- iteration 4
              +--- iteration 5
```

```text
avrig/00001/rc.001
avrig/00001/rc.002
avrig/00001/rc.003
```

On pass, that plan's version is decided from its content, for example backward-compatible functionality gives:

```text
AVRIG-00001 -> 1.2.0
```

The whole timeline, viewed once:

```text
TIME -------------------------------------------------------------->

                    AVRIG-00001
                   /            \
                  /              \
1.0.0 ------------+-------------------------------+---> 1.2.0
                  \
                   \
                    AVRIG-00002
                       \
                        \
                         ---> 1.1.0
```

And in repository terms, with the `WEB` project running its own untouched series alongside:

```text
AVRIG repository
    Branches
        main
        feature/AVRIG-00001
        feature/AVRIG-00002
        fix/AVRIG-00001-validation
        fix/AVRIG-00002-timeout

    Git tags
        1.0.0
        avrig/00001/rc.001
        avrig/00001/rc.002
        avrig/00002/rc.001
        avrig/00002/rc.002
        avrig/00002/rc.003
        1.1.0
        1.2.0

    Build artifacts, not tags
        AVRIG-00001-build.001
        AVRIG-00001-build.002
        AVRIG-00001-build.003
        AVRIG-00002-build.001
        AVRIG-00002-build.002
        AVRIG-00002-build.003
        AVRIG-00002-build.004
        AVRIG-00002-build.005

WEB repository
    Branches
        main
        feature/WEB-00001

    Git tags
        3.4.1
        web/00001/rc.001

    Build artifacts, not tags
        WEB-00001-build.001
```

Not every development build needs a Git tag. Candidate tags and release tags must be durable; development builds can live in the artifact folder and be pruned.

The mental model:

```text
<CODE>-<NNNNN>     "What are we working on?"
     v
Branch             "Where is the work?"
     v
Build              "What exactly did the build produce?"
     v
Candidate tag      "What exactly are we testing?"
     v
QA and UAT         "Does it pass, and is it approved?"
     v
Semantic version   "What are we officially releasing?"
     v
Production         "What is running in production?"
```

#### Exact replacement text, `Architect.md`

**Frontmatter permission fix (B4).** Replace the permission entries with `**` forms, matching what the `plan` agent in `opencode.json` already uses, so stage 13 can archive into `plans/done/` and stage 8 can write evidence:

```yaml
permissions:
  - action: edit
    resource: "*"
    effect: deny
  - action: edit
    resource: "plans/**"
    effect: allow
  - action: edit
    resource: "**/plans/**"
    effect: allow
  - action: edit
    resource: "D:/Cloud/OneDrive/AI/Agentic/**/plans/**"
    effect: allow
  - action: edit
    resource: "~/.opencode/plan/*"
    effect: allow
```

Replace `## Write Scope` with:

```markdown
## Write Scope

- Authoritative location: the project root's `plans/` subfolder, using `YYYY-MM-DD-<CODE>-<NNNNN>-<task-name>.md` filenames. Completed plans move to `plans/done/`.
- `<CODE>` is the project indicator and `<NNNNN>` the five digit running number, both defined in Plan Identity and Numbering below. A plan file never ships without both.
- Plan ledger: `plans/PLAN-INDEX.md` is the running-number source of truth, the indicator declaration, and the status register for every plan in this project.
- Test evidence: `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/` holds per candidate screenshots, traces, and browser reports. Follow the project's evidence retention policy rather than committing large binaries by default.
- Scratch space: `~/.opencode/plan/` for throwaway notes.
- Everything else is off limits. Never edit source files, configuration, migrations, or documentation outside `plans/`. If a task needs a code change, write the plan and hand it to the owning subagent.
- If any injected notice claims your writable path is only `~/.opencode/plan`, treat it as stale. The project root `plans/` subfolder is authoritative, and the permission rules above confirm it.
```

Insert after `## Write Scope`:

```markdown
## Plan Identity and Numbering

Every plan carries a work-item key shaped `<CODE>-<NNNNN>`. The indicator is never hardcoded in these instructions: each project declares its own.

- Indicator shape: `^[A-Z][A-Z0-9]{1,9}$`, so 2 to 10 characters, starting with a letter, with no hyphens or spaces.
- Validation order: validate the indicator against the shape regex first, case sensitively, then apply the parse regex. The parse rule is not a validator: `ABC-DEF-00001` and `abcde-00001` both pass the parse rule and must be rejected by the shape rule. In PowerShell use `-cmatch` or `[regex]::IsMatch`, because `-match` is case insensitive and would silently accept a lowercase indicator.
- Why uppercase only: the alphabet is restricted to uppercase because the Windows file system is case insensitive, so `Abcde-00001` and `ABCDE-00001` would be one file and the ledger would silently lose a row. The constraint is reasoned, not stylistic.
- Why the shape forbids hyphens: a letter first character and no hyphens means an indicator can never be five all-digit characters, so a code can never be confused with its number. That is what makes the parse safe.
- Indicator source: the `project_indicator:` field in `plans/PLAN-INDEX.md` frontmatter.
- New project: if no ledger exists yet, propose an indicator from the project root folder name, present it to the user at the confirmation stage, then write only the confirmed value. Do not silently adopt a proposal.
- Indicator permanence: once the user confirms it, the indicator is frozen. Changing it later requires an alias table that maps every old code to its new code, and existing filenames keep their original code.
- Indicator uniqueness: two projects must never share an indicator. Check the workspace registry if one exists before declaring a new one.
- Running number: five digits, zero padded, starting at `00001`.
- Allocation source: take the maximum from the union of `git ls-tree -r --name-only origin/<default> -- plans/`, the local `plans/*.md`, the local `plans/done/**/*.md`, and every coded branch name in `git branch --all`. A row that exists only on an unpushed branch, or only on the remote, still claims its number.
- Freshness precondition: run `git fetch origin <default>` (and `git fetch --all --prune` when other remotes are configured) immediately before reading the union. `origin/<default>` is a cached ref, so without a fetch a pushed plan from another clone is invisible and the number is reissued. The fetch and the recheck are one step, and nothing else runs between them.
- Default branch is per repository, never assumed, and never read from `origin/HEAD` alone. Resolve it with the four step contract in the plan: current tracking branch, else `git symbolic-ref --short refs/remotes/origin/HEAD`, else the sole local branch when remote HEAD and local branches disagree, else stop and ask. Do not assume `main`: one repository here works on `master` while its remote advertises `main`.
- Allocation filter, mandatory: keep only codes whose indicator equals this project's `project_indicator`, then take the maximum over that filtered set. Never take a maximum across all codes. Two codes can appear in one filename, and a plan in another project may legitimately mention a code from this one, so an unfiltered scan inflates this project's series permanently because numbers are never renumbered.
- Allocation parse: use the anchored filename regex `^(?<date>\d{4}-\d{2}-\d{2})-(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<slug>.+)$`, which captures only the code adjacent to the date. Match a ledger cell with `^(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})$` and a branch name with `<type>/<CODE>-(?<num>\d{5})`. In every form the captured indicator must equal the declared value by case sensitive comparison: in PowerShell use `-ceq` or `[string]::Equals($a, $b, 'Ordinal')`, never `-eq`, because `-eq` is case insensitive by default and would accept a lowercase indicator that the shape rule forbids.
- Never split a filename at a hyphen, and never scan loosely for any five digit run. A slug may contain `20250` or `12345`, which a loose scan would read as the next number and jump the series permanently. Both rules are required, not optional.
- A filename with no matching token contributes nothing. Never treat it as number zero.
- Numbers are permanent. A number is never reused, renumbered, or reclaimed when a plan is abandoned, superseded, or archived. An abandoned plan keeps its row with status `abandoned`.
- Single writer: allocation is serialized through the Architect role, which is the only role that writes ledger rows.
- Recheck before write: immediately before writing the row, re-read the ledger and the allocation sources, confirm the chosen number is still unclaimed, then write with nothing in between. Record the claiming branch in the row so a reader can see where the claim lives.
- Duplicate assertion after write: re-read the ledger and abort if the number appears more than once. If two sessions race, the second push fails as non-fast-forward, which is the intended fail-fast signal and should be reported as expected rather than worked around.
- Authoring commit: plan authoring is the single sanctioned commit on the default branch. The Architect, or `build` on its behalf, commits only the new plan file and `plans/PLAN-INDEX.md` with a `docs(<CODE>-<NNNNN>):` message and pushes before any implementation branch is cut. This makes the reservation visible to every checkout and worktree. No other plan work lands on the default branch directly.
- Worktree rule: a linked worktree inherits the indicator of its main checkout, detected with `git rev-parse --git-common-dir`, and never proposes one of its own. It also merges or fast-forwards the default branch before allocating, so it can read the newest ledger.
- Filename pattern: `plans/YYYY-MM-DD-<CODE>-<NNNNN>-<task-name>.md`.
- Frontmatter carries `plan_id: <CODE>-<NNNNN>`, `project_indicator: <CODE>`, `branch: <type>/<CODE>-<NNNNN>`, `candidate_tags: []` appended per test cycle, and `release_version:` left undecided until UAT.
- Status vocabulary, in order: `draft`, `under-review`, `awaiting-approval`, `approved`, `in-progress`, `testing`, `passed`, `release-version-decided`, `merged`, `deployed`, `released`, `abandoned`.
- Plans authored before this ledger existed keep their legacy filenames and are exempt from the filename rule, so existing cross-references stay valid.
```

Insert after `## Plan Identity and Numbering`:

```markdown
## Identifier Taxonomy

Six identifiers exist and must never be conflated.

| Identifier | Shape | Example | Owner |
|---|---|---|---|
| Work item | `<CODE>-<NNNNN>` | `AAAAA-00002` | Architect |
| Branch | `<type>/<CODE>-<NNNNN>` | `feature/AAAAA-00002` | build |
| Slice branch | `<type>/<CODE>-<NNNNN>-<slice>` | `feature/AAAAA-00002-reporting` | be, fe |
| Build id | `<CODE>-<NNNNN>-build.<NNN>` | `AAAAA-00002-build.003` | build, artifact space only, not a Git tag |
| Candidate tag | `<code-lower>/<NNNNN>/rc.<NNN>` | `aaaaa/00002/rc.002` | build |
| Release tag | `X.Y.Z` | `1.1.0` | build |

The example column uses a neutral stand-in so this table never prescribes a real project's indicator. Replace `AAAAA` with the project indicator in force.

Where `<type>` is one of `feature`, `fix`, `chore`, `docs`, `refactor`, `perf`. A slice branch is a branch subtype, not a seventh identifier.

- A work-item code identifies work. It never implies a SemVer and never reserves one. Two plans authored on the same day have no version relationship to each other.
- The version is assigned only when a release is approved, from what the change actually contains: `major` for breaking, `minor` for backward-compatible functionality, `patch` for backward-compatible fixes.
- Build ids live in the artifact folder or CI artifact space. Do not create a Git tag for every development build.
- Every candidate tag has its own build, cut from the same commit, with `build.<NNN>` aligned to `rc.<NNN>`. The artifact promoted to production is the build belonging to the passing candidate.
- Candidate tags are immutable and lowercase, because Git refs are case insensitive on Windows file systems. The indicator is uppercased for work items and lowercased for tags, both derived from the one declared value.
- Release tags follow the repository release policy: bare `X.Y.Z`, no `v` prefix, no build metadata.
- Every release is traceable to a work item, a branch, a candidate tag, a commit SHA, a build id, a test evidence folder, a UAT approval, and the deployed artifact.
```

Replace the existing `## Orchestration Stages` list with:

```markdown
## Orchestration Stages

Every plan step designates an assignee and an execution mode. The stages are ordered. Stages 3 and 4 are hard gates: implementation never begins until both pass.

1. **Stage 1, Discovery and Detailed Design (`Assignee: Architect`)** - Read or propose the project indicator from `plans/PLAN-INDEX.md`, validate it against the shape regex, resolve each repository's default branch with the four step contract and record the resolved name plus the deciding step, run `git fetch origin <default>` so the cached remote ref is fresh, allocate the running number from the union of the remote tree, the local tree, and all branch names, filtered to this project's indicator by case sensitive comparison, recheck immediately before writing with nothing in between, query the knowledge graph via graphify, map affected modules, define contracts, specify exact target file paths, write the plan file and its ledger row, assert the number is unique, then commit and push only those two files with a `docs(<CODE>-<NNNNN>):` message. That authoring commit is the single sanctioned commit on the default branch and it makes the reservation visible to every checkout. Move status from `draft` to `under-review`. Do not assign a SemVer at this stage.
2. **Stage 2, Analyst Review Gate (`Assignee: analyst`)** - Runs immediately after the plan is written, with no intervening gate. The analyst audits against the coding principles and universal programming references, adjusts wording where it diverges, and records the verdict under `## Review Findings`.
3. **Stage 3, Test Matrix Attachment (`Assignee: tester`)** - Runs in parallel with stage 2 and completes before stage 4. The tester attaches `## Test Specification and Validation Matrix` with exact commands, fixtures, journeys, and pass criteria. A plan with an empty matrix may not reach stage 4.
4. **Stage 4, Findings Confirmation and User Consultation (`Assignee: Architect`)** - Present the analyst findings, the test matrix, the proposed indicator if it is new, and every open clarification, then ask for confirmation. Status becomes `awaiting-approval`. Never proceed on a silent assumption.
5. **Stage 5, Default Branch Reconciliation and Branch Creation (`Assignee: Architect` dispatches, `build` executes)** - Runs only after the user approves, and it has two parts that must both succeed before any implementation commit.
   - **5a, reconcile released content into each default branch.** For every repository the plan touches, resolve its default branch, then `git fetch origin --tags --prune`. Enumerate **release tags only**, meaning bare `X.Y.Z` that match the release regex; never a candidate tag. For each release tag, test `git merge-base --is-ancestor refs/tags/<X.Y.Z> refs/heads/<default>`. If every release tag is already an ancestor, the repository is reconciled and nothing is merged. If any release tag is not an ancestor, that released content is stranded off the default branch and the plan branch would be cut from stale code, so merge it with `git merge --no-ff <X.Y.Z>` on the default branch, then push. Record every repository, every release tag tested, and every merge performed, in the plan.
   - **5b, cut the branch.** With the default branch reconciled, `git pull --ff-only`, then `git switch -c <type>/<CODE>-<NNNNN>`, then push with upstream tracking. Record every repository, its resolved default branch, and the new branch in the plan.
   - Hard rules for both parts. Never merge a candidate tag (`<code-lower>/<NNNNN>/rc.<NNN>`) into a default branch, because it is unapproved work and merging it would bypass UAT and stage 14 entirely. Never move, delete, or force a tag to make it an ancestor; if reconciliation requires rewriting released history, stop and escalate to the user. If the merge conflicts, stop and escalate rather than resolving silently, because a conflict here means the default branch diverged from a released artifact. All implementation and all fixes happen on the plan branch. The default branch receives no implementation commits; the single exception is the Stage 1 authoring commit, which touched only the plan file and the ledger, plus the 5a reconciliation merges. Untracked local files are edited in place on the working checkout and are covered by the instruction manifest, not by a branch.
6. **Stage 6, Concurrent Implementation (`Assignee: edm`, `be`, `fe`)** - Commit to the plan branch only. Each subagent reports the commit SHA and the repository, and never switches branches or touches the default branch. Slice branches are `<type>/<CODE>-<NNNNN>-<slice>` and merge back into the plan branch.
7. **Stage 7, Workspace Build Gate (`Assignee: build`)** - Run the workspace builds (`cargo check --workspace`, `pnpm build`) on the plan branch, validate types, isolate compiler diagnostics, and record the build id `<CODE>-<NNNNN>-build.<NNN>`. Plans that change no buildable source record this stage as not applicable with a stated reason.
8. **Stage 8, Candidate Tag Before Test (`Assignee: build`)** - Before the first test run, create the annotated candidate tag `<code-lower>/<NNNNN>/rc.<NNN>`, starting at `rc.001`, on the plan branch head, and push it. Record the tag, its commit SHA, and its build id in the plan's `candidate_tags` list and in the ledger. A test run never starts against an untagged tree.
9. **Stage 9, QA: Automated Verification and Live Browser Test (`Assignee: tester`)** - Resolve the candidate with `git rev-parse <code-lower>/<NNNNN>/rc.<NNN>^{commit}` and test exactly that commit. Run the matrix with the token cache (`.secrets/test_token.json`), including a real live browser pass. Store evidence under `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/`. Report one line naming the tested tag, its SHA, and the verdict.
10. **Stage 10, Remediation Loop with a Fresh Tag per Fix (`Assignee: be`, `fe`, `edm`, then `build`)** - On failure, fix on the plan branch, commit, rebuild so the build id advances, then create the next candidate `rc.<NNN+1>` before retesting. Failed tags stay in history. Never move, delete, or force push a tag, and never treat a green run on an older tag as a pass for a newer tree.
11. **Stage 11, Resynchronization Before Final Candidate (`Assignee: build`)** - If the default branch advanced because another plan released, merge it into the plan branch, resolve conflicts on the branch, rebuild, and cut a fresh candidate. A candidate cut before the merge cannot be the release candidate.
12. **Stage 12, UAT, Version Decision, and Bump on the Branch (`Assignee: build`, approved by `primary`)** - When and only when QA passes against one candidate, present the result to the user for UAT approval. On approval, decide the SemVer from content, run the bump on the plan branch, commit it there, then cut and QA test one more candidate that includes the bump. Record the decision in the ledger and set status `release-version-decided`.
13. **Stage 13, Ancestry Assertion and Merge (`Assignee: build`)** - Before merging, assert `git merge-base --is-ancestor <default> <candidate>`; abort on exit 1. Then merge with `--no-ff` and assert the resulting tree equals the candidate tree. Set status `merged`. Concurrent plans stay independent: a later plan never waits for an earlier one.
14. **Stage 14, Release Tag and Publication (`Assignee: build`)** - Create the annotated release tag by hand at the default branch tip whose tree equals the passing candidate, `git tag -a <X.Y.Z> <sha> -m "<project-tag-message> <X.Y.Z>"`, using the same message text the publisher would use for this project (do not invent one, and do not hardcode any project's name in this instruction), because the retained script can only tag HEAD and has no target-commit parameter. Then, with the default branch checked out and the tree clean, invoke the publisher with `-SkipBump`, which finds the tag already present, reuses it without moving it, and pushes the branch and tag to the release set. Never create the release tag before the merge, so a failed merge cannot orphan a published tag.
15. **Stage 15, Deployment and Smoke Verification (`Assignee: Infra`, then `tester`)** - Deploy the artifact built for the passing candidate. Never rebuild for production, because the tested artifact is the promoted artifact. Then run post-deployment live smoke and browser health checks.
16. **Stage 16, Publication, Archival, and Retrospective (`Assignee: build`, `km`, `Architect`)** - Confirm the release tag across the release set, run the retrospective, set status `released`, and move the plan file to `plans/done/` while keeping its code and ledger row forever.
```

Replace the existing `## Build, Release, and Versioning` list with:

```markdown
## Release Versioning Policy

1. `<CODE>-<NNNNN>` is a work-item and delivery-plan identifier.
2. A work-item code must never be assumed to correspond to a semantic version.
3. Semantic versions are assigned only when a release is approved.
4. Development builds use the work-item code plus a build number, and are not Git tags.
5. Test candidates use `<code-lower>/<NNNNN>/rc.<NNN>`.
6. Candidate tags are immutable. Never move or overwrite an existing tag.
7. Every candidate has its own build, cut from the same commit, aligned by number.
8. A production release must carry the artifact that passed the final QA and UAT. Because a `--no-ff` merge creates a new commit, identity is asserted on the tree, not the commit: the merge is preceded by `git merge-base --is-ancestor <default> <candidate>` and followed by an assertion that `git rev-parse <default>^{tree}` equals `git rev-parse <candidate>^{tree}`. The release tag is placed on that default-branch tip.
9. The artifact that passed QA and UAT must be promoted to production unchanged.
10. The version bump is committed on the plan branch and is itself candidate tested before the merge.
11. The merge precedes the release tag, so a failed merge cannot orphan a published tag.
12. Before merging, assert the default branch is an ancestor of the candidate.
13. Before cutting a plan branch, reconcile each affected repository's default branch with every release tag: `git merge-base --is-ancestor refs/tags/<X.Y.Z> refs/heads/<default>`, merging any stranded release with `--no-ff`. A plan branch cut from a default branch that is missing released content is not a valid base.
14. Never merge a candidate tag into a default branch. Candidate tags are unapproved work, and merging one bypasses UAT and the release path.
15. Never move, delete, or force a tag to make it an ancestor. If reconciliation would rewrite released history, stop and escalate.
16. The release tool runs only with the default branch checked out and the tree clean.
17. The release tool reuses the already created tag, never moves it, and fails rather than retagging if the tag is absent.
18. Number allocation is filtered to the project's own indicator, so a code mentioned in another project's plan never inflates this series.
19. Concurrent plans may be released independently.
20. A later-completing plan must not block an earlier-completing plan.
21. When the default branch advances because another plan released, long-running branches must merge it and recut a candidate before their final release.
22. Production versions follow Semantic Versioning, `MAJOR.MINOR.PATCH`.
23. `MAJOR` is a breaking or incompatible change.
24. `MINOR` is backward-compatible functionality.
25. `PATCH` is a backward-compatible bug or security fix.
26. Never use `latest` as a production version identifier.
27. Every production release must be traceable to its work item, commit, build id, test result, UAT approval, and production artifact.
28. The project indicator is declared per project and never hardcoded in these instructions. Two projects never share one.
```

#### Exact additions to `tester.md`

First, add a permissions block to the `tester.md` frontmatter. It currently has none, so nothing grants write access to the evidence folder that the browser responsibility makes mandatory:

```yaml
permissions:
  - action: edit
    resource: "**/plans/evidence/**"
    effect: allow
```

Then insert after the existing automated verification responsibility, numbering it as the third:

```markdown
3. **Live Browser Testing (Mandatory whenever the plan has a user interface surface):**
   - Verify the running application in a real browser, not only through HTTP calls. Read the project's own test harness first and name the exact command you ran. When the project uses a Playwright harness, the usual entry points are `npx playwright test` for the local stack, `npx playwright test --config=<sso-config>` for an SSO journey, and the project's summary or report target to read results.
   - Fallback path for a surface the harness does not cover is the `wmux` browser, in this order: `wmux browser open <url>`, then `wmux browser snapshot` to get accessibility refs, then `wmux browser click <ref>`, `wmux browser fill <ref> "<text>"`, `wmux browser wait <ref> <ms>`, `wmux browser get-text <ref>`, `wmux browser eval "<js>"`, `wmux browser screenshot [--full]`. Write refs bare, without an `@` prefix, and always take a fresh snapshot before acting on refs. The `screenshot` command takes no path argument.
   - The `wmux` binary is not on `PATH` and needs a caller surface. Run inside a `wmux` pane, or pass an explicit caller surface when invoking it from a normal session.
   - Test the candidate tag, not the working tree. Check out or build the candidate tag commit, serve that artifact, record the served URL, and name the tag and its commit SHA in the result line. A tag is a commit reference, not a servable location.
   - Assert on rendered DOM text and visible state, never on internal implementation details.
   - Cover the plan's named journeys end to end: load the page, complete the primary action, assert the resulting visible state, then confirm the browser console shows no errors and no network request failed.
   - Capture evidence per run under `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/`: at least one full page screenshot per journey, the console error log, and the trace or HTML report when the harness produced one. Follow the project's evidence retention policy. A browser claim with no artifact in that folder counts as not tested.
   - Headless by default. Run headed only when the plan needs visual judgement, and say so in the report.
   - Cover one desktop width (`1440x900`) and one narrow width (`390x844`) unless the plan scopes the surface to desktop only.
   - Plans with no user interface surface record this responsibility as not applicable, with a one line reason, rather than skipping it silently.
   - Report browser failures with the failing ref, expected visible text, actual visible text, the screenshot path, and the same structured diagnostics used for other failures.
```

Renumber the following responsibilities (`Post-Deployment Smoke Verification`, `Session-End Goals Review with Analyst`, `Release Trigger`).

Replace the release trigger wording in `tester.md` so it reports the passing candidate tag and SHA, recommends the increment from content, and creates no tag, because `build` owns candidate tags, the release tag, the merge, and the push.

### Target Program Files (Mandatory)

No Rust, TypeScript, or SQL file is touched. The instruction files are configuration, not program source. The Architect cannot write them under its own permission scope, so `be` owns those writes.

The repository column matters, because the target files live in two repositories with different default branches, and because six of them are untracked by decision 2.

| File | Repo | Action | Owning assignee | Change |
|---|---|---|---|---|
| `.opencode/agents/Architect.md` | Agentic, **local only** | edit in place, back up first | be | Permission `**` fix, Write Scope, Plan Identity and Numbering, Identifier Taxonomy, 16 stages, 28 rule policy, and the `## Plan File Standards & Structure` frontmatter list (lines 46 to 55), which still omits `plan_id`, `project_indicator`, `branch`, `candidate_tags`, `release_version` |
| `.opencode/agents/tester.md` | Agentic, **local only** | edit in place, back up first | be | Live Browser Testing with real `wmux` call forms, not-applicable path, line 12 filename pattern updated, release trigger alignment, renumber, **plus a frontmatter permissions block granting edit on `**/plans/evidence/**`**, because without it the mandatory evidence folder has no writer |
| `.opencode/agents/plan.md` | Agentic, **local only** | edit in place, back up first | be | Holds the old Phase 1 to 7 workflow and status `completed`; either redirect it to `Architect.md` or align it in the same pass |
| `.opencode/agents/Infra.md` | Agentic, **local only** | edit in place, back up first | be | Line 67 still sets status `completed`, which is absent from the new vocabulary |
| `.opencode/agents/build.md` | Agentic, **local only** | edit in place, back up first | be | Candidate tag creation, ancestry assertion, `--no-ff` merge, hand-made release tag at the candidate SHA, `-SkipBump` publisher, per-repository default branch precondition |
| `.opencode/agents/analyst.md` | Agentic, **local only** | edit in place, back up first | be | Analyst-first gate, indicator and identifier separation checks, instruction manifest verification |
| `AGENTS.md` | Agentic, tracked, default `master` | branch `feature/AVRIG-00001` | be | Identifier taxonomy, indicator rules, candidate tag gate, 28 rule policy, per-repository default branch rule, and the corrected sentence that names `plan.md` as the workflow authority |
| `avrig-ai/AGENTS.md` | `avrig-ai`, tracked, default `main` | branch `feature/AVRIG-00001` | be | Same policy, plus the indicator declaration and the four-repository publish rule |
| `avrig-ai/plans/PLAN-INDEX.md` | `avrig-ai` | authoring commit on `main`, then maintain | Architect | Ledger with indicator, allocation rule and indicator filter, status vocabulary, and the `AVRIG-00001` row. Maintained at stages 8, 12, 13, 14 and 16 |
| `avrig-ai/plans/2026-11-19-AVRIG-00001-agent-workflow-update.md` | `avrig-ai` | authoring commit on `main` | Architect | This plan |
| `avrig-ai/plans/evidence/` | `avrig-ai` | create folder, gitignore entry | be | Retention policy plus the SHA-256 instruction manifest for the local-only files |
| `avrig-ai/.gitignore` | `avrig-ai`, tracked | branch `feature/AVRIG-00001` | be | Add the evidence ignore rule so `git add -A` does not sweep screenshots into releases |

The six `local only` rows are untracked by decision 2. They are edited in place on the working checkout, backed up as `<file>.bak-<timestamp>` first, and verified by the SHA-256 manifest rather than by a candidate tag. Only `AGENTS.md`, `avrig-ai/AGENTS.md`, the plans tree, and `.gitignore` are covered by the branch and the tag.

Both `AGENTS.md` files are tracked and land on the plan branch, so they are taggable. The instruction files are not, which is the accepted risk recorded in "Local-only files and how they are verified".

### EDM Design

None. This plan creates no table, column, index, constraint, or migration, and reads no database. Persisting plan metadata instead of a Markdown ledger would be a separate plan with its own `edm` phase.

## Parallel Execution Plan

| Stream | Assignee | Depends on | Mode |
|---|---|---|---|
| P1 Ledger, plan authoring, code allocation, duplicate assertion | Architect | none | done in this pass |
| P1b Default branch resolution recorded per repository | Architect | P1 | done in this pass, measured |
| P2 Analyst review of this plan | analyst | P1 | parallel with P2b |
| P2b Attach the test matrix | tester | P1 | parallel with P2 |
| P3 User confirmation of findings and clarifications | Architect, user | P2, P2b | sequential, gate |
| P4 Default branch reconciliation against every release tag, then branch creation | build | P3 approval | sequential, gate |
| P5 `Architect.md` rewrite | be | P4 | parallel with P6, P7, P8 |
| P6 `tester.md` rewrite | be | P4 | parallel with P5, P7, P8 |
| P7 `AGENTS.md`, `avrig-ai/AGENTS.md`, evidence ignore | be | P4 | parallel with P5, P6, P8 |
| P8 `plan.md`, `Infra.md`, `build.md`, `analyst.md` alignment, plus clearing the three stale `completed` status values at `Architect.md` line 84, `plan.md` line 68, and `Infra.md` line 67 | be | P4 | parallel with P5, P6, P7 |
| P9 Instruction consistency read-back | analyst | P5 to P8 | sequential |
| P10 Build and candidate `rc.001` with its build id | build | P9 | sequential |
| P11 QA matrix and live browser test on `rc.001` | tester | P10 | sequential |
| P12 Fix cycle, rebuild, next candidate | be then build | P11 failure | loop |
| P13 Resync with the default branch if it advanced | build | P11 or P12 pass | conditional, gate |
| P14 UAT and version decision | user, build | P13 | sequential, gate |
| P15 Bump on branch, commit, rebuild, candidate for the bump | build | P14 | sequential |
| P16 QA the bump candidate | tester | P15 | sequential |
| P17 Ancestry assertion and `--no-ff` merge | build | P16 | sequential, gate |
| P18 Release with `-SkipBump` | build | P17 | sequential |
| P19 Retrospective and archival | km, Architect | P18 | sequential |

P5 to P8 touch disjoint file sets, so they run concurrently. P10 must not start until P9 confirms the documents agree on the tag shape, the branch pattern, the token regex, the ancestry assertion, and the release command.

## Execution Record

Stage 5 was executed on 2026-11-19, after the user approved the plan on the same day. This section is the durable record required by stage 5, and it is appended on the plan branch rather than on the default branch.

### 5a, default branch reconciliation

Command `C18` was run after `git fetch origin --tags --prune --quiet` in every repository. Result: `stranded_release_tags=0`, verdict `PASS`.

| Repository | Resolved default | Release tags tested | Stranded | Reconciliation merge |
|---|---|---|---|---|
| `avrig-ai` | `main` | `0.2.0`, `0.2.1`, `0.3.0`, `0.4.0` | 0 | none required |
| `avrig-api` | `main` | `0.2.0`, `0.2.1`, `0.3.0`, `0.4.0` | 0 | none required |
| `avrig-lib` | `main` | `0.2.0`, `0.2.1`, `0.3.0`, `0.4.0` | 0 | none required |
| `avrig-ui` | `main` | `0.2.0`, `0.2.1`, `0.3.0`, `0.4.0` | 0 | none required |
| `Agentic` | `master` | none (no SemVer tags exist) | 0 | none required |

Every local default branch was also confirmed identical to its `origin` counterpart after the fetch, so `C18` did not pass against a stale local ref. No candidate tag was examined, by construction: a three segment ref cannot match the anchored release regex, and the gate forbids merging one regardless.

### 5b, branch creation

| Repository | Default | Authoring commit | Plan branch | Branch head | Upstream |
|---|---|---|---|---|---|
| `avrig-ai` | `main` | `5aaa879`, "AVRIG-00001: plan and ledger for agent workflow update", pushed to `origin/main` | `feature/AVRIG-00001` | `5aaa879` | `origin/feature/AVRIG-00001` |
| `Agentic` | `master` | none (this plan adds no tracked file there yet) | `feature/AVRIG-00001` | `0bf72a5` | `origin/feature/AVRIG-00001` |

The authoring commit touched exactly two paths, `plans/PLAN-INDEX.md` and this plan file. A pre-existing modified plan, `plans/2026-11-19-gateway-opencode-header-passthrough.md`, was deliberately left out of it and remains uncommitted.

The Agentic plan branch is currently identical to `master` because `AGENTS.md` is not written until P7. Cutting it now satisfies the gate: P5 to P8 cannot start without it, and the branch must exist before `be` writes into it.

## Open Implementation Decisions

1. **The Agentic `AGENTS.md` working copy already carries uncommitted drift that predates this plan.** `git diff AGENTS.md` shows 54 insertions and 1 deletion: a new `## Environment & Directories` section, a `## Codebase Exploration & Navigation (graphify > grep)` section, a rewritten `## Subagent Delegation & Operational Workflows` section, and a `Local project AGENTS.md takes precedence` sentence. None of it is AVRIG-00001 content, and it still contains the stale sentence this plan exists to fix: "The Plan agent owns plan creation and lifecycle updates. Follow its instructions in `$env:OPENCODE_CONFIG_DIR/.opencode/agents/plan.md`". Committing `AGENTS.md` on the plan branch would therefore sweep in a large governance rewrite of unverified provenance together with this plan's change.

   Options: (a) commit only this plan's AGENTS.md change, reconstructed from `git show master:AGENTS.md` plus the plan's edits, leaving the drift uncommitted in the working tree (recommended, since it keeps the branch commit honest and is fully reversible); (b) commit the whole working tree file at P7 with the drift included and disclose it in the commit message; (c) commit the drift to `master` first as its own change, then branch and make the targeted edit.

   Blocked by this: only the P7 `AGENTS.md` write in the Agentic repository. P5, P6 and P8 are unaffected because they write untracked `.opencode/agents/` files, and the `avrig-ai` half of P7 is unaffected because `avrig-ai/AGENTS.md` has no pre-existing drift. Waiting on: the user.

## Resolved Decisions

Answered by the user on 2026-11-19. These are settled and are no longer questions.

1. **Default branch differs per repository, and remote HEAD can be wrong.** Each repository declares its own default branch and the workflow never assumes `main`. Resolution follows the four step contract in `#### Measured state of the workspace`: the current tracking branch, else `origin/HEAD`, else the sole local branch when the two disagree, else stop and ask. Measured outcome for this workspace: `avrig-ai`, `avrig-api`, `avrig-lib` and `avrig-ui` resolve to `main` by the remote HEAD step, and the Agentic configuration repository resolves to `master` by the sole-local-branch step because `origin/HEAD` there points at `origin/main` while no local `main` exists. Every stage records the resolved name and the step that decided it. No repository's default branch is renamed, deleted, or harmonized by this plan.
2. **Agent instruction files are local only.** `.opencode/agents/` stays untracked in the Agentic repository by decision, not by accident. Consequence: the candidate tag cannot cover them, so their verification is read-back plus a recorded checksum manifest rather than a tagged artifact. See "Local-only files and how they are verified" below.
3. **Plans are committed.** The plan file and `plans/PLAN-INDEX.md` are committed to the project's default branch as the single sanctioned authoring commit, before any implementation branch is cut. This publishes the number reservation so other checkouts and worktrees can see it.

## Local-only files and how they are verified

Decision 2 removes the seven agent instruction files from version control, which breaks the assumption that a candidate tag identifies everything a plan changed. Rather than hide that, the plan handles it explicitly.

| Property | Behaviour |
|---|---|
| Version control | None. `.opencode/agents/` is untracked and stays that way |
| Candidate tag coverage | None. A candidate tag covers only tracked content |
| Edited in place | Yes, on the working checkout, by `be`, outside any branch |
| Verification | A consistency read-back by `analyst` plus a SHA-256 manifest of every edited file recorded under `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/instruction-manifest.txt` |
| Rollback | Because there is no git history, `be` copies each file to `<file>.bak-<timestamp>` before editing, so a bad edit is recoverable |
| Drift detection | The manifest is regenerated and compared on each release. A mismatch means a local edit landed without a plan |
| What a candidate tag proves | Only the tracked half of the change: the plans tree, and any source a plan touches |

This is a deliberate accepted risk, recorded so a later reader does not assume the tag covers the instruction files. The mitigation is the backup plus the manifest, not version control.

## Remaining Open Clarifications

Non-blocking. Each has a recommended default, and execution proceeds on the recommendation unless the user overrides it.

1. **Indicator confirmation.** Confirm `AVRIG` for this project. The ledger marks it `pending-user-confirmation` rather than frozen, so the rule and the artifact agree.
2. **Indicator derivation policy.** Deriving from the folder name produces `AVRIGAIGAT` for the worktree, which truncates a word, and `API` or `WEB` for generic folders. Should the Architect always require the user to supply the indicator, with derivation offered only as a hint, and never truncate inside a word? Recommended: yes on both.
3. **Test evidence retention.** Commit `plans/evidence/` (which `git add -A` sweeps into releases), keep it local with a manifest checksum recorded in the ledger, or store it outside both repositories? Recommended: local plus checksum, with a `.gitignore` entry.
4. **Release set scope.** The retained script tags all four repositories regardless of what a plan touched. Accept that the release set is always all four, or lift the non-goal and add a repository filter to `release.ps1`? Recommended: accept all four, since the script tags HEAD of repositories with no pending change, which is harmless.
5. **Candidate tag namespace.** `<code-lower>/<NNNNN>/rc.<NNN>` versus flat `<CODE>-<NNNNN>-rc.<NNN>`. Both are provably disjoint from SemVer, so this is readability only. Recommended: namespaced.
6. **Indicator uniqueness registry.** Adopt `<OPENCODE_CONFIG_DIR>/.opencode/plan-projects.json` now, or only when a second project adopts plans? Recommended: write the rule now, create the file when needed.

Removed as already settled by evidence: the `v` prefix question (`release.ps1` anchors the regex at `^(0|[1-9]\d*)`, so `v1.1.0` is impossible), the governance mirror question (the file table already mandates those rows), the legacy backfill question (the non-goal and the forward-only test settle it), and the new-project indicator derivation question (the propose-then-confirm rule settles it).

## Test Specification and Validation Matrix

Authored and attached by `tester` at stage 3. Attached as of 2026-11-19 under stream `P2b`.

This plan changes instruction documents, a ledger, and two `AGENTS.md` files. It writes no Rust, TypeScript, or SQL, and it adds no HTTP route. There is therefore no compile-and-run target and no API surface to exercise, and this matrix does not pretend otherwise: it is a document conformance matrix plus one live browser pass. Every check below names a command that has been executed at least once during authoring, so the command is known to run rather than assumed to run. Where a check legitimately fails against the current text, the failure is called out here rather than smoothed over, because a matrix that only passes is not a measurement.

Commands are cited by ID (`C01` to `C18`) and their verbatim bodies follow the table. Each writes its output to the evidence folder, so a pass is a file rather than a claim.

The seven instruction files are untracked by resolved decision 2, so a candidate tag cannot cover them. Their verification is a SHA-256 manifest plus a read-back (`D13`), which is the strongest statement available without version control, not a substitute for it.

| ID | Requirement | Method (exact command) | Pass criteria | Evidence artifact |
|---|---|---|---|---|
| D01 | The fenced instruction blocks destined for `Architect.md` and `tester.md` contain zero literal occurrences of this project's indicator, case insensitive, while the neutral `AAAAA` stand-in remains permitted in the taxonomy Example column only | `C01` (slice the replacement region, enumerate fences, count `(?i)avrig` per fence) | 0 indicator hits in every fence. `AAAAA` may appear in the Identifier Taxonomy fence and nowhere else. Failing fence named | `rc.<NNN>/D01-fence-indicator-count.txt` |
| D02 | The indicator shape regex rejects every adversarial value and accepts the boundary lengths | `C02` (13 cases through `[regex]::IsMatch` against `^[A-Z][A-Z0-9]{1,9}$`) | 13 of 13 match expectation: accepts `AVRIG`, `WEB`, `AB`, `ABCDEFGHIJ`; rejects `A`, `ABCDEFGHIJK`, `MY-PROJ`, `avrig`, `AV RIG`, `1AVRIG`, `_AVRIG`, `AVRIG!`, empty | `rc.<NNN>/D02-shape-regex.txt` |
| D03 | The anchored filename regex extracts the code adjacent to the date, and neither a hyphen split nor a loose digit scan is used | `C03` (anchored regex over one real name plus five hostile names) | `2026-11-19-AVRIG-00001-...` yields `AVRIG/00001`; `AVRIG2-00042` yields `AVRIG2/00042`; `chore-migrate-to-20250-table` yields no match, proving `20250` is not read from the slug; the legacy, four digit, and lowercase forms each yield no match | `rc.<NNN>/D03-parse-regex.txt` |
| D04 | The allocation filter keeps only this project's indicator, so a foreign code in a slug or filename never inflates the series | `C04` (unfiltered max versus indicator filtered max over five names, one carrying a higher foreign code) | Unfiltered max is strictly greater than filtered max (measured 91 versus 43). Filtered values are exactly the two `AVRIG` claims. A foreign code raises the unfiltered max and leaves the filtered max unchanged | `rc.<NNN>/D04-indicator-filter.txt` |
| D05 | The instruction text names all six identifier kinds and states that a work-item code never implies a SemVer | `C05` (count the seven required tokens inside the replacement region) | `Six identifiers` present; `Work item`, `Branch`, `Slice branch`, `Build id`, `Candidate tag`, `Release tag` each present; the SemVer separation sentence present | `rc.<NNN>/D05-identifier-kinds.txt` |
| D06 | `Architect.md` places `analyst` review immediately after authoring, with the test matrix attached before the approval stage | `C06` (index positions of stages 1 to 4 in the replacement region) | All four stage headings found and strictly increasing: Stage 1 < Stage 2 < Stage 3 < Stage 4. Stage 3 names the matrix and stage 4 names the confirmation | `rc.<NNN>/D06-stage-order.txt` |
| D07 | `Architect.md` states the branch is cut from the repository's resolved default branch, only after user approval, in the pattern `<type>/<CODE>-<NNNNN>` | `C07` (token counts in the replacement region) | `symbolic-ref --short refs/remotes/origin/HEAD` present; `<type>/<CODE>-<NNNNN>` present; an explicit approval precondition present; no unconditional `git switch main` | `rc.<NNN>/D07-branch-gate.txt` |
| D08 | A candidate tag and its aligned build exist before the first test, and every fix produces the next numbered pair | `C08` (token counts plus a scale check) | `rc.<NNN>` present; `build.<NNN>` present; `rc.<NNN+1>` present; the first-test precondition present; `immutable` and the no-move rule present | `rc.<NNN>/D08-candidate-gate.txt` |
| D09 | The release sequence is stated in the correct order: bump on branch, candidate the bump, ancestry assertion, tree equality, merge, hand-made tag, `-SkipBump` publisher | `C09` (ordered index walk over seven anchors) | All seven anchors found and strictly increasing. `merge-base --is-ancestor` before `--no-ff`; tree equality before `git tag -a`; `git tag -a` before `-SkipBump` | `rc.<NNN>/D09-release-order.txt` |
| D10 | `tester.md` names the Playwright harness and the `wmux browser` fallback with real ref-based call forms, and grants write permission for `**/plans/evidence/**` | `C10` (count the nine required forms plus the permission glob) | `npx playwright test` present; `wmux browser open`, `snapshot`, `click <ref>`, `fill <ref>`, `wait <ref> <ms>`, `get-text <ref>`, `eval`, `screenshot [--full]` each present; `**/plans/evidence/**` present in the permissions block; no `@` prefix on refs | `rc.<NNN>/D10-tester-browser.txt` |
| D11 | No edited instruction file carries the stale status value `completed` | `C11` (count `status:\s*completed` and the backticked token across all eight files) | 0 status assignments and 0 backticked `completed` tokens. Prose such as "completed history" is exempt and reported separately, because it is not a status value | `rc.<NNN>/D11-stale-status.txt` |
| D12 | Every recorded default branch equals the value the four step resolution contract actually returns, including the disagreeing case | `C12` (apply the contract per repository, then compare to the plan's table, printing the deciding step for each) | The resolved value for each repository matches the plan's recorded default branch, and the deciding step is recorded. The Agentic repository must resolve to `master` by the sole-local-branch step while `origin/HEAD` reports `origin/main`, so a run that returns `main` there is a BLOCKER, not a warning | `rc.<NNN>/D12-default-branch.txt` |
| D13 | A SHA-256 instruction manifest exists for the local-only files and every edited file has a `.bak-` sibling | `C13` (hash eight files, write manifest, then re-hash from the manifest) | Manifest exists at the recorded path; read-back verifies 8 of 8 hashes; 8 of 8 `.bak-` siblings present; no `MISSING` placeholder row | `rc.<NNN>/instruction-manifest.txt`, `rc.<NNN>/D13-manifest-readback.txt` |
| D14 | Tracked edits are confined to `plans/`, the two `AGENTS.md` files, and `.gitignore`, observed per repository with absolute paths | `C14` (baseline capture before implementation, then one `git diff --stat` per repository) | The after-minus-before delta contains no path outside the allowed set, in both `Agentic` and `avrig-ai`. Pre-existing drift is subtracted, not tolerated | `rc.<NNN>/D14-drift-agentic.txt`, `rc.<NNN>/D14-drift-avrig-ai.txt`, `rc.<NNN>/D14-baseline.txt` |
| D15 | Live browser verification is actually executable, with a screenshot, a stated URL, and a stated verdict | `C15` (Playwright journey against the platform login surface) | Page reaches HTTP 200, the login form renders with one email and one password input, both viewport screenshots exist and are non-empty, zero requests failed, and every console error is reconciled by name. A surface that cannot be served is recorded BLOCKED with a reason, never PASS | `rc.<NNN>/browser-login-1440x900.png`, `rc.<NNN>/browser-login-390x844.png`, `rc.<NNN>/D15-browser-report.json` |
| D16 | The plan itself carries no em-dash and no en-dash, since it mandates that rule | `C16` (count U+2014 and U+2013 in the plan file) | 0 and 0 | `rc.<NNN>/D16-dash-scan.txt` |
| D17 | `Architect.md` states the pre-branch reconciliation gate, naming release tags only, and forbids merging a candidate tag into a default branch | `C17` (token counts in the replacement region) | `merge-base --is-ancestor refs/tags/` present; `--no-ff` present in the reconciliation step; a prohibition on merging `rc.<NNN>` into a default branch present; a prohibition on moving or forcing a tag present; no wording that permits merging a candidate tag | `rc.<NNN>/D17-pre-branch-reconcile.txt` |
| D18 | Every release tag is an ancestor of its repository's default branch, so the plan branch is not cut from stale code | `C18` (`git fetch origin --tags --prune`, then per-tag `git merge-base --is-ancestor` across all repositories) | Zero stranded release tags, or every stranded tag named with its repository and merged before branching. Candidate tags are excluded from the check by design | `rc.<NNN>/D18-release-tag-ancestry.txt` |

### Preconditions and measured environment baseline

Checked on 2026-11-19 while authoring this matrix, so a later run can tell a regression from a standing condition.

| Item | Measured now | Consequence for this matrix |
|---|---|---|
| wmux caller surface | `WMUX_SURFACE_ID` is unset, and every `wmux` subcommand from a plain PowerShell session exits 0 with empty stdout and empty stderr. The binary is at `C:\Program Files\wmux\wmux.exe` and is not on `PATH` | The `wmux browser` fallback is BLOCKED from a non-wmux session. D15 therefore runs the Playwright path, which is proved working below. The `wmux` leg is recorded BLOCKED with this reason, never PASS |
| Playwright harness | `D:\Cloud\OneDrive\AI\Agentic\test` holds `playwright.config.ts`, `playwright.keycloak.config.ts`, a `Makefile` with `test`, `keycloak`, `report`, `summary` targets, and `npx playwright --version` reports 1.63.0. Browsers are installed under `%LOCALAPPDATA%\ms-playwright` | The verified path. The harness resolves only from that directory, so every Node command must run with that working directory |
| Login surface | `https://iam.avrig.ai/` returns 200 and renders a Rauthy account chooser. Clicking `Account` reaches `https://iam.avrig.ai/auth/v1/oidc/authorize?...` titled `Login: Rauthy` with one email input and one password input | Usable as the executor-capability surface. It is the platform IdP, not a UI this plan changes |
| Test token cache | `.secrets/test_token.json` exists in `avrig-ai` with an `access_token`, `expires_in` 1800, obtained 113.6 minutes ago | EXPIRED. It must be refreshed before any authenticated request. No check in this matrix depends on it, because this plan exposes no authenticated endpoint |
| Evidence folder | `plans/evidence/` does not exist, and `git check-ignore plans/evidence/test/x.png` exits 1 | The `.gitignore` row is load bearing: until it lands, `git add -A` would sweep screenshots into a release commit |
| Backup siblings | Zero `*.bak-*` files exist under `.opencode/agents/` | `be` must create them before editing. D13 fails until it does |
| Agentic pre-existing drift | 22 tracked modifications already present, including `.obsidian/`, `.opencode/opencode.json`, eight `shared/skills/` paths, `service.json`, and three gitlink entries (`agentic`, `api`, `web`). `git submodule status` reports `no submodule mapping found in .gitmodules for path 'agentic'` | D14 cannot be a diff-against-HEAD check. It must be a baseline delta, or it fails on work this plan never touched |
| avrig-ai pre-existing drift | Two plan files already modified: `2026-11-18-release-0.3.0-consolidated.md` and `2026-11-19-gateway-opencode-header-passthrough.md` | Same consequence: baseline captured first, delta compared after |
| Candidate tags | `git tag --list 'avrig/*'` returns nothing; release tags stop at `0.4.0` | `rc.001` does not exist yet, so every evidence path below is created by the first run rather than reused |

### Command bodies

Each body is verbatim and self-contained. Replace `<plan>` with the absolute plan path and `<rc>` with the candidate evidence folder.

**C01, indicator count per fence**

This body deliberately avoids `exit`, which would close the calling session. A malformed region is reported as `RESULT FAIL` with a reason instead of terminating the shell.

```powershell
$plan = '<plan>'; $rc = '<rc>'
$raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`')
$b = $raw.IndexOf('### Target Program Files (Mandatory)')
$lines = @()
if ($a -lt 0 -or $b -le $a) {
    $lines += 'RESULT FAIL region-not-found'
} else {
    $region = $raw.Substring($a, $b - $a)
    $fences = [regex]::Matches($region, '```(?<lang>[a-z]*)\r?\n(?<body>[\s\S]*?)\r?\n```')
    $n = 0; $total = 0
    foreach ($f in $fences) {
        $n++
        $hits = ([regex]::Matches($f.Groups['body'].Value, '(?i)avrig')).Count
        $aaaa = ([regex]::Matches($f.Groups['body'].Value, 'AAAAA')).Count
        $total += $hits
        $lines += 'fence{0} lang={1} indicator_hits={2} AAAAA={3}' -f $n, $f.Groups['lang'].Value, $hits, $aaaa
    }
    $lines += "fences=$n TOTAL_indicator_hits=$total"
    $lines += if ($total -eq 0 -and $n -ge 8) { 'RESULT PASS' } else { 'RESULT FAIL' }
}
$lines | Set-Content -LiteralPath "$rc\D01-fence-indicator-count.txt" -Encoding utf8
$lines
```

**C02, shape regex against adversarial values**

```powershell
$shape = '^[A-Z][A-Z0-9]{1,9}$'
$cases = @(
    @('AVRIG','PASS'), @('WEB','PASS'), @('AB','PASS'), @('ABCDEFGHIJ','PASS'),
    @('A','FAIL'), @('ABCDEFGHIJK','FAIL'), @('MY-PROJ','FAIL'), @('avrig','FAIL'),
    @('AV RIG','FAIL'), @('1AVRIG','FAIL'), @('_AVRIG','FAIL'), @('AVRIG!','FAIL'), @('','FAIL')
)
$bad = 0; $out = @()
foreach ($c in $cases) {
    $got = if ([regex]::IsMatch($c[0], $shape)) { 'PASS' } else { 'FAIL' }
    if ($got -ne $c[1]) { $bad++ }
    $out += "'{0}' expect={1} got={2}" -f $c[0], $c[1], $got
}
$out += "mismatches=$bad"
$out += if ($bad -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D02-shape-regex.txt" -Encoding utf8
$out
```

**C03, anchored filename parse**

```powershell
$fileRx = '^(?<date>\d{4}-\d{2}-\d{2})-(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<slug>.+)$'
$names = @(
    '2026-11-19-AVRIG-00001-agent-workflow-update.md',
    '2026-11-19-AVRIG2-00042-fix-v2-timeout-in-rc.2.md',
    '2026-11-19-chore-migrate-to-20250-table.md',
    '2026-11-18-release-0.3.0-consolidated.md',
    '2026-11-19-AVRIG-0001-fourdigits.md',
    '2026-11-19-avrig-00044-lowercase.md'
)
$expect = @('AVRIG/00001','AVRIG2/00042','NO MATCH','NO MATCH','NO MATCH','NO MATCH')
$out = @(); $bad = 0; $i = 0
foreach ($name in $names) {
    $m = [regex]::Match($name, $fileRx)
    $got = if ($m.Success) { "$($m.Groups['code'].Value)/$($m.Groups['num'].Value)" } else { 'NO MATCH' }
    if ($got -ne $expect[$i]) { $bad++ }
    $out += '{0} -> {1} (expect {2})' -f $name, $got, $expect[$i]
    $i++
}
$out += "mismatches=$bad"
$out += if ($bad -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D03-parse-regex.txt" -Encoding utf8
$out
```

**C04, indicator filter with a higher foreign code**

```powershell
$own = 'AVRIG'
$fileRx = '^(?<date>\d{4}-\d{2}-\d{2})-(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<slug>.+)$'
$names = @(
    '2026-11-19-AVRIG-00001-agent-workflow-update.md',
    '2026-11-19-AVRIG-00043-mentions-WEB-00009.md',
    '2026-11-19-WEB-00091-shared-work.md',
    '2026-11-19-AVRIG2-00042-fix-v2-timeout-in-rc.2.md',
    '2026-11-19-chore-migrate-to-20250-table.md'
)
$all = @(); $mine = @()
foreach ($name in $names) {
    $m = [regex]::Match($name, $fileRx)
    if ($m.Success) {
        $all += [int]$m.Groups['num'].Value
        if ($m.Groups['code'].Value -ceq $own) { $mine += [int]$m.Groups['num'].Value }
    }
}
$unf = ($all | Measure-Object -Maximum).Maximum
$fil = ($mine | Measure-Object -Maximum).Maximum
$out = @(
    "unfiltered=$unf values=$($all -join ',')",
    "filtered=$fil values=$($mine -join ',')",
    'unfiltered greater than filtered: ' + ($unf -gt $fil)
)
$out += if ($fil -eq 43 -and $unf -gt $fil) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D04-indicator-filter.txt" -Encoding utf8
$out
```

**C05, six identifier kinds and SemVer separation**

```powershell
$plan = '<plan>'; $raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`'); $b = $raw.IndexOf('### Target Program Files (Mandatory)')
$region = $raw.Substring($a, $b - $a)
$need = @('Six identifiers','Work item','Slice branch','Build id','Candidate tag','Release tag','never implies a SemVer')
$out = @(); $miss = 0
foreach ($t in $need) {
    $c = ([regex]::Matches($region, [regex]::Escape($t))).Count
    if ($c -eq 0) { $miss++ }
    $out += '{0} count={1}' -f $t, $c
}
$out += "missing=$miss"
$out += if ($miss -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D05-identifier-kinds.txt" -Encoding utf8
$out
```

**C06, analyst-first stage ordering**

```powershell
$plan = '<plan>'; $raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`'); $b = $raw.IndexOf('### Target Program Files (Mandatory)')
$region = $raw.Substring($a, $b - $a)
$stages = @('Stage 1, Discovery','Stage 2, Analyst Review','Stage 3, Test Matrix','Stage 4, Findings Confirmation')
$pos = @(); $miss = 0
foreach ($s in $stages) {
    $i = $region.IndexOf($s)
    if ($i -lt 0) { $miss++ }
    $pos += $i
}
$ok = $miss -eq 0
for ($k = 1; $k -lt $pos.Count; $k++) { if ($pos[$k] -le $pos[$k-1]) { $ok = $false } }
$out = @("positions=$($pos -join ',')", "missing=$miss", 'ordered=' + $ok)
$out += if ($ok) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D06-stage-order.txt" -Encoding utf8
$out
```

**C07, branch gate**

```powershell
$plan = '<plan>'; $raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`'); $b = $raw.IndexOf('### Target Program Files (Mandatory)')
$region = $raw.Substring($a, $b - $a)
$out = @()
$resolve = ([regex]::Matches($region, 'symbolic-ref --short refs/remotes/origin/HEAD')).Count
$pattern = ([regex]::Matches($region, [regex]::Escape('<type>/<CODE>-<NNNNN>'))).Count
$approve = ([regex]::Matches($region, '(?i)after the user approves')).Count
$naive   = ([regex]::Matches($region, 'git switch main')).Count
$out += "resolve_command=$resolve pattern=$pattern approval_precondition=$approve unconditional_switch_main=$naive"
$out += if ($resolve -ge 1 -and $pattern -ge 1 -and $approve -ge 1 -and $naive -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D07-branch-gate.txt" -Encoding utf8
$out
```

**C08, candidate tag gate and fresh tag per fix**

```powershell
$plan = '<plan>'; $raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`'); $b = $raw.IndexOf('### Target Program Files (Mandatory)')
$region = $raw.Substring($a, $b - $a)
$out = @()
$rc      = ([regex]::Matches($region, [regex]::Escape('rc.<NNN>'))).Count
$build   = ([regex]::Matches($region, [regex]::Escape('build.<NNN>'))).Count
$nextRc  = ([regex]::Matches($region, [regex]::Escape('rc.<NNN+1>'))).Count
$preTest = ([regex]::Matches($region, '(?i)before the first test')).Count
$immut   = ([regex]::Matches($region, '(?i)immutable')).Count
$noMove  = ([regex]::Matches($region, '(?i)never move')).Count
$out += "rc=$rc build=$build next_rc=$nextRc first_test_precondition=$preTest immutable=$immut never_move=$noMove"
$out += if (@($rc,$build,$nextRc,$preTest,$immut,$noMove) -notcontains 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D08-candidate-gate.txt" -Encoding utf8
$out
```

**C09, release sequence order**

```powershell
$plan = '<plan>'; $raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`'); $b = $raw.IndexOf('### Target Program Files (Mandatory)')
$region = $raw.Substring($a, $b - $a)
$order = @(
    'run the bump on the plan branch',
    'cut and QA test one more candidate that includes the bump',
    'merge-base --is-ancestor',
    '--no-ff',
    'tree equals the candidate tree',
    'git tag -a',
    '-SkipBump'
)
$pos = @(); $miss = @(); $out = @()
foreach ($t in $order) {
    $i = $region.ToLowerInvariant().IndexOf($t.ToLowerInvariant())
    if ($i -lt 0) { $miss += $t } else { $pos += $i }
    $out += '{0} index={1}' -f $t, $i
}
$ok = ($miss.Count -eq 0)
for ($k = 1; $k -lt $pos.Count; $k++) { if ($pos[$k] -le $pos[$k-1]) { $ok = $false } }
$out += "missing=$($miss.Count) ordered=$ok"
$out += if ($ok) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D09-release-order.txt" -Encoding utf8
$out
```

**C10, tester browser forms and evidence permission**

```powershell
$plan = '<plan>'; $raw = Get-Content -LiteralPath $plan -Raw
$t = $raw.Substring($raw.IndexOf('First, add a permissions block'), 5000)
$need = @(
    'npx playwright test',
    'wmux browser open',
    'wmux browser snapshot',
    'wmux browser click <ref>',
    'wmux browser fill <ref> "<text>"',
    'wmux browser wait <ref> <ms>',
    'wmux browser get-text <ref>',
    'wmux browser eval',
    'wmux browser screenshot [--full]',
    '**/plans/evidence/**'
)
$out = @(); $miss = 0
foreach ($n in $need) {
    $c = ([regex]::Matches($t, [regex]::Escape($n))).Count
    if ($c -eq 0) { $miss++ }
    $out += '{0} count={1}' -f $n, $c
}
$atPrefix = ([regex]::Matches($t, 'click @e')).Count
$out += "missing=$miss at_prefixed_refs=$atPrefix"
$out += if ($miss -eq 0 -and $atPrefix -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D10-tester-browser.txt" -Encoding utf8
$out
```

**C11, stale status value**

```powershell
$files = @(
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\Architect.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\plan.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\Infra.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\build.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\analyst.md',
    'D:\Cloud\OneDrive\AI\Agentic\AGENTS.md',
    'D:\Cloud\OneDrive\AI\Agentic\avrig-ai\AGENTS.md'
)
$total = 0; $out = @()
foreach ($f in $files) {
    if (-not (Test-Path -LiteralPath $f)) { $out += "MISSING $f"; $total++; continue }
    $raw   = Get-Content -LiteralPath $f -Raw
    $yaml  = ([regex]::Matches($raw, 'status:\s*completed')).Count
    $tick  = ([regex]::Matches($raw, '`completed`')).Count
    $prose = ([regex]::Matches($raw, '(?i)completed (history|plans)')).Count
    $total += $yaml + $tick
    $out += '{0} status_value={1} backticked={2} prose_exempt={3}' -f (Split-Path $f -Leaf), $yaml, $tick, $prose
}
$out += "TOTAL stale_status_values=$total"
$out += if ($total -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D11-stale-status.txt" -Encoding utf8
$out
```

**C12, recorded default branch versus resolved default branch**

Implements the four step resolution contract rather than reading `origin/HEAD` alone, which is wrong in the Agentic repository where `origin/HEAD` reports `origin/main` but the only local branch is `master`.

```powershell
$repos = [ordered]@{
    'Agentic'  = 'D:\Cloud\OneDrive\AI\Agentic'
    'avrig-ai' = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ai'
    'avrig-api'= 'D:\Cloud\OneDrive\AI\Agentic\avrig-api'
    'avrig-lib'= 'D:\Cloud\OneDrive\AI\Agentic\avrig-lib'
    'avrig-ui' = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ui'
}
$recorded = @{ 'Agentic'='master'; 'avrig-ai'='main'; 'avrig-api'='main'; 'avrig-lib'='main'; 'avrig-ui'='main' }
$out = @(); $bad = 0
foreach ($k in $repos.Keys) {
    $p = $repos[$k]
    if (-not (Test-Path -LiteralPath $p)) { $out += "$k MISSING PATH"; $bad++; continue }

    $sym   = (& git -C $p symbolic-ref --short refs/remotes/origin/HEAD 2>$null)
    $remote = ($sym -replace '^origin/','')
    $locals = @(& git -C $p for-each-ref --format='%(refname:short)' refs/heads 2>$null)

    # four step contract
    $name = $null; $step = $null
    if ($locals.Count -eq 1) {
        $name = $locals[0]; $step = 'sole-local-branch'
        if ($remote -and $remote -ne $name) { $step = 'sole-local-branch (origin/HEAD disagrees)' }
    } elseif ($remote -and ($locals -contains $remote)) {
        $name = $remote; $step = 'origin-HEAD'
    } elseif ($remote) {
        $name = $null; $step = 'STOP remote-HEAD-has-no-local-branch'
    } else {
        $name = $null; $step = 'STOP unable-to-resolve'
    }

    $agree = ($name -ceq $recorded[$k])
    if (-not $agree) { $bad++ }
    $out += '{0} resolved={1} recorded={2} agree={3} step={4} origin_HEAD={5} local_branches={6}' -f `
        $k, $name, $recorded[$k], $agree, $step, $remote, ($locals -join ',')
}
$out += "disagreements=$bad"
$out += if ($bad -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "<rc>\D12-default-branch.txt" -Encoding utf8
$out
```

**C13, instruction manifest and backup siblings**

```powershell
$rc = '<rc>'
$files = @(
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\Architect.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\plan.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\Infra.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\build.md',
    'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\analyst.md',
    'D:\Cloud\OneDrive\AI\Agentic\AGENTS.md',
    'D:\Cloud\OneDrive\AI\Agentic\avrig-ai\AGENTS.md'
)
New-Item -ItemType Directory -Force -Path $rc | Out-Null
$rows = foreach ($f in $files) {
    if (Test-Path -LiteralPath $f) {
        '{0}  {1}' -f (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLowerInvariant(), $f
    } else { '{0}  {1}' -f ('MISSING').PadRight(64,'0'), $f }
}
$rows | Set-Content -LiteralPath "$rc\instruction-manifest.txt" -Encoding utf8
$ok = 0; $bad = 0; $out = @()
foreach ($ln in (Get-Content -LiteralPath "$rc\instruction-manifest.txt")) {
    if ($ln -match '^([0-9a-f]{64})\s+(.+)$') {
        $want = $Matches[1]; $fp = $Matches[2]
        $got = (Get-FileHash -LiteralPath $fp -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($got -eq $want) { $ok++ } else { $bad++; $out += "MISMATCH $fp" }
    } else { $bad++; $out += "UNPARSED $ln" }
}
$bak = (Get-ChildItem 'D:\Cloud\OneDrive\AI\Agentic\.opencode\agents' -Filter '*.bak-*' -File -ErrorAction SilentlyContinue).Count
$out += "manifest_ok=$ok manifest_bad=$bad backup_siblings=$bak"
$out += if ($ok -eq 8 -and $bad -eq 0 -and $bak -ge 6) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "$rc\D13-manifest-readback.txt" -Encoding utf8
$out
```

**C14, drift as a baseline delta**

Run the baseline before implementation and the after capture once edits land. The comparison subtracts the baseline, which is required because both repositories already carry drift this plan never caused.

```powershell
# Baseline, run BEFORE implementation
$rc = '<rc>'; $base = '<rc>\D14-baseline.txt'
'D:\Cloud\OneDrive\AI\Agentic','D:\Cloud\OneDrive\AI\Agentic\avrig-ai' | ForEach-Object {
    "=== $_ ==="
    & git -C $_ rev-parse --show-toplevel
    & git -C $_ diff --stat HEAD
} | Set-Content -LiteralPath $base -Encoding utf8
Get-Content -LiteralPath $base

# After capture, run AFTER implementation
$rc = '<rc>'
$repos = [ordered]@{ 'agentic'='D:\Cloud\OneDrive\AI\Agentic'; 'avrig-ai'='D:\Cloud\OneDrive\AI\Agentic\avrig-ai' }
foreach ($k in $repos.Keys) {
    $p = $repos[$k]
    & git -C $p rev-parse --show-toplevel | Set-Content -LiteralPath "$rc\D14-drift-$k.txt" -Encoding utf8
    & git -C $p diff --stat HEAD | Add-Content -LiteralPath "$rc\D14-drift-$k.txt" -Encoding utf8
}
$allowed = @('^plans/','^AGENTS\.md$','^\.gitignore$')
$out = @(); $bad = 0
foreach ($k in $repos.Keys) {
    $status = & git -C $repos[$k] status --porcelain 2>$null
    foreach ($ln in ($status | Where-Object { $_ -notmatch '^\?\?' })) {
        $path = $ln.Substring(3)
        $okPath = $false
        foreach ($a in $allowed) { if ($path -match $a) { $okPath = $true } }
        if (-not $okPath) { $bad++; $out += "OUTSIDE-EDIT-SET repo=$k path=$path" }
    }
}
$out += "outside_edit_set=$bad"
$out += 'NOTE: pre-existing drift is present in both repositories and must be matched against D14-baseline.txt'
$out += if ($bad -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
$out | Set-Content -LiteralPath "$rc\D14-drift-summary.txt" -Encoding utf8
$out
```

**C15, live browser journey**

Run from `D:\Cloud\OneDrive\AI\Agentic\test`, because the harness resolves `@playwright/test` only from that directory. Measured: the module fails to resolve from any other working directory, including with `NODE_PATH` set.

```powershell
$rc = '<rc>'
$js = "$env:TEMP\avrig-login-check.mjs"
@'
import { chromium } from '@playwright/test'
import fs from 'node:fs'
const out = process.argv[2]
const url = 'https://iam.avrig.ai/'
fs.mkdirSync(out, { recursive: true })
const browser = await chromium.launch()
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } })
const consoleErrors = [], failed = []
page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()) })
page.on('requestfailed', r => failed.push(r.url() + ' ' + (r.failure()?.errorText || '')))
const resp = await page.goto(url, { waitUntil: 'networkidle', timeout: 45000 })
const landingTitle = await page.title()
const accountVisible = await page.getByRole('button', { name: 'Account' }).isVisible()
await page.getByRole('button', { name: 'Account' }).click()
await page.waitForLoadState('networkidle')
await page.waitForTimeout(1500)
const formUrl = page.url()
const formTitle = await page.title()
const emailInputs = await page.locator('input[type=email], input[name=email]').count()
const pwInputs = await page.locator('input[type=password]').count()
await page.screenshot({ path: out + '/browser-login-1440x900.png', fullPage: true })
await page.setViewportSize({ width: 390, height: 844 })
await page.screenshot({ path: out + '/browser-login-390x844.png', fullPage: true })
const report = { url, httpStatus: resp ? resp.status() : null, landingTitle, accountVisible,
  formUrl, formTitle, emailInputs, pwInputs, consoleErrors, failed }
fs.writeFileSync(out + '/D15-browser-report.json', JSON.stringify(report, null, 2))
console.log(JSON.stringify(report, null, 2))
await browser.close()
'@ | Set-Content -LiteralPath $js -Encoding utf8

Push-Location 'D:\Cloud\OneDrive\AI\Agentic\test'
node $js $rc
$exit = $LASTEXITCODE
Pop-Location
Remove-Item -LiteralPath $js -Force
"node_exit=$exit"
```

The `wmux browser` leg, in the order the instruction mandates, recorded as BLOCKED when no caller surface exists:

```powershell
$wmux = 'C:\Program Files\wmux\wmux.exe'
# Precondition: WMUX_SURFACE_ID must be set, which happens only inside a wmux pane.
if (-not $env:WMUX_SURFACE_ID) {
    'BLOCKED: WMUX_SURFACE_ID is unset, so wmux has no caller surface. Observed: every'
    'wmux subcommand exits 0 with empty stdout and empty stderr from a plain session.'
    'Re-run inside a wmux pane, or pass an explicit caller surface.'
} else {
    & $wmux browser open 'https://iam.avrig.ai/'
    & $wmux browser snapshot           # must precede any ref-based action
    & $wmux browser screenshot --full
}
```

**C16, dash scan on the plan**

```powershell
$plan = '<plan>'
$raw = Get-Content -LiteralPath $plan -Raw
$out = @(
    'U+2014 em-dash = ' + ([regex]::Matches($raw, [char]0x2014)).Count,
    'U+2013 en-dash = ' + ([regex]::Matches($raw, [char]0x2013)).Count
)
$out | Set-Content -LiteralPath "<rc>\D16-dash-scan.txt" -Encoding utf8
$out
```

**C17, pre-branch reconciliation gate in the instruction text**

```powershell
$plan = '<plan>'; $rc = '<rc>'
$raw = Get-Content -LiteralPath $plan -Raw
$a = $raw.IndexOf('#### Exact replacement text, `Architect.md`')
$b = $raw.IndexOf('### Target Program Files (Mandatory)')
$out = @()
if ($a -lt 0 -or $b -le $a) {
    'RESULT FAIL region-not-found' | Set-Content -LiteralPath "<rc>\D17-pre-branch-reconcile.txt" -Encoding utf8
} else {
    $region = $raw.Substring($a, $b - $a)
    $checks = [ordered]@{
        'ancestor assertion on release tags' = 'merge-base --is-ancestor refs/tags/'
        'no-ff reconciliation merge'         = 'git merge --no-ff'
        'candidate merge prohibition'        = 'Never merge a candidate tag'
        'tag immutability prohibition'       = 'Never move, delete, or force'
        'stage 5 names reconciliation'       = 'Default Branch Reconciliation'
    }
    $fail = 0
    foreach ($k in $checks.Keys) {
        $present = $region.Contains($checks[$k])
        if (-not $present) { $fail++ }
        $out += '{0} present={1}' -f $k, $present
    }
    $out += "missing=$fail"
    $out += if ($fail -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL' }
    $out | Set-Content -LiteralPath "<rc>\D17-pre-branch-reconcile.txt" -Encoding utf8
}
$out
```

**C18, release tag ancestry against every default branch**

Enumerates release tags only. Candidate tags are excluded by construction, because the release regex cannot match a three segment ref.

```powershell
$rc = '<rc>'
$repos = [ordered]@{
    'avrig-ai' = @{ Path = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ai'; Default = 'main' }
    'avrig-api'= @{ Path = 'D:\Cloud\OneDrive\AI\Agentic\avrig-api'; Default = 'main' }
    'avrig-lib'= @{ Path = 'D:\Cloud\OneDrive\AI\Agentic\avrig-lib'; Default = 'main' }
    'avrig-ui' = @{ Path = 'D:\Cloud\OneDrive\AI\Agentic\avrig-ui'; Default = 'main' }
    'Agentic'  = @{ Path = 'D:\Cloud\OneDrive\AI\Agentic'; Default = 'master' }
}
$out = @(); $stranded = 0
foreach ($k in $repos.Keys) {
    $p = $repos[$k].Path; $d = $repos[$k].Default
    if (-not (Test-Path -LiteralPath $p)) { $out += "${k}: MISSING PATH"; continue }
    & git -C $p fetch origin --tags --prune --quiet 2>$null | Out-Null

    $tags = @(& git -C $p tag --list 2>$null) | Where-Object { $_ -match '^\d+\.\d+\.\d+$' }
    if ($tags.Count -eq 0) { $out += "${k} (${d}): no release tags, reconciled by definition"; continue }

    foreach ($t in $tags) {
        & git -C $p merge-base --is-ancestor "refs/tags/$t" "refs/heads/$d" 2>$null
        $ok = ($LASTEXITCODE -eq 0)
        if (-not $ok) { $stranded++ }
        $out += '{0} ({1}) release_tag={2} ancestor={3}' -f $k, $d, $t, $ok
    }
}
$out += "stranded_release_tags=$stranded"
$out += if ($stranded -eq 0) { 'RESULT PASS' } else { 'RESULT FAIL reconcile before branching' }
$out | Set-Content -LiteralPath "<rc>\D18-release-tag-ancestry.txt" -Encoding utf8
$out
```

### What the matrix already finds wrong

Run during authoring, so the plan inherits the defects rather than discovering them after a candidate tag. Findings 1, 2, 3 and 5 are closed in the current revision and the closure is recorded under `## Review Findings`, `Pass 5`. Finding 4 amended the drift outcome. Finding 6 is a correction to a pass criterion, not a defect in the plan.

1. **`D01` failed during authoring with exactly one hit, in the Orchestration Stages fence.** Fence 5 of the region contained `-m "avrig <X.Y.Z>"`, reproducing the literal tag message from `release.ps1`. It is a faithful quote of the tool, and it is also a hardcoded project name inside instruction text destined for `Architect.md`, which is exactly what B1 forbade for the taxonomy. **Closed:** the literal is now `<project-tag-message>`, with an instruction to reuse the publisher's message text for the project, so no project name ships. `D01` now reports 8 fences and 0 hits.
2. **`D12` failed during authoring, and this was the most consequential finding.** The mandated command `git symbolic-ref --short refs/remotes/origin/HEAD` returns `origin/main` in the Agentic repository while the plan records `master`. Local `main` does not exist there, `master` is 28 commits ahead of `origin/main`. **Closed by resolving it as a procedure rather than a single command:** a four step contract (tracking branch, then `origin/HEAD`, then the sole local branch when the two disagree, then stop and ask) is now the rule in decision 1, stage 1, and `C12`. Measured with the contract: Agentic resolves to `master` by the sole-local-branch step and records the disagreement, the four product repositories resolve to `main`, and `C12` reports 0 disagreements. No remote head is repointed and no local branch is created, because decision 1 forbids harmonizing defaults.
3. **`D11` failed during authoring with three values.** `Architect.md` line 84 and `plan.md` line 68 each carry a backticked `completed`, and `Infra.md` line 67 carries `status: completed`. Confirmed independently. **Open, by design:** this is implementation work owned by `be` at stream P5 and P8, and it stays a pass criterion rather than a plan edit, because the plan cannot write those files. Prose usages such as "completed history" are exempt and counted separately so the fix does not over-reach into legitimate English.
4. **`D14` could not be a diff-against-HEAD check.** The Agentic repository already carries 22 tracked modifications outside this plan's edit set, including `.obsidian/`, `.opencode/opencode.json`, eight `shared/skills/` paths, `service.json`, and three gitlink entries. `avrig-ai` already carries two modified plan files. **Closed:** the "No production drift" outcome is amended to a baseline delta, so pre-existing drift is subtracted rather than tolerated.
5. **`C01` counts eight fences, not six.** The replacement region holds six fences for `Architect.md` and two for `tester.md`. The audit row claiming "all six target fences scored 0" was wrong in both count and result once the tester block was added, and once the tag-message literal was present. **Closed:** the audit row and the evidence row now say eight, and the measured result is 8 fences, 0 hits.
6. **`D15` has a real friction point in the pass criteria.** The verified journey renders cleanly and zero requests failed, but the console reports a 401 and a 404 while the account chooser probes OIDC discovery before authentication. A naive "zero console errors" assertion fails on a healthy surface. The criterion is therefore zero failed requests plus every console error reconciled by name, which is checkable without pretending the two resource errors are absent.

### Report at the end of a run

One line per run, written to `plans/evidence/AVRIG-00001/rc.<NNN>/RESULT.txt` and reported to `build`:

```text
rc.<NNN> @ <commit SHA> | verdict PASS or FAIL | <n>/18 checks | evidence plans/evidence/AVRIG-00001/rc.<NNN>/
```

Rules that keep the line honest:

- The tag and the commit SHA come from `git rev-parse <code-lower>/<NNNNN>/rc.<NNN>^{commit}`, not from the working tree, because the working tree is not what was tested.
- `PASS` requires all 18 checks PASS. Any `BLOCKED` check makes the verdict `FAIL` unless this matrix explicitly permits that check to be blocked, which it does only for the `wmux` leg inside `D15`, and only while its Playwright leg is PASS and the blocker is recorded with its reason.
- A check that could not run is reported as `BLOCKED` with its reason, never as `PASS`.
- The verdict is reported to `build` and to no one else's authority: `tester` creates no tag, bumps no version, and pushes nothing.

## Review Findings

### Pass 1, audit of the universal indicator revision

Verdict: **not ready for stage 3**, 5 Blockers. All verified by execution against the repository or in a scratch git repository.

Method: all eight fenced instruction blocks in the replacement region were scanned for indicator literals; the shape regex and parse rules were executed against adversarial values; candidate tag case behaviour was tested in a scratch repo with `git check-ref-ignore` and `git check-ref-format`; the workspace inventory was taken with `git worktree list` and `git rev-parse --show-toplevel`; `release.ps1` was read for its staging, commit and tag sequence.

#### Blockers

**B1. The Identifier Taxonomy fence hardcoded the indicator five times.** The Example column read `AVRIG-00002` and similar, so "no hardcoded project code" failed on the mandated text itself. An agent authoring a plan for another project would copy the example rather than the abstraction. Closed: the Example column now uses a neutral `AAAAA` stand-in with an explicit note that it is not a real project's indicator, and measurable outcome 1 is restated to permit an Example column while describing the shape by regex.

**B2. Number allocation was not atomic, and merge-first did not make it atomic.** A worktree merge only synchronizes the view at that moment; it serializes nothing afterwards. Two checkouts could both read the same maximum and both claim the next number. Worse, the row was written at Stage 1 but the branch did not exist until Stage 4, so the reservation lived on an unpushed branch and was invisible to every other checkout. Confirmed reachable: `avrig-ai-gateway-oauth` had three plan files and no `PLAN-INDEX.md` at all. Closed: allocation now unions the remote tree via `git ls-tree origin/<default>`, the local tree, the archive, and all coded branch names; a mandatory recheck runs immediately before the row is written; the claiming branch is recorded in the row; and plan authoring is now a single sanctioned `docs(<CODE>-<NNNNN>)` commit on the default branch, which publishes the reservation.

**B3. Stage 1 wrote the plan with no legal home.** Stage 4 forbids plan commits on the default branch, yet Stage 1 had to write the files somewhere, so the rule set was unsatisfiable as ordered. It was already live: both new files sat untracked on `main`. A checkout that could not see the ledger also concluded "no ledger exists" and proposed a fresh indicator, which yields `AVRIGAIGAT` for the worktree. Closed: the authoring commit is now explicitly sanctioned on the default branch, and a linked worktree inherits its main checkout's indicator via `git rev-parse --git-common-dir`.

**B4. Stage 4's commands failed in the repository owning four of the eight target files.** The Agentic repo has no local `main`; the checkout is `master` while the remote carries both. Closed: verified and escalated to the user, then settled as resolved decision 1 (default branch differs per repository), and the stage now cuts a branch in every affected repository from that repository's own default branch.

**B5. "Release tag at the tested commit" could not be produced by `release.ps1`.** The script bumps manifests on the checked-out branch, commits, then tags HEAD, so the tagged commit always contains changes no candidate covered. Confirmed against history: tag `0.3.0` sits on a `chore(release)` commit whose diff is exactly the bump. Closed: bump on the plan branch, commit, cut and QA test one more candidate, merge, then release with `-SkipBump`, which reaches the existing-tag reuse path and never moves the tag.

#### Majors

- **M1. Filename parse was never specified, and the allocation wording permitted reading a number from the slug.** A loose digit scan on `migrate-to-20250-table` would return `20250` and jump the series permanently. Closed: anchored filename regex `^(?<date>\d{4}-\d{2}-\d{2})-(?<code>[A-Z][A-Z0-9]{1,9})-(?<num>\d{5})-(?<slug>.+)$` in the plan, the insert, and the ledger, with both a no-hyphen-split and a no-loose-scan prohibition and a hostile-name table.
- **M2. The parse rule alone accepted invalid indicators, and PowerShell `-match` is case insensitive.** `MY-PROJ-00001` and `avrig-00001` passed the parse rule; `-match` would accept lowercase silently. Closed: shape is now a stated precondition with case-sensitive matching required, and the uppercase-only alphabet is justified by the case-insensitive Windows file system.
- **M3. `plan.md` and `Infra.md` were omitted while global `AGENTS.md` pointed plan authoring at `plan.md`.** Closed: both added to the file table, and the `AGENTS.md` sentence is in the edit set.
- **M6. Test evidence had no writer, no permission grant, and no git policy.** `tester.md` declares no permissions, `plans/*` does not reach `plans/evidence/`, and `release.ps1` runs `git add -A` with no image or trace filter. Closed: permission block switched to `**` forms, evidence folder and `.gitignore` added to the file table, and retention carried into `## Remaining Open Clarifications` as "Test evidence retention".
- **M7. No duplicate assertion after write.** Closed: post-write re-read assertion added, with non-fast-forward push named as the expected race signal.
- **M8. The release tag was created before the merge, and nothing asserted main was still an ancestor.** Reproduced: with main unmoved the merge tree equals the candidate; with main advanced it does not. Closed: ancestry assertion `git merge-base --is-ancestor` added as a mandatory pre-merge gate, and the tag now follows the merge.
- **M9. Build id and candidate tag were not one to one.** Closed: every candidate carries its own build from the same commit, aligned by number, and the loop rebuilds.
- **M10. QA and UAT were used as gates but never defined, owned, or given a pass condition.** Closed: both defined in the design section and named in the state machine.
- **M11. No stream authored the test matrix.** Closed: stream P2b added, parallel to the analyst review, required before stage 4.
- **M12. The no-drift outcome could not be observed with one command.** Closed: restated per repository with absolute paths, naming both `AGENTS.md` files.
- **M13. Release scope contradicted the publisher, and no precondition required the default branch to be checked out.** Closed: carried into `## Remaining Open Clarifications` as "Release set scope", and the default-branch-plus-clean-tree precondition is now in stage 14 and in the policy.

#### Minors

m1 identifier count unified at six, with slice branch named as a subtype. m2 all en-dash connectors replaced with ASCII. m3 four `wmux` call forms corrected to ref-based `click`, `fill`, `wait <ref> <ms>`, and `screenshot [--full]` with no path. m4 the `WMUX_SURFACE_ID` and caller-surface precondition stated. m5 the stale `v` prefix question deleted as settled by the anchored regex. m6 the governance mirror question deleted as already mandated by the file table. m7 stage 7 given a not-applicable path. m8 file table corrected and ledger maintenance assigned to the Architect at every stage that records. m9 the undocumented `indicator_frozen` key replaced by `indicator_status`, and the alias table location named. m10 `release-version-decided` is now set by its own stage 12. m11 the ledger's loose allocation wording fixed. m12 the tester "serve the build from a tag" wording corrected, since a tag is not a servable location.

#### Confirmations

- **C1.** Candidate tags cannot be mistaken for a release. `avrig/00001/rc.001` does not match the anchored `$SemVerRegex`, so every validation path rejects it and `-SkipBump` fails fast. The namespaces are disjoint by construction.
- **C2.** `git merge --no-ff` yields a merge commit whose tree equals the candidate when the default branch has not moved. The model is correct; only the ordering and the ancestry guard were missing.
- **C3.** All Playwright harness commands cited exist in the `test` project and its Makefile.
- **C4.** Every target file row names exactly one owning assignee.
- **C5.** Eight of ten measurable conditions were checkable by inspection; the three that were not are closed above.
- **C6.** The uppercase work-item form and lowercase tag form are separated structurally (bare key versus three-segment ref) while deliberately sharing one number series, which is correct.
- **C7.** Case insensitivity of Git refs on this machine was verified in a scratch repo, so the lowercase tag rule is a real constraint rather than a preference.

### Pass 2 findings, and their disposition in this revision

1. **Indicator inherent to project identity.** Closed: the ledger now declares `project_indicator` per project, the instruction text uses placeholders only, and the taxonomy example column uses a neutral stand-in.
2. **Freeze must not precede user confirmation.** Closed: ledger records `pending-user-confirmation` and the plan frontmatter carries `indicator_status`.
3. **Derivation truncates mid-word and produces generic nouns.** Recorded, carried into `## Remaining Open Clarifications` as "Indicator derivation policy", with the recommendation to require the user to supply the indicator and never truncate inside a word.
4. **Worktree must inherit, not derive.** Closed: inheritance rule added, keyed off `git rev-parse --git-common-dir`.
5. **Release construction must be executable by the retained script.** Closed: the six step bump-on-branch sequence is written out, with the `-SkipBump` reuse path named.
6. **The release must run from the default branch.** Closed: precondition stated in stage 14 and in policy rule 13.
7. **Ancestry assertion before merge.** Closed: stage 13.
8. **Merge must precede the tag.** Closed: stage 13 then 14.
9. **A failed merge must not orphan a published tag.** Closed by the ordering above.
10. **QA and UAT must be defined.** Closed in the design section and the state machine.
11. **The test matrix needs an owner.** Closed: stream P2b.
12. **Evidence retention must be decided.** Carried into `## Remaining Open Clarifications` as "Test evidence retention".
13. **Untracked `.opencode/agents/` breaks the candidate tag premise.** Escalated to the user, then settled as resolved decision 2: the files stay local only, and the plan states that a candidate tag cannot cover them, with backup plus manifest as the mitigation. This finding was not in the pass 1 audit and was raised during pass 2 preparation.
14. **Stale untagged `0.4.0`.** Withdrawn: verified that all four repositories now tag `0.4.0` (`avrig-ai` `05413ed`, `avrig-api` `d153202`, `avrig-lib` `f26a285`, `avrig-ui` `c61d338`), so the manifests and tags agree and no gap exists.

### Pass 3, confirmation audit

Verdict at the time: not ready for `awaiting-approval`. Four checks were scoped: allocation atomicity, indicator leakage, release executability, and residual correctness. This is the third independent pass, and the plan text changed between passes, so each closure below was verified against `release.ps1` and the repositories rather than accepted from the disposition table.

| Check | Verdict then | Evidence |
|---|---|---|
| Allocation atomicity | STILL OPEN on one narrow point | Clauses b, c and d were present and the ledger carried a `Claiming branch` column, but the union read `origin/<default>` without a fetch. Proven in a fresh clone: a pushed plan stayed invisible to `git ls-tree origin/main -- plans/` until an explicit `git fetch` |
| No indicator leak | CLOSED | All eight target fences scored 0 for `(?i)avrig`, including the stage fence whose quoted tag message was replaced with `<project-tag-message>`; `AAAAA` appears five times as the permitted stand-in and no such project exists in the workspace |
| Release sequence | WRONG | `release.ps1` has no target-commit parameter, so `-SkipBump` with no pre-existing tag created `1.1.0` at HEAD. Reproduced: candidate `420ee5b`, merge `af5bed9`, same commit False, tree equal True |
| Residual, branch coverage | CLOSED | All three blockers are genuine user decisions; all four repositories tag `0.4.0` at the named SHAs |
| Residual, tree identity | STILL OPEN | Goal 8 demanded "the exact commit that passed" while stage 13 requires `--no-ff`, and a merge commit is never the candidate commit |

### Pass 4, closures applied after the confirmation audit

Two defects were code-bearing and are now closed in this revision.

**A4-B1. Allocation read a cached remote ref.** The union included `git ls-tree origin/<default>` but nothing refreshed that ref, so a plan pushed from another clone stayed invisible and its number could be reissued. Reproduced in a fresh clone: the pushed plan was absent from `ls-tree origin/main -- plans/` until `git fetch` ran. Closed: stage 1 and the allocation rule now require `git fetch origin <default>` immediately before the union read, and the fetch plus the recheck are one indivisible step.

**A4-B2. The release sequence could not place the tag on the tested commit.** `release.ps1` accepts only `$Target`, `$Message`, `$NoPush`, `$SkipBump`, `$Force`, `$Range` and `$RangeTag`, so it cannot target a commit, and its tagging line `git tag -a $new -m "avrig $new"` takes no commit argument. Reproduced end to end: candidate `420ee5b`, `--no-ff` merge `af5bed9`, so `same commit` is False while `tree equal` is True. Closed two ways: `build` now creates the annotated release tag by hand at the candidate SHA before invoking the publisher, which makes the script's existing-tag reuse path the one actually taken (verified against the script source: it checks `git tag --list $new`, prints "Tag $new already exists locally, reusing", and never uses `--force` on the reuse path), and every identity claim is now stated as tree equality rather than commit equality, because a `--no-ff` merge legitimately produces a new commit.

Also closed in the same pass:

- **A4-M1. Stale goal wording.** Goals 5 and 9 and the `Branch gate` measurable outcome still said branches were cut from `main`, contradicting stage 5's per-repository resolution. Now they name the repository's resolved default branch, with `main` only as the usual case.
- **A4-M2. Goal 8 contradicted stage 13.** Goal 8 now states tree identity on the merged default branch tip, matching the mechanics.
- **A4-M3. Duplicate paragraph** introduced when the file table was replaced. Removed.
- **A4-M4. Accumulated duplicate audit passes** at the end of this section, including one pass whose findings referenced an already superseded revision. Consolidated into this record so a reader is not asked to reconcile two contradictory verdicts.

### Current status of every check

| Requirement | Status | Where settled |
|---|---|---|
| Indicator is per project and never hardcoded | Closed | Indicator contract, taxonomy stand-in `AAAAA`, tested at zero leaks |
| Indicator frozen only after confirmation | Closed | Ledger `indicator_status: pending-user-confirmation` |
| Allocation is collision safe and indicator scoped | Closed | Union of four sources, fetch precondition, indicator filter, recheck, duplicate assertion, claiming-branch column |
| Filename parse is exact | Closed | Anchored regex, no hyphen split, no loose digit scan, hostile-name table |
| Analyst runs immediately after authoring | Closed | Stage 2, no intervening gate |
| Test matrix authored before approval | Closed | Stage 3 and stream P2b |
| Branch cut after approval, from the resolved default | Closed | Stage 5, goals 5, 9 and 12, per-repository resolution |
| Release tags reconciled before branching | Closed | Stage 5a, policy rules 13 to 15, goal 6, ledger pre-branch section, matrix `D17` and `D18` |
| Candidate tag exists before every test, fresh per fix | Closed | Stages 8 and 10 |
| Release artifact is the tested artifact | Closed | Bump on branch, candidate the bump, ancestry assertion, tree equality, hand-made tag, `-SkipBump` reuse |
| Live browser testing is mandatory | Closed | `tester.md` block with real `wmux` call forms and per-candidate evidence |
| Local-only files are verifiable | Closed | Backup plus SHA-256 instruction manifest, detectable risk stated |
| No em-dashes | Closed | Measured zero U+2014 and zero U+2013 in both plan files |

### Open items, all requiring the user

Nothing in this section is a defect. Four are confirmations and two are judgment calls with a stated recommendation.

1. Confirm the indicator `AVRIG` so the ledger can move from `pending-user-confirmation` to frozen.
2. Confirm that derivation is only a hint and the user always supplies the indicator.
3. Decide the test evidence retention policy.
4. Decide whether the release set stays all four repositories.
5. Decide the candidate tag namespace shape.
6. Decide whether to create the workspace indicator registry now.

Each has a recommended default in `## Remaining Open Clarifications`, and execution proceeds on the recommendation if the user does not object.

### Pass 5, test matrix authoring findings

The `tester` authored the matrix at stage 3 and executed every command rather than assuming, which surfaced four defects that the three analyst passes had missed.

**A5-B1. `origin/HEAD` is not the default branch, and following it would have failed outright.** Measured: in the Agentic repository `git symbolic-ref --short refs/remotes/origin/HEAD` returns `origin/main`, local `main` does not exist (`git rev-parse --verify --quiet main` exits 1), the only local branch is `master`, and `git rev-list --left-right --count master...origin/main` reports `28 0`. So the previously stated resolution rule would have resolved `main` and then failed at `git switch main` in the repository owning four of the eight target files, which is precisely the failure this plan exists to remove. Closed: decision 1 and stage 1 now use a four step resolution contract (tracking branch, then `origin/HEAD`, then the sole local branch when the two disagree, then stop and ask), the resolved name and the deciding step are recorded per repository, and the measured outcome for all five repositories is written down.

**A5-B2. The instruction text hardcoded a project name in a tag message.** Stage 14 contained `git tag -a <X.Y.Z> <sha> -m "avrig <X.Y.Z>"`, so the mandated text carried this project's name, which the plan's own first acceptance condition forbids. Closed: replaced with `<project-tag-message>`, with the instruction to reuse the publisher's message text for the project rather than inventing one.

**A5-B3. Indicator comparison was specified without a case sensitivity operator.** The allocation rule said the captured indicator "must equal the project's own" without naming an operator, and PowerShell `-eq` on strings is case insensitive by default, so a lowercase indicator would pass a rule whose shape regex forbids it. Closed: `-ceq` or `[string]::Equals(..., 'Ordinal')` is now named explicitly in both the plan and the ledger.

**A5-B4. Three stale `completed` status values remain in the live instruction files.** Found by executing the matrix command, not by inspection: `Architect.md` line 84, `plan.md` line 68, and `Infra.md` line 67. The file table already names all three files, so this is a scope confirmation rather than a new target, and it is now an explicit pass criterion in the matrix (`D11`).

Also corrected from the same run: `.secrets/test_token.json` is present but expired (1800 second lifetime, 113 minutes old), so the verification run must refresh it before any authenticated step rather than assuming it is valid.

### Pass 6, pre-branch reconciliation gate

Raised by the user before implementation, and it is a genuine gap in every earlier revision.

**A6-B1. Nothing guaranteed the plan branch was cut from a default branch containing released content.** Stage 5 previously said only `git pull --ff-only` then branch. That is insufficient: a release tag can exist on a commit that never reached the default branch, in which case the plan branch is cut from code that is missing shipped work, and every later candidate inherits the hole. Nothing in the plan asserted otherwise, so the defect was invisible until asked about directly.

Closed, with the distinction that matters. The gate reconciles **release tags only**:

- Enumerate bare `X.Y.Z` tags that match the release regex. Candidate tags (`<code-lower>/<NNNNN>/rc.<NNN>`) are excluded by construction, because a three segment ref cannot match an anchored SemVer pattern.
- Per tag, assert `git merge-base --is-ancestor refs/tags/<X.Y.Z> refs/heads/<default>`.
- If every tag is an ancestor, nothing is merged. If any is not, that released content is stranded, so merge it with `git merge --no-ff <X.Y.Z>` on the default branch and push, then branch.

Four prohibitions close the obvious ways this could go wrong: never merge a candidate tag into a default branch, since it is unapproved work that would bypass UAT and stage 14; never move, delete, or force a tag to make it an ancestor; never resolve a reconciliation conflict silently, because a conflict there means the default branch diverged from a shipped artifact; and never treat a failed fetch as an empty tag list, since `--tags --prune` must run first or the check reads stale refs.

Where it is now stated: stage 5 is split into 5a reconciliation and 5b branch creation, policy rules 13 to 15 cover the gate and both prohibitions, goal 6 states it, the branch gate measurable outcome requires it, the ledger carries a `## Pre-branch reconciliation` section, and the matrix adds `D17` (the rule is present in the instruction text) and `D18` (the rule passes against real state).

Measured on 2026-11-19 with `C18` executed: all sixteen release tags across `avrig-ai`, `avrig-api`, `avrig-lib` and `avrig-ui` (four each, `0.2.0` through `0.4.0`) are ancestors of `main`, the Agentic repository carries no SemVer tags, and `stranded_release_tags=0`. Every default branch is also in sync with its remote. So no reconciliation merge is required before this plan branches; the gate exists for the case where one is, and it now fails loudly instead of silently producing a stale base.

### Preserved audit evidence

Kept because it records what was executed rather than assumed, so the audit can be replayed.

| Claim | Method |
|---|---|
| No hardcoded indicator in instruction text | Extracted all eight fenced blocks between the Architect replacement text and the file table, counting `(?i)avrig` and `AAAAA` inside each fence |
| Shape regex behaviour | Executed `^[A-Z][A-Z0-9]{1,9}$` against eight adversarial values plus lengths 2, 10 and 11 |
| Filename parse | Executed the anchored regex, a final-hyphen split, and a loose digit scan against one real filename and three hostile slugs |
| Indicator filter | Executed an unfiltered and a project-filtered extraction over three filenames, one of which mentions a foreign code in its slug |
| Case handling | In a scratch repository, created `avrig/00001/rc.001` and resolved it as `AVRIG/00001/rc.001`, then ran `git check-ref-format` on the candidate shape |
| Tag and SemVer disjointness | Ran candidate names against the anchored `$SemVerRegex` in `release.ps1` and confirmed no match |
| Repository inventory | `git worktree list`, `git rev-parse --show-toplevel` per folder, and per-repository branch, tag and `plans/` presence |
| Release construction | Read `release.ps1` staging, commit and tag sequence, its parameter contract, and its existing-tag reuse branch |
| Release reproduces on the wrong commit | Built a scratch repository with a candidate and a `--no-ff` merge, then compared commit identity and tree identity |
| Merge tree equality | Reproduced in three cases: default branch unmoved, advanced without resync, and resync then merge |
| Ancestry assertion | Verified `git merge-base --is-ancestor` exits 1 exactly when the default branch is not an ancestor of the candidate |
| Release tag ancestry | Ran the `D18` body across all repositories: enumerated bare `X.Y.Z` tags only, asserted each against its default branch, and confirmed the candidate namespace cannot match the release filter |
| Default branch staleness | Compared each local default branch with its `origin` counterpart after a fetch: all five repositories in sync, and `git rev-list --left-right --count` reports no divergence |
| Fetch precondition | In a fresh clone, confirmed a pushed plan was invisible to `git ls-tree origin/main -- plans/` until `git fetch` ran |

### Judgment on the indicator derivation rule

Applied to this workspace's real folder names, deriving an indicator by uppercasing, stripping non alphanumerics, and truncating to ten produces:

| Folder | Proposal | Assessment |
|---|---|---|
| `avrig-ai` | `AVRIGAI` | Acceptable, though the natural answer is `AVRIG` |
| `avrig-api` | `AVRIGAPI` | Visually confusable with `AVRIGAI` |
| `avrig-lib` | `AVRIGLIB` | Visually confusable |
| `avrig-ui` | `AVRIGUI` | Visually confusable |
| `avrig-ai-gateway-oauth` | `AVRIGAIGAT` | Unacceptable: mid-word truncation of GATEWAY, and it is a worktree so it must inherit `AVRIG` regardless |
| `api` | `API` | Weak, a generic English noun |
| `web` | `WEB` | Weak, and ambiguous against `avrig-ui`, also a frontend |
| `TripoSR` | `TRIPOSR` | Pointless, a vendored upstream repository with no reason to join plan governance |

Verdict: derivation is a defensible hint and an unacceptable default. Three named failures: truncation cutting a word in half, four near-identical prefixes sharing a five character stem under a permanent freeze with no renumber policy, and generic nouns passing the regex while remaining bad identifiers. The regex is necessary and not sufficient. `api`, `web` and `TripoSR` also carry no `plans/` folder, so they have no reason to acquire an indicator until they adopt plans.


