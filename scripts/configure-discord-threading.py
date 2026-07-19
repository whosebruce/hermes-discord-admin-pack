#!/usr/bin/env python3
"""Configure a protected Discord command lane in a local Hermes profile."""
from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path
from typing import Any

import yaml


def _load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise SystemExit(f"Expected a YAML mapping in {path.name}")
    return data


def _channels(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def _atomic_write(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"config.yaml.pre-discord-pack-{stamp}.bak")
        backup.write_bytes(path.read_bytes())
        backup.chmod(0o600)
        print("backup_created=true")
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hermes-home",
        default=os.getenv("HERMES_HOME", str(Path.home() / ".hermes")),
        help="Hermes home containing config.yaml; repeat the command for each profile",
    )
    parser.add_argument(
        "--channel",
        action="append",
        required=True,
        help="Trusted Discord channel ID to add; repeat as needed",
    )
    parser.add_argument(
        "--restrict-to-configured-channels",
        action="store_true",
        help="Also place the configured lanes in discord.allowed_channels",
    )
    parser.add_argument(
        "--approvals-mode",
        choices=("manual", "smart", "off"),
        help="Set Hermes approvals.mode; 'smart' auto-approves low-risk work and prompts on risky actions",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    home = Path(args.hermes_home).expanduser().resolve()
    config_path = home / "config.yaml"
    config = _load(config_path)
    discord = config.setdefault("discord", {})
    if not isinstance(discord, dict):
        raise SystemExit(f"Expected discord: to be a mapping in {config_path.name}")

    existing = _channels(discord.get("free_response_channels"))
    requested = [str(item).strip() for item in args.channel if str(item).strip()]
    if not requested:
        raise SystemExit("At least one non-empty --channel is required")
    merged = list(dict.fromkeys(existing + requested))
    discord.update(
        {
            "require_mention": True,
            "auto_thread": True,
            "auto_thread_free_response": True,
            "free_response_channels": merged,
        }
    )
    if args.restrict_to_configured_channels:
        allowed = _channels(discord.get("allowed_channels"))
        discord["allowed_channels"] = list(dict.fromkeys(allowed + merged))
    if args.approvals_mode:
        approvals = config.setdefault("approvals", {})
        if not isinstance(approvals, dict):
            raise SystemExit(f"Expected approvals: to be a mapping in {config_path.name}")
        approvals["mode"] = args.approvals_mode

    rendered = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    print(f"free_response_channel_count={len(merged)}")
    print(f"allowed_channel_restriction={'enabled' if args.restrict_to_configured_channels else 'unchanged'}")
    print(f"approvals_mode={args.approvals_mode or 'unchanged'}")
    if args.dry_run:
        print("dry_run=true")
        return 0

    _atomic_write(config_path, rendered)
    print("updated=config.yaml")
    print("restart_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
