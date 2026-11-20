# AVRIG-00003 rc.002 desktop UAT result

Result line:

    avrig/00003/rc.002 @ 60835fa209e6482b10bf9fc4e66878b775ab14a1 | agent-desktop 1.3.1 | BLOCKED on one mandatory row (E3) | 71/73 PASS, 0 FAIL, 2 BLOCKED | plans/evidence/AVRIG-00003/rc.002/desktop/

The release trigger is **not** reported, because the plan's own gate is a run with no BLOCKED row and no FAIL row (plan line 385). One mandatory row could not be produced on this host, so the candidate stays untagged-for-release and the decision returns to the orchestrator.

## Scope of the run

- Candidate tag: `avrig/00003/rc.002`, annotated, commit `60835fa209e6482b10bf9fc4e66878b775ab14a1`.
- Branch: `chore/AVRIG-00003-agent-desktop-uat-tooling`, worktree clean, tag commit equal to HEAD (`logs/RUN-FACTS.txt`).
- Definition under test: `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md`, SHA256 `2F733F260A174E4D9C4D83A101051BAEB06ECBDB3B137EC50DF62911F9007F82`, 247 lines, 26855 bytes, identical before and after the run (`logs/G13-definition-hash-pre.txt`, `logs/G13-definition-hash-post.txt`, `logs/G13-manifest-readback.txt`).
- Installed CLI: `agent-desktop 1.3.1` on Windows. Envelope schema `2.6` is a separate number and is not a product version (`logs/B3-versions.txt`, `logs/N8-version-audit.txt`).
- Host: one interactive Windows session, unelevated shell (`logs/A0-elevation.txt`), Notepad as the smoke target.
- No `--headed` command was run at any point, and no `Start-Sleep` appears in any recorded step.

## Tally

| Verdict | Count | Of which mandatory |
|---|---|---|
| PASS | 71 | 52 |
| FAIL | 0 | 0 |
| BLOCKED | 2 | 1 (E3) |
| Total | 73 | 53 |

Per-row verdicts and evidence are in `ledger.csv`. Advisory rows are the twenty named at plan line 368; every one of them is recorded with its envelope rather than left silent.

## The two BLOCKED rows

**E3 (mandatory): two windows of one app are chosen silently, by focus, and not refused.**
The row assumes a window of the application can be brought to the foreground. That premise is unreachable without physical input on this host. With two Notepad windows open (`w-1444236` "opencode.json - Notepad" and `w-4589872` "Untitled - Notepad", same pid 34320, neither focused because the terminal holds the foreground), every attempt to establish focus failed or was refused:

- `focus-window --window-id w-1444236` returns `ACTION_FAILED`, "Target window did not become foreground before headed delivery", `physical_delivery_started: false`, retry safe (`logs/E3-focus-a.json`).
- `maximize` and `restore` on the same window return `delivered_verified` for the window state but leave `is_focused: false` (`logs/E3-maximize-a.json`, `logs/E3-restore-a.json`, `logs/E3-list-windows-after-max.json`).
- `open-system-surface --surface taskbar` returns `POLICY_DENIED` headless (`logs/E3-taskbar-open.json`).

In that state the unpinned `snapshot --app "Notepad"` does not silently pick a window: it returns `ok: false` with `AMBIGUOUS_TARGET`, `candidate_count: 2`, and both window ids (`envelopes/E3-focused-a.json`). The row's expected observation, two `ok: true` snapshots each covering the window in front, therefore could not be produced. Recovery: rerun E3 in a session where a Notepad window can hold the foreground (physical input permitted), or record the deviation under user authority. `--headed` was not used as a workaround, which the plan forbids.

**A8 (advisory): reinstall is idempotent rather than duplicated.**
The second `npm install -g agent-desktop@1.3.1` fails with exit `-4048`, `EPERM` on `mkdir 'd:\nodejs\.npm\global\node_modules\.agent-desktop-jpia8Jsv'`, because the prefix ACL grants `Users` and `Authenticated Users` RX only (`logs/A1-acl.txt`) and this shell is unelevated. No duplicate was created and the shim set is still exactly `agent-desktop`, `agent-desktop.cmd`, `agent-desktop.ps1` (`logs/A8-reinstall.txt`), but the row asks for exit `0`, which this host cannot produce without elevation. Recovery: run the same command from an elevated PowerShell. Recorded as BLOCKED rather than FAIL because the outcome says nothing about the artifact under test.

## Findings, including one definition defect

