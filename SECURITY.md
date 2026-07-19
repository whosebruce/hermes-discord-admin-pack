# Security Policy

This pack modifies a Hermes Agent installation and can expose Discord server-management actions. Treat installation and configuration as privileged administration work.

## Core rules

- Never commit a bot token, `.env`, real `config.yaml`, auth file, server/channel/user/role ID, session log, local hostname, private IP, phone number, email address, or operator-specific path.
- Keep `discord.require_mention: true` globally. Add only deliberately trusted command lanes to `free_response_channels`.
- For a dedicated command bot, also use `allowed_channels` to restrict where it can respond.
- Keep bot-authored messages disabled by default. Discord mentions are not a safe multi-agent handoff bus and can create acknowledgement loops.
- Grant the Discord bot only the permissions it needs. `Administrator` is convenient but is not the least-privilege choice.
- Destructive actions such as deleting channels still require explicit owner intent. `approvals.mode: smart` is not a bypass: it should automatically approve low-risk work and surface genuinely risky operations for owner approval.
- Never use `approvals.mode: off` on an internet-facing or shared Discord gateway.

## Local secret handling

Store `DISCORD_BOT_TOKEN` only in the target profile's local `.env`. Keep real config-lock files outside this repository or in an ignored local file. The committed examples contain placeholders only.

## Release scanning

Run the generic scanner:

```bash
python scripts/privacy_scan.py --surface all
```

For operator-specific names, IDs, paths, domains, or labels, place one literal per line in an ignored local file and run:

```bash
python scripts/privacy_scan.py --surface all \
  --patterns-file .privacy-patterns.local
```

The scanner reports only surface, path, detector type, and line number; it does not print the matched value.

After pushing, clone the public HTTPS repository into a new temporary directory and rerun tests and the privacy scanner there.

## Reporting a vulnerability

Use GitHub's private vulnerability-reporting or security-advisory interface for the repository. Do not open a public issue containing a token, private identifier, exploit transcript, or personal data.
