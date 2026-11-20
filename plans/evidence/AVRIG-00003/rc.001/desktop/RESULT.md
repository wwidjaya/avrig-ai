# RESULT: AVRIG-00003 rc.001 desktop UAT

**Verdict: FAIL.** Tag `avrig/00003/rc.001`, commit `68520e980a10a220fed78b7a86b6ba36e63e0e36`, agent-desktop CLI `1.3.1`, 63 of 72 checks PASS, 9 FAIL, 0 BLOCKED, evidence at `plans/evidence/AVRIG-00003/rc.001/desktop/`.

Envelope schema `2.6` is a schema number, not a version of anything shipped, and is kept separate from the CLI version everywhere in this folder.

## The five failures that withhold the verdict

| Check | Expected | Observed | Owning agent |
|---|---|---|---|
| A1 | `npm install -g agent-desktop@1.3.1` without elevation exits 0 and shows the postinstall step | Exit `-4048`, `EPERM mkdir d:\nodejs\.npm\global\node_modules\.agent-desktop-jpia8Jsv`. The prefix is RX-only for Users; the manifest records the elevated install. The matrix premise is wrong about the host, not the tool. | Architect, plan correction to A1 |
| D7 | The act the definition prescribes returns `ok: true` and the value lands | `'agent-desktop-uat-0001' | agent-desktop set-value '<ref>' --stdin` returns `ok: true`, `delivered_verified`, `verified: true`, and the field stays empty. The green envelope is a false positive. | Infra as installer (shim), Architect (matrix premise) |
| E3 | Two windows of one app make `snapshot --app` return `AMBIGUOUS_TARGET` with candidate window ids | `ok: true`, `window.id: w-11274556`, no error block. The tool silently snapped the focused window. | Architect, plan correction to E3 |
| F1 | The sentinel appears in the next snapshot | With the documented invocation it does not appear, and the envelope still says `delivered_verified`. With the `.cmd` shim the value appears and the envelope says `ACTION_FAILED`. No single `--stdin` invocation satisfies both the envelope and the effect. | Infra as installer, Architect as editor |
| N4 | No sentinel appears after `set-value`, `type` or `clipboard-set` in an argument list | One diagnostic step passed the fake sentinel positionally (`logs/F1-diag-positional.txt`) to isolate the shim defect. Fake value, deliberate step, still a literal N4 failure. | reported, not routed |

## The four advisory failures

| Check | Expected | Observed |
|---|---|---|
| A8 | A second install exits 0 with no duplicate shims | Exit `-4048` `EPERM`, same permissions cause as A1. Shim count stayed three. |
| C4 | Every stated call form matches the shipped guides or `--help` | Two disagree: `get '<ref>'` returns one property and never `available_actions`; `snapshot --app` does not raise `AMBIGUOUS_TARGET` for two windows. Details in `logs/C4-form-diff.txt`. |
| D12 | `wait` replaces `Start-Sleep` for the post-action settle | `wait --text "agent-desktop-uat-0001"` returns `TIMEOUT` after 30s, because document text lives in the textfield `value` and the text predicate does not read it. |
| F2 | `clipboard-set --stdin` then `clipboard-get` returns the sentinel | Through the `.ps1` shim the clipboard is empty; through `.cmd` it holds the sentinel plus a trailing CRLF added by the PowerShell pipe. |

## Root cause of the `--stdin` failures, stated plainly

`agent-desktop` resolves to `d:\nodejs\.npm\global\agent-desktop.ps1` in PowerShell (`logs/A2-getcommand.txt`), and that shim is:

```powershell
& 'd:\nodejs\.npm\global\node_modules\agent-desktop\bin\agent-desktop-win32-x64.exe' @args
exit $LASTEXITCODE
```

A PowerShell script does not forward its own pipeline input into a native command invoked inside it, so `$input` is discarded and the binary reads EOF on `--stdin`. It then sets an empty value and, because the readback also reads empty, reports `delivered_verified` with `verified: true`. A credential written that way is silently lost while every envelope looks healthy.

Running the same pipe through `agent-desktop.cmd`, or into the `.exe` directly, does deliver the value, and the tool then reports `ACTION_FAILED` with `details.kind: post_action_verification` and a `post_state` that carries no `value` field (its own readback is incomplete). Passed positionally, the same act returns `delivered_verified` with `post_state.value` populated, which is why the false negative appears only on the stdin route.

Both halves matter for the definition: its `### Secrets` and `### Windows and PowerShell specifics` sections name `set-value --stdin` piped in PowerShell as the headless default, and that exact form is the one that silently writes nothing.

## Where the matrix was wrong about the tool

1. A1 assumed the npm global prefix is user writable. It is not; the pinned install needs elevation, and the manifest says so.
2. A2 predicted two `where.exe` lines. This host prints three: the extensionless shim, `.cmd` and `.ps1`.
3. D6 said `get '<ref>'` reports declared actions. It reports one property; `available_actions` comes from the snapshot.
4. D10 said `close-app --app "Notepad"`. `close-app` takes a positional `<APP>` and rejects `--app` with `INVALID_ARGS`; the documented positional form works and was used.
5. E3 said two windows produce `AMBIGUOUS_TARGET`. They do not; the focused window is taken silently.
6. D12 assumed `wait --text` can match a value typed into a field. It cannot; text that lives in a control's `value` is invisible to that predicate.

## Definition hash, before and after

`Sha256 7AAA385ACF8AD4E867FAF69C7D9E712ABDEB62160411AE45FB6D0C9191A749B6` at the first check and at the last one, equal to the manifest row, with the backup `tester.md.bak-20261120-062939` still matching `ED5581F4DB65377B8961CC0D6A4D7F6E412A3139CA6F5D50AA10CC174C4D4F56`. Nobody edited the thing being measured. Read-back: `logs/G13-manifest-readback.txt` and `logs/G13-manifest-readback-after.txt`.

## Desktop left clean

`logs/D10-list-windows-final.txt` lists only the windows that were open before the run. Notepad and Character Map, the two applications this run opened, are gone (`envelopes/D10b-close-charmap.json`, `logs/D10-windows-after-close.txt`). No `--headed` run was left alive, and none was started.
