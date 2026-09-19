#!/usr/bin/env python3
"""Capture only protected Discord and approval settings into a local config lock."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import yaml

DISCORD_KEYS = (
    "require_mention",
    "auto_thread",
    "free_response_auto_thread",
    "thread_require_mention",
    "free_response_channels",
    "allowed_channels",
    "ignored_channels",
    "no_thread_channels",
    "history_backfill",
    "history_backfill_limit",
    "missed_message_backfill",
    "reactions",
    "bots_require_inline_mention",
    "server_actions",
)
PORTABLE_PATHS = (
    "approvals.mode",
    "approvals.cron_mode",
    "approvals.gateway_timeout",
    "security.redact_secrets",
    "privacy.redact_pii",
    "display.platforms.discord.streaming",
)
REQUIRED = {
    "require_mention": True,
    "auto_thread": True,
    "free_response_auto_thread": True,
}


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing {path.name}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise SystemExit(f"Expected a YAML mapping in {path.name}")
    return loaded


def parse_profile(value: str) -> tuple[str, Path]:
    name, separator, raw_home = value.partition("=")
    if not separator or not name.strip() or not raw_home.strip():
        raise argparse.ArgumentTypeError("profiles must use NAME=/path/to/hermes-home")
    return name.strip(), Path(raw_home.strip()).expanduser().resolve()


def channel_count(value: Any) -> int:
    if isinstance(value, list):
        return len([item for item in value if str(item).strip()])
    if isinstance(value, str):
        return len([item for item in value.split(",") if item.strip()])
    return 0


def dotted_get(data: dict[str, Any], dotted: str) -> tuple[bool, Any]:
    current: Any = data
    for part in dotted.split("."):
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def capture_profile(home: Path, require_smart: bool) -> tuple[dict[str, Any], int]:
    config = load_yaml(home / "config.yaml")
    discord_raw = config.get("discord")
    approvals_raw = config.get("approvals")
    discord = dict(discord_raw) if isinstance(discord_raw, dict) else {}
    if "auto_thread_free_response" in discord:
        discord.setdefault("free_response_auto_thread", discord.pop("auto_thread_free_response"))
    approvals = approvals_raw if isinstance(approvals_raw, dict) else {}

    missing = [key for key, expected in REQUIRED.items() if discord.get(key) is not expected]
    if channel_count(discord.get("free_response_channels")) == 0:
        missing.append("free_response_channels")
    if require_smart and approvals.get("mode") != "smart":
        missing.append("approvals.mode")
    if missing:
        raise SystemExit(f"Profile is not ready; missing or incorrect fields: {','.join(missing)}")

    values: dict[str, Any] = {}
    for key in DISCORD_KEYS:
        if key in discord:
            values[f"discord.{key}"] = discord[key]
    for dotted in PORTABLE_PATHS:
        present, value = dotted_get(config, dotted)
        if present:
            values[dotted] = value
    return values, channel_count(discord.get("free_response_channels"))


def atomic_write(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.name}.{stamp}.bak")
        backup.write_bytes(path.read_bytes())
        backup.chmod(0o600)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        action="append",
        type=parse_profile,
        help="Profile as NAME=/path/to/hermes-home; repeat as needed",
    )
    parser.add_argument(
        "--output",
        default=str(Path.home() / ".hermes" / "local-overrides" / "discord-admin-config-lock.yaml"),
    )
    parser.add_argument("--require-smart-approvals", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    profiles = args.profile or [("default", (Path.home() / ".hermes").resolve())]
    lock_profiles: dict[str, Any] = {}
    total_channels = 0
    for name, home in profiles:
        if name in lock_profiles:
            raise SystemExit(f"Duplicate profile name: {name}")
        values, count = capture_profile(home, args.require_smart_approvals)
        lock_profiles[name] = {"home": str(home), "values": values}
        total_channels += count
        print(f"profile={name} captured_channel_count={count}")

    rendered = yaml.safe_dump({"profiles": lock_profiles}, sort_keys=False, allow_unicode=True)
    print(f"profiles_captured={len(lock_profiles)}")
    print(f"total_captured_channel_count={total_channels}")
    if args.dry_run:
        print("dry_run=true")
        return 0
    atomic_write(Path(args.output).expanduser().resolve(), rendered)
    print("config_lock_written=true")
    print("protected_values_printed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
