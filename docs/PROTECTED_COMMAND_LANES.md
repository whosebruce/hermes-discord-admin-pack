# Protected Discord Command Lanes

This guide describes the reusable pattern only. Replace placeholders locally and never commit real Discord identifiers.

## Recommended Hermes profile

```yaml
discord:
  require_mention: true
  auto_thread: true
  auto_thread_free_response: true
  free_response_channels:
    - 'YOUR_TRUSTED_CHANNEL_ID'

  # Recommended for a dedicated command bot. Omit when the same bot must work
  # in other deliberately authorized channels.
  allowed_channels:
    - 'YOUR_TRUSTED_CHANNEL_ID'

  history_backfill: true
  history_backfill_limit: 50
  reactions: true

  # Defense in depth if bot-authored messages are ever enabled separately.
  bots_require_inline_mention: true

approvals:
  # Low-risk actions may proceed automatically; risky actions remain owner-gated.
  mode: smart
```

`approvals.mode: smart` controls Hermes command approvals. It does not grant Discord role or channel permissions and does not make destructive actions safe without clear owner intent.

Apply the profile without logging channel IDs:

```bash
python scripts/configure-discord-threading.py \
  --hermes-home ~/.hermes \
  --channel 'YOUR_TRUSTED_CHANNEL_ID' \
  --restrict-to-configured-channels \
  --approvals-mode smart
```

## Least-privilege lane overwrites

A common private-lane setup is:

1. Deny `View Channel` to the server's `@everyone` role.
2. Allow the owner member or trusted operator role to view, send, read history, create public threads, and send in threads.
3. Allow the Hermes bot role the same permissions plus `Manage Threads` when operationally required.
4. Confirm the bot role is below no role it must manage; Discord role hierarchy still applies.

The current admin patch accepts Discord's decimal permission bitsets. The following values are intentionally generic:

| Purpose | Allow | Deny |
|---|---:|---:|
| Hide lane from `@everyone` | `0` | `1024` |
| Trusted operator lane access | `309237713920` | `0` |
| Bot lane access, including Manage Threads | `326417583104` | `0` |

Example deny for `@everyone`:

```json
{
  "action": "set_channel_permission",
  "channel_id": "CHANNEL_ID",
  "overwrite_id": "EVERYONE_ROLE_ID",
  "overwrite_type": "role",
  "allow": "0",
  "deny": "1024"
}
```

Example bot-role allow:

```json
{
  "action": "set_channel_permission",
  "channel_id": "CHANNEL_ID",
  "overwrite_id": "BOT_ROLE_ID",
  "overwrite_type": "role",
  "allow": "326417583104",
  "deny": "0"
}
```

Permission bitsets evolve as Discord adds capabilities. Inspect the resulting channel from Discord and test with a non-privileged account before relying on the lane as private.

## Multi-bot safety

Hermes ignores other bots by default. Keep that default whenever possible.

Do not make several auto-replying Hermes profiles communicate by replying to one another in Discord. Discord reply mentions can wake the other bot and create an acknowledgement loop. Use a durable queue, ledger, or task database for agent handoffs; Discord can carry human-visible notifications, not the authoritative assignment state.

If a trusted relay bot must be accepted, scope it narrowly and require a literal inline mention. Never enable unrestricted bot-authored input across several auto-replying profiles.

## Behavior verification

After restarting the gateway:

1. Send one top-level message in the configured command lane without mentioning the bot.
2. Confirm Hermes creates one new Discord thread.
3. Reply inside that thread and confirm the same session continues.
4. Send a message in a non-allowed channel and confirm the dedicated bot stays silent.
5. Try one low-risk action and one intentionally blocked/risky test to confirm smart approvals are behaving as expected.
