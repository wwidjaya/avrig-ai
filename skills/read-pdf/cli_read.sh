#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read_script="$script_dir/read_pdf.py"

# Resolve venv python from OPENCODE_CONFIG_DIR relative path
venv_python="${VENV_PYTHON:-$script_dir/../../../../Development/kb/ai-system/.venv/bin/python}"

if [[ ! -f "$venv_python" ]]; then
    echo "Python venv not found at: $venv_python" >&2
    echo "Set VENV_PYTHON environment variable." >&2
    exit 1
fi

exec "$venv_python" "$read_script" "$@"
