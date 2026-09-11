#!/usr/bin/env bash
set -euo pipefail

TARGET_REPO="${1:?usage: check-upstream-compat.sh /path/to/hermes-agent}"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCHES=(
  "$PACK_DIR/patches/hermes-discord-admin.patch"
  "$PACK_DIR/patches/discord-free-response-auto-thread.patch"
  "$PACK_DIR/patches/discord-native-thread-auto-rename.patch"
)

git -C "$TARGET_REPO" rev-parse --is-inside-work-tree >/dev/null 2>&1 \
  || { echo "not_a_git_repo=true" >&2; exit 2; }
bash "$PACK_DIR/scripts/apply-discord-admin-pack.sh" "$TARGET_REPO"

echo "hermes_sha=$(git -C "$TARGET_REPO" rev-parse HEAD)"
echo "patch_count=${#PATCHES[@]}"
cd "$TARGET_REPO"
bash scripts/run_tests.sh \
  tests/tools/test_discord_tool.py \
  tests/gateway/test_discord_channel_controls.py \
  tests/gateway/relay/test_relay_threads.py -q
