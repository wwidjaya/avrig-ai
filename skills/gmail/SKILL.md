---
name: gmail
description: Send, read, search, draft, label, and delete the user's Google email (wwidjaya@gmail.com and wirianto.widjaja@composync.id) via the himalaya CLI + ortie OAuth broker over the Gmail REST API. Use when asked to send/email, reply, forward, check/search/read mail, list inbox/unread/drafts, or manage labels, flags, trash, or threads.
---

# Gmail Skill

Send and manage the user's Google mailboxes through the **himalaya** CLI
(Rust) against the **Gmail REST API** (labels as mailboxes, Gmail query
syntax). OAuth 2.0 access tokens are supplied by **ortie** and auto-refreshed.
Two accounts are configured:

| Alias | Address | Notes |
|---|---|---|
| `gmail` | `wwidjaya@gmail.com` | default account |
| `composync` | `wirianto.widjaja@composync.id` | Google Workspace account |

Software already installed and configured:

- `himalaya` v2 at `D:\rust\cargo\bin` (`himalaya --version`)
- `ortie` (OAuth broker) at `D:\rust\cargo\bin`
- skill-local himalaya config at `himalaya/config.toml` (gitignored)
- ortie config at `~/.config/ortie/config.toml` (tokens in
  `~/.config/ortie/<alias>.token.json`, out of the repo)

## Invocation

Use the wrapper — it injects `-c <skill>/himalaya/config.toml` and the chosen
account (`-a`). Pass `-Account <alias>` to pick a mailbox; it defaults to
`gmail`:

- **Windows:** `powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" [-Account <alias>] <himalaya args...>`
- **WSL/Linux:** `bash $OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.sh [-Account <alias>] <himalaya args...>`

Run against `composync` with `-Account composync`, e.g.:

```
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" -Account composync gmail messages list -q "is:inbox is:unread" -s 5 --json
```

The wrapper is a pass-through; append `--json` when you want machine-readable
output. All examples below use the wrapper (default account `gmail`).

> The wrapper changes the working directory to `<skill>\himalaya\` (so the
> relative `-c config.toml` survives the Windows drive-letter `:` splitting).
> **Always pass absolute paths** for `--body-file`, `--attach`, and `-d`.

## Setup (one-time, already largely done)

1. Install binaries (done): `cargo install --locked --git https://github.com/pimalaya/himalaya.git`
   and `cargo install --locked ortie`.
2. OAuth (done): ortie accounts `gmail` and `composync` are configured with
   Google's verified public Thunderbird client — no Google Cloud Console setup
   needed. `himalaya gmail ...` calls `ortie token show`, which auto-refreshes.
3. Verify with:
   ```
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" account check
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" -Account composync account check
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" gmail messages list -q "is:inbox is:unread" -s 5 --json
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" -Account composync gmail messages list -q "is:inbox is:unread" -s 5 --json
   ```
   If one is missing/broken, re-run the OAuth consent once (always pass the
   alias, both on `get` and `resume`):
   `ortie auth get -a gmail` / `ortie auth get -a composync` (browser sign-in
   as the matching address).

> The running opencode session loaded skills at start; **restart opencode** if
> this skill was just created.

## Read / search

| Goal | Command |
|---|---|
| Search (Gmail query) | `gmail-tool.ps1 gmail messages list -q "<query>" [-l <label>] [-s 20] [--include-spam-trash] --json` |
| Browse a label | `gmail-tool.ps1 envelope list -m <alias\|label> -s 20 --json` |
| Read one message | `gmail-tool.ps1 gmail messages get <ID> --format full --json` (raw / metadata / minimal) |
| Human-readable read | `gmail-tool.ps1 message read <ID>` (`--raw` raw RFC5322, `--seen` marks read) |
| Headers only | `gmail-tool.ps1 gmail messages get <ID> --format metadata --header From --header Subject --json` |
| Whole thread | `gmail-tool.ps1 gmail threads get <TID> --json` |
| List labels | `gmail-tool.ps1 gmail labels list --json` |
| Attachments | `gmail-tool.ps1 attachment list <ID> --json`; `gmail-tool.ps1 attachment download <ID> <ATT...> -d <dir>` |
| Drafts | `gmail-tool.ps1 gmail drafts list [-q "<query>"] [-s 20] --json` |

Gmail query syntax: `from:`, `to:`, `subject:`, `label:`, `has:attachment`,
`is:unread|read|starred|important|inbox`, `newer_than:7d`, `older_than:2y`,
`after:/before:yyyy/mm/dd`. Combine with spaces.

## Send

