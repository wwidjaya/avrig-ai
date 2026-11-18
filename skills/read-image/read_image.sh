#!/usr/bin/env bash
set -euo pipefail

FILE=""
PROMPT="Extract all text from this image. Preserve structure and layout."
OUTPUT=""
BASE_URL="http://localhost:20128/v1"

usage() {
    echo "Usage: $(basename "$0") --file <image> [--prompt <text>] [--output <file>] [--base-url <url>]"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --file)    FILE="$2";    shift 2 ;;
        --prompt)  PROMPT="$2";  shift 2 ;;
        --output)  OUTPUT="$2";  shift 2 ;;
        --base-url) BASE_URL="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done

if [[ -z "$FILE" ]]; then
    echo "Error: --file is required" >&2
    usage >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/read_image.py"

VENV_PYTHON="/mnt/d/miniconda3/envs/kb/bin/python"
if [[ -f "$VENV_PYTHON" ]]; then
    PYTHON="$VENV_PYTHON"
else
    PYTHON="$(command -v python3 || command -v python)"
fi

ARGS=("--file" "$FILE" "--base-url" "$BASE_URL" "--prompt" "$PROMPT")
if [[ -n "$OUTPUT" ]]; then
    ARGS+=("--output" "$OUTPUT")
fi

"$PYTHON" "$PYTHON_SCRIPT" "${ARGS[@]}"
