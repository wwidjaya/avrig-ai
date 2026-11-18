#!/usr/bin/env bash
set -euo pipefail

SERVICE_URL="${SERVICE_URL:-http://172.26.0.50:18600}"
TOP_K=5; QUERY=""

while getopts "q:n:s:" opt; do
  case "$opt" in
    q) QUERY="$OPTARG" ;;
    n) TOP_K="$OPTARG" ;;
    s) SERVICE_URL="$OPTARG" ;;
    *) echo "Usage: $0 -q 'query' [-n top_k=5] [-s service_url]"; exit 1 ;;
  esac
done

[ -z "$QUERY" ] && { echo "Query required (-q 'query')"; exit 1; }
(( TOP_K < 1 )) && TOP_K=1
(( TOP_K > 10 )) && TOP_K=10

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Robust null device: use /dev/null on Unix, temp file fallback on Windows
NULL_DEVICE="${NULL_DEVICE:-/dev/null}"
[ ! -e "$NULL_DEVICE" ] && NULL_DEVICE=$(mktemp -u /tmp/null.XXXXXX 2>/dev/null || echo "/tmp/null")

RAW="$(curl -s -m 60 -G "$SERVICE_URL/search" --data-urlencode "q=$QUERY" --data-urlencode "top_k=$TOP_K" 2>"$NULL_DEVICE")" || RAW=""

if [ -z "$RAW" ]; then
  echo "Primary semantic search failed — retrieval service unreachable at $SERVICE_URL."
  echo "Fall back: bash \"$DIR/search-vault.sh\" -k '<term1>' -k '<term2>'"
  exit 0
fi

set +e
OUT="$(python3 - "$RAW" <<'PY'
import json, sys
data = json.loads(sys.argv[1])
if not data:
    sys.exit(1)
for i, r in enumerate(data, 1):
    ty = r.get('type', '?')
    sc = r.get('score', 0)
    ti = r.get('title', '')
    pa = r.get('filepath', '')
    sn = " ".join((r.get('snippet') or '').split())[:200]
    print("[{}] [{}] score={:.3f} | {}".format(i, ty, sc, ti))
    print("    Path:    {}".format(pa))
    print("    Snippet: {}...".format(sn))
    print()
print("Explanation: type 'vault' = local note (read the full file at Path for complete info, snippet truncated). type 'web' = external source. Scores = reranker relevance (higher = better).")
PY
)"
RC=$?
set -e

if [ "$RC" -eq 0 ]; then
  printf '%s\n' "$OUT"
else
  echo "Primary semantic search failed — no results (or invalid response) from $SERVICE_URL."
  echo "Fall back: bash \"$DIR/search-vault.sh\" -k '<term1>' -k '<term2>'"
fi