1. **The definition sentence about `snapshot --app` is over-broad (routes to the Architect as a definition correction; C4).** The section states that `snapshot --app` does not raise `AMBIGUOUS_TARGET` when an application has several windows, and silently takes the focused window. Measured on 1.3.1: with several windows and none focused it does raise `AMBIGUOUS_TARGET` and names every candidate (`envelopes/E3-focused-a.json`). The silent pick happens only when one of that app's windows already holds focus. The remedy the section gives, pin `--window-id` whenever `list-windows` shows more than one window, stays correct and is what E4 exercises (`envelopes/E4-window-id.json`). Suggested edit: qualify the sentence rather than delete the remedy.

2. **The `.ps1` shim loses a piped value while every field in its envelope looks correct (F2, definition confirmed).** `'uat-secret-0002' | agent-desktop.ps1 set-value '<ref>' --stdin` returns `ok: true`, `disposition.delivery: delivered_verified`, `steps[0].verified: true`, and the read-back snapshot plus `get --property value` show the field empty, having emptied a field that held a value (`envelopes/F2-ps1-set-value.json`, `snapshots/F2-snapshot-readback.json`, `envelopes/F2-readback.json`, `logs/F2-routes.txt`). This is exactly the failure the definition's shim rule exists to prevent.

3. **The `.cmd` route delivers but reports failure (F1, known false negative, now reproduced).** `agent-desktop.cmd` returns `ok: false`, `ACTION_FAILED`, `delivered_unverified`, `retry: unsafe`, with no `post_state.value`, while the following snapshot and `get --property value` both hold the sentinel exactly (`envelopes/F1-cmd-set-value.json`, `snapshots/F1-snapshot-after-cmd.json`, `envelopes/F1-readback.json`). Verdict is taken from the read-back, never from `delivered_verified`.

4. **Host finding: the first Notepad process exited on its own (D5, plan deviation recorded).** After a click on the `opencode.json` tab, `list-windows --app Notepad` and `list-apps --app notepad.exe` both returned empty, and snapshot answered `WINDOW_NOT_FOUND` (`retry: safe`) for a HWND that had failed process-instance corroboration (`logs/E0-notepad-exit.txt`, `snapshots/E2-snapshot-opencode-selected.json`). A fresh Notepad was launched rather than retrying the dead one. The plan already records this host behaviour as deviation D5.

5. **The definition's action-and-ref discipline holds end to end.** `click '@e8'` is refused with `INVALID_ARGS` naming the expected shape; a ref captured before a `--root` redrill is refused with `STALE_REF` and followed by a fresh snapshot rather than a second attempt; `focus-window --title 'Notepad'`, `find --app Notepad --name File` and an unpinned `snapshot --app` all raise `AMBIGUOUS_TARGET` with the candidate list, and the recovery is always `list-windows` plus a pinned `--window-id`. See `envelopes/E1-bare-ref.json`, `envelopes/E2-stale-ref.json`, `logs/E5-recovery-order.txt`, `logs/E6-dispositions.txt`, `logs/E7-ambiguous-probe.txt`.

6. **Three matrix-quoting defects, worked around and recorded rather than silently repaired.** `focus-window` takes `--title`, `--window-id` or `--app` and no positional title; `find` takes `--name`, `--value`, `--text` or `--role` and no positional query (`logs/help-focus-window.txt`, `logs/help-find.txt`). A2's "three entries from `where.exe`" is wrong: `where.exe` prints two, the extensionless shim and the `.cmd`, and the third shim is what PowerShell's command resolution picks instead (`logs/A2-where.txt`, `logs/A2-getcommand.txt`). All three are plan wording, not product behaviour.

7. **`permissions --guide` is macOS-only, as the matrix expects.** It returns `PLATFORM_NOT_SUPPORTED start_permission_guide` on Windows while plain `permissions` returns `ok: true` (`envelopes/B4-permissions.json`, `logs/B4-permissions-guide.txt`). `list-notifications` returns `POLICY_DENIED` because the Action Center is closed and headless observation cannot open it, which the matrix records as a preflight state rather than a failure (`envelopes/D11-notifications.json`).

8. **The plan's `candidate_tags` ledger records `avrig/00003/rc.002` without its commit SHA (routes to the Architect).** The entry reads `"avrig/00003/rc.002 (AVRIG-00003-build.002), cut after the remediation set landed"`, while the `rc.001` entry above it carries `@ 68520e980a10a220fed78b7a86b6ba36e63e0e36`. The SHA this run resolved and tested is `60835fa209e6482b10bf9fc4e66878b775ab14a1` (`logs/RUN-FACTS.txt`); it belongs in that line. The plan was not edited by this run, by design.

