#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"

if [ -z "$TARGET" ]; then
    echo "Usage: $0 <patch|minor|major|X.Y.Z[-PRERELEASE][+BUILD]>" >&2
    exit 1
fi

SEMVER_REGEX='^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-([0-9A-Za-z.-]+))?(\+([0-9A-Za-z.-]+))?$'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

CARGO_TOML="$ROOT_DIR/Cargo.toml"
WEB_PACKAGE_JSON="$ROOT_DIR/apps/web/package.json"

if [ ! -f "$CARGO_TOML" ]; then
    echo "Error: Cargo.toml not found at $CARGO_TOML" >&2
    exit 1
fi

CURRENT_VERSION=$(sed -n '/\[workspace\.package\]/,/\[.*\]/p' "$CARGO_TOML" | grep -E '^version\s*=' | sed -E 's/.*"([^"]+)".*/\1/' | head -n 1)

if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Could not extract [workspace.package] version from $CARGO_TOML" >&2
    exit 1
fi

echo "Current workspace version: $CURRENT_VERSION"

if [[ ! "$CURRENT_VERSION" =~ $SEMVER_REGEX ]]; then
    echo "Error: Current version '$CURRENT_VERSION' does not match SemVer 2.0" >&2
    exit 1
fi

MAJOR="${BASH_REMATCH[1]}"
MINOR="${BASH_REMATCH[2]}"
PATCH="${BASH_REMATCH[3]}"

NEW_VERSION=""
case "$TARGET" in
    patch)
        NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
        ;;
    minor)
        NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
        ;;
    major)
        NEW_VERSION="$((MAJOR + 1)).0.0"
        ;;
    *)
        if [[ ! "$TARGET" =~ $SEMVER_REGEX ]]; then
            echo "Error: Target version '$TARGET' is not a valid SemVer 2.0 string (or patch/minor/major command)" >&2
            exit 1
        fi
        NEW_VERSION="$TARGET"
        ;;
esac

echo "Updating workspace version to: $NEW_VERSION"

# Update Cargo.toml
python3 -c "
import re
with open('$CARGO_TOML', 'r', encoding='utf-8') as f:
    content = f.read()
updated = re.sub(r'(\[workspace\.package\][\s\S]*?version\s*=\s*)\"[^\"]+\"', r'\g<1>\"$NEW_VERSION\"', content, count=1)
with open('$CARGO_TOML', 'w', encoding='utf-8') as f:
    f.write(updated)
" || sed -i.bak -E "/\\[workspace\\.package\\]/,/\\[/ s/(version[[:space:]]*=[[:space:]]*)\"[^\"]+\"/\\1\"$NEW_VERSION\"/" "$CARGO_TOML"

# Update apps/web/package.json
if [ -f "$WEB_PACKAGE_JSON" ]; then
    python3 -c "
import json
with open('$WEB_PACKAGE_JSON', 'r', encoding='utf-8') as f:
    data = json.load(f)
data['version'] = '$NEW_VERSION'
with open('$WEB_PACKAGE_JSON', 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
    f.write('\n')
" || sed -i.bak -E "s/(\"version\"[[:space:]]*:[[:space:]]*)\"[^\"]+\"/\\1\"$NEW_VERSION\"/" "$WEB_PACKAGE_JSON"
    echo "Updated $WEB_PACKAGE_JSON"
fi

echo "Running 'cargo check --workspace' to sync Cargo.lock..."
(cd "$ROOT_DIR" && cargo check --workspace)

echo "Successfully bumped version to $NEW_VERSION"