| Goal | Command |
|---|---|
| New email | `gmail-tool.ps1 message compose -t "a@x.com, b@x.com" [--cc ..] [--bcc ..] -s "Subject" --body-file <file> [--attach <file> ...] --send` |
| Reply | `gmail-tool.ps1 message reply <ID> --body-file <file> [-P top\|bottom] --send` |
| Forward | `gmail-tool.ps1 message forward <ID> -t "c@x.com" --body-file <file> --send` |
| Send as alias | add `--from "Name <alias@domain>"` (only for verified "Send mail as" addresses) |

- Write the email body to a temp file and pass `--body-file` — this sidesteps
  shell quoting/encoding problems and stays UTF-8 clean. Use the `write` tool,
  never PowerShell `Set-Content`/`Get-Content` round-trips (mojibake).
- `message reply`/`forward` automatically set `Re:`/`Fwd:`, `In-Reply-To`/
  `References`, and (reply) quote the original — thread continuity is handled.
- Send returns the new Gmail message/thread ids with `--json`.

## Drafts

| Goal | Command |
|---|---|
| Draft new | `gmail-tool.ps1 message compose -t .. -s .. --body-file <file> --save DRAFT` |
| Draft (threaded) | write composed bytes to msg.eml, then `gmail-tool.ps1 gmail drafts create --thread-id <TID> -- msg.eml` |
| Read draft | `gmail-tool.ps1 gmail drafts get <ID> --format raw --json` |
| Send draft | `gmail-tool.ps1 gmail drafts send <ID>` |
| Delete draft | `gmail-tool.ps1 gmail drafts delete <ID>` |

To produce `msg.eml` byte-exactly on Windows, run the composer under
`cmd /c`: `cmd /c pwsh -NoProfile -File "$env:OPENCODE_CONFIG_DIR/shared/skills/gmail/gmail-tool.ps1" message compose -t .. -s .. --body-file body.txt > msg.eml`.

## Manage

| Goal | Command |
|---|---|
| Mark read/unread | `gmail-tool.ps1 flag add --flag seen <IDs...>` / `gmail-tool.ps1 flag remove --flag seen <IDs...>` |
| Star / urgent | `flag add --flag flagged <IDs...>` / `flag set --flag flagged <IDs...>` |
| Apply/remove labels | `gmail-tool.ps1 gmail messages modify <ID> --add-label <LABEL> --remove-label <LABEL>` |
| Trash / restore | `gmail-tool.ps1 gmail messages trash <ID>` / `gmail messages untrash <ID>` |
| Permanent delete | `gmail-tool.ps1 gmail messages delete <ID>` (batch: `gmail messages batch-delete --ids ...`) |
| Thread-level | `gmail threads trash|untrash|delete|modify <TID> [--add-label ..]` |
| Create label | `gmail-tool.ps1 gmail labels create` (see `--help`) |

Label ids: `gmail labels list --json` returns `id` + `name`. The `modify`
`--add-label`/`--remove-label` flags accept either. System ids: `INBOX`,
`UNREAD`, `STARRED`, `IMPORTANT`, `SENT`, `DRAFT`, `TRASH`, `SPAM`,
`ALL_MAIL` (archive).

## Rules

1. **Read before write.** For send/reply/forward/delete: identify the message
   by exact id (`gmail messages get`/`threads get`), then confirm the action
   with the user. Never guess an id from memory.
2. **Send/reply/forward = confirmation-required.** Show recipients, subject, and
   body preview; obtain explicit user approval before `--send`. For sensitive or
   uncertain content prefer saving a draft first (`--save DRAFT`) and letting the
   user review.
3. **Never email external addresses on the assistant's own initiative.** Only
   send to recipients the user named or clearly implied.
4. **Destructive ops confirm first.** Prefer `trash`/`untrash` and label changes
   over permanent `delete`/`batch-delete`. Confirm before any delete.
5. **Preserve originals.** Never modify a message's labels/flags without asking
   unless the user asked for that change.
6. **Quoting.** Quote exact message ids and the target mailbox/label in
   summaries so the user can verify.
7. **Secrets.** Never print tokens, never run `ortie token show` (himalaya does
   that internally), and never commit `himalaya/config.toml` or ortie token
   files.
8. **Attachments.** Don't download unexpected attachments; save downloads to a
   temp or user-designated dir; don't open files that could be malware unless
   the user asks.
9. Use `--json` for logic; it makes ids and fields parseable. When not asked,
   prefer concise human-readable summaries over raw dumps.
10. First unread check before claiming the user's inbox: `gmail messages list
   -q "is:inbox is:unread" -s 5 --json`.

## Troubleshooting

- `400 ... token`: re-authorize once with `ortie auth get -a gmail` (or
  `-a composync`, matching the broken account).
- himalaya not on PATH (Windows PowerShell): add `D:\rust\cargo\bin` to `$env:PATH`.
- Wrong account: the wrapper pins the account from `-Account` (default
  `gmail`); don't mix it up with himalaya's own `-a`.
