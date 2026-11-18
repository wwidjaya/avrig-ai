# Config editing: headless + pane, with guardrails

## When to use which path

- **GUI pane** — a running `zerocode` session exists and you want validation + live apply. Edit inline; no daemon restart.
- **Headless TOML** — terminal / headless host / scripted provisioning, or when no GUI is available. Validate the file manually before save.

For this install the config is non-default: `D:\agentic\config.toml` (runtime default is `~/.zeroclaw/`). Always resolve first.

## Safe merge rules (headless)

ZeroClaw config deserializes keyed tables `[section.alias]`. Merge, never clobber:

- **Add a new section** — append at end of file. New bundle example:
  ```toml
  [skill_bundles.pa]
  directory = "D:\agentic\shared\skills\pa"
  ```
  The alias is picked up on next config read; no restart required for bundle attach.
- **Append to existing list** — e.g. `skill_bundles = ["mail"]` becomes `["mail", "new-bundle"]`. Keep order, do not drop prior entries.
- **Never overwrite a running value without re-checking.** Runtime profiles enforce ceilings; bumping `max_actions_per_hour`, `max_cost_per_day_cents`, `message_timeout_secs`, `shell_timeout_secs`, or workspace paths silently can drop tool calls mid-turn. Re-read the affected agent after editing.
- **Secrets are opaque here.** Tokens use opaque prefixes (`enc2:`). Never print, diff-match, or rotate them casually. Confirm presence unchanged before save.

## Validate before save (headless)

1. Parse TOML - file loads without error.
2. No duplicate section header (`[agents.pa]` must appear once).
3. Target section present and keyed (`[skill_bundles.pa]`, `[channels.telegram.pa]`).
4. Secret strings still present, byte-identical.
5. Diff before/after - only intended lines changed; no accidental blank-line merges.

```powershell
# diff only if you made an edit; abort if secret/token lines moved
git diff -- "D:\agentic\config.toml"
```

Reload and confirm (all CLI calls need `--config-dir "D:\agentic"` - the binary defaults to `~/.zeroclaw/` and will not read our file):

```powershell
& "D:\agentic\zeroclaw.exe" config list --config-dir "D:\agentic"   # no load error
& "D:\agentic\zeroclaw.exe" skills list --agent pa                           # bundle now loaded
```

## GUI pane (zerocode)

Open a `zerocode` session. The **Config** pane exposes typed controls for running settings:

- Validation rejects malformed values before they reach the daemon - a typo cannot leave config in a fails-load state.
- Most fields apply live on the next frame, no restart; values persist to config.
- Registry-backed choices (provider/model/channel/theme) show only what this build supports - use those, not hand-typed alternatives.
- Read descriptions on the saved result before editing a field - they explain the key.
- Not every field is in the pane: daemon-owned sections still require headless edit.

## Common edits and where they live

- Add/attach skill bundle -> `[skill_bundles.pa]` + alias in `[agents.pa].skill_bundles`.
- Enable channel instance (e.g. discord) -> `[channels.discord.pa] enabled = true` + its `[providers.models...]`.
- Swap model provider for an agent -> `agents.pa.model_provider = "<provider>.<alias>"` and define that provider.
- Tighten autonomy -> edit `risk_profiles.pa` (`level`, `auto_approve`, `allowed_commands`, `block_high_risk_commands`).
- Tune runtime behavior -> `[runtime_profiles.default.<sub-profile>]` (tool_receipts, context_compression, thinking, history_pruning).

## Guardrails

- Do not hand-edit sections the pane owns if a session is open; avoid races.
- Keep `[agents.pa]` keyed block intact - it carries channels, identity, memory, risk, workspace.
- One change at a time; verify after each so the diff stays reversible.
