#!/usr/bin/env bash
set -euo pipefail

TARGET_REPO="${1:-$HOME/.hermes/hermes-agent}"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_FILE="$PACK_DIR/patches/hermes-discord-admin.patch"

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "Target is not a git repo: $TARGET_REPO" >&2
  exit 1
fi

if [[ ! -f "$PATCH_FILE" ]]; then
  echo "Patch not found: $PATCH_FILE" >&2
  exit 1
fi

cd "$TARGET_REPO"

echo "Target: $TARGET_REPO"
echo "Current status:"
git status -sb

echo
echo "Checking whether patch applies..."
git apply --check "$PATCH_FILE"

echo "Applying patch..."
git apply "$PATCH_FILE"

echo
echo "Patch applied. Run tests with:"
echo "  source venv/bin/activate && python -m pytest -o 'addopts=' tests/tools/test_discord_tool.py -q"
