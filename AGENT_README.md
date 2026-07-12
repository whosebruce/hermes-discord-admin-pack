# Agent Handoff: Hermes Discord Admin + Command-Channel Threading

This file is for the AI agent installing or maintaining this pack on a Hermes host.

## Non-negotiable configuration rule

**Behavior settings belong in the target agent's local Hermes config, not in the Hermes Agent source checkout and not in this public repository.**

- Default profile: `~/.hermes/config.yaml`
- Named profile: that profile's own `HERMES_HOME/config.yaml`, commonly `~/.hermes/profiles/<name>/config.yaml`
- Secrets such as `DISCORD_BOT_TOKEN`: the matching local `.env`
- Source patches: the local Hermes checkout, with a preservation/reapply workflow

A Hermes source update replaces or rebases files under `~/.hermes/hermes-agent`. Values edited only in source examples/defaults are not durable operator configuration. Never commit private channel IDs, bot tokens, or a real `config.yaml` to this repo.

## Desired command-channel behavior

A trusted Discord command channel should:

1. accept messages without requiring `@bot`;
2. create a fresh thread for each new top-level request; and
3. continue context when the user replies inside that thread.

The required local config is:

```yaml
discord:
  require_mention: true
  auto_thread: true
  auto_thread_free_response: true
  free_response_channels:
    - 'YOUR_TRUSTED_CHANNEL_ID'
```

Keep IDs quoted so YAML does not coerce Discord snowflakes into numbers.

Hermes upstream normally keeps free-response channels inline. This pack's `discord-free-response-auto-thread.patch` adds the explicit `auto_thread_free_response` opt-in. Both the source patch **and** the local config value are required.

## Installation workflow

```bash
PACK=/path/to/hermes-discord-admin-pack
HERMES_REPO="$HOME/.hermes/hermes-agent"

# 1. Inspect and preserve local work.
git -C "$HERMES_REPO" status -sb
stamp=$(date +%Y%m%d-%H%M%S)
git -C "$HERMES_REPO" branch "backup/pre-discord-admin-pack-$stamp"

# 2. Apply all source patches. The script preflights every patch first.
bash "$PACK/scripts/apply-discord-admin-pack.sh" "$HERMES_REPO"

# 3. Write behavior to LOCAL config, not the source tree.
python "$PACK/scripts/configure-discord-threading.py" \
  --hermes-home "$HOME/.hermes" \
  --channel 'YOUR_TRUSTED_CHANNEL_ID'

# Repeat step 3 for every named profile that owns a separate gateway/config.

# 4. Reinstall and test.
source "$HERMES_REPO/venv/bin/activate"
python -m pip install -e "$HERMES_REPO"
python -m pytest -o 'addopts=' \
  "$HERMES_REPO/tests/tools/test_discord_tool.py" \
  "$HERMES_REPO/tests/gateway/test_discord_channel_controls.py" -q

# 5. Restart and verify live behavior.
hermes gateway restart
```

## Update rule for every agent

Before a Hermes update:

1. back up each profile's `config.yaml`, `.env`, and auth files without printing secrets;
2. preserve local source patches or changes;
3. update/reinstall Hermes;
4. reapply this pack's patches if upstream still lacks the features;
5. verify each profile's local `discord` values;
6. restart each affected gateway; and
7. perform a real Discord test from a configured top-level command channel.

If the source patch is already upstream, `git apply --reverse --check` will identify it as already applied. Do not force a stale patch through conflicts; inspect upstream behavior and update the patch/tests.

## Verification contract

Report only evidence:

- local config path(s) updated (never their secret contents);
- patch status for both patch files;
- focused pytest result;
- gateway restart result; and
- real behavior: one top-level message created a new thread, then one reply continued in that same thread.

Do not report success from configuration inspection alone.
