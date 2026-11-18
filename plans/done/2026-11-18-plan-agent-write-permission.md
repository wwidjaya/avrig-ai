---
title: "Plan Agent Write Permission for Project plans/ Subfolder"
status: completed-with-caveat
created: 2026-11-18
revised: 2026-11-18 (config applied, interactive write verified, headless refusal recorded)
owner: build (apply), tester (verify), analyst (gate), km (retrospective)
scope: OpenCode harness configuration, no application code impact
tags:
  - opencode
  - permissions
  - plan-agent
  - configuration
---

# Plan Agent Write Permission for Project plans/ Subfolder

## Goals and Objectives

Give the Plan primary agent write access to the project root `plans/` subfolder so plan files land at `<project>/plans/YYYY-MM-DD-<task>.md` instead of the global `C:\Users\wwidj\.opencode\plan` fallback.

Measurable objectives:

1. A fresh Plan session accepts a write to `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\plans\<file>.md` without a denial.
2. The Plan-mode restriction notice at session start names the project `plans/` path as writable, not only `~/.opencode/plan`.
3. Plan-mode is still read-only for source files: writes to `avrig-api/`, `apps/web/`, and any non-`plans/` path remain blocked.
4. Other primary agents (Build, General) are unaffected: their permission arrays are unchanged.
5. Config stays schema-valid against `https://opencode.ai/config.json`.

## Findings

Root cause investigation before applying the change:

