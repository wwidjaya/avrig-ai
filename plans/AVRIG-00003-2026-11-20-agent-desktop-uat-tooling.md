---
title: Agent-Desktop as the Desktop UAT Harness for the Tester Agent
plan_id: AVRIG-00003
project_indicator: AVRIG
branch: chore/AVRIG-00003-agent-desktop-uat-tooling
candidate_tags:
  - "avrig/00003/rc.001 @ 68520e980a10a220fed78b7a86b6ba36e63e0e36 (AVRIG-00003-build.001)"
release_version:
status: testing
created: 2026-11-20
owner: Architect
tags:
  - tooling
  - testing
  - uat
  - agent-config
  - windows
---

# Agent-Desktop as the Desktop UAT Harness for the Tester Agent

## Goals and Objectives

The tester agent can verify a browser surface and cannot verify a native window. `agent-desktop` closes that gap, so UAT covers the two desktop surfaces this project ships.

1. `agent-desktop` resolves from a plain `pwsh` session on this host, with every path `where.exe agent-desktop` prints sitting inside `d:\nodejs\.npm\global` (the extensionless shim, the `.cmd`, and the `.ps1`, matching `agent-browser`, with the count recorded rather than asserted), and it reports `version` and `status` with `ok: true` and serves its bundled `desktop` and `platform` guides.
2. A real observe, act, verify loop completes against one live application named in the matrix (Notepad is the default choice, and any other application needs the user's permission), and produces a snapshot, an action, a second snapshot, and a screenshot, with every envelope saved as evidence.
3. `.opencode/agents/tester.md` carries an executable Desktop UAT contract: when it applies, the exact call forms, the ref lifecycle rules, the secret-handling rule, the evidence layout, and the not-applicable path. A tester reading only that file can run the loop without reading this plan.
4. The existing web path is unchanged. Playwright remains the harness for `apps/web` and the SSO journey, and a plan that touches both a browser surface and a desktop surface requires both harnesses, not one replacing the other.
5. No product source, schema, migration, or build configuration changes. The diff is one agent definition plus a host-level CLI install.
6. The pairing rule is written down, so no future tester records "not applicable" for a native desktop surface on the grounds that Playwright cannot see it.

## Key Detailed Design

### Program Design

#### What the tool is, and why it is the right harness

`agent-desktop` is a Rust CLI that reads an operating system accessibility tree and returns it as JSON, with a ref for every element the agent may act on. There is no model inside it: the observe, act, verify loop lives in the agent. On Windows the adapter talks to UI Automation; on macOS to AX; on Linux to AT-SPI.

That property is what makes it usable as UAT evidence. Playwright asserts on the DOM of a page it loaded, which is why it cannot reach a Tauri window or a Bevy overlay. `agent-desktop` asserts on the same tree Windows exposes to a screen reader, which is the surface a user actually operates, and its refs are snapshot-scoped, so a stale ref fails loudly instead of clicking the wrong control.

#### Host fit, verified before planning

| Fact | Value | Consequence |
|---|---|---|
| OS | Windows, build `10.0.26300` | Windows 10 1809 or later is the documented floor, so the UI Automation adapter applies |
| Architecture | x64 | The package ships `win32` binaries for `x64` and `arm64`, so no source build is needed |
| Node | `v26.7.0` | Satisfies the npm launcher |
| npm | `11.14.1` | Installs succeed, but the global prefix grants ordinary users read and execute only, so the install needs an elevated session, as recorded in Deviations D1 |
| Global prefix | `d:\nodejs\.npm\global` | Already on `PATH`, and already holds `agent-browser`, `opencode`, and `omniroute`, so a global CLI is the established pattern here |
| Package version at planning time | `agent-desktop@1.3.1` | Pinned in the install command, and its version envelope is recorded in the evidence folder, because the bundled guide text changes with the version |
| Registry | resolves through `registry.npmmirror.com` | The package is available; the install is pinned and `dist.integrity` is recorded rather than the version being assumed |

#### Surface to harness mapping

This is the rule the tester definition will carry, and it is the whole point of the change.

| Surface | Example route or artifact | Harness | Reason |
|---|---|---|---|
| Web page in a browser | `apps/web`, `/login`, SSO journey | Playwright harness in `D:\Cloud\OneDrive\AI\Agentic\test` | DOM, console, and network evidence are all available |
| Native desktop window | `apps/desktop` (Tauri, product name `avrig.ai Desktop`) | `agent-desktop` | No DOM exists; the accessibility tree is the only addressable surface |
| Native overlay window | `avatar/pet-desktop` (Bevy, binary `pet-desktop.exe`) | `agent-desktop` | Same reason, plus the window is transparent and always-on-top, where screenshots alone are ambiguous |
| Browser surface the harness does not cover | ad hoc page | `wmux browser` | Unchanged last-resort fallback |

A Bevy-rendered overlay may expose very little through UI Automation, since a GPU canvas is not a control tree. The tester must therefore treat "snapshot returns a window with no interactive children" as a finding about the app, recorded with the snapshot as evidence, not as a tool failure. That distinction is written into the definition so it is not rediscovered each cycle.

#### The tester definition change

`D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md`, edited in place. Frontmatter is unchanged: the edit permission on `**/plans/evidence/**` already covers the new evidence subfolder.

| Location in the file | Change |
|---|---|
| `## Responsibilities`, item 3 | Retitle from `Live Browser Testing (Mandatory whenever the plan has a user interface surface)` to `UI Verification: Live Browser and Desktop Application UAT`, and add one bullet pointing at both sections, so the index still reads in order and no numbering shifts |
| `## Live Browser Testing`, `### When it applies` | Add the boundary sentence: a native desktop surface is not a browser surface, it belongs to `## Desktop UAT Testing`, and it must never be recorded as not applicable here |
| `## Live Browser Testing`, `### Choose the harness, then name the command` | Add the desktop branch to the numbered harness choice, so the reader picks the harness before writing the step |
| New `## Desktop UAT Testing` section, placed after `### Reporting a browser failure`, the last subsection of `## Live Browser Testing` | The full contract, subsections below. It must not be inserted inside `## Live Browser Testing`, because that would split the browser contract |

The new section carries these subsections, in this order.

1. `### When it applies`: mandatory when the plan changes or exercises `apps/desktop`, `avatar/pet-desktop`, or any native window. Not applicable only for a genuinely windowless plan, recorded with a one line reason. A surface that exists but could not be reached is BLOCKED, never not applicable.
2. `### Preflight`: `agent-desktop status` first, and record platform, permissions, and supported surfaces. `agent-desktop version` is recorded in the evidence folder. If `status` fails, the row is BLOCKED with the failing envelope attached.
3. `### Read the bundled guides before the first action`: run `agent-desktop skills get desktop` and `agent-desktop skills get platform` at the start of a session and follow them. The guides are version-matched to the binary, so they win over anything memorized or copied into a prompt.
4. `### The observe, act, verify loop`: `snapshot` first, act on a ref from that snapshot, snapshot again to assert the result. A ref is qualified, shaped `@<snapshot_id>:e<N>` such as `@s8f3k2p9:e1`, and belongs to one snapshot. A bare `@e8` or `e8` is rejected with `INVALID_ARGS`, and the envelope names the expected shape. `STALE_REF` and `AMBIGUOUS_TARGET` mean take a new snapshot, never retry the same ref.
5. `### Windows and PowerShell specifics`: quote every ref as a single-quoted string, because a leading `@token` is the splatting operator in PowerShell. Use `--window-id` when a snapshot returns `AMBIGUOUS_TARGET` and lists candidate windows. Use `snapshot --skeleton --compact` then `--root` to drill into a dense window. `type`, `focus`, `right-click`, `double-click`, and `triple-click` need `--headed` on this platform, and `type` synthesizes keystrokes through SendInput, so it is a permissioned exception rather than the default text path.
6. `### Launch the tested artifact`: launch the binary built from the candidate tag commit, never a local rebuild. Name the artifact path in the matrix. `launch` is the entry point when the app is not already running; `list-apps` and `list-windows` are how the tester confirms what is on screen before acting.
7. `### Secrets`: `type`, `set-value`, and `clipboard-set` accept `--stdin`, and `set-value --stdin` is the headless path. `type --stdin` also works but is keystroke synthesis on Windows and needs `--headed`, so it applies only where the application demands real keystrokes and the user has permitted physical input. Any token, password, or key reaches the app through `--stdin` or a separate `clipboard-set` step, never as a process argument.
8. `### Retry discipline`: retry only when `error.disposition.retry` is `safe`. Any other disposition is a finding, with the error code quoted.
9. `### What to assert`: accessibility tree role and name, and visible state transitions. A notification check uses `list-notifications --headed`, or a run where the Action Center is already open, because on Windows that command returns `POLICY_DENIED` headless when the center is closed; a `POLICY_DENIED` there is a preflight state, not an application finding. Screenshots are supporting evidence, never the assertion, because a pixel comparison cannot tell a correct disabled state from a broken one.
10. `### Evidence per run`: `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/desktop/` holding the snapshot JSON envelopes, one screenshot per asserted state, the `version` output, the `status` output, and one result line naming the tag, the commit SHA, the verdict, the passing check count, and the folder path. The edit to this definition is untracked, so no candidate tag can contain it: its proof is the instruction manifest at `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json` plus a read-back, while the desktop evidence sits beside the browser evidence for the same candidate number.
11. `### Reporting a desktop failure`: failing ref or window id, the expected role and name, the actual role and name, the snapshot path, the screenshot path, and the same root cause routing used elsewhere (`be`, `fe`, `edm`, `Infra`, `build`).

#### Command vocabulary the definition will state

These are the real forms, and the definition states them instead of a prose description, because a call the reader has to reconstruct is a call that gets improvised.

| Purpose | Form |
|---|---|
| Preflight | `agent-desktop status`, `agent-desktop version`, `agent-desktop permissions` (`--guide` is macOS only, so it is not part of the Windows preflight) |
| Guides | `agent-desktop skills get desktop`, `agent-desktop skills get platform` (the latter resolves the `agent-desktop-windows` guide on this host) |
| Observe | `agent-desktop snapshot --app "<app name>" -i`, `--skeleton --compact`, `--root '<ref>'`, `--window-id <id>` |
| Locate | `agent-desktop find`, `agent-desktop get`, `agent-desktop is` |
| Act on a ref | `agent-desktop click '@<snapshot_id>:e<N>'`, `type`, `set-value`, `toggle`, `select`, `scroll-to` |
| Keyboard and window | `agent-desktop press`, `launch`, `list-apps`, `list-windows`, `focus-window`, `close-app` |
| Evidence | `agent-desktop screenshot`, and optionally `agent-desktop trace export` after a trace-enabled `session start`, because bare `trace` only reads a timeline |
| Verify state | `agent-desktop wait`, and `agent-desktop list-notifications` where the Action Center is open or `--headed` is permitted |
| Batch | `agent-desktop batch '<json array>'` (no secrets inside a batch) |

Every command prints one JSON envelope, so the definition requires the envelope to be saved rather than paraphrased.

#### Invariants this change introduces

- The desktop section never claims a browser assertion. Playwright keeps the DOM, console, and network contract unchanged.
- A candidate tag is still the unit of test. The desktop loop runs against the artifact built from the candidate commit, and the evidence folder is keyed by the same `rc.<NNN>` number as the browser evidence. The definition edit itself is untracked, so the tag cannot contain it and the instruction manifest, not the branch, is what proves it.
- No tag, merge, bump, or push is introduced. The tester still creates nothing.
- The tool exposes private desktop content (snapshots, clipboard, screenshots). The definition states that evidence stays inside `plans/evidence/` and is never pasted into a public issue or a commit message.

#### Risks and mitigations

| Risk | Mitigation |
|---|---|
| Automating a live desktop disrupts the user's session | Ref actions are headless by default and need no pointer, and `type`, `focus`, `right-click`, `double-click` and `triple-click` are named as the `--headed` set; launching and closing an app is still visible, so the matrix names the app, and every run closes what it opened with `close-app` |
| A headless action is expected where Windows needs physical input | The definition states that headed mode is never used to recover from a headless failure, so a `POLICY_DENIED` there is reported as a finding instead of retried with `--headed` |
| A transparent Bevy overlay exposes almost nothing to UI Automation | Recorded as an app finding with the snapshot attached, and the definition says so, so it is not misread as a broken tool |
| Version drift in the bundled guides | The install is pinned to `agent-desktop@1.3.1`, `npm view agent-desktop@1.3.1 dist.integrity` and the `version` output are stored per evidence folder, and `postinstall` verifies the shipped `.sha256` files, so a rule quoted from a different release is traceable |
| Install lands outside `PATH` in a different shell | Preflight uses `where.exe agent-desktop` and a bare `agent-desktop version` in `pwsh`, and a missing binary is BLOCKED with the recovery command |
| The section grows into a second copy of the binary's own documentation | The definition cites the bundled guides as the authority and quotes only the call forms and the rules an agent gets wrong |

### Target Program Files (Mandatory)

| Path | Action | Owner |
|---|---|---|
| `d:\nodejs\.npm\global\node_modules\agent-desktop\` | Created by `npm install -g agent-desktop@1.3.1` | `Infra` |
| `d:\nodejs\.npm\global\agent-desktop`, `agent-desktop.cmd`, `agent-desktop.ps1` | Created by the same install, shims that put the CLI on `PATH` | `Infra` |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md` | Edited: item 3 retitled, two boundary bullets added, one new `## Desktop UAT Testing` section | `Infra` on behalf of the Architect |
| `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md.bak-20261120-<HHMMSS>` | Required backup, written immediately before the edit, in the timestamped form the Agentic `.gitignore` already covers so nothing untracked leaks | `Infra` |
| `D:\Cloud\OneDrive\AI\Agentic\avrig-ai\plans\evidence\<CODE>-<NNNNN>\instruction-manifest.json` | Created and committed on the plan branch: one row per edited instruction file carrying `File`, `Bytes`, `Sha256`, `Backup`, `BackupSha256`, re-hashed after the edit, with no `MISSING` row | `Infra` |

No file under `avrig-ai/crates`, `avrig-ai/apps`, `avrig-ai/packages`, `migrations`, or `scripts` is created, edited, or removed, and the manifest above is the only new file inside the repository. No `package.json`, `Cargo.toml`, or lockfile changes, because the install is host-global rather than a repository dependency.

### EDM Design

Not applicable. The plan creates no table, column, constraint, index, or migration, and reads no database. The only persistence it introduces is test evidence on the local file system under `plans/evidence/`.

## Parallel Execution Plan

| Step | Work | Assignee | Mode |
|---|---|---|---|
| 1 | Author this plan as a draft, with no code, no ledger row, no branch | Architect | complete |
| 2 | Audit the plan against the coding principles and the universal references, record `## Review Findings` | `analyst` | parallel with step 3 |
| 3 | Attach `## Test Specification and Validation Matrix` with exact commands and pass criteria | `tester` | parallel with step 2 |
| 4 | Present findings and the matrix, ask for approval, then allocate the next free `AVRIG` number by running the ledger allocation, set `plan_id`, write the ledger row, and rename the file | Architect | sequential, gate |
| 5 | Reconcile release tags, publish the issue, create the plan branch through it | `Architect` dispatches, `build` executes | sequential, only after approval |
| 6 | Install the CLI globally and smoke it | `Infra` | parallel with step 7 after the branch exists |
| 7 | Apply the `tester.md` edits, then write the instruction manifest and read it back | `Infra` | parallel with step 6, no file overlap |
| 8 | Build gate: not applicable, no buildable source changes, reason recorded | `build` | sequential |
| 9 | Candidate tag `avrig/<NNNNN>/rc.001` on the plan branch head | `build` | sequential |
| 10 | QA against that candidate, including a live desktop loop | `tester` | sequential |
| 11 | UAT approval, version decision, release path | `build`, approved by the user through `primary` | sequential |

These step numbers are local to this plan and are not the canonical 16 stages in `.opencode/agents/Architect.md`: steps 1 to 5 map to canonical stages 1 to 5, steps 6 and 7 to stage 6, step 8 to stage 7, step 9 to stage 8, step 10 to stage 9, and step 11 to stages 12 to 14. Read the canonical stage number from the Architect definition, never from this table.

Steps 6 and 7 touch different files and no shared resource, so they run concurrently. Step 9 does not start until both land, because QA must run against the finished definition. The candidate tag still cannot contain that definition, since the file is untracked, so the manifest and its read-back are the proof of that half of the work while the tag proves the rest of the tree.

## Test Specification and Validation Matrix

Attached by the `tester` subagent at step 3, from a read of this plan, a read of `.opencode/agents/tester.md`, and read only host checks. Nothing in this matrix installs the CLI or edits the definition: both belong to `Infra`, and the tester verifies what they produced.

### Prerequisites

The matrix assumes this exact starting state. Every row below was observed on this host, not assumed.

| Fact | Verified value | How it was read |
|---|---|---|
| OS and architecture | Windows build `10.0.26300`, `AMD64` | `(Get-CimInstance Win32_OperatingSystem).Version`, `$env:PROCESSOR_ARCHITECTURE` |
| Node | `v26.7.0` | `node --version` |
| npm | `11.14.1` | `npm --version` |
| npm global prefix | `d:\nodejs\.npm\global`, already present on `PATH` | `npm config get prefix`, `$env:PATH` |
| npm registry | `https://registry.npmmirror.com` | `npm config get registry` |
| Resolvable package version today | `1.3.1` | `npm view agent-desktop version` |
| Package bin entry | `bin/agent-desktop`, a single shim name | `npm view agent-desktop bin --json` |
| Declared platforms | `darwin`, `win32`, `linux` on `arm64` and `x64` | `npm view agent-desktop os cpu --json` |
| Install lifecycle scripts | `postinstall`: `node scripts/postinstall.js` | `npm view agent-desktop scripts --json` |
| Unpacked size | `31974390` bytes, roughly 32 MB | `npm view agent-desktop dist.unpackedSize` |
| Existing global CLI precedent | `agent-browser`, `opencode`, `opencode2`, `omniroute` all installed with `.cmd` and `.ps1` shims | `Get-ChildItem d:\nodejs\.npm\global` |
| `agent-desktop` present before install | no match | `where.exe agent-desktop` |
| Envelope schema version | `2.6`, a field inside each envelope and a different number from the CLI version | package README |
| Ref shape | `@<snapshot_id>:<element>`, for example `@s8f3k2p9:e8` | package README |
| Playwright harness | `playwright.config.ts` and `playwright.keycloak.config.ts` present in `D:\Cloud\OneDrive\AI\Agentic\test` | directory listing |
| Tester definition | 112 lines, last heading `### Reporting a browser failure` | `Select-String -Pattern '^#{1,3} '` |

The install command under test is `npm install -g agent-desktop@1.3.1`, run by `Infra` in an elevated `pwsh` session, with no `--prefix` override. The prefix `d:\nodejs\.npm\global` grants `BUILTIN\Users` and `Authenticated Users` only `(I)(OI)(CI)(RX)`, so an unelevated attempt returns `EPERM`, and every pre-existing global CLI in that folder is administrator owned. The requirement is recorded in Deviations D1 and in the manifest as `installed_elevated: true`, so A1 asserts the elevated install and the binary it produced, and no check expects an unelevated attempt to succeed.

For this plan, "installed correctly" means all of the following, and any missing item fails the install group rather than being retried silently:

1. `npm install -g agent-desktop@1.3.1` exits `0` at elevated integrity, and its output shows the `postinstall` step completing, because the package ships a `postinstall` script that runs `node scripts/postinstall.js`, and the platform binary that script unpacks exists under `node_modules\agent-desktop\`, because a shim without a working launcher is not an install. The elevation requirement is recorded in the evidence rather than assumed away.
2. `d:\nodejs\.npm\global\node_modules\agent-desktop\` exists, and `d:\nodejs\.npm\global\agent-desktop` plus `agent-desktop.cmd` and `agent-desktop.ps1` exist beside it.
3. `agent-desktop version` runs in a fresh `pwsh` and prints one JSON envelope with `ok: true`.
4. The reported package version is recorded, and the installed version matches the resolve point the matrix was written against (`1.3.1`) or is newer with the delta recorded, in which case the bundled guides are re-read because they are matched to the binary.
5. `agent-desktop status` reports a Windows platform with UI Automation available.

The artifact under test for this plan is the installed CLI plus the definition file, not a product binary. The plan changes no product source, so no desktop app is built from a candidate commit and the live loop targets a built in Windows app instead. Step 9 fixes the candidate tag `avrig/<NNNNN>/rc.<NNN>`, which step 10 resolves with `git rev-parse avrig/<NNNNN>/rc.<NNN>^{commit}`. The definition is untracked, so its proof is the instruction manifest and a read-back rather than a commit or a tag.

Three corrections this matrix applies, because the read only checks disagree with the plan text:

- On this host `where.exe` prints three entries for an npm global CLI, which rc.001 confirmed for `agent-desktop` and which `agent-browser` shows too: the extensionless shim, the `.cmd`, and the `.ps1`. Goal 1 says "prints exactly one path", which a correct install cannot satisfy, so check A2 asserts residency under the prefix and records the count instead of asserting it.
- `agent-desktop permissions --guide` is documented as the macOS Accessibility grant walkthrough. On Windows the permission state is read from `agent-desktop status`, so B4 runs the bare form and records both.
- `.opencode/agents/tester.md` has no `## Evidence per run` heading. It has `### Evidence per run` on line 99, followed by `### Reporting a browser failure` on line 110, both inside `## Live Browser Testing`. A new section placed before `### Evidence per run` would split the browser contract, so G2 asserts the new section lands after `### Reporting a browser failure`.

Before the first check, create the evidence folder, open `ledger.csv` with the columns `id,verdict,evidence,note`, and write the tag, the commit SHAs, and the installed version into it. A check with no row in the ledger is not a check that passed.

### A. Install and PATH resolution

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| A1 | The install completes, produces a launcher, and its elevation requirement is recorded | `icacls d:\nodejs\.npm\global` and the integrity level of the installing shell, then `npm install -g agent-desktop@1.3.1` in an elevated `pwsh` with no `--prefix` override | Exit code `0` at elevated integrity, the output shows the `postinstall` step finishing, and the platform binary that step unpacks exists under `node_modules\agent-desktop\`, so the shim has a launcher behind it. The ACL shows `(I)(OI)(CI)(RX)` for `BUILTIN\Users` and `Authenticated Users`, which is the recorded reason the install needs elevation, and no check expects an unelevated attempt to succeed | `logs/A1-install.txt` and `logs/A1-acl.txt` |
| A2 | The CLI resolves from a plain shell into the global prefix | `where.exe agent-desktop` and `(Get-Command agent-desktop).Source` | Every entry printed by `where.exe` is inside `d:\nodejs\.npm\global`, and `Get-Command` resolves there too. The count is recorded and not asserted: this host prints three entries, the extensionless shim, the `.cmd`, and the `.ps1`, and a different count is recorded with its explanation rather than failing the check | `logs/A2-where.txt` and `logs/A2-getcommand.txt` |
| A3 | The shims and the package folder exist where the plan says | `Get-ChildItem d:\nodejs\.npm\global -Filter 'agent-desktop*'` and `Test-Path d:\nodejs\.npm\global\node_modules\agent-desktop` | Both shim and `.cmd` present, `Test-Path` true, and the `.ps1` shim present as it is for the other global CLIs | `logs/A3-shims.txt` |
| A4 | The install landed nothing new in either repository | `git -C D:\Cloud\OneDrive\AI\Agentic\avrig-ai status --porcelain` and the same in `D:\Cloud\OneDrive\AI\Agentic` | No `package.json`, lockfile, `Cargo.toml`, `crates/`, `apps/`, `packages/`, or `migrations/` entry appears. Only evidence files, the instruction manifest, and the definition or its backup are new | `logs/A4-git-status.txt` |
| A5 | The launcher starts in a clean shell, not only the installing one | `pwsh -NoProfile -Command "agent-desktop version"` | Exit code `0` and one JSON envelope. A `-NoProfile` failure is a PATH defect, not a profile quirk | `envelopes/A5-version-noprofile.json` |
| A6 | Version pinning is recorded rather than assumed | `npm list -g agent-desktop --depth=0`, `agent-desktop version`, and `npm view agent-desktop@1.3.1 dist.integrity` | Installed version is exactly `1.3.1`, because the install is pinned and the bundled guides are matched to the binary. Any other version fails the install group rather than being tested against different guides, and the integrity value is recorded for traceability | `envelopes/A6-version.json`, `logs/A6-npm-list.txt`, `logs/A6-integrity.txt` |
| A7 | The install survives a second `pwsh` process | Launch a separate `pwsh` window, run `agent-desktop status` there | `ok: true`. A shell that resolves the old `PATH` because it was already open is a finding worth recording | `envelopes/A7-status-second-shell.json` |
| A8 | Reinstall is idempotent rather than duplicated | `npm install -g agent-desktop@1.3.1` a second time | Exit `0`, no second copy of the shims, still one resolved path per shim name | `logs/A8-reinstall.txt` |

### B. `status`, `version`, and `permissions`

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| B1 | `version` satisfies the plan goal | `agent-desktop version` | One envelope, `ok: true`, `command` equal to `version`, and a version string in `data` | `envelopes/B1-version.json` |
| B2 | `status` reports the platform the plan assumes | `agent-desktop status` | `ok: true`, platform is Windows, and the accessibility backend named is UI Automation or its Windows equivalent | `envelopes/B2-status.json` |
| B3 | The envelope schema version is not confused with the binary version | Read `version` at the envelope root and the binary version from `agent-desktop version` | Both recorded separately. Envelope `2.6` with binary `1.3.1` is the expected shape and neither number is written into the definition | `logs/B3-versions.txt` |
| B4 | `permissions` is available and its Windows output is recorded | `agent-desktop permissions` and, for the record, `agent-desktop permissions --guide` with both outcomes saved | `permissions` returns `ok: true` on Windows. A `--guide` that fails or refuses on Windows is recorded as expected, since the guide walks a macOS grant, and is not a failure | `envelopes/B4-permissions.json` and `logs/B4-permissions-guide.txt` |
| B5 | Supported surfaces are visible to the tester | `agent-desktop list-surfaces` | `ok: true` and at least one surface listed, so a later "no interactive refs" finding can name what the tool believed it could see | `envelopes/B5-list-surfaces.json` |
| B6 | Every command writes exactly one envelope to stdout and nothing else | `agent-desktop status 2> logs/B6-stderr.txt` | stdout parses as a single JSON object, `$LASTEXITCODE` is `0`, and any stderr text is diagnostics rather than a second payload | `envelopes/B6-status.json` and `logs/B6-stderr.txt` |

### C. Bundled guide retrieval

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| C1 | The desktop guide is retrievable | `agent-desktop skills get desktop` | Non empty text, and it states the loop, the ref rules, and the retry rule | `guide-desktop.txt` |
| C2 | The platform guide is retrievable | `agent-desktop skills get platform` | Non empty text, and it addresses Windows specifically | `guide-platform.txt` |
| C3 | The guides are version matched, which is why they outrank memory | Compare the guide header or any version line with `agent-desktop version` | Version agreement recorded, or the guide is silent on version and that is noted | `logs/C3-guide-version.txt` |
| C4 | The definition's quoted call forms agree with the shipped guides | Diff the forms in the new `## Desktop UAT Testing` section against the two guide files | Every form the definition states appears in a guide or in `agent-desktop <command> --help`, and any disagreement is raised as a definition defect | `logs/C4-form-diff.txt` |
| C5 | The guide names the ref lifecycle rule the matrix tests | Search the guides for the stale ref and ambiguous target statements | Both present, so E2, E3, and E7 are testing documented behaviour rather than an assumption | `logs/C5-guide-refs.txt` |

### D. Live observe, act, verify loop

Target: a built in Windows app, chosen so the run proves the harness without touching product code. Primary target `notepad.exe`, fallback `calc.exe`, then `mspaint.exe`. The tester opens and closes only what this loop opens, and every envelope is saved verbatim.

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| D1 | The chosen app launches through the tool | `agent-desktop launch notepad.exe` | `ok: true` and the envelope identifies the launched app or window | `envelopes/D1-launch.json` |
| D2 | What is on screen is confirmed before acting | `agent-desktop list-apps` | The launched app appears, with the name recorded verbatim because D3 reuses it | `envelopes/D2-list-apps.json` |
| D3 | A window is enumerable for the app | `agent-desktop list-windows --app "Notepad"` | At least one window listed with an id usable as `--window-id` | `envelopes/D3-list-windows.json` |
| D4 | A first snapshot returns addressable refs | `agent-desktop snapshot --app "Notepad" -i` | `ok: true`, `data.snapshot_id` present, `data.ref_count` at least `1`, and the tree carries at least one node with a ref of the form `@<snapshot_id>:<element>` | `envelopes/D4-snapshot-observe.json` |
| D5 | The app choice is honest, not forced | If D4 returns a window with no interactive children, repeat D1 through D4 with `calc.exe`, then `mspaint.exe`, recording each attempt | At least one candidate app yields interactive refs. All three empty is recorded as BLOCKED with all three snapshots, never silently downgraded | `envelopes/D5-fallback-<app>.json` |
| D6 | A node's property is read by name, and its actions come from the snapshot | `agent-desktop get --help`, then one property read exactly as that help states, for example the `value` of the text field, on the ref chosen in D4 | `get` returns exactly one named property from `text`, `value`, `title`, `bounds`, `role`, and `states`, with the property named in the invocation, and the envelope is saved. `available_actions` is never expected here, because `get` does not report it: the actions a node offers are read from the listing in the snapshot, and the help text is saved as the proof of the property set | `envelopes/D6-get-ref.json` and `logs/D6-get-help.txt` |
| D7 | One ref is acted on, harmlessly, through the route F1 asserts | `agent-desktop click '<ref>'` for a button, or the sentinel `agent-desktop-uat-0001` piped into `d:\nodejs\.npm\global\agent-desktop.cmd set-value '<ref>' --stdin` for a text field | The envelope names the command issued and the ref is quoted in single quotes as PowerShell requires. The step is judged by the D8 read-back rather than by the envelope, because a `.cmd` act reports `ACTION_FAILED` with no `post_state.value` even where the value lands | `envelopes/D7-act.json` |
| D8 | A second snapshot proves the change | `agent-desktop snapshot --app "Notepad" -i` after D7 | `ok: true`, a new `snapshot_id` different from D4, and for a text field the sentinel visible in the tree. A ref from D4 is not reused | `envelopes/D8-snapshot-verify.json` |
| D9 | A screenshot backs the assertion instead of replacing it | `agent-desktop screenshot --help` first, then the screenshot command with an explicit output path in the evidence folder | One image file exists in the evidence folder, and the assertion in D8 is stated in tree terms rather than in pixels | `screens/D9-after-act.png` and `logs/D9-screenshot-help.txt` |
| D10 | The loop leaves nothing open, and the close form is the one the tool takes | `agent-desktop close-app "notepad.exe"` with the app name positional and the name D2 recorded, then `agent-desktop list-apps`, then `agent-desktop close-app --app "notepad.exe"` to record the rejection | `ok: true` on the positional close and the app gone from the follow up listing. The `--app` form answers `INVALID_ARGS`, which is recorded rather than used. A hosted target is the exception: there `close-app` answers `APP_NOT_FOUND`, so the close goes through the window's own Close ref from a fresh snapshot and is confirmed with `list-windows` | `envelopes/D10-close-app.json`, `envelopes/D10-close-app-app-flag.json`, and `envelopes/D10-list-apps-after.json` |
| D11 | Notifications are checked rather than ignored | `agent-desktop list-notifications` | Envelope saved. An unexpected notification is a finding and an empty list is a pass. `POLICY_DENIED` with the Action Center closed is recorded as a preflight state rather than a failure, and the check is rerun with `--headed` only if the user permits physical input | `envelopes/D11-notifications.json` |
| D12 | `wait` waits for a condition it can see, and a value is read instead | `agent-desktop wait --help`, `agent-desktop wait` after the action in D7 where the app settles asynchronously, then `agent-desktop get '<ref>'` for the value written in D7 | `ok: true` on the wait, and no `Start-Sleep` appears in the recorded step. The help text is saved to show what `wait` can match, and the value written in D7 is asserted with `get` on the `value` property rather than with `wait --text`, which cannot match a value held inside a control | `envelopes/D12-wait.json`, `logs/D12-wait-help.txt`, and `envelopes/D12-get-value.json` |
| D13 | Every saved envelope is valid JSON with the documented shape | `Get-ChildItem envelopes\*.json` piped to `ConvertFrom-Json`, asserting `version`, `ok`, `command` on each | Every file parses and carries the three root fields. One unparseable file fails the group | `logs/D13-envelope-audit.txt` |
| D14 | The loop is reproducible from the evidence alone | Read `logs/D14-commands.txt` and compare with the envelopes | The recorded command sequence reproduces the envelopes in the same order, with no step skipped between observe, act, and verify | `logs/D14-commands.txt` |

### E. Ref lifecycle error paths

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| E1 | A bare ref is rejected rather than resolved | `agent-desktop click '@e8'` | `ok: false` and the error code is `INVALID_ARGS`. Any successful click fails this check outright | `envelopes/E1-bare-ref.json` |
| E2 | A superseded ref fails loudly instead of clicking the wrong control | Take a snapshot, capture a ref, change the tree so that ref is superseded, then act on the captured ref | Error code is `STALE_REF` or `AMBIGUOUS_TARGET`, and `ok` is `false`. Never a success | `envelopes/E2-stale-ref.json` and `logs/E2-tree-change.txt` |
| E3 | Two windows of one app are chosen silently, by focus, and not refused | Open a second Notepad window, confirm both in `agent-desktop list-windows --app "Notepad"`, then `agent-desktop snapshot --app "Notepad" -i` with no `--window-id`, twice: once with the first window brought forward through `agent-desktop focus-window` and once with the second | Both snapshots return `ok: true` with no `AMBIGUOUS_TARGET`, and each covers the window that was in front at the time, shown by the two differing `snapshot_id` values and by the window identity the envelope reports. If the envelope carries no window identity, a screenshot taken immediately after each snapshot is the corroboration and its absence is noted. The silent choice is recorded, because a reader who expects an error here would pin nothing and snapshot whichever window happened to be in front | `envelopes/E3-focused-a.json`, `envelopes/E3-focused-b.json`, and `logs/E3-windows.txt` |
| E4 | `--window-id` addresses the window the tester means, not the one in front | `agent-desktop snapshot --app "Notepad" -i --window-id <id>`, with `<id>` taken from `agent-desktop list-windows --app "Notepad"` for the window that is not in front | `ok: true`, and the snapshot covers exactly the pinned window while the other window stays focused, so the pin is the only way to reach a background window. This is the route the definition requires whenever more than one window exists | `envelopes/E4-window-id.json` |
| E5 | The recovery path is a new snapshot, not a retry | Read the recorded sequence after E2 | A fresh `snapshot` appears before the next action, the failed ref appears only once in the command log, and no second attempt with the same ref is recorded | `logs/E5-recovery-order.txt` |
| E6 | Retry discipline is read from the envelope | Inspect `error.disposition.retry` in every error envelope captured in E1, E2, and E7 | Recorded verbatim per error. Any retry performed must sit behind a `safe` disposition, and any other disposition appears in the report as a finding | `logs/E6-dispositions.txt` |
| E7 | `AMBIGUOUS_TARGET` is raised where a name is genuinely not unique | A name addressed act or window command against the two Notepad windows opened in E3, where both windows carry the same accessible name, for example `agent-desktop focus-window "<title both windows share>"` and `agent-desktop find "<a name present in both>"` | If `AMBIGUOUS_TARGET` is returned, `ok` is `false` and `error.details` lists the candidates, and the recovery is a fresh snapshot or a pinned `--window-id`, never a retry of the same argument. If no form raises it, both envelopes are saved as printed and the absence is reported as a deviation from the bundled guide, so the rule is exercised and recorded either way rather than assumed | `envelopes/E7-ambiguous-<command>.json` and `logs/E7-ambiguous-probe.txt` |

### F. Secret handling through `--stdin`

The sentinel `uat-secret-0002` stands in for a credential. It is a fake, and it must still travel the way a real one would, because the check is about the path rather than the value. Two routes are tested rather than one, because a value piped into the `.ps1` shim never reaches the binary while its envelope still claims delivery, so the route is named explicitly in every command below and the read-back snapshot decides the verdict rather than any field in the envelope.

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| F1 | The `.cmd` route carries the value, and a read-back proves it | The sentinel piped into `d:\nodejs\.npm\global\agent-desktop.cmd set-value '<ref>' --stdin` for the text field opened in D1, then a fresh snapshot and a `get '<ref>'` read of the `value` property | The sentinel is present in the read-back snapshot and in the `get` value. The verdict is taken from that read alone: the envelope is saved and its `delivered_verified` is recorded but never accepted as evidence, and an `ACTION_FAILED` envelope over a read-back that holds the sentinel is a pass on the delivery path, with the envelope behaviour reported as a finding. The invocation log shows the ref as the only argument and the value arriving on stdin | `envelopes/F1-cmd-set-value.json`, `envelopes/F1-readback.json`, and `logs/F1-invocation.txt` |
| F2 | The `.ps1` route is shown to lose a piped value, which is why it is never the route | The same pipeline through `d:\nodejs\.npm\global\agent-desktop.ps1 set-value '<ref>' --stdin`, then the same read-back snapshot and `get` | The read-back shows no sentinel in the field while the envelope, saved as printed, reports `ok: true` with `delivered_verified` where that is what it returns. The check passes when the loss is demonstrated and the definition names `agent-desktop.cmd` or the native `.exe` as the route, never the `.ps1` shim. An envelope claiming delivery over an absent value is exactly the case this row exists to prove, so the envelope is evidence of the defect rather than of a result | `envelopes/F2-ps1-set-value.json`, `envelopes/F2-readback.json`, and `logs/F2-routes.txt` |
| F3 | Batch is not used for a secret step | `agent-desktop batch --help`, and the definition's `### Secrets` text | The definition states that batch JSON text appears in process arguments, and no recorded secret step uses `batch` | `logs/F3-batch-help.txt` |
| F4 | The clipboard path carries a value the same way, and the desktop is left clean | The sentinel piped into `d:\nodejs\.npm\global\agent-desktop.cmd clipboard-set --stdin`, then `agent-desktop clipboard-get`, then `agent-desktop clipboard-clear` and clearing the text field | `clipboard-get` returns the sentinel, which shows the clipboard path also needs the `.cmd` route, and after `clipboard-clear` plus the field clear no sentinel remains in either place, with a follow up snapshot showing the field empty | `envelopes/F4-clipboard-get.json`, `envelopes/F4-clipboard-clear.json`, and `screens/F4-cleared.png` |
| F5 | Nothing sensitive reaches durable evidence | Search the evidence folder and the result line for the sentinel name in prose form, and confirm no real credential appears anywhere | Only the fake sentinel and the declared non-secret probe string exist, no live token is present, and the result line names the check rather than quoting a value | `logs/F5-secret-audit.txt` |
| F6 | The definition states the route, the read-back rule, and the boundary a reader can follow | Read `### Secrets` and the loop subsection in the new section | It says tokens, passwords, and keys reach the app through `--stdin` or a separate `clipboard-set` step and never as a process argument, that `--stdin` goes through `agent-desktop.cmd` or the native `.exe` and never through the `.ps1` shim, and that the value is read back rather than trusted from `delivered_verified`, which is not evidence for any act | `logs/F6-secrets-text.txt` |
| F7 | The headed boundary is probed on purpose, with a value that is not a secret | `agent-desktop type '<ref>' "uat-probe-0003"` with no `--headed`, on the text field opened in D1, where `uat-probe-0003` is a non-secret probe string declared as such in the evidence | The envelope reports `POLICY_DENIED`, and the definition names `type` as part of the `--headed` set rather than as the default text path. This is the only row that puts a literal in an argument list, and that literal carries no credential, which is what makes it safe to record. Retrying with `--headed` happens only with the user's explicit permission | `envelopes/F7-type-headless.json` |

### G. Definition conformance against `tester.md`

Base state, for reference: 112 lines, headings `## Responsibilities` on 12, `## Live Browser Testing` on 52, its subsections on 56, 61, 68, 90, 99, and 110, frontmatter on lines 1 to 8 with `mode: subagent` and the `**/plans/evidence/**` allow rule.

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| G1 | The frontmatter still parses and still grants the evidence edit | Read the block between the first two `---` lines of `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md` | `description`, `mode: subagent`, and the `permissions` entry with `resource: "**/plans/evidence/**"` and `effect: allow` all still present and unchanged | `logs/G1-frontmatter.txt` |
| G2 | The new section exists once and sits where the plan says | `Select-String -Path tester.md -Pattern '^## '` with line numbers | Exactly one `## Desktop UAT Testing` heading, and its line number is greater than 110, so it follows `### Reporting a browser failure` and does not split the browser contract | `logs/G2-headings.txt` |
| G3 | All eleven subsections are present in the plan's order | List the `###` headings under the new `##` heading | Exactly eleven, in this order: `When it applies`, `Preflight`, `Read the bundled guides before the first action`, `The observe, act, verify loop`, `Windows and PowerShell specifics`, `Launch the tested artifact`, `Secrets`, `Retry discipline`, `What to assert`, `Evidence per run`, `Reporting a desktop failure` | `logs/G3-subsections.txt` |
| G4 | Item 3 is retitled as the plan specifies | Read the `## Responsibilities` item 3 heading line | It reads `UI Verification: Live Browser and Desktop Application UAT` verbatim | `logs/G4-item3.txt` |
| G5 | Numbering has no gap and no duplicate | Extract the numbered items in `## Responsibilities` | Items run 1 through 6 with no gap and no duplicate, and every item still carries a bold title | `logs/G5-numbering.txt` |
| G6 | Item 3 points at both sections | Read the bullets under item 3 | One bullet names `## Live Browser Testing` and one names `## Desktop UAT Testing`, so the index reads in order | `logs/G6-item3-bullets.txt` |
| G7 | The browser section disowns the desktop surface | Read `### When it applies` under `## Live Browser Testing` | It states that a native desktop surface belongs to `## Desktop UAT Testing` and must never be recorded as not applicable there | `logs/G7-boundary.txt` |
| G8 | The harness choice names desktop as a branch | Read `### Choose the harness, then name the command` | The desktop harness is one of the numbered choices, so the reader picks a harness before writing a step | `logs/G8-harness-choice.txt` |
| G9 | The call forms a reader needs are present as literal text | Search the new section for `agent-desktop status`, `skills get desktop`, `skills get platform`, `snapshot --app`, `-i`, `--window-id`, `close-app`, `--stdin`, `agent-desktop.cmd`, `delivered_verified`, `INVALID_ARGS`, `STALE_REF`, `AMBIGUOUS_TARGET`, `error.disposition.retry` | Every string present. A prose paraphrase where a form is required fails the check | `logs/G9-forms.txt` |
| G10 | The PowerShell quoting rule is stated | Read `### Windows and PowerShell specifics` | It says to quote every ref as a single quoted string, and gives the reason that a bare `@token` is splatting | `logs/G10-powershell.txt` |
| G11 | The evidence layout is stated with the desktop subfolder | Read `### Evidence per run` in the new section | It names `plans/evidence/<CODE>-<NNNNN>/rc.<NNN>/desktop/` and lists the snapshots, the screenshots, the version and status output, and one result line | `logs/G11-evidence-text.txt` |
| G12 | No binary version is hardcoded in the definition | `Select-String -Path tester.md -Pattern '1\.3\.1'` and a general dotted version scan | Zero matches. The version lives in evidence folders, and a match is a defect even where it looks helpful | `logs/G12-version-scan.txt` |
| G13 | The edit is proven, because no tag can contain it | Read `plans/evidence/<CODE>-<NNNNN>/instruction-manifest.json`, recompute `Get-FileHash -Algorithm SHA256` for `tester.md` and for the `.bak-<timestamp>` sibling | One row for `tester.md`, its `Sha256` matches the recomputed hash, `BackupSha256` matches the backup, the backup file exists, and no row is `MISSING` | `logs/G13-manifest-readback.txt` |

### H. Regression, the web path stays intact

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| H1 | The browser section survives with all its subsections | List `###` headings under `## Live Browser Testing` | `When it applies`, `Choose the harness, then name the command`, the wmux browser fallback heading with its real call forms, `What to test and how to assert`, `Evidence per run`, `Reporting a browser failure`, all still present | `logs/H1-browser-headings.txt` |
| H2 | Playwright is still the named web harness | Search for the harness path and both configs | `D:\Cloud\OneDrive\AI\Agentic\test` named, with `playwright.config.ts`, `playwright.keycloak.config.ts`, and the Makefile targets `test`, `keycloak`, `report`, and `summary` | `logs/H2-playwright.txt` |
| H3 | The `wmux browser` fallback is unchanged | Compare the fallback subsection against `tester.md.bak-20261120-<HHMMSS>` with `Compare-Object`, not `git diff`, because the definition is untracked and `git diff` reports nothing for it | Identical apart from any intended boundary sentence, and the `WMUX_SURFACE_ID` rule about empty output counting as BLOCKED still stands | `logs/H3-wmux-diff.txt` |
| H4 | Responsibilities items 1, 2, 4, 5, and 6 are untouched | `Compare-Object` the current file against the `.bak-<timestamp>` sibling and read each difference | Every difference falls in item 3, the browser section, or the new section, and nothing else changed. A run that compares against `git diff` proves nothing here, since an untracked file produces no diff | `logs/H4-diff.txt` |
| H5 | The Playwright harness still loads after the edit | `npx playwright test --list` in `D:\Cloud\OneDrive\AI\Agentic\test` | The project enumerates its tests with no config error. Listing only, no browser is launched | `logs/H5-playwright-list.txt` |

### N. Negative and adversarial checks, what must not happen

| ID | Purpose | Exact command or file assertion | Pass criterion | Evidence |
|---|---|---|---|---|
| N1 | No green verdict without an envelope behind it | Read `ledger.csv` and confirm each PASS row names a file that exists | Every PASS row has at least one artefact on disk. A row claiming a result with an empty evidence column is rewritten as not tested and the verdict is withheld | `logs/N1-ledger-audit.txt` |
| N2 | A desktop surface is never recorded as not applicable because Playwright cannot see it | Read the verdict lines for every desktop row | No row says not applicable for a native window. An unreachable surface is BLOCKED with the failing envelope attached | `logs/N2-not-applicable-audit.txt` |
| N3 | A ref is never retried after a stale ref error | Read `logs/E5-recovery-order.txt` | The stale ref appears once, followed by a new snapshot. A retry of the same ref is a failed check, not a flaky one | `logs/N3-retry-audit.txt` |
| N4 | A token never travels as a process argument | Read every recorded invocation in the evidence folder | No sentinel, token, password, or key appears after `set-value`, `type`, or `clipboard-set` in an argument list, and secret steps are separate commands rather than a batch. The single exception is the non-secret probe literal in F7, which carries no credential and is labelled as a probe wherever it appears. A sentinel found in any argument list fails this check outright | `logs/N4-argument-audit.txt` |
| N5 | Nothing sensitive reaches a commit, an issue, or a result line | `git status --porcelain` in both repositories, and a read of the result line | Evidence stays under `plans/evidence/`, the result line contains no credential, and no snapshot or screenshot is staged for a public artifact | `logs/N5-publish-audit.txt` |
| N6 | An app with no interactive children is not reported as a tool failure | Read the D5 outcome | Recorded as an app finding with the snapshot attached, and the distinction is stated rather than implied | `logs/N6-empty-tree.txt` |
| N7 | The tester did not do the installer's or the author's job | `git status --porcelain` and a comparison of `tester.md` against the `Infra` output | The tester installed nothing, edited no definition, and created only evidence files. A tester side edit of `tester.md` voids the run | `logs/N7-ownership.txt` |
| N8 | The envelope version is never written up as the release version | Read the result line and `logs/B3-versions.txt` | The result line names the candidate tag, the commit SHA, the installed CLI version, and the verdict, with no envelope schema number presented as a product version | `logs/N8-version-audit.txt` |

### Evidence layout

Everything lands under `plans/evidence/AVRIG-<NNNNN>/rc.<NNN>/desktop/`, beside the browser evidence for the same candidate number. `<NNNNN>` is unassigned until the plan is approved, so every path here is written with the placeholder and the real number replaces it at step 4. `rc.<NNN>` matches the candidate tag the run tested. The instruction manifest sits one level up, at `plans/evidence/AVRIG-<NNNNN>/instruction-manifest.json`, because it describes the definition rather than a candidate.

```text
plans/evidence/AVRIG-<NNNNN>/rc.<NNN>/desktop/
  ledger.csv                      id, verdict, evidence, note, one row per check
  RESULT.md                       one result line: tag, commit SHA, CLI version, verdict, pass count, folder path
  version.json                    agent-desktop version envelope
  status.json                     agent-desktop status envelope
  guide-desktop.txt               bundled desktop guide, as retrieved
  guide-platform.txt              bundled platform guide, as retrieved
  envelopes/<id>-<command>.json   stdout envelope per command, unedited
  logs/<id>-<subject>.txt         stderr, invocation records, audits, diffs
  screens/<id>-<state>.png        one screenshot per asserted state
```

Rules that make the layout useful rather than decorative:

- One folder per candidate tag, never a shared folder with mixed tags.
- Envelopes are saved exactly as printed, because a paraphrased envelope cannot be re-read when a result is questioned.
- The result line names the tag, the commit SHA, the installed CLI version, the verdict, the count of passing checks, and this folder path.
- Large screenshots follow the project evidence retention policy instead of being committed by default.
- A claim with no file in this folder counts as not tested, and the verdict line says so.

### Pass gate

A PASS requires every check in groups A, B, C, D, E, F, G, and H that is listed as mandatory below, plus every negative check in N, with a passing verdict and an artefact on disk for each.

Mandatory for PASS: A1 through A6, B1 through B4, C1 and C2, D1 through D10, D13, E1 through E5, E7, F1, F2, and F6, G1 through G13, H1 through H4, and N1 through N4. Two rules are mandatory through those rows rather than as rows of their own. The read-back rule makes the following snapshot or a `get` read the assertion in D8 and F1, and in the advisory D12, and it forbids `delivered_verified` from counting as evidence anywhere. The shim route is F1 and F2, so a value step taken through the `.ps1` shim cannot pass on a healthy envelope even when every field in that envelope looks correct.

Advisory, recorded but not gating: A7, A8, B5, B6, C3 through C5, D11, D12, D14, E6, F3, F4, F5, F7, H5, and N5 through N8. A failure here is reported as a finding with its envelope and does not by itself withhold the verdict, except where a later mandatory check depends on it.

Forced BLOCKED rather than FAIL, with the reason recorded and the recovery command named:

- The registry is unreachable, or the install cannot be completed even at elevated integrity, so no binary exists to test.
- There is no interactive user session available, such as a locked or disconnected desktop, so no window can be launched.
- Every candidate app in D5 returns a window with no interactive children, which means the environment cannot exercise the loop rather than that the definition is wrong.
- The `wmux` caller surface is unset, where a fallback check needs it, which affects H3 only and is reported per the browser contract.
- The instruction manifest is missing, or its `Sha256` does not match the current definition, because then the edit is unproven and there is no definition to assert against.

Forced FAIL, routed to the owning agent:

- Any definition content defect in group G routes to `Infra` as the editor on behalf of the Architect, with the failing heading and the expected text quoted.
- Any install defect in group A or B routes to `Infra` as the installer, with the install log attached.
- Any regression in H routes to `Infra`, because the plan permits no product source or harness change and the definition edit is the only intended diff.
- A tool behaviour that contradicts the bundled guides, in C or E, routes to the Architect as a plan correction rather than to `Infra`, because the plan quoted a form the binary does not implement.

A run with no BLOCKED row and no FAIL row is the release trigger. The tester reports the passing candidate tag `avrig/<NNNNN>/rc.<NNN>`, its commit SHA from `git rev-parse avrig/<NNNNN>/rc.<NNN>^{commit}`, and the recommended increment, which for this plan is `minor`, since it adds a backward compatible capability to the tester agent with no breaking change to any product surface. The tester creates no tag.

## Review Findings

Verdict: **PASS WITH FINDINGS**. Scope, ownership, and measurable acceptance hold after the edits below; the plan is ready for the step 4 approval gate, and it is a draft with no code, no ledger row, and no `plan_id`, which is correct.

How the claims were checked, rather than assumed: the shipped `agent-desktop@1.3.1` package was unpacked to a temporary folder and its Windows binary was run on this host. Every command name, flag, error code, and disposition value cited below was either executed or read from that binary's own `--help`, and the temporary copy was deleted afterwards. Host facts were re-read: node `v26.7.0`, npm `11.14.1`, prefix `d:\nodejs\.npm\global` with `agent-browser`, `opencode`, and `omniroute` shims, registry `registry.npmmirror.com`, package `1.3.1` under Apache-2.0, README Windows floor of 10 1809.

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| A1 | High | No instruction manifest. `tester.md` is untracked (`git status` prints `?? .opencode/agents/`), so no candidate tag can contain the edit, while the plan listed only the file and an optional `.bak`. The governing rule in `Architect.md` covers untracked instruction edits by manifest, not by branch. | Added the plan level manifest row in Target Program Files with `Sha256` and `BackupSha256`, made the `.bak-<timestamp>` backup required, and added check G13 that recomputes both hashes. |
| A2 | High | Two evidence claims were impossible. The plan said the candidate "must include the finished definition", and the matrix forced BLOCKED when "the Agentic repository is not at a commit that contains the `Infra` edit". An untracked file never appears in a tag or a commit. Related: matrix checks H3 and H4 used `git diff`, which prints nothing for an untracked file, so both would pass vacuously. | Rewrote the ordering reason and the BLOCKED condition to rest on the manifest and a read-back, and changed H3 and H4 to compare against the `.bak` baseline with `Compare-Object`. |
| A3 | High | Windows needs `--headed` for `type`, `focus`, `right-click`, `double-click`, and `triple-click`; the plan taught `type --stdin` as a headless secret path and stated broadly that ref actions are headless. A tester following the definition would hit `POLICY_DENIED` and then be tempted to force headed mode. | Added the headed set to the Windows subsection, named `set-value --stdin` as the headless text path, kept `type --stdin` as a permissioned exception, and added advisory check F7 plus a risk row that forbids headed mode as a recovery from a headless failure. |
| A4 | Medium | `list-notifications` returns `POLICY_DENIED` headless on this host when the Action Center is closed, which was confirmed by running it. The plan treated notification envelopes as an assertion and the matrix would have recorded neither a pass nor a finding. | Scoped the assertion in the definition and rewrote D11 so `POLICY_DENIED` there is a preflight state, with `--headed` only under explicit permission. |
| A5 | Medium | `permissions --guide` is the macOS grant walkthrough, stated in its own `--help` and the README, and the plan listed it in the Windows preflight. | Removed it from the preflight row and marked it macOS only, which matches the tester's existing B4. |
| A6 | Medium | `trace` was listed as an evidence producer. It is a parent command with `show` and `export` that reads session timelines, so a bare `trace` produces no evidence. | Corrected to `trace export` after a trace-enabled `session start`, and marked it optional. |
| A7 | Medium | The ref shape was never stated, and every example in the plan was the rejected form. The envelope from a real run says `Invalid ref_id '@e8': expected @<snapshot_id>:e<N>`. | Stated the qualified form in the loop subsection and in the command table, and kept the bare form only as the documented rejection case. |
| A8 | Medium | The install was unpinned while the plan's own guide-matching argument depends on a fixed version, and the matrix allowed a newer version with a delta. | Pinned `agent-desktop@1.3.1` in Target Files, the matrix install rows, and A1 and A8; A6 now requires exactly `1.3.1` and records `dist.integrity`. |
| A9 | Low | Goal 1 required `where.exe` to print exactly one path. It prints several entries for every npm global CLI on this host, three for `agent-desktop` as rc.001 confirmed, which the tester had already measured against `agent-browser`. | Rewrote goal 1 to require every printed path to sit inside the global prefix, and A2 now records the count instead of asserting it. |
| A10 | Low | Two path defects. Evidence was written as `rc.<NNNNN>` against the taxonomy's `rc.<NNN>`, and the section placement row named `## Evidence per run`, which does not exist as a level 2 heading in `tester.md`; it is `### Evidence per run` inside the browser section. | Corrected the evidence path, and specified placement after `### Reporting a browser failure` with the reason that inserting inside the browser section would split its contract. |
| A11 | Low | The plan renumbered the lifecycle stages as steps 1 to 11, then the matrix referred to "stage 10 records the candidate tag" against a table where the tag is step 9. Two numbering vocabularies invite a wrong stage reference later. | Renamed the column to `Step`, added the mapping to the canonical 16 stages, and fixed the matrix references. |
| A12 | Medium | The number this plan expected is already taken. `AVRIG-00002` is allocated to "Landing and Console Unslop Redesign": the ledger carries its row, its frontmatter says `plan_id: AVRIG-00002`, and `git ls-tree origin/main -- plans/` lists the file. A plan approved on the assumption of `00002` would collide with approved work and reuse a permanent number. | Step 4 now runs the allocation instead of taking a number on trust. The highest claimed `AVRIG` number at review time is `00002`, with no `AVRIG-00003` plan or branch present, so approval will most likely claim `00003`, and only a fresh fetch at that moment can settle it. This draft still carries no code, which is why nothing needs renaming now. |

Checked and clean: no em dash or en dash; no SemVer, tag, merge, or bump asserted before release approval; the tester still creates nothing; no product source, schema, or build configuration in scope; no UI work, so `unslop` and `modern-web-guidance` are correctly absent rather than wrongly invoked; the status value `under-review` is in the allowed vocabulary; and the draft identity is correct, with a dated filename, an empty `plan_id`, no ledger row, and no number claimed. The three open risks I did not resolve, because they belong to later stages and must not be lost: no version may be written before deployment, the step 4 gate depends on the matrix already attached here, and the manifest plus read-back is the only proof available for the untracked definition.

## Decisions Confirmed by the User

| Question | Decision |
|---|---|
| Scope of the UAT role | Desktop applications only, alongside Playwright. Playwright keeps web and SSO, `wmux browser` stays the last-resort fallback |
| Install target | Global npm install on the host, matching the existing `agent-browser` precedent |
| Documentation surface | The tester definition only. No new skill wrapper, no global `AGENTS.md` change, and the binary's own bundled guides are the authority for detail |

## Allocation and Publication Record

Allocated at approval on 2026-11-20, after `git fetch origin main --tags --prune`.

| Item | Value |
|---|---|
| Work item | `AVRIG-00003` |
| Filename | `plans/AVRIG-00003-2026-11-20-agent-desktop-uat-tooling.md` |
| Claiming branch | `chore/AVRIG-00003-agent-desktop-uat-tooling` |
| Union of sources, filtered to `AVRIG` | `00001` (archive, ledger, branch), `00002` (remote tree, ledger), so max `2`, next `3` |
| `00003` free at claim time | Confirmed absent from `origin/main -- plans/`, from the local plans tree, and from every local and remote branch |
| Release version | Empty. No version exists until deployment succeeds |

`AVRIG-00002` was already claimed by "Landing and Console Unslop Redesign" through `7ed2d73 docs(AVRIG-00002):`, pushed between this plan's first allocation scan and this approval. The scan was correct when it ran and stale when it was reused, which is exactly why the number is claimed only here, with a fresh fetch and no step in between. The analyst flagged this as finding A12 before the collision could reach a filename.

Because the definition being edited is untracked in the Agentic checkout, `.opencode/agents/` is not versioned, so no branch commit and no candidate tag can contain this plan's actual deliverable. The invitation is recorded twice rather than argued away: `plans/evidence/AVRIG-00003/instruction-manifest.json` pins `Sha256` and `BackupSha256` for the edited file, and the untracked directory itself is recorded in the ledger under Deferred defects, because versioning it is a separate decision with its own plan.

### Branch, default branch, and issue

| Repository | Default branch, and the step that decided it | Plan branch | Feature request |
|---|---|---|---|
| `avrig-ai` | `main`, by step 3: `origin/HEAD` resolves to `origin/main` and local `main` exists | `chore/AVRIG-00003-agent-desktop-uat-tooling` from `main` | [#4](https://github.com/wwidjaya/avrig-ai/issues/4), created before the branch and linked through `gh issue develop` |
| `Agentic` (`wwidjaya/agentic`) | `master`, by step 1: the checkout tracks `origin/master` and it is the only long-lived local branch. `origin/HEAD` still advertises `main`, so the disagreement is recorded rather than resolved silently | `chore/AVRIG-00003-agent-desktop-uat-tooling` from `master` | Not opened. The Agentic repository is configuration, and the work item belongs to the `avrig-ai` ledger, so its issue lives there |

### Pre-branch reconciliation

`git fetch origin --tags --prune` then an ancestry test per release tag, in `avrig-ai`:

| Release tag | `git merge-base --is-ancestor` against `refs/heads/main` |
|---|---|
| `0.2.0` | exit 0 |
| `0.2.1` | exit 0 |
| `0.3.0` | exit 0 |
| `0.4.0` | exit 0 |
| `0.5.0` | exit 0 |

Every release tag is already an ancestor, so no reconciliation merge was performed and the plan branch is cut from a default branch that already contains all released content. Candidate tags `avrig/00001/rc.001` through `rc.005` were enumerated only to confirm they are not release tags and were not merged.

The Agentic repository carries no SemVer tags, so its reconciliation table is empty and no merge is performed there.

## Deviations Recorded During Implementation

Each item below was found by running the real binary or by observing the real environment, not by reading documentation. None of them changes the plan's scope. All of them change what a future reader would otherwise believe.

| ID | Planned assumption | What was measured | Resolution |
|---|---|---|---|
| D1 | The global install succeeds without elevation, because the prefix sits under `d:\nodejs` and `node` itself is usable | `EPERM` on the first non-elevated attempt. The prefix grants `BUILTIN\Users` and `Authenticated Users` only `(I)(OI)(CI)(RX)`, and write access belongs to Administrators and SYSTEM. Every pre-existing global CLI there is admin owned, so they were all installed elevated | Installed at High integrity with explicit user approval, same command, exit 0. The manifest records `installed_elevated: true`. Matrix check A1 is corrected from "installs without elevation" to "installs, and the elevation requirement is recorded" |
| D2 | The manifest is committed on the plan branch | `plans/evidence/**` is gitignored by `.gitignore` line 50 | Staged with `git add -f`, which the ignore rule's own comment sanctions for an artifact a plan explicitly calls for. This is the first evidence file committed in this repository, so the practice is recorded rather than assumed |
| D3 | The shared `avrig-ai` checkout can host the whole plan | A concurrent session moved that checkout to `main` mid-task | The plan branch moved to a dedicated worktree, `D:\Cloud\OneDrive\AI\Agentic\AVRIG-00003\avrig-ai`, matching the `AVRIG-00002` convention already in use. The shared checkout was left untouched, and the concurrent session's modified `plans/AVRIG-00002-2026-11-20-landing-console-unslop-redesign.md` was never staged |
| D4 | `close-app "<App>.exe"` closes what the tester launched | It answers `APP_NOT_FOUND`, demanding the exact process identity, even while `list-windows --app "<App>.exe"` finds the window, because `--app` resolves against `list-apps` and a hosted application appears there as `ApplicationFrameHost.exe`. Reproduced against `CalculatorApp.exe` | The definition's `### Launch the tested artifact` was amended with the hosted application route: close through the window's own Close ref from a fresh snapshot, then confirm with `list-windows`. Amending an approved definition is a deviation, so it is recorded here and the manifest notes the single amendment |
| D5 | Any harmless built-in application is a stable smoke target | A baseline Notepad process and a launched one both disappeared before any close command ran | The smoke moved to the documented fallback, and the behaviour is recorded rather than explained away. A target that exits on its own is a finding about the host, and the observe, act, verify loop reports it as such instead of retrying |

Screenshot and `screenshot` by window are subject to the same hosted-application limit as `close-app`, so a hosted target is captured through its window ref or with the full surface rather than by process name.

## Candidate and Test Record

| Stage | Record |
|---|---|
| 7, workspace build gate | Not applicable, with the reason stated: the diff from the approval commit `1ad27f4` to the branch head contains only `plans/AVRIG-00003-2026-11-20-agent-desktop-uat-tooling.md` and `plans/evidence/AVRIG-00003/instruction-manifest.json`. No buildable source changed, so there is nothing for `cargo check --workspace` or `pnpm build` to say about this plan |
| 8, candidate tag | `avrig/00003/rc.001`, annotated, on `68520e980a10a220fed78b7a86b6ba36e63e0e36`, build id `AVRIG-00003-build.001`, pushed. The tag resolves to that commit, and it is the commit the matrix runs against |
| 9, QA | Verdict recorded once the run completes, against the tag rather than the tree |

The tag covers the manifest, and the manifest covers the definition. That chain is the only evidence available for a file the Agentic repository does not version, which is why check G13 recomputes the live hash instead of trusting the recorded one.

## QA Result and Remediation

`avrig/00003/rc.001` at `68520e980a10a220fed78b7a86b6ba36e63e0e36` returned **FAIL, 63 of 72 checks PASS, 9 FAIL, 0 BLOCKED**. The definition hash was confirmed unchanged before and after the run, and groups G and H were fully green, so the edit under test is present and intact. The failures are about the tool and the matrix, not about whether the section was written.

### The finding that matters

`agent-desktop` resolves to `agent-desktop.ps1` on this host, and that shim is `& ...agent-desktop-win32-x64.exe @args`. A PowerShell script does not forward its own pipeline into a native command it invokes, so the binary reads EOF, writes an empty string, reads the empty string back, and returns `ok: true` with `delivered_verified`. Through `agent-desktop.cmd` the value does land, but the same act reports `ACTION_FAILED` with no `value` in `post_state`.

Both directions are dangerous in a different way. The first silently loses a secret and every envelope looks healthy. The second reports failure over success and invites a retry that writes twice. The approved definition taught `set-value --stdin` as the headless secret path, which on this host is the first behaviour, so the definition as approved would have had a tester believe a credential was delivered when an empty string was.

Neither behaviour is fixable here, because the tool is a pinned third party binary. So the contract changes at the only place it can: `delivered_verified` stops being evidence, and the next snapshot becomes the assertion. That rule is correct for every shim, every platform, and every version, which is why it is the right fix rather than a workaround for one bug.

### Remediation, stage 10

| Target | Change |
|---|---|
| Definition, `### Secrets` | `--stdin` goes through `agent-desktop.cmd` or the native executable, never the `.ps1` shim, and the value is always read back |
| Definition, `### The observe, act, verify loop` | `delivered_verified` is not evidence. The following snapshot is, for every act, not only for secrets |
| Definition, `### Windows and PowerShell specifics` | `get '<ref>'` reads one named property and never reports `available_actions`, which come from the snapshot. `snapshot --app` does not raise `AMBIGUOUS_TARGET` when an application has several windows, it silently takes the focused one, so `--window-id` is pinned whenever more than one window exists |
| Definition, `### What to assert` | `wait --text` cannot match a value held in a control, so a value is asserted with `get`, not with `wait` |
| Matrix | A1 corrected for the elevation requirement, A2 for three shim entries with residency asserted instead of a count, D6 for the `get` property contract, D10 for the positional `close-app` form, E3 for the silent window choice plus a new E7 for the case that does raise `AMBIGUOUS_TARGET`, D12 for the `wait` limit, F1 and F2 replaced so the `.cmd` route is asserted to carry the value and the `.ps1` route is shown to lose it with a read-back deciding both, and the F7 against N4 contradiction resolved so no row mandates a secret in an argument list |
| Candidate | `rc.002` recut at the corrected head. `rc.001` stays in history as a failed candidate and is never moved |

`rc.002` also absorbs the bookkeeping commit that landed after `rc.001` was cut, so the tree that is finally merged is the tree that was finally tested. `rc.001` was a valid run against `68520e9` and it is not a pass for any later tree.

Two process facts were disclosed by the testing agent rather than hidden, and both are recorded rather than tidied away: a `Select-String` over the evidence logs matched its own output and grew one file to 25 GB before being killed and rewritten, and one `Start-Sleep` was used between a close and its verification instead of `wait`. Neither affects a verdict, and both are in `logs/D14-commands.txt`.
