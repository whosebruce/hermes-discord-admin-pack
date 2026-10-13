#!/usr/bin/env bash
set -euo pipefail

TARGET_REPO="${1:-$HOME/.hermes/hermes-agent}"
PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_FILES=(
  "$PACK_DIR/patches/hermes-discord-admin.patch"
  "$PACK_DIR/patches/discord-native-thread-auto-rename.patch"
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

TARGET_REPO="$(cd "$TARGET_REPO" && pwd)"
cd "$TARGET_REPO"

echo "Target: $TARGET_REPO"
echo "Current status:"
git status -sb

python "$PACK_DIR/scripts/check-native-threading.py" "$TARGET_REPO"

# Each patch may have older variants in patches/compat/<name>.<hermes-release>.patch for
# Hermes releases that predate the current patch. The current patch is tried first.
patch_candidates() {
  local patch_file="$1" stem
  stem="$(basename "$patch_file" .patch)"
  printf '%s\n' "$patch_file"
  for variant in "$PACK_DIR/patches/compat/$stem".*.patch; do
    [[ -f "$variant" ]] && printf '%s\n' "$variant"
  done
  return 0
}

declare -a pending=()
echo
echo "Preflighting patches..."
for patch_file in "${PATCH_FILES[@]}"; do
  patch_name="$(basename "$patch_file")"
  chosen=""
  applied=""
  while IFS= read -r candidate; do
    if git apply --reverse --check "$candidate" 2>/dev/null; then
      applied="$candidate"
      break
    fi
    if [[ -z "$chosen" ]] && git apply --check "$candidate" 2>/dev/null; then
      chosen="$candidate"
    fi
  done < <(patch_candidates "$patch_file")
  if [[ -n "$applied" ]]; then
    echo "  already applied: $patch_name ($(basename "$applied"))"
  elif [[ -n "$chosen" ]]; then
    echo "  pending: $patch_name ($(basename "$chosen"))"
    pending+=("$chosen")
  else
    echo "  incompatible: $patch_name" >&2
    echo "No patches were applied. Update the patch for this Hermes revision; do not force it." >&2
    exit 1
  fi
done

# ${arr[@]+...}: macOS bash 3.2 treats an empty array as unset under set -u.
for patch_file in ${pending[@]+"${pending[@]}"}; do
  echo "Applying $(basename "$patch_file")..."
  git apply "$patch_file"
done

echo
echo "Patch state ready. Configure command channels in the LOCAL HERMES_HOME/config.yaml:"
echo "  python '$PACK_DIR/scripts/configure-discord-threading.py' --channel 'YOUR_CHANNEL_ID' --restrict-to-configured-channels --approvals-mode smart --enable-output-redaction"
echo "Then run tests with:"
echo "  bash scripts/run_tests.sh tests/tools/test_discord_tool.py tests/gateway/test_discord_channel_controls.py tests/gateway/test_discord_free_response.py tests/gateway/relay/test_relay_threads.py -q"
echo "Then run the identifier-safe readiness doctor:"
echo "  python '$PACK_DIR/scripts/discord-pack-doctor.py' --hermes-repo '$TARGET_REPO' --require-smart-approvals"
