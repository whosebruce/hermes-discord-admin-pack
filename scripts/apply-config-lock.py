#!/usr/bin/env python3
"""Reapply a sanitized set of protected Hermes config values after updates."""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise SystemExit(f"Expected a YAML mapping in {path.name}")
    return loaded


def set_dotted(data: dict[str, Any], dotted: str, value: Any) -> None:
    cur = data
    parts = dotted.split(".")
    if not all(parts):
        raise SystemExit("Config-lock keys must be non-empty dotted paths")
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    cur[parts[-1]] = value


def atomic_write(path: Path, rendered: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"config.yaml.pre-config-lock-{stamp}.bak")
        backup.write_bytes(path.read_bytes())
        backup.chmod(0o600)
    tmp = path.with_suffix(".yaml.tmp")
    tmp.write_text(rendered, encoding="utf-8")
    tmp.chmod(0o600)
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", required=True, help="Config-lock YAML; keep real IDs in a local ignored copy")
    parser.add_argument("--profile", action="append", help="Apply only this profile name; repeat as needed")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    lock = load_yaml(Path(args.lock).expanduser())
    profiles = lock.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise SystemExit("Config lock must contain a non-empty profiles: mapping")
    wanted = set(args.profile or [])
    changed = 0
    visited = 0

    for name, spec in profiles.items():
        if wanted and name not in wanted:
            continue
        if not isinstance(spec, dict):
            raise SystemExit(f"Profile {name!r} must be a mapping")
        home_raw = spec.get("home")
        values = spec.get("values")
        if not home_raw or not isinstance(values, dict) or not values:
            raise SystemExit(f"Profile {name!r} requires home and non-empty values")
        visited += 1
        cfg_path = Path(str(home_raw)).expanduser() / "config.yaml"
        cfg = load_yaml(cfg_path)
        before = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        for dotted, value in values.items():
            set_dotted(cfg, str(dotted), value)
        after = yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True)
        if before != after:
            changed += 1
            if not args.dry_run:
                atomic_write(cfg_path, after)
            print(f"profile={name} status={'would-update' if args.dry_run else 'updated'}")
        else:
            print(f"profile={name} status=ok")

    if wanted and visited != len(wanted):
        missing = sorted(wanted - set(profiles))
        raise SystemExit(f"Unknown profile name(s): {', '.join(missing)}")
    print(f"profiles_checked={visited}")
    print(f"profiles_changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
