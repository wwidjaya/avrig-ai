#!/usr/bin/env bash
# Gmail skill wrapper (WSL/Linux) — runs himalaya against the skill-local config.
# Pass-through that pins account `gmail` and the skill-local config.
# cd into the config dir so `-c config.toml` stays relative (avoids PATH-style
# `:` splitting). Pass ABSOLUTE paths for --body-file / --attach / -d.
set -euo pipefail

dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/himalaya" && pwd)"

if [[ ! -f "$dir/config.toml" ]]; then
    echo "Config not found: $dir/config.toml — copy himalaya/config.toml.example to himalaya/config.toml and fill it in first." >&2
    exit 1
fi

if ! command -v himalaya >/dev/null 2>&1; then
    echo "himalaya not found on PATH (install: cargo install --locked --git https://github.com/pimalaya/himalaya.git)." >&2
    exit 1
fi

# Select the account (default gmail) with -Account/--account <name>.
account="gmail"
if [[ "${1:-}" == "-Account" ]] || [[ "${1:-}" == "--account" ]]; then
    account="${2:-gmail}"
    shift 2
fi

cd "$dir"
exec himalaya -c config.toml -a "$account" "$@"