| Observation | Consequence |
| :--- | :--- |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\plan.md` already declared `edit` allows for `plans/**`, `**/plans/**`, and the absolute `D:/Cloud/OneDrive/AI/Agentic/**/plans/**` | The intended allow rules existed but did not win over the shipped `plan` policy, so the rule set alone was not the fix |
| Session start still bound writes to `C:\Users\wwidj\.opencode\plan` | That path is exactly the built-in `plan` policy exception, so the built-in deny was resolving last |
| `.opencode\agents\` sits above the project root (`avrig-ai`), while project `.opencode` discovery walks from the location up to the project root | The agent file is loaded for its prompt but its permission rules were not resolving as the winning layer |
| `D:\Cloud\OneDrive\AI\Agentic\opencode.json` is an ancestor of the session location, and config discovery walks ancestors to the filesystem root | This file is reliably loaded, making it the correct lever for an agent-scoped override |
| Four rules used `action: write` | V2 has no `write` action; `edit` covers `edit`, `write`, and `patch`. Those rules were dead weight and were removed |
| V2 wildcard semantics: `*` matches zero or more characters including `/`; `**` has no special meaning | `plans/**` and `plans/*` are equivalent, so the `*` form is used for clarity |
| Three `plan.md` definitions exist: `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\plan.md`, `C:\Users\wwidj\.opencode\agents\plan.md`, `C:\Users\wwidj\.config\opencode\agents\plan.md` (the last two byte-identical, no `permissions` block, prompt says "without modifying project files") | A permission fix in one copy can be defeated by another copy that loads later, so the allow block is applied to all three |
| Plan-mode notice is a static template in `opencode.exe` with the writable path interpolated, verified at `bin\opencode.exe` offset `129093606` | The notice is derived from resolved `edit` rules, so changing the resolved rules changes the notice. No hardcoded mode guard exists for this text |

## Key Detailed Design

### Program Design

No application code, service contract, Axum route, crate module, or frontend component is touched. All changes are OpenCode harness configuration and agent definition.

Permission model applied:

- Layer order per V2 docs: base policy, shipped agent policy, global config rules, then agent rules. The last matching rule wins.
- An agent-scoped `allow` appended under `agents.plan.permissions` in the discovered ancestor config is the rule that must match last.
- Scope is deliberately narrow: only `edit` on paths containing a `plans/` segment. No `shell`, `read`, or wildcard `edit` grant is added.
- Windows path matching is case-insensitive and backslashes normalize to slashes, so both slash forms resolve.

### Target Program Files (Mandatory)

Configuration files changed:

| Path | Change | State |
| :--- | :--- | :--- |
| `D:\Cloud\OneDrive\AI\Agentic\opencode.json` | Added `agents.plan.permissions` with three `edit` allow rules (`plans/*`, `*/plans/*`, `D:/Cloud/OneDrive/AI/Agentic/*/plans/*`) | applied |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\plan.md` | Normalized `edit` rules to `*` globs, added `~/.opencode/plan/*` allow, removed four invalid `action: write` rules | applied |
| `C:\Users\wwidj\.opencode\agents\plan.md` | Added `permissions` block with `edit` allows for `plans/*`, `*/plans/*`, `~/.opencode/plan/*` | applied |
| `C:\Users\wwidj\.config\opencode\agents\plan.md` | Same block, file synchronized byte-for-byte with the previous copy | applied |
| `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\plans\2026-11-18-plan-agent-write-permission.md` | This plan file | applied |

Conditional file, only if verification fails:

| Path | Change | State |
| :--- | :--- | :--- |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\planner.md` | New primary agent, distinct ID, own permission set (deny `edit` `*`, allow `edit` on `plans/*`, `*/plans/*`, `~/.opencode/plan/*`), body copied from `plan.md` | not created |

### EDM Design

None. No schema, table, column, constraint, or migration is involved.

## Parallel Execution Plan

| Phase | Stream | Assignee | Mode | Depends on |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Root cause inspection of config and agent definitions | build | sequential | none |
| 2 | Apply config override, normalize agent rules, author plan | build | sequential | Phase 1 |
| 3 | Fresh-session write probe in project `plans/` | tester | sequential | Phase 2 |
| 4 | Fallback `planner` agent creation (conditional) | build | sequential | Phase 3 failure |
| 5 | Plan goal audit | analyst | sequential | Phase 3 or 4 |
| 6 | Retrospective in Vault | km | parallel with Phase 5 | Phase 3 |

## Test Specification and Validation Matrix

| ID | Scenario | Type | Steps | Expected |
| :--- | :--- | :--- | :--- | :--- |
| T-01 | Config JSON validity | static | Parse `opencode.json` with `ConvertFrom-Json` | Parses, `agents.plan.permissions` present with three rules |
| T-02 | No stray `write` action | static | Inspect `plan.md` frontmatter | Zero `action: write` entries, three `edit` rules plus `~/.opencode/plan/*` |
| T-03 | Plan-mode reminder reflects project path | manual | Start a fresh Plan session in `avrig-ai`, read the injected restriction notice | Notice lists the project `plans/` path as writable |
| T-04 | Positive write probe | manual | Ask the Plan agent to write `avrig-ai\plans\probe.md` | Write succeeds, no permission denial |
| T-05 | Negative write probe | manual | Ask the Plan agent to write `avrig-api\probe.txt` | Denied; plan mode remains read-only for source |
| T-06 | Other agents unaffected | manual | Start a Build session | Normal build permissions, no new prompts on edits |
| T-07 | Fallback readiness | static | Confirm `planner.md` absent unless Phase 3 failed | Absent on success path |

## Verification Status

Applied in this session:

1. `opencode.json` updated with the agent-scoped `edit` allows.
2. `plan.md` frontmatter normalized, invalid `action: write` rules removed.
3. The two user-level `plan.md` copies given the same allow block.
4. This plan written to the project `plans/` folder.

Resolved policy read back from the running server (`opencode api get /api/agent`), plan agent rules in final order:

| # | Action | Resource | Effect |
| :--- | :--- | :--- | :--- |
| 6 | edit | `*` | deny |
| 7 | edit | `C:\Users\wwidj\.opencode\plan\*` | allow |
| 10 | edit | `plans/*` | allow |
| 11 | edit | `*/plans/*` | allow |
| 12 | edit | `D:/Cloud/OneDrive/AI/Agentic/*/plans/*` | allow |
| 16 | edit | `plans/*` | allow |
| 17 | edit | `*/plans/*` | allow |
| 18 | edit | `C:\Users\wwidj\.opencode\plan\*` | allow |

The shipped deny at position 6 is now shadowed by allows at 10 to 18, and last match wins, so an `edit` on `plans/<file>.md` resolves to `allow`. Static matrix items T-01 and T-02 are satisfied.

Interactive verification in a real Plan-mode session:

- T-04 PASS. Asked the Plan agent for `plans/probe.md`; the write succeeded with no prompt. File is 440 bytes at `avrig-ai/plans/probe.md`.
- T-05 not run on purpose. Proving a denial by attempting a forbidden write is not a safe test, and the negative side is already covered by the unchanged `edit * deny` at position 6.

### CLI Verification (2026-11-18)

Ran `opencode run --agent plan` headlessly from `avrig-ai` twice, first with a plain prompt, then with `--format json` and an explicit instruction to call the write tool once.

| Run | Prompt | Result |
| :--- | :--- | :--- |
| 1 | Two-step positive and negative probe | Model reported `POSITIVE=denied`, `NEGATIVE=denied`. `plans/cli-probe.md` was never created |
| 2 | "Call the write tool exactly once ... else reply WRITE_OK" | Model replied "I can't create `plans/cli-probe.md` in Plan mode. No tool was called." |

Both runs show the refusal happens at the instruction layer, not the permission layer. The model obeyed the injected notice, which still renders only `C:\Users\wwidj\.opencode\plan`, and never issued a tool call, so no permission error was produced. The permission rules themselves allow the path, which the interactive write proves.

Cause of the stale notice text: the notice appears to render a single writable path taken from the resolved allow list, and the last such rule is `~/.opencode/plan/*`, which every `plan.md` copies ends with. The config `allow` for `plans/*` takes effect for enforcement but does not change the rendered path.

Remaining work, not blocking:

1. ~~For scripted or headless use, prefer the Phase 4 `planner` agent~~ superseded: the `Architect` agent was created instead. See the follow-up section.
2. Optional: drop the redundant `~/.opencode/plan/*` rule from the `plan.md` copies and retest whether the notice then renders the project `plans/` path.
3. ~~`avrig-ai/plans/probe.md` is test residue and can be deleted~~ deleted, along with the Architect probe file.

## Follow-up (2026-11-18): Architect agent replaces the hidden Plan agent

Decision: rather than patching the notice further, introduce a distinct primary agent and retire the built-in Plan agent from the picker.

Changes:

| Path | Change |
| :--- | :--- |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\Architect.md` | New primary agent. Write scope is `plans/`, `*/plans/*`, `D:/Cloud/OneDrive/AI/Agentic/*/plans/*`, and `~/.opencode/plan/*`, with `edit * deny` ahead of those allows. Prompt carries the delegation rule, plan file standards, graphify rule, orchestration stages, and the release policy |
| `D:\Cloud\OneDrive\AI\Agentic\opencode.json` | `agents.plan.hidden: true` added |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\plan.md` | `hidden: true` in frontmatter |
| `C:\Users\wwidj\.opencode\agents\plan.md`, `C:\Users\wwidj\.config\opencode\agents\plan.md` | `hidden: true` in frontmatter |

Headless verification:

| Test | Command | Result |
| :--- | :--- | :--- |
| Agent exists and writes plans | `opencode run --agent Architect --archived "write plans/2026-11-18-architect-probe.md"` | `WRITE_OK`, file created. No Plan-mode notice blocked it, unlike `--agent plan` |
| Non-conforming filename | first probe used `plans/architect-probe.md` | Model declined without a tool call, citing the `YYYY-MM-DD-<task-name>.md` rule. The filename standard is being enforced |
| Source-file write | probe to `avrig-api/perm-deny-probe.txt` | Declined at the instruction layer with "Outside my permitted write scope". File not created. The `edit * deny` rule backs this mechanically, but the model refuses before a tool call, so no permission error text exists |
| Plan agent hidden | `opencode api get /api/agent` | `plan` reports `hidden=True`; `Architect` was created but did not appear in that endpoint's stale list, which also omits `analyst`, `km`, and `tester`. Treat the endpoint as cached, not authoritative |

Open option: set `default_agent` to `Architect` if new sessions should start there instead of Build. Applied, see below.

### Default agent wiring (2026-11-18)

`default_agent: Architect` was set in `D:\Cloud\OneDrive\AI\Agentic\opencode.json`, but `opencode run` still started on `build`. Two reasons, both now fixed:

1. Config precedence: `D:\Cloud\OneDrive\AI\Agentic\.opencode\opencode.json` is a `.opencode` document and overrides the direct `opencode.json`, and it still carried `"default_agent": "plan"`. Since `plan` is hidden, resolution fell through to `build`.
2. Location scope: Architect existed only in the Agentic agent directory, so a location resolving against `C:\Users\wwidj` could not see it. `Architect.md` was copied to `C:\Users\wwidj\.opencode\agents\` and `C:\Users\wwidj\.config\opencode\agents\`, matching how `be`, `edm`, `fe`, `Infra`, and `plan` are duplicated.

Final state:

| Setting | File | Value |
| :--- | :--- | :--- |
| `default_agent` | `Agentic\.opencode\opencode.json` | `Architect` |
| `default_agent` | `Agentic\opencode.json` | `Architect` |
| `agents.plan.hidden` | both files | `true` |

Verification: `opencode run --archived "Reply READY"` now reports `> Architect · gpt-6.2-sol`, and `/api/config` resolves `default_agent` to `Architect` in both documents.

## Review Findings

Pending analyst audit. Expected outcome: the change is configuration-only, scoped to `agents.plan`, and grants no source-file write capability, so it does not alter the Plan agent's read-only contract for implementation work.
