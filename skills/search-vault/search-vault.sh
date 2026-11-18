#!/usr/bin/env bash
set -eo pipefail

VAULT_PATH="D:/Cloud/OneDrive/AI/Personal/vault"
TOP_N=5
KEYS=()

while getopts "k:n:p:" opt; do
  case "$opt" in
    k) KEYS+=("$OPTARG") ;;
    n) TOP_N="$OPTARG" ;;
    p) VAULT_PATH="$OPTARG" ;;
    *) echo "Usage: $0 -k kw1 -k kw2 -n count=5 -p vault_path"; exit 1 ;;
  esac
done

[ "${#KEYS[@]}" -lt 1 ] && { echo "At least one keyword required (-k)"; exit 1; }

IFS='|'; PATTERN="${KEYS[*]}"; unset IFS

if command -v rg &>/dev/null; then
  rg -i -n --no-heading -g '*.md' "$PATTERN" "$VAULT_PATH" 2>/dev/null || true
else
  grep -rniE --include='*.md' "$PATTERN" "$VAULT_PATH" 2>/dev/null || true
fi | while IFS=: read -r file _ rest; do
  [ -z "$file" ] && continue
  if echo "$rest" | grep -qiE "^title:\s.*$PATTERN" || echo "$rest" | grep -qiE "^#\s+.*$PATTERN"; then
    w=10
  elif echo "$rest" | grep -qiE "^#{2,}\s+.*$PATTERN"; then
    w=5
  else
    w=1
  fi
  printf '%s|%d\n' "$file" "$w"
done | awk -F'|' '{s[$1]+=$2} END{for(k in s) print k "|" s[k]}' | sort -t'|' -k2 -rn | head -n "$TOP_N"