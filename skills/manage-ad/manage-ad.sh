#!/usr/bin/env bash
set -euo pipefail

BASE_DN="DC=wirianto,DC=ai"
SAM_LDB="/var/lib/samba/private/sam.ldb"

if [ $# -lt 1 ]; then
    echo "Usage: $0 <samba-tool command...> | search <filter> [attrs...]" >&2
    exit 1
fi

if [ "$1" = "search" ]; then
    shift
    FILTER="$1"
    shift || true
    sudo ldbsearch -H "$SAM_LDB" -b "$BASE_DN" "$FILTER" "$@" 2>&1 | grep -vE 'WARNING|setproctitle' || true
else
    sudo samba-tool "$@" 2>&1 | grep -vE 'WARNING|setproctitle' || true
fi
