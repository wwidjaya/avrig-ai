# AGENTS.md

## Project Documentation & Knowledge Base

Project specifications, architecture designs, and discovery research for **avrig-ai** are maintained in the central Obsidian Vault rather than inside this repository:

- **Vault Project Path:** `D:\Cloud\OneDrive\AI\Personal\vault\02-projects\avrig-ai\`
- **Project Index:** `02-projects/avrig-ai/_index.md`
- **System Architecture:** `02-projects/avrig-ai/design/System-Architecture.md`
- **Technology Architecture:** `02-projects/avrig-ai/design/Technology-Architecture.md`
- **Knowledge Management (`[KM]`):** `02-projects/avrig-ai/design/Knowledge-Management.md`
- **Dev Infrastructure Baseline:** `02-projects/avrig-ai/infra/Infrastructure.md`
- **Task Plans & Workflows:** `plans/` (Active project-root plans) and `plans/done/` (Completed/archived plans)
- **Discovery & Capability Baselines:** `02-projects/avrig-ai/discovery/`

## Environment & Directories

The OpenCode configuration directory is located at `$env:OPENCODE_CONFIG_DIR` (`D:\Cloud\OneDrive\AI\Agentic`). Global and shared OpenCode artifacts such as `.opencode/` definitions, agents, skills, and configuration are anchored to this directory.

## Project Guidelines

1. **Authoritative Architecture Source:** Always consult the design and discovery documents in the Vault path above when designing or implementing SDLC, Office OS, or harness features.
2. **Writing & Modification Rules:** When creating or editing notes within the Vault, adhere strictly to the `write-vault` skill guidelines:
   - Include valid YAML frontmatter.
   - Maintain a single `#` H1 heading matching the frontmatter title verbatim.
   - Do not use em-dashes (replace with colons, commas, or parentheses).
   - Enclose `---` section separators in blank lines.
   - Normalize paragraph flow and escape markdown table pipes (`\|`).
3. **Subagent Delegation & Planning:** Follow the global subagent delegation policy (`edm`, `Infra`, `fe`, `be`, `tester`, `analyst`, `km`, `explore`). Primary agents must strictly delegate implementation, exploration, testing, and infrastructure work to their dedicated subagents rather than performing domain tasks directly. Follow the plan workflow in `$env:OPENCODE_CONFIG_DIR/.opencode/agents/Architect.md`, which owns plan identity, numbering, branches, candidate tags, and releases. Where `.opencode/agents/plan.md` differs, it is superseded and must not be treated as the workflow authority.
   - **Infra Agent Specialization**: Owns development infrastructure, systemd services (`avrig.service`, `rauthy.service`, `vault.service`), reverse proxy configurations, and IAM management via the `manage-rauthy` and `manage-nginx` skills.
