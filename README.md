# Hermes Discord Admin Pack

A sanitized helper pack for enabling richer Discord server-management actions on Hermes Agent instances.

This repo contains **no tokens, API keys, Discord IDs, or private config files**. It ships only:

- a patch against Hermes Agent's `tools/discord_tool.py`
- focused tests for the new Discord admin actions
- an install script that applies the patch to a local Hermes checkout
- an operator guide for configuring another Hermes agent safely

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

## Safety model

This pack intentionally does **not** include credentials.

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

# Apply the patch
bash /tmp/hermes-discord-admin-pack/scripts/apply-discord-admin-pack.sh ~/.hermes/hermes-agent

# Run focused tests
source venv/bin/activate
python -m pytest -o 'addopts=' tests/tools/test_discord_tool.py -q

# Enable toolsets if needed
hermes tools enable discord
hermes tools enable discord_admin

# Restart gateway so the live tool schema reloads
hermes gateway restart
# or, if installed as a user systemd service:
systemctl --user restart hermes-gateway.service
```

Expected focused test result after this pack:

```text
99 passed
```

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

## Secret-safety checklist before pushing changes

Run this from this pack repo before pushing:

```bash
git status -sb
find . -type f \
  ! -path './.git/*' \
  ! -path './README.md' \
  ! -path './patches/*' \
  ! -path './scripts/*' \
  -print

grep -RInE 'DISCORD_BOT_TOKEN=|OPENAI_API_KEY=|ANTHROPIC_API_KEY=|OPENROUTER_API_KEY=|gho_|github_pat_|xox[baprs]-|BEGIN (RSA|OPENSSH|PRIVATE) KEY|password\s*[:=]' . \
  --exclude-dir=.git || true
```

The grep should return no real secrets. Placeholder strings like `DISCORD_BOT_TOKEN=REDACTED...` are okay.

## Notes

This is a bridge pack for Bruce's Hermes agents. Long term, the better home for these actions is an upstream Hermes Agent PR or a maintained fork/branch.
