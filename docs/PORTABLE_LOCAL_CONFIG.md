# Portable local configuration matrix

This pack publishes **behavior and tooling**, not an operator's live Hermes configuration.

| Surface | Publicly reusable | Local/private value | Preservation method |
|---|---|---|---|
| Discord mention and thread behavior | `require_mention`, `auto_thread`, `auto_thread_free_response`, `thread_require_mention` | none unless a channel list is supplied | sanitized examples + private config lock |
| Discord command lanes | list structure and configuration helper | real channel, guild, user, and role IDs | placeholders publicly; values only in ignored local config/lock |
| Discord safety controls | `bots_require_inline_mention`, backfill policy, reactions, ignored/no-thread/allowed-channel structure | any IDs inside those lists/maps | allowlist-only private capture |
| Discord admin actions | tool operations and tests | bot token, guild-specific permission targets | source patch publicly; token only in local `.env` |
| Thread title behavior | semantic native-thread rename and stale-name guard | none | public source patch + safe-update reapply |
| Approval behavior | `approvals.mode`, `cron_mode`, `gateway_timeout` | none | sanitized example + private config lock |
| Output privacy | `security.redact_secrets`, `privacy.redact_pii` | none | sanitized example + private config lock |
| Discord display | streaming behavior | none | allowlist-only private capture |
| Credentials and identity | never | tokens, API keys, OAuth/auth files, emails, phones, names, addresses | excluded; keep in local `.env`, auth files, or credential vault |
| Machine topology | never | home paths, hostnames, IPs, mounts, profile layout | excluded; configure independently per host |
| Unrelated Hermes behavior | never by this pack | models, providers, memory, cron jobs, skills, business/family configuration | excluded from capture and release |

## Why identifiers can appear in a private lock

Channel lists are necessary to reproduce command-lane behavior on the same
operator's installation. The capture helper may therefore preserve their
values in an ignored, mode-`0600` local lock. It never prints those values and
they are never copied into the public repository. A different operator starts
from placeholders and supplies their own IDs locally.

## Release gate

A release is considered portable only after:

1. all three patches apply to current upstream Hermes;
2. focused upstream and pack tests pass;
3. the working tree, exact Git index, and reachable history pass privacy scans;
4. an ignored operator-pattern scan passes without printing matched values;
5. GitHub Actions passes for the pushed commit; and
6. a fresh public HTTPS clone repeats the tests, patch checks, and scans.
