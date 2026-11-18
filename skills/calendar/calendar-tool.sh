#!/usr/bin/env bash
# Calendar skill wrapper (WSL/Linux) — runs calendula against the skill-local config.
# Pass-through that pins account `calendar`, backend `gcal`, and the skill-local
# config. cd into the config dir so `-c config.toml` stays relative (avoids the
# PATH-style `:` splitting). Pass ABSOLUTE paths for any <ICAL> / file args.
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/calendula" && pwd)"

if [[ ! -f "$dir/config.toml" ]]; then
    echo "Config not found: $dir/config.toml — copy calendula/config.toml.example to calendula/config.toml and fill it in first." >&2
    exit 1
fi

if ! command -v calendula >/dev/null 2>&1; then
    echo "calendula not found on PATH (install: cargo install --locked --git https://github.com/pimalaya/calendula.git)." >&2
    exit 1
fi

cd "$dir"
exec calendula -c config.toml -a calendar -b caldav "$@"