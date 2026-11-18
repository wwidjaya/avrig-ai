---
name: calendar
description: Read and manage the user's Google Calendar (wwidjaya@gmail.com) via the calendula CLI + ortie OAuth broker over Google CalDAV. Use when asked to check/plan the agenda, schedule/book, list or create events, resolve conflicts, or manage Google Calendar events.
---

# Calendar Skill

Read and manage the user's Google Calendar through the **calendula** CLI
(Rust, pimalaya — the calendar sibling of himalaya). Events are served by
Google's **CalDAV v2** endpoint; OAuth 2.0 bearer tokens come from **ortie**
(account `calendar`, auto-refresh). Primary calendar:
`wwidjaya@gmail.com`.

> Why CalDAV and not calendula's native `gcal` (Calendar API v3 REST)
> backend? The ortie `calendar` account authenticates with Google's verified
> public **Thunderbird** OAuth client, and that shared project has the
> Calendar **API** disabled (HTTP 403). Google **CalDAV** needs no extra API
> enablement and the same `calendar` scope, so it works out of the box. Native
> `gcal` unlocks quick-add, free-busy, recurrence expansion, and calendar
> listing — requiring your own Google Cloud OAuth client (see *Upgrade*).

## Invocation

Use the wrapper — it injects `-c <skill>/calendula/config.toml`, `-a calendar`,
and `-b caldav`:

- **Windows:** `pwsh $env:OPENCODE_CONFIG_DIR/shared/skills/calendar/calendar-tool.ps1 <calendula args...>`
- **WSL/Linux:** `bash $OPENCODE_CONFIG_DIR/shared/skills/calendar/calendar-tool.sh <calendula args...>`

Append `--json` for machine-readable output. All examples below use it.

> The wrapper changes the working directory to `<skill>\calendula\` (so the
> relative `-c config.toml` survives the Windows drive-letter `:` splitting).
> **Always pass absolute paths** for `.ics` files.

## Setup

1. Install: `cargo install --locked --git https://github.com/pimalaya/calendula.git` (done).
2. OAuth (done): `ortie -a calendar auth get` in an interactive terminal
   (browser consent for `https://www.googleapis.com/auth/calendar`; token in
   `~/.config/ortie/calendar.token.json`).
3. `pwsh calendar-tool.ps1 event list --from <today> --to <+7d> --json` to confirm.

## Read

| Goal | Command |
|---|---|
| Events on a day/range | `calendar-tool.ps1 event list -k <cal> --from 2026-08-27 --to 2026-08-31 --json` |
| Day/week/month grid | `calendar-tool.ps1 event agenda -n 3` (`-1` one month, `-y` year) |
| One event | `calendar-tool.ps1 event read <UID> -k <cal> --json` (raw iCal) |

- `<cal>` defaults to `calendar.default` = `wwidjaya@gmail.com/events`;
  secondary calendars use their id from Google web UI (settings → calendar →
  "Calendar ID"), e.g. `-k somerandomid@group.calendar.google.com/events`.
- Google CalDAV does **not** enumerate calendars (`calendar list` reports
  none) — target ids must be known/pinned. `calendar list`/`create`/`update`/
  `delete` are unsupported; `gcal free-busy`, `gcal quick-add`, `gcal
  instances`, `gcal move`, `gcal calendars`/`acl`/`colors`/`settings` are the
  native-gcal surface and will 404/403 on the CalDAV backend.
- Event UIDs are stable ids (iCal `UID`); `event read/update/delete` use them.

## Write

| Goal | Command |
|---|---|
| Create | build an `.ics` file, then `calendar-tool.ps1 event create <C:\...\event.ics> -k <cal> --json` |
| Update | `event read <UID>` → edit the iCal → `calendar-tool.ps1 event update <UID> <C:\...\event.ics> -k <cal> --json` |
| Delete | `calendar-tool.ps1 event delete <UID> -k <cal> --json` |

Build `.ics` files with the `write` tool (absolute temp path), UTF-8:

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//kb//calendar//EN
BEGIN:VEVENT
UID:20260827-1000-demo@wirianto.ai
DTSTAMP:20260826T000000Z
DTSTART:20260827T100000Z
DTEND:20260827T110000Z
SUMMARY:Demo event
LOCATION:Office
DESCRIPTION:Written note
ATTENDEE:mailto:alice@example.com
RRULE:FREQ=WEEKLY;COUNT=4
END:VEVENT
END:VCALENDAR
```

- `DTSTART`/`DTEND`: UTC `...Z` (15-char basic) or explicit `TZID=...`; never
  invent timezone abbreviations. New `UID`s must be unique (e.g. date-slug).
- `event update` **overwrites** the whole event — always `event read` the
  current one first and preserve iCal fields you aren't changing.
- There is no native "quick add"/free-busy/move on CalDAV; schedule by
  computing/create days manually, and confirm by re-reading.

## Rules

1. **Confirm before writing.** `create`, `update`, `delete` need explicit user
   approval after you show a preview: title, calendar, start/end, attendees.
2. **Read before update/delete.** Always `event read` the exact UID first;
   never guess an id from a list you haven't inspected.
3. **Read-only ops run freely:** `event list/read/agenda`.
4. **Check conflicts manually** before scheduling (list the window across the
   relevant calendars) and flag overlaps rather than booking silently.
5. **Prefer UTC or explicit TZ** timestamps; never invent a timezone.
6. **Secrets.** Never print tokens, never run `ortie token show`, never commit
   `calendula/config.toml` or ortie token files.
7. Quote calendar ids and event uids in summaries so the user can verify.
8. Use `--json` for logic; render `agenda`/`list` text views when the user
   wants a readable overview.

## Upgrade (full native gcal backend, optional)

To enable `quick-add`, `free-busy`, recurrence expansion, calendar listing and
calendar creation, register your **own** Google Cloud OAuth client:

1. Google Cloud Console → enable **Google Calendar API** → OAuth consent screen
   (External, add your address as a test user) → **Desktop** OAuth client →
   download `client_secret.json`.
2. Add an ortie account (e.g. `calendar2`) with that `client-id`/`client-secret`,
   scope `https://www.googleapis.com/auth/calendar`, storage file
   `calendar2.token.json`; run `ortie auth get -a calendar2`.
3. Point `gcal.auth.token.command` at it, set `calendar.default` to a bare
   calendar id, and switch the wrappers to `-b gcal`.

## Troubleshooting

- `403 ... API has not been used / disabled`: expected for `gcal` with the
  Thunderbird client — use the CalDAV backend.
- `400 ... token` / missing token: `ortie -a calendar auth get` once.
- calendula not on PATH (pwsh): add `D:\rust\cargo\bin` to `$env:PATH`.
- Empty/unknown calendar: pin the calendar id (default is your email +
  `/events`) and use `-k <id>/events`.
- The wrapper pins `-a calendar -b caldav`; don't override `-a`.