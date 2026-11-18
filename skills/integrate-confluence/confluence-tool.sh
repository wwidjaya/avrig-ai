#!/usr/bin/env bash
#
# Confluence Cloud connector wrapper (Linux/WSL).
#
# Runs the Python Confluence connector. Credentials come from confluence.env
# next to this script.
#
# Subcommands:
#   space resolve [--key KEY]
#   search       -q "text" [--limit N] [--space KEY]
#   get          -page-id N [--body json|none]
#   create       [-title T] [-parent-id N] [-space-id S] [-no-full-width] -doc FILE.json
#   update       -page-id N [-title T] [-version N] -doc FILE.json
#   append       -page-id N -doc FILE.json
#   full-width   -page-id N
#
# Bodies use Confluence storage format (table widths in px, default 1800px).
# New pages are created at maximum (full) width by default — the connector
# sets the content-appearance-* properties to full-width. Pass --no-full-width
# to create at the default fixed width instead.
# Title falls back to the model `title` (from note frontmatter), then the
# existing page title (update).
#
# Usage:
#   bash confluence-tool.sh space resolve
#   bash confluence-tool.sh search -q "User Roles"
#   bash confluence-tool.sh get -page-id 12345
#   bash confluence-tool.sh create -title "New Page" -parent-id 12345 -doc doc.json
#   bash confluence-tool.sh update -page-id 12345 -version 3 -doc doc.json
#   bash confluence-tool.sh append -page-id 12345 -doc section.json
#   bash confluence-tool.sh full-width -page-id 12345
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="$SCRIPT_DIR/confluence_tool.py"

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <space|search|get|create|update|append|full-width> [args...]" >&2
  exit 1
fi

python3 "$PY_SCRIPT" "$@"