4. **Build & Deployment Standards (Dual Windows & Linux ELF):**
   - The unified runtime service builds both a Windows PE binary (`avrig.exe`) and a Linux ELF binary (`avrig`) embedding `apps/web/dist`.
   - Always run `make build` in `avrig-api` to compile both targets with fresh frontend assets.
   - Run `make deploy` in `avrig-api` to deploy to both Windows (`D:\avrig\`) and Linux/WSL (`/opt/avrig/avrig`).
5. **Codebase Exploration & Knowledge Graph (graphify > grep):**
   - **MANDATORY:** Always use `graphify` (`D:\miniconda3\envs\kb\Scripts\graphify.exe query "<question>"`) or dispatch the `explore` subagent (`agent: "explore"`) to inspect and understand codebase structures, components, functions, and cross-module relationships.
   - Recursive or directory-wide `grep` searches for exploration or discovery are strictly prohibited across all subagents.
5. **Testing & Token Cache Workflow:**
   - Active plans must specify clear, measurable `## Goals and Objectives`.
   - `tester` subagent must check or prepare `.secrets/test_token.json` before running authenticated test suites across iterations.
   - At the conclusion of a verification session, `tester` asks the `analyst` subagent to audit achievement of the plan's goals and record findings under `## Review Findings`.
6. **Release & Versioning Policy (Mandatory):** the authoritative rules are the 28 numbered rules under `## Release Versioning Policy` below, and that list wins wherever this summary appears to disagree with it.
   - **Bump mechanics:** run `make bump-version VERSION=<X.Y.Z>` in `avrig-ai`, and commit the bump on the plan branch rather than on the default branch. The bump is itself candidate tested before the merge, so the released tree is a tested tree. `scripts/release.ps1` validates SemVer 2.0, synchronizes `avrig-ai/Cargo.toml`, `avrig-ai/apps/web/package.json`, and `avrig-api/Cargo.toml`, and refreshes both lockfiles.
   - **Tag and publish:** create the release tag by hand at the merged default branch tip whose tree equals the passing candidate, then run `scripts/release.ps1 <X.Y.Z> -SkipBump` with the default branch checked out and the tree clean. The four-repository publish rule applies: `avrig-ai`, `avrig-api`, `avrig-lib`, and `avrig-ui` each receive the tag `X.Y.Z` (no `v` prefix, no build metadata) and the branch push, including a repository with no pending change.
   - **Verification:** confirm `git ls-remote --tags origin` lists `X.Y.Z` in all four repositories and report the commit SHA, tag, and branch per repository.
   - The `build` subagent orchestrates bump, tag, and push. `tester` reports the passing candidate tag and its commit SHA, recommends the increment from content, and creates no tag.

## Plan Identity and Indicator

Every plan in this project carries a work-item key shaped `<CODE>-<NNNNN>`, where `<CODE>` is the project indicator `AVRIG` and `<NNNNN>` a five digit zero padded running number starting at `00001`. So `AVRIG-00001` is the first work item of this project.

This project declares its indicator once, in the frontmatter of `plans/PLAN-INDEX.md`, as `project_indicator: AVRIG`. The ledger is the source of truth, and the declaration is frozen once the user confirms it.

- Shape: `^[A-Z][A-Z0-9]{1,9}$`. Two to ten characters, the first character a letter, no hyphens, no spaces, uppercase only. Uppercase is a requirement rather than a preference: the Windows file system is case insensitive, so a mixed-case indicator would collide with its own uppercase form and the ledger would silently lose a row.
- Declared once per project: the indicator lives in the ledger frontmatter, and one indicator owns one independent number series.
- Proposed, then confirmed, then frozen: a proposed indicator is presented to the user and written only after the user confirms it. A later change requires an alias table mapping every old code to its new code, and existing filenames keep their original code.
- Unique per project: no other project may share `AVRIG`, and this project must not adopt another project's indicator.
- Never hardcoded in instructions: agent definitions, instruction files, and shared configuration name the shape and the ledger field, never a project's actual indicator. `AVRIG` appears here because this is the project's own file, alongside the ledger and its plans.
- Parse by token, never by split: extract the code with `([A-Z][A-Z0-9]{1,9})-([0-9]{5})` and require the captured indicator to equal `AVRIG` by case sensitive comparison. Never split a filename at a hyphen, and never scan for any five digit run, because a slug can contain a number that would jump the series permanently.
- A filename with no matching token contributes nothing to allocation. It is never treated as number zero.
- Numbers are permanent: a number is never reused, renumbered, or reclaimed, including for an abandoned, superseded, or archived plan.
- Allocation is filtered to `AVRIG` and unioned across the fetched remote tree, the local plans folder, `plans/done/`, and all coded branch names, with a recheck immediately before the row is written and a uniqueness assertion after it.
- A linked worktree of this repository inherits `AVRIG` from its main checkout and never proposes its own.

## Identifier Taxonomy

Six identifiers exist in this project and must never be conflated.

| Identifier | Shape | Example | Owner |
|---|---|---|---|
| Work item | `<CODE>-<NNNNN>` | `AVRIG-00002` | Architect |
| Branch | `<type>/<CODE>-<NNNNN>` | `feature/AVRIG-00002` | build |
| Slice branch | `<type>/<CODE>-<NNNNN>-<slice>` | `feature/AVRIG-00002-reporting` | be, fe |
| Build id | `<CODE>-<NNNNN>-build.<NNN>` | `AVRIG-00002-build.003` | build, artifact space only, never a Git tag |
| Candidate tag | `<code-lower>/<NNNNN>/rc.<NNN>` | `avrig/00002/rc.002` | build |
| Release tag | `X.Y.Z` | `1.1.0` | build |

`<type>` is one of `feature`, `fix`, `chore`, `docs`, `refactor`, `perf`. A slice branch is a branch subtype, not a seventh identifier.

- A work-item code identifies work. It never implies a SemVer and never reserves one. `AVRIG-00002` does not mean `1.1.0` and does not reserve it.
- A version is assigned only when a release is approved, from what the change contains: `major` for breaking, `minor` for backward-compatible functionality, `patch` for backward-compatible fixes.
- Build ids live in the artifact folder or the CI artifact space. Do not create a Git tag for every development build.
- Every candidate tag carries its own build, cut from the same commit, with `build.<NNN>` aligned to `rc.<NNN>`. The artifact promoted to production is the build belonging to the passing candidate.
- Candidate tags are lowercase, because Git refs are case insensitive on Windows file systems. `AVRIG` is uppercased in work items and lowercased as `avrig` in tags, both derived from the one declared value.
- Release tags are bare `X.Y.Z`, with no `v` prefix and no build metadata.
- One commit can carry several identifiers, but only one release version.
- Every release is traceable to its work item, branch, candidate tag, commit SHA, build id, test evidence folder, UAT approval, and deployed artifact.

## Branch, Candidate Tag, and Reconciliation Gates

**Default branch is per repository.** Never assume `main`. This project's default branch is `main`, but the rule is a resolution, not an assumption, because other repositories in the workspace differ. Resolve the default branch separately in every repository with this contract, and record the resolved name plus the deciding step in the plan:

1. If the current branch tracks a remote and is the repository's only long-lived branch, it is the default.
2. Else read `git symbolic-ref --short refs/remotes/origin/HEAD` and strip the remote prefix from the result.
3. If that name exists as a local branch, it is the default.
4. Else if exactly one local branch exists, that branch is the default, and the `origin/HEAD` disagreement is recorded in the plan.
5. Else stop and ask the user. Never guess.

`avrig-ai`, `avrig-api`, `avrig-lib`, and `avrig-ui` resolve to `main` by step 3. The Agentic configuration repository resolves by step 4 to `master`, because its `origin/HEAD` advertises `origin/main` while no local `main` exists.

**Pre-branch reconciliation gate.** A plan branch is cut only from a default branch that already contains every released artifact.

- In every repository the plan touches, run `git fetch origin --tags --prune` before checking anything. A failed fetch is not an empty tag list.
- Enumerate release tags only: bare `X.Y.Z` that match the release pattern. Never enumerate a candidate tag.
- Per release tag, assert `git merge-base --is-ancestor refs/tags/<X.Y.Z> refs/heads/<default>`. A tag that is not an ancestor is stranded released content, so merge it with `git merge --no-ff <X.Y.Z>` on the default branch and push before branching.
- Never merge a candidate tag into a default branch. A candidate is unapproved work, and merging it would bypass UAT and the release path.
- Never move, delete, or force a tag to make it an ancestor. If reconciliation would rewrite released history, stop and escalate to the user.
- If a reconciliation merge conflicts, stop and escalate rather than resolving silently, because a conflict there means the default branch diverged from a shipped artifact.
- Record every repository, every release tag tested, and every merge performed in the plan.
- Cut the branch only after explicit user approval, in the pattern `<type>/<CODE>-<NNNNN>`, in every affected repository, then push it with upstream tracking. All implementation and all fixes happen on that branch. The default branch receives no implementation commits.

**Candidate tag gate.** A test run never starts against an untagged tree.

- Before the first test run, create the annotated candidate tag `<code-lower>/<NNNNN>/rc.<NNN>`, starting at `rc.001`, on the plan branch head, and push it. Record the tag, its commit SHA, and its build id in the plan's `candidate_tags` list and in the ledger.
- The tester resolves the tag to a commit and tests exactly that commit, never the working tree. A tag is a commit reference, not a servable location.
- On every fix, rebuild and create the next candidate, incrementing `rc.<NNN>`. A green run on an older tag is never a pass for a newer tree.
- Candidate tags are immutable. Never move, delete, reuse, or force push one.
- If `main` advanced because another plan released, merge it into the plan branch, resolve conflicts there, rebuild, and cut a fresh candidate. A candidate cut before that merge cannot be the release candidate.
- Evidence lives under `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/`, keyed by the same candidate number, so a result is always traceable to the tree it describes.

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

The four-repository publish rule sits on top of those rules: a release reaches `avrig-ai`, `avrig-api`, `avrig-lib`, and `avrig-ui`, each receiving the annotated tag `X.Y.Z` and the branch push, including a repository that carries no pending change. Filtering the release set is out of scope, so the policy and `scripts/release.ps1` agree rather than diverge.
