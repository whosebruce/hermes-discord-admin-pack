#!/usr/bin/env python3
"""Persist Discord command-channel threading in a local Hermes config."""
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
        raise SystemExit(f"Expected a YAML mapping in {path}")
    return data


def _channels(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if value is None:
        return []
    return [item.strip() for item in str(value).split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--hermes-home",
        default=os.getenv("HERMES_HOME", str(Path.home() / ".hermes")),
        help="Hermes home containing config.yaml (repeat for each profile)",
    )
    parser.add_argument(
        "--channel",
        action="append",
        required=True,
        help="Trusted Discord channel ID to add; repeat as needed",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    home = Path(args.hermes_home).expanduser().resolve()
    config_path = home / "config.yaml"
    config = _load(config_path)
    discord = config.setdefault("discord", {})
    if not isinstance(discord, dict):
        raise SystemExit(f"Expected discord: to be a mapping in {config_path}")

    existing = _channels(discord.get("free_response_channels"))
    requested = [str(item).strip() for item in args.channel if str(item).strip()]
    merged = list(dict.fromkeys(existing + requested))
    discord.update(
        {
            "require_mention": True,
            "auto_thread": True,
            "auto_thread_free_response": True,
            "free_response_channels": merged,
        }
    )

    rendered = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    if args.dry_run:
        print(rendered)
        return 0

    home.mkdir(parents=True, exist_ok=True)
    if config_path.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = config_path.with_name(f"config.yaml.pre-discord-threading-{stamp}.bak")
        backup.write_bytes(config_path.read_bytes())
        backup.chmod(0o600)
        print(f"backup={backup}")

    tmp = config_path.with_suffix(".yaml.tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(config_path)
    print(f"updated={config_path}")
    print(f"free_response_channels={','.join(merged)}")
    print("restart_required=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
