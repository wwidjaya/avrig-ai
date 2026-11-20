# AVRIG-00003 stage 10 final QA, candidate rc.003

Tag: `avrig/00003/rc.003`
Commit SHA: `04ee97c6a6709869787f50883bbb782cfc8b8990` (resolved with `git rev-parse "avrig/00003/rc.003^{commit}"`, equal to HEAD, worktree clean)
Installed CLI: agent-desktop `1.3.1` (envelope schema `2.6`, which is a JSON shape version and not a product version)
Verdict: **PASS**
Passed: **72 of 73** checks, 53 of 53 mandatory
Blocked: **1** (A8, advisory, recorded rather than gating)
Failed: **0**
Evidence folder: `plans/evidence/AVRIG-00003/rc.003/desktop/`

Definition under test: `D:\Cloud\OneDrive\AI\Agentic\.opencode\agents\tester.md`
Definition SHA256 before the run: `FE53CBA420BBADC24396A57C13E82B372B0421AA0315126C9060E09DF28421D6` (246 lines, 26974 bytes, matches the manifest row)
Definition SHA256 after the run: `FE53CBA420BBADC24396A57C13E82B372B0421AA0315126C9060E09DF28421D6` (unchanged)

Rows that changed since rc.002, all three now passing:
- `E3` asserts the pin only: two windows, ids from `list-windows --app`, two pinned `snapshot --window-id` runs reporting `data.window.id` equal to the pinned id in each run (`w-7145708` and `w-9046438`), no foreground claim made or needed.
- `E4` asserts repeatability: both pins repeat with the same identity, `is_focused: false` on both windows recorded as the environment limit.
- `E7` raises `AMBIGUOUS_TARGET` on both `focus-window --title` and `find --name`, with both candidate ids listed and `retry: safe`, so the error path beside E3's passing path is exercised rather than assumed.

The release trigger is reported to `build`. No tag, bump, merge or push was created by this run.
