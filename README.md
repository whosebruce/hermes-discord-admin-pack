# Hermes Discord Admin Pack

[![Compatibility and privacy](https://github.com/whosebruce/hermes-discord-admin-pack/actions/workflows/compatibility.yml/badge.svg)](https://github.com/whosebruce/hermes-discord-admin-pack/actions/workflows/compatibility.yml)

Current public release: **1.1.0**. See [`CHANGELOG.md`](CHANGELOG.md), [`SECURITY.md`](SECURITY.md), and the [MIT license](LICENSE).

A sanitized helper pack for enabling richer Discord server-management actions on Hermes Agent instances.

This repo contains **no tokens, API keys, Discord IDs, or private config files**. It ships only:

- a patch against Hermes Agent's `tools/discord_tool.py`
- an opt-in patch that lets trusted free-response command channels auto-create threads
- focused tests for the Discord changes
- an install script that preflights and applies both patches to a local Hermes checkout
- an operator guide and local-config helper for configuring another Hermes agent safely
- a non-mutating doctor, generic config-lock helper, and daily current-upstream compatibility CI
- an all-surface privacy scanner that checks the working tree, exact index, and reachable history

> **Agent/operator rule:** Discord behavior settings must live in each target
> agent's local `HERMES_HOME/config.yaml`; editing Hermes source defaults is not
> durable across updates. See [`AGENT_README.md`](AGENT_README.md).

## What this adds

Native `discord_admin` actions for Hermes:

- `create_channel` — create text, voice, category, announcement/news, forum, stage, or media channels
- `edit_channel` — rename/edit topic/category/slowmode/voice limits/common channel fields
- `move_channel` — reorder/move channels, optionally into a category
- `set_channel_permission` — create/update role/member channel permission overwrites
- `delete_channel_permission` — remove a channel permission overwrite
- `delete_channel` — delete a channel or thread

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
adds an explicit opt-in. Put these values in the **local** config for every
gateway/profile that needs the behavior:

```yaml
discord:
  require_mention: true
  auto_thread: true
  auto_thread_free_response: true
  free_response_channels:
    - 'YOUR_TRUSTED_CHANNEL_ID'
```

The source patch enables the feature; the local config selects it. Both are
required. Never commit a real `config.yaml` or private channel IDs here.

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

# Clone this pack somewhere temporary
git clone https://github.com/whosebruce/hermes-discord-admin-pack.git /tmp/hermes-discord-admin-pack

# Apply both patches
bash /tmp/hermes-discord-admin-pack/scripts/apply-discord-admin-pack.sh ~/.hermes/hermes-agent

# Persist command-channel behavior in LOCAL config (repeat --channel as needed)
python /tmp/hermes-discord-admin-pack/scripts/configure-discord-threading.py \
  --hermes-home ~/.hermes \
  --channel 'YOUR_TRUSTED_CHANNEL_ID' \
  --restrict-to-configured-channels \
  --approvals-mode smart

# Run focused tests
source venv/bin/activate
python -m pytest -o 'addopts=' \
  tests/tools/test_discord_tool.py \
  tests/gateway/test_discord_channel_controls.py -q

# Run pack-local helper tests and the identifier-safe readiness doctor
python -m pytest -q /tmp/hermes-discord-admin-pack/tests
python /tmp/hermes-discord-admin-pack/scripts/discord-pack-doctor.py \
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
against current Hermes Agent `main`. The 1.1.0 release was locally verified
against Hermes `4c96172d9`: both patches applied cleanly and 126 focused tests
passed with two dependency deprecation warnings.

## Surviving Hermes updates

The local config is the source of truth for operator behavior, while this pack
contains source patches Hermes may replace during an update. Before updating,
back up each profile's `config.yaml`/`.env` and preserve local source changes.
After updating, reapply the pack, confirm the local values, reinstall Hermes,
restart the gateway, and perform a real top-level-message/thread-continuation
test. Full agent instructions are in [`AGENT_README.md`](AGENT_README.md).

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

The config-lock helper reports profile names and counts only; it never prints
the protected values.

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
  "name": "🧪-experiments-2",
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
  "name": "📚-resources",
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

## Notes

This is a bridge pack for Hermes operators. Long term, the better home for these actions is an upstream Hermes Agent PR or a maintained fork/branch.
