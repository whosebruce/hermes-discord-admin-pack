#!/usr/bin/env bash
set -euo pipefail

PACK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_HOME="${HERMES_HOME:-$HOME/.hermes}"
LOCK_PATH="${HERMES_DISCORD_CONFIG_LOCK:-$DEFAULT_HOME/local-overrides/discord-admin-config-lock.yaml}"
BIN_DIR="${HERMES_DISCORD_BIN_DIR:-$HOME/.local/bin}"
WRAPPER="$BIN_DIR/hermes-discord-safe-update"

case "$PACK_DIR" in
  /tmp/*|/var/tmp/*)
    if [[ "${HERMES_DISCORD_ALLOW_TEMP_PACK:-0}" == "1" ]]; then
      :
    else
    echo "error=pack_must_be_persistent" >&2
    echo "Clone the pack under ~/.hermes/local-packs before installing the guard." >&2
    exit 2
    fi
    ;;
esac

profiles=("$@")
if [[ ${#profiles[@]} -eq 0 ]]; then
  profiles=("default=$DEFAULT_HOME")
fi

capture_args=()
for profile in "${profiles[@]}"; do
  capture_args+=(--profile "$profile")
done

python "$PACK_DIR/scripts/capture-discord-config-lock.py" \
  "${capture_args[@]}" \
  --output "$LOCK_PATH" \
  --require-smart-approvals

mkdir -p "$BIN_DIR"
ln -sfn "$PACK_DIR/scripts/hermes-discord-safe-update.sh" "$WRAPPER"

echo "update_guard_installed=true"
echo "config_lock_present=true"
echo "wrapper_name=hermes-discord-safe-update"
echo "raw_hermes_update_protected=false"
echo "Use the wrapper for source updates; it reapplies patches and the local config lock."
