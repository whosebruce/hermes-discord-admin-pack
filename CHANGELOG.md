# Changelog

All notable public changes are recorded here. Real server IDs, profile names, credentials, and operator-specific paths are never included.

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

- Tested against Hermes Agent `e598cef87` on 2026-07-19.
- Both patches applied cleanly.
- Focused upstream suite: 126 passed; two dependency deprecation warnings.

## 1.0.0 — 2026-07-12

- Initial sanitized Discord administration patch.
- Free-response command-channel auto-thread opt-in.
- Local configuration helper and agent handoff documentation.
