---
name: manage-zeroclaw
description: Manage and customize a running ZeroClaw install, including upgrading the binary, adding skills, editing channels/provider/risk/runtime config, and wiring bundles to agents. Use when asked to update or upgrade ZeroClaw, customize its config, add skill bundles, expose or hide the gateway, inspect skill loading, patch TOML safely, or reconcile config with docs.
---

# manage-zeroclaw

Edit the live ZeroClaw install without breaking what already runs. Every change preserves existing secrets, keyed agent blocks (`[agents.pa]`), and `skill_bundles`. Validate then reload.

## Resolve roots first (readonly)

Before touching anything confirm the two paths below match this install - do not guess:

- `<install>` = `D:\agentic` (where `config.toml`, `state/`, `shared/`, and `zeroclaw.exe` live).
- Config = `D:\agentic\config.toml`. **Non-default** - runtime default is `~/.zeroclaw/`. Verify it loads first, else edits miss the active file.

Verify both (binary is NOT on PATH; invoke via `& "D:\agentic\zeroclaw.exe"`):

```powershell
$B = "D:\agentic\zeroclaw.exe"
# confirm this config dir resolves and parses (no load error)
& $B config list --config-dir "D:\agentic"
# baseline: what pa loads before changes
& $B skills list --agent pa
```

**`--config-dir` is required.** The bare binary defaults to the runtime default (`~/.zeroclaw/`) and will NOT read our file - every CLI call must pass `--config-dir "D:\agentic"`. Do not use `--path` (removed). Re-run after any config change to confirm it still loads.

If `skills list` errors, the config path did not resolve - fix default or point runtime at it before continuing.

## Upgrade ZeroClaw

The built-in updater is the preferred method. It downloads the latest release, verifies its checksum, backs up the current executable, validates the replacement, swaps it, and runs a smoke test with rollback on failure.

1. Resolve `<install>` and config as above. Confirm the active config with `config list --config-dir <install>`; never run an updater against an assumed default config directory.
2. Record the current version and check the latest release without changing anything:

   ```powershell
   $B = "D:\agentic\zeroclaw.exe"
   & $B --version
   & $B update --check --config-dir "D:\agentic" --json
   ```

   Review the reported version and release notes, especially breaking changes. If the installed binary does not support `update`, stop and consult the official installation instructions for that platform rather than downloading an arbitrary binary.

3. Before upgrading, make a timestamped copy of `config.toml` in the install directory. Preserve the updater's own executable backup. Do not stop or restart a service unless the release procedure requires it.
4. Apply the latest release through the built-in updater, explicitly targeting the install's config directory:

   ```powershell
   & $B update --config-dir "D:\agentic" --verbose
   ```

   For a specific release, use `--version <version>`. Do not use `--force` unless reinstalling or intentionally downgrading. Confirm the updater reports success; it handles download validation, binary replacement, and rollback.

5. Verify the new binary version and load the active config:

   ```powershell
   & $B --version
   & $B config list --config-dir "D:\agentic"
   ```

6. If release notes require a config migration, read those notes before running it. For schema v4 releases, migrate once with `config migrate --config-dir <install> --json`; this rewrites config and creates backups, including a versioned downgrade copy. Inspect migration output, then rerun `config list` and the relevant agent/skill checks. Keep downgrade backups until no longer needed; they may contain retired keys or plaintext secrets. Do not delete backups automatically.

7. If any verification fails, stop and report the error and backup locations. Do not restore or overwrite config blindly; the updater rolls back the executable on its own smoke-test failure, but config migration is a separate operation.

## Skills / bundles (attach)

Three load locations. For agent `pa`:

- Per-agent workspace: `<install>/agents/pa/workspace/skills/<name>/`.
- Shared bundle: `<install>/shared/skills/pa/<name>/`. Loaded when alias listed in `[skill_bundles.pa]`. Bundle default dir resolves to `<install>/shared/skills/pa/` when `directory` omitted.
- Global: `<install>/data/skills/<name>/`. CLI-installed only - **not** auto-loaded by agents.

Invoke the binary directly: it is `D:\agentic\zeroclaw.exe` and is not on PATH (use `& "D:\agentic\zeroclaw.exe" ...`).

Skills subcommands: `list add edit bundle audit install remove test`.

Install from local dir, Git catalog URL, or registry name:

