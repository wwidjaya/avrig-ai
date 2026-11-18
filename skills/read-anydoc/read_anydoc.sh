#!/usr/bin/env bash
set -euo pipefail

FILE=""
OUTPUT=""
FORMAT=""
DPI=200
OCR_MODEL="ocr"
OCR_BASE_URL="http://localhost:20128/v1"
KEEP_IMAGES=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output) OUTPUT="$2"; shift 2 ;;
        --format) FORMAT="$2"; shift 2 ;;
        --dpi) DPI="$2"; shift 2 ;;
        --ocr-model) OCR_MODEL="$2"; shift 2 ;;
        --ocr-base-url) OCR_BASE_URL="$2"; shift 2 ;;
        --keep-images) KEEP_IMAGES=true; shift ;;
        *) FILE="$1"; shift ;;
    esac
done

[[ -z "$FILE" ]] && { echo "Usage: $0 <file> [-o output] [--format fmt] [--dpi 200] [--ocr-model ocr] [--ocr-base-url url] [--keep-images]" >&2; exit 2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

ARGS=(-y @firecrawl/anydoc "$FILE")
[[ -n "$OUTPUT" ]] && ARGS+=(-o "$OUTPUT")
[[ -n "$FORMAT" ]] && ARGS+=(--format "$FORMAT")

set +e
npx "${ARGS[@]}"
EXIT_CODE=$?
set -e

[[ $EXIT_CODE -ne 3 ]] && exit $EXIT_CODE

echo "anydoc: scanned PDF detected, falling back to local OCR..." >&2

if [[ -f "$HOME/miniconda3/envs/kb/bin/python" ]]; then
    PYTHON="$HOME/miniconda3/envs/kb/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
else
    echo "Python not found. Install or activate kb conda env for OCR fallback." >&2
    exit 1
fi

OCR_ARGS=(--file "$FILE" --base-url "$OCR_BASE_URL" --dpi "$DPI" --ocr-model "$OCR_MODEL")
[[ -n "$OUTPUT" ]] && OCR_ARGS+=(--output "$OUTPUT")
$KEEP_IMAGES && OCR_ARGS+=(--keep-images)

$PYTHON "$SCRIPT_DIR/ocr_pdf.py" "${OCR_ARGS[@]}"
