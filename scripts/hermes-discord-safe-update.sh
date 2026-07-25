#!/usr/bin/env bash
set -euo pipefail

HERMES_HOME_DIR="${HERMES_HOME:-$HOME/.hermes}"
HERMES_REPO="${HERMES_REPO:-$HERMES_HOME_DIR/hermes-agent}"
PACK_DIR="${HERMES_DISCORD_PACK_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
CONFIG_LOCK="${HERMES_DISCORD_CONFIG_LOCK:-$HERMES_HOME_DIR/local-overrides/discord-admin-config-lock.yaml}"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$HERMES_HOME_DIR/backups/discord-safe-update-$STAMP"

[[ -d "$HERMES_REPO/.git" ]] || { echo "error=hermes_repo_missing" >&2; exit 2; }
[[ -f "$PACK_DIR/patches/discord-free-response-auto-thread.patch" ]] \
  || { echo "error=persistent_pack_missing" >&2; exit 2; }
[[ -f "$CONFIG_LOCK" ]] || { echo "error=config_lock_missing" >&2; exit 2; }

mkdir -p "$BACKUP_DIR"
for file in config.yaml .env auth.json channel_directory.json webhook_subscriptions.json; do
  [[ -e "$HERMES_HOME_DIR/$file" ]] && cp -a "$HERMES_HOME_DIR/$file" "$BACKUP_DIR/$file"
done
if [[ -d "$HERMES_HOME_DIR/profiles" ]]; then
  mkdir -p "$BACKUP_DIR/profiles"
  while IFS= read -r -d '' file; do
    relative="${file#$HERMES_HOME_DIR/}"
    mkdir -p "$BACKUP_DIR/$(dirname "$relative")"
    cp -a "$file" "$BACKUP_DIR/$relative"
  done < <(find "$HERMES_HOME_DIR/profiles" -maxdepth 2 \
    \( -name config.yaml -o -name .env -o -name auth.json \) -print0)
fi

echo "backup_created=true"
cd "$HERMES_REPO"
git config rerere.enabled true
git config rerere.autoupdate true
git status -sb > "$BACKUP_DIR/git-status-before.txt"
git diff > "$BACKUP_DIR/worktree-before.patch" || true
git diff --staged > "$BACKUP_DIR/index-before.patch" || true

head_has_semantic_patch() {
  local patch_name="$1"
  local text=""
  case "$patch_name" in
    discord-free-response-auto-thread.patch)
      text="$(git show HEAD:plugins/platforms/discord/adapter.py 2>/dev/null || true)"
      [[ "$text" == *"DISCORD_AUTO_THREAD_FREE_RESPONSE"* ]]
      ;;
    hermes-discord-admin.patch)
      text="$(git show HEAD:tools/discord_tool.py 2>/dev/null || true)"
      [[ "$text" == *"set_channel_permission"* && "$text" == *"move_channel"* ]]
      ;;
    *) return 1 ;;
  esac
}

for patch in "$PACK_DIR"/patches/*.patch; do
  patch_name="$(basename "$patch")"
  if ! head_has_semantic_patch "$patch_name" \
    && git apply --reverse --check "$patch" >/dev/null 2>&1; then
    git apply --reverse "$patch"
    echo "temporarily_removed_patch=$patch_name"
  fi
done

stashed=0
if [[ -n "$(git status --porcelain)" ]]; then
  git branch "backup/pre-discord-safe-update-$STAMP" >/dev/null 2>&1 || true
  git stash push -u -m "pre-discord-safe-update-$STAMP"
  stashed=1
fi

git fetch --all --prune --tags
git pull --ff-only origin main

if [[ "$stashed" == "1" ]]; then
  if ! git stash pop; then
    echo "error=stash_conflict" >&2
    echo "Resolve the preserved local changes before restarting the gateway." >&2
    echo "backup_available=true" >&2
    exit 3
  fi
fi

bash "$PACK_DIR/scripts/apply-discord-admin-pack.sh" "$HERMES_REPO"

if [[ -d venv ]]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi
python -m pip install -e .
python -m pip install --quiet pytest pytest-asyncio
hermes config migrate </dev/null || true
python "$PACK_DIR/scripts/apply-config-lock.py" --lock "$CONFIG_LOCK"

python -m pytest -o 'addopts=' \
  tests/tools/test_discord_tool.py \
  tests/gateway/test_discord_channel_controls.py -q
python "$PACK_DIR/scripts/discord-pack-doctor.py" \
  --hermes-repo "$HERMES_REPO" \
  --hermes-home "$HERMES_HOME_DIR" \
  --require-smart-approvals

git status -sb > "$BACKUP_DIR/git-status-after.txt"
echo "safe_update_complete=true"
echo "gateway_restarted=false"
echo "Restart only after reviewing the successful checks above."
