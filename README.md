# Hermes Discord Admin Pack

[![Compatibility and privacy](https://github.com/whosebruce/hermes-discord-admin-pack/actions/workflows/compatibility.yml/badge.svg)](https://github.com/whosebruce/hermes-discord-admin-pack/actions/workflows/compatibility.yml)

A sanitized patch and setup pack that adds Discord server-management actions to Hermes Agent, with a safe-update wrapper that reapplies them after Hermes updates.

Current release: **1.4.0**. Command-channel threading now uses native Hermes support, and the old threading source patch has been removed. See [`CHANGELOG.md`](CHANGELOG.md), [`SECURITY.md`](SECURITY.md), and the [MIT license](LICENSE).

This repo contains **no tokens, API keys, Discord IDs, or private config files**. It ships only:

- a patch against Hermes Agent's `tools/discord_tool.py` and its tests
- local configuration helpers for native free-response auto-threading
- a regression-test patch for native Discord thread-title renaming, now supported by upstream
- an install script that confirms native threading support, then preflights and applies both patches to a local Hermes checkout
- an operator guide and local-config helper for configuring another Hermes agent safely
- a non-mutating doctor, generic config-lock helper, and daily current-upstream compatibility CI
- an all-surface privacy scanner that checks the working tree, exact index, and reachable history

> **Agent/operator rule:** Discord behavior settings must live in each target
> agent's local `HERMES_HOME/config.yaml`; editing Hermes source defaults is not
> durable across updates. See [`AGENT_README.md`](AGENT_README.md).

## What this adds

Native `discord_admin` actions for Hermes:

- `create_channel`: create text, voice, category, announcement/news, forum, stage, or media channels
- `edit_channel`: rename/edit topic/category/slowmode/voice limits/common channel fields
- `move_channel`: reorder/move channels, optionally into a category
- `set_channel_permission`: create/update role/member channel permission overwrites
- `delete_channel_permission`: remove a channel permission overwrite
- `delete_channel`: delete a channel or thread

Existing useful actions remain available:

- `list_guilds`
- `list_channels`
- `channel_info`
- `list_roles`
- `add_role`
- `remove_role`
- `fetch_messages`
- `create_thread`

## Free-response command channels with automatic threads

Hermes normally answers free-response channels inline. For a command-center
workflow where every new top-level request should open a fresh thread, this pack
uses the native opt-in. Put these values in the **local** config for every
gateway/profile that needs the behavior:

```yaml
discord:
  require_mention: true
  auto_thread: true
  free_response_auto_thread: true
  free_response_channels:
    - 'YOUR_TRUSTED_CHANNEL_ID'
```

Threading requires current Hermes with native `free_response_auto_thread` support.
No threading source patch is installed. Never commit real configs or private IDs.

### Upgrading from v1.3.0

Rename `discord.auto_thread_free_response` to `discord.free_response_auto_thread`
in each local config. The configurator writes the native key and removes the old
one. Config-lock capture translates old-only configs; applying an old lock
translates its key without changing the lock file. An explicitly captured native
value wins if both keys exist. Re-capture the lock after migration.

If the old threading source patch is still installed, preserve a source diff and
config backup before removing only that patch. Do not force it onto native Hermes
or discard unrelated edits. The installer refuses old or mixed source trees;
resolve any safe-updater stash conflict before restarting.

Current upstream already handles native Discord semantic renaming correctly.
The rename patch adds only a regression test that verifies the guarded native
adapter signature; it does not rewrite upstream gateway code.

## Smart approvals

Hermes can use risk-aware command approvals:

```yaml
approvals:
  mode: smart
```

`smart` allows low-risk commands to proceed automatically while genuinely
risky actions remain owner-gated. It does not grant Discord permissions and
does not remove the requirement for clear owner intent before destructive
actions. Never use `approvals.mode: off` on a shared or internet-facing
gateway.

See [`docs/PROTECTED_COMMAND_LANES.md`](docs/PROTECTED_COMMAND_LANES.md) for
the complete private-lane, least-privilege, smart-approval, and multi-bot
loop-safety pattern.

## Safety model

This pack intentionally does **not** include credentials.

Read [`SECURITY.md`](SECURITY.md) before granting server-management permissions.

Each Hermes agent must have its own local `.env` with a Discord bot token:

```bash
DISCORD_BOT_TOKEN=REDACTED_PUT_TOKEN_IN_LOCAL_ENV_ONLY
```

Do not commit `.env`, `config.yaml`, bot tokens, OpenClaw config, session logs, or credential files.

Recommended Discord bot permissions:

- View Channels
- Send Messages
- Read Message History
- Manage Channels
- Manage Messages
- Create Public Threads
- Manage Roles, only if role/permission actions are needed

For a trusted private command-center bot, `Administrator` is simpler but less safe.

## Install on another Hermes agent

On the target machine:

```bash
cd ~/.hermes/hermes-agent

git status -sb
# Optional but recommended: make a safety branch before patching
stamp=$(date +%Y%m%d-%H%M%S)
git branch "backup/pre-discord-admin-pack-$stamp"

# Keep the pack outside the Hermes source checkout so update tooling survives.
PACK="$HOME/.hermes/local-packs/hermes-discord-admin-pack"
mkdir -p "$(dirname "$PACK")"
if [[ -d "$PACK/.git" ]]; then
  git -C "$PACK" pull --ff-only
else
  git clone https://github.com/whosebruce/hermes-discord-admin-pack.git "$PACK"
fi

# Apply both remaining patches
bash "$PACK/scripts/apply-discord-admin-pack.sh" ~/.hermes/hermes-agent

# Persist command-channel behavior in LOCAL config (repeat --channel as needed)
python "$PACK/scripts/configure-discord-threading.py" \
  --hermes-home ~/.hermes \
  --channel 'YOUR_TRUSTED_CHANNEL_ID' \
  --restrict-to-configured-channels \
  --approvals-mode smart \
  --enable-output-redaction

# Capture only Discord + approvals values into a private local lock and install
# the safe-update wrapper. Add more NAME=HERMES_HOME arguments for profiles.
bash "$PACK/scripts/install-update-guard.sh" "default=$HOME/.hermes"

# Run focused tests. Current Hermes keeps its test tools in a
# [dependency-groups] dev table, which needs pip 25.1 or newer.
source venv/bin/activate   # or .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e . --group dev
# Older Hermes checkouts without that table: python -m pip install -e ".[dev]"
bash scripts/run_tests.sh \
  tests/tools/test_discord_tool.py \
  tests/gateway/test_discord_channel_controls.py \
  tests/gateway/test_discord_free_response.py \
  tests/gateway/relay/test_relay_threads.py -q

# Run pack-local helper tests and the identifier-safe readiness doctor
python -m pytest -q "$PACK/tests"
python "$PACK/scripts/discord-pack-doctor.py" \
  --hermes-repo ~/.hermes/hermes-agent \
  --hermes-home ~/.hermes \
  --require-smart-approvals

# Enable toolsets if needed
hermes tools enable discord
hermes tools enable discord_admin

# Restart gateway so the live tool schema reloads
hermes gateway restart
# or, if installed as a user systemd service:
systemctl --user restart hermes-gateway.service
```

Test counts change as Hermes evolves; require a zero exit code rather than a
hard-coded pass count.

The repository's scheduled GitHub Actions workflow repeats this process
against current Hermes Agent `main`. Compatibility evidence is tied to each
workflow run rather than a stale hard-coded upstream revision or test count.

## Surviving Hermes updates

The installed behavior has two layers:

1. `config.yaml` stores the trusted lane IDs and `free_response_auto_thread`.
2. Current Hermes owns native threading; this pack still patches admin actions.

The threading config normally survives a source update, but the admin patch may not.
Therefore a blind `hermes update`, raw `git pull`, or replacement checkout is
**not** claimed to preserve the complete behavior automatically. Install the
guard above and use this wrapper instead:

```bash
git -C ~/.hermes/local-packs/hermes-discord-admin-pack pull --ff-only
hermes-discord-safe-update
```

The wrapper backs up default/profile config and auth files, temporarily removes
pack-owned source changes before pulling, preserves unrelated local work in a
stash, updates Hermes, reapplies both remaining patches, migrates config, reapplies the
private config lock, reinstalls Hermes, and runs focused tests plus the doctor.
It deliberately does not restart the gateway after a failed or unreviewed
update.

For values that must survive every update, copy
[`examples/config-lock.yaml.example`](examples/config-lock.yaml.example) to an
ignored local path, replace placeholders locally, and run:

```bash
python scripts/apply-config-lock.py --lock /path/to/local-config-lock.yaml
python scripts/discord-pack-doctor.py \
  --hermes-repo ~/.hermes/hermes-agent \
  --hermes-home ~/.hermes \
  --require-smart-approvals
```

The capture and apply helpers report profile names and counts only; they never
print protected channel IDs or captured values. The capture allowlist includes
Discord behavior, approval policy, Discord streaming, and the secret/PII
redaction booleans; it excludes model credentials, provider keys, tokens,
personal paths, and unrelated config. See the
[portable local configuration matrix](docs/PORTABLE_LOCAL_CONFIG.md) for the
public/private boundary. Full agent instructions are in
[`AGENT_README.md`](AGENT_README.md).

## Configure the Discord bot

1. Create or reuse a Discord application/bot in the Discord Developer Portal.
2. Enable required privileged intents if needed:
   - Message Content Intent for reading message text broadly.
   - Server Members Intent for member lookup/search.
3. Invite the bot to the server with appropriate permissions.
4. On the Hermes host, put the bot token in the local Hermes env file only:

```bash
hermes config env-path
# edit that file locally, never commit it
```

Example local-only env entry:

```bash
DISCORD_BOT_TOKEN=your_local_token_here
```

5. Restart the Hermes gateway.

## Usage examples

Create a text channel:

```json
{
  "action": "create_channel",
  "guild_id": "DISCORD_GUILD_ID",
  "name": "experiments-2",
  "channel_type": "text",
  "parent_id": "OPTIONAL_CATEGORY_ID",
  "topic": "Testing area"
}
```

Create a voice channel:

```json
{
  "action": "create_channel",
  "guild_id": "DISCORD_GUILD_ID",
  "name": "War Room",
  "channel_type": "voice",
  "parent_id": "OPTIONAL_CATEGORY_ID",
  "bitrate": 64000,
  "user_limit": 5
}
```

Move a channel:

```json
{
  "action": "move_channel",
  "guild_id": "DISCORD_GUILD_ID",
  "channel_id": "CHANNEL_ID",
  "position": 5,
  "parent_id": "OPTIONAL_CATEGORY_ID",
  "lock_permissions": true
}
```

Rename/edit a channel:

```json
{
  "action": "edit_channel",
  "channel_id": "CHANNEL_ID",
  "name": "resources",
  "topic": "Curated links and documents"
}
```

Set a channel permission overwrite:

```json
{
  "action": "set_channel_permission",
  "channel_id": "CHANNEL_ID",
  "overwrite_id": "ROLE_OR_USER_ID",
  "overwrite_type": "role",
  "allow": "1024",
  "deny": "0"
}
```

Delete a channel permission overwrite:

```json
{
  "action": "delete_channel_permission",
  "channel_id": "CHANNEL_ID",
  "overwrite_id": "ROLE_OR_USER_ID"
}
```

Delete a channel:

```json
{
  "action": "delete_channel",
  "channel_id": "CHANNEL_ID"
}
```

For destructive actions like `delete_channel`, require explicit user confirmation before calling the tool.

## Privacy gate before pushing changes

Run this from this pack repo before pushing:

```bash
git status -sb
python scripts/privacy_scan.py --surface all
```

Add operator-specific names, IDs, paths, domains, and labels to the ignored
`.privacy-patterns.local` file, then run:

```bash
python scripts/privacy_scan.py --surface all \
  --patterns-file .privacy-patterns.local
```

The scanner reports where a finding occurred without printing the matched
private value. After pushing, fresh-clone the public HTTPS repository and run
the tests and scanner again.

## Status

This is a bridge pack for Hermes operators. Long term, the better home for these actions is an upstream Hermes Agent PR or a maintained fork/branch.

MIT licensed. Maintained by Jonathan Bruce ([@whosebruce](https://github.com/whosebruce)).