## What was not tested

- E3's silent-pick observation, for the reason above.
- A8's elevated idempotency, for the reason above. The install that produced the tested 1.3.1 tree is attested by the manifest (`installed_elevated: true`) and by the installed artifacts (`logs/A1-install.txt`), not re-observed here.

No other row is silent: every remaining row has a verdict, an envelope or log, and a note in `ledger.csv`.

## Evidence index

- `ledger.csv`: 73 rows, `id,verdict,evidence,note`.
- `version.json`, `status.json`: preflight envelopes; `logs/`: 98 audit and invocation files; `envelopes/`: 42 envelopes, all parsing as one JSON object with `version`, `ok`, `command` (`logs/D13-envelope-audit.txt`); `snapshots/`: 15 snapshot envelopes.
- `screens/D9-after-act.png`, `screens/F4-cleared.png`: supporting images only, never the assertion.
- `guide-desktop.txt`, `guide-platform.txt`: the bundled guides exactly as retrieved, decoded at `logs/C1-desktop-guide-content.txt` and `logs/C2-platform-guide-content.txt`.
- `logs/D14-commands.txt`: the full command sequence in order, each step tied to its envelope.
- `logs/N1-ledger-audit.txt` through `logs/N8-version-audit.txt`: the negative checks that keep the green rows honest.

## Goals check against the plan's six objectives

This is the tester's own reading of `## Goals and Objectives`, recorded here because the analyst handoff could not be made from this session (the subagent depth limit refused it). It is offered as input to that audit, not as a substitute for it: the analyst still appends its finding to the plan's `## Review Findings`.

| Goal | Status | Deciding artefact |
|---|---|---|
| 1. `agent-desktop` resolves from a plain shell, every path inside `d:\nodejs\.npm\global`, `version` and `status` report `ok: true`, bundled guides served | Met | `envelopes/A5-version-noprofile.json`, `logs/A2-where.txt` (two `where.exe` paths, the third shim resolved by `Get-Command`), `envelopes/B1-version.json`, `status.json`, `guide-desktop.txt`, `guide-platform.txt`. The goal says the count is recorded rather than asserted, and it is: two, not the three the matrix row claims. |
| 2. A real observe, act, verify loop against one live application, with snapshot, action, second snapshot, screenshot, every envelope saved | Met | `snapshots/D8-snapshot-verify.json` (value and window title carry the sentinel), `envelopes/D7-act.json`, `screens/D9-after-act.png`, `envelopes/D12-wait-value.json`. |
| 3. The definition carries an executable Desktop UAT contract covering applicability, call forms, ref lifecycle, secret rule, evidence layout, not-applicable path | Met | `logs/G2-headings.txt` (one section, after the browser contract), `logs/G3-subsections.txt` (eleven, in plan order), `logs/G9-forms.txt` (all fourteen literals), `logs/G11-evidence-text.txt`, `logs/G7-boundary.txt`. One stated behaviour in it is over-broad and is reported as finding 1. |
| 4. The web path is unchanged and both harnesses are required where both surfaces exist | Met | `logs/H1-browser-headings.txt`, `logs/H3-wmux-diff.txt` (zero differences in the fallback subsection), `logs/H4-diff.txt` (four intended edits only), `logs/G8-harness-choice.txt` (desktop is numbered choice 3). |
| 5. No product source, schema, migration, or build configuration change | Met | `logs/N7-ownership.txt`: worktree clean, zero tracked changes, zero new entries in the Agentic checkout, definition hash identical before and after. |
| 6. The pairing rule is written down so no future tester marks a native surface not applicable because Playwright cannot see it | Met | `logs/G7-boundary.txt` and the second bullet of Responsibilities item 3 (`logs/G6-item3-bullets.txt`); enforced in this run by `logs/N2-not-applicable-audit.txt`. |

The plan's pass gate is not met as written: E3 is mandatory and BLOCKED. Goals 1 to 6 are nonetheless each backed by an artefact, so the work the plan set out to do is present and executable; what is missing is one observation that this host cannot produce.

## Reproduction

From `plans/evidence/AVRIG-00003/rc.002/desktop/logs/D14-commands.txt`, with `agent-desktop 1.3.1` on `PATH` and the definition at the SHA above. Elevation and a foreground-capable session are the two prerequisites this run lacked.
