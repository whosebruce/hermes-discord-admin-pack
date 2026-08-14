# Changelog

All notable public changes are recorded here. Real server IDs, profile names, credentials, and operator-specific paths are never included.

## 1.2.0 — 2026-08-14

### Added

- Native Discord semantic thread-title auto-rename compatibility.
- Safe output-redaction configuration for local Hermes profiles.

### Changed

- Refreshed the Discord administration and free-response auto-thread patches against current Hermes Agent.
- Expanded the private config-lock allowlist to preserve reusable Discord, approval, streaming, and redaction behavior while excluding credentials, personal paths, model/provider settings, and unrelated config.
- Extended current-upstream, privacy, and fresh-clone verification to all three patches.

## 1.1.1 — 2026-07-19

### Added

- Persistent-pack installation under the operator's Hermes home.
- A privacy-minimized config-lock capture helper that stores only approved Discord and approval settings.
- `hermes-discord-safe-update`, which backs up local state, preserves unrelated work, updates Hermes, reapplies the pack and config lock, reinstalls, and verifies before any gateway restart.

### Clarified

- The pack reproduces the protected top-level-message → fresh-thread behavior.
- Local config alone survives ordinary source updates, but the source patch is only update-safe when the installed wrapper or an equivalent preservation workflow is used. A blind raw update is not claimed as protected.

## 1.1.0 — 2026-07-19

### Added

- Daily and push-triggered compatibility CI against current Hermes Agent `main`.
- `discord-pack-doctor.py` for identifier-safe patch and profile readiness checks.
- A generic local config-lock reapply helper and sanitized template.
- Optional `approvals.mode: smart` configuration for low-risk automatic approval with risky actions still gated.
- Protected command-lane and multi-bot loop-safety guidance.
- Working-tree, exact-index, and reachable-history privacy scanning.
- Public security policy and MIT license.
- Unit tests for the configuration, config-lock, doctor, and privacy helpers.

### Changed

- The command-lane configurator no longer prints configured channel IDs.
- Installation examples use local smart approvals and an optional channel allowlist.
- Update guidance now includes a non-mutating doctor and config-lock reapplication.

### Compatibility evidence

- Tested against Hermes Agent `9823f15f6` on 2026-07-19.
- Both patches applied cleanly.
- Focused upstream suite: 126 passed; two dependency deprecation warnings.

## 1.0.0 — 2026-07-12

- Initial sanitized Discord administration patch.
- Free-response command-channel auto-thread opt-in.
- Local configuration helper and agent handoff documentation.