```powershell
& "D:\agentic\zeroclaw.exe" skills install ./path --bundle pa
& "D:\agentic\zeroclaw.exe" skills install <git-url> --bundle pa
& "D:\agentic\zeroclaw.exe" skills install <registry-name> --agent pa          # falls back to <install>/data/skills/ when no --bundle
```

Install destination precedence: explicit `--bundle`, else the target agent's single assigned bundle (omit `--bundle` only when it has one), else global. Multi-bundle agents require `--bundle`.

Add an empty skill scaffold from scratch:

```powershell
& "D:\agentic\zeroclaw.exe" skills add
```

Audit before trust, never trust blindly:

```powershell
& "D:\agentic\zeroclaw.exe" skills audit ./local-skill-or-name
```

Install destination precedence: explicit `--bundle`, else the target agent's single assigned bundle (omit `--bundle` only when it has one), else global. Multi-bundle agents require `--bundle`.

Audit before trust, never trust blindly:

```powershell
& "D:\agentic\zeroclaw.exe" skills audit ./local-skill-or-name
```

Scripts in skills are blocked by default unless config sets `[skills] allow_scripts = true` (this install already does). Gate any script-bearing skill explicitly. Community loading opt-in via `open_skills_dir` - do not enable unless source reviewed.

## Modify config

Two paths, pick per case. Prefer GUI pane when a running zerocode session exists - it validates and applies live. Use headless edits only for terminal/headless hosts or scripted provisioning.

### Headless: edit TOML directly

Schema-aware merge. Insert or extend keyed tables; preserve existing `[agents.pa]`, `skill_bundles`, secrets, and `[runtime_profiles.default]`. Do not overwrite values a running agent depends on without re-checking thresholds (`max_actions_per_hour`, `max_cost_per_day_cents`).

Rules:

- Add a new section rather than edit inline. Append `[skill_bundles.pa]` at end of file for a new bundle; it is picked up config reads.
- Append aliases to existing `skill_bundles = ["mail"]` -> `["mail", "new-bundle"]`. Never reorder or drop prior entries.
- Reference authoritative key/defaults from the config schema reference (see `references/schema.md`) - do not guess undocumented keys.
- Validate before save: load the file, confirm TOML parses and no duplicate section header, confirm secret strings (`enc2:` tokens) still present unchanged.

### GUI pane: zerocode

Running pane offers typed control with inline validation; most fields apply live on next frame without daemon restart, values persist to config. Open the session, edit inline, read descriptions on the saved result - do not hand-edit a file while pane owns that field.

### Context window for OpenAI-compatible local models

If a known-large-context model returns "request exceeds the selected model's context window," check the model metadata and provider config. The server may not advertise the model's actual context capacity, and ZeroClaw may otherwise infer a smaller limit. For a model verified to support 256k tokens, explicitly set:

```powershell
& "D:\agentic\zeroclaw.exe" config set providers.models.openai.main.context_window 262144 --config-dir "D:\agentic"
& "D:\agentic\zeroclaw.exe" config list --config-dir "D:\agentic"
```

Use the actual supported token limit, not this example value, and only set it after confirming the backend model can accept that context. This setting is distinct from `max_tokens`, which controls generated output. Re-test the request after saving; do not claim the backend's limit was independently verified merely because ZeroClaw accepted the config value.

## Verify (always last)

After any change:

```powershell
& "D:\agentic\zeroclaw.exe" skills list --agent pa            # all bundles present under <install>/shared/skills/pa/
& "D:\agentic\zeroclaw.exe" skills list --bundle pa
& "D:\agentic\zeroclaw.exe" config list --config-dir "D:\agentic"   # no load error
```

No skill listed means it is in the global group only - re-run install with `--bundle pa`. Confirm agent runtime sees it (channel/agent response), not just CLI listing.

## Author new skills

Repo skill-creator loop: draft `SKILL.md`/`SKILL.toml` -> write 2-3 test prompts to `evals.json` -> run with-skill + baseline in parallel -> grade -> aggregate -> `generate_review.py` viewer for human sign-off -> iterate. Keep SKILL.md under 500 lines; push detail into `references/`. Frontmatter fields supported: `name, description, author, version, tags, always, slash_options`. `always: true` keeps full instructions inline system prompt in compact mode (safety-critical only).
