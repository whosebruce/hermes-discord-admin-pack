#!/usr/bin/env bash
set -euo pipefail

TARGET_REPO="${1:-$HOME/.hermes/hermes-agent}"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_FILES=(
  "$PACK_DIR/patches/hermes-discord-admin.patch"
  "$PACK_DIR/patches/discord-free-response-auto-thread.patch"
)

if [[ ! -d "$TARGET_REPO/.git" ]]; then
  echo "Target is not a git repo: $TARGET_REPO" >&2
  exit 1
fi

for patch_file in "${PATCH_FILES[@]}"; do
  if [[ ! -f "$patch_file" ]]; then
    echo "Patch not found: $patch_file" >&2
    exit 1
  fi
done

cd "$TARGET_REPO"

echo "Target: $TARGET_REPO"
echo "Current status:"
git status -sb

declare -a pending=()
echo
echo "Preflighting patches..."
for patch_file in "${PATCH_FILES[@]}"; do
  patch_name="$(basename "$patch_file")"
  if git apply --check "$patch_file" 2>/dev/null; then
    echo "  pending: $patch_name"
    pending+=("$patch_file")
  elif git apply --reverse --check "$patch_file" 2>/dev/null; then
    echo "  already applied: $patch_name"
  else
    echo "  incompatible: $patch_name" >&2
    echo "No patches were applied. Update the patch for this Hermes revision; do not force it." >&2
    exit 1
  fi
done

for patch_file in "${pending[@]}"; do
  echo "Applying $(basename "$patch_file")..."
  git apply "$patch_file"
done

echo
echo "Patch state ready. Configure command channels in the LOCAL HERMES_HOME/config.yaml:"
echo "  python '$PACK_DIR/scripts/configure-discord-threading.py' --channel 'YOUR_CHANNEL_ID'"
echo "Then run tests with:"
echo "  source venv/bin/activate && python -m pytest -o 'addopts=' tests/tools/test_discord_tool.py tests/gateway/test_discord_channel_controls.py -q"
