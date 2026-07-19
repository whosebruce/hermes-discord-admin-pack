#!/usr/bin/env python3
"""Check patch, config, and smart-approval readiness without exposing identifiers."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

import yaml

REQUIRED_DISCORD = {
    "require_mention": True,
    "auto_thread": True,
    "auto_thread_free_response": True,
}


def run_git(repo: Path, *args: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def semantic_patch_present(repo: Path, patch: Path) -> bool:
    """Recognize pack behavior even when later local edits prevent reverse-apply."""
    if patch.name == "discord-free-response-auto-thread.patch":
        config = repo / "hermes_cli" / "config.py"
        adapter = repo / "plugins" / "platforms" / "discord" / "adapter.py"
        if not config.exists() or not adapter.exists():
            return False
        config_text = config.read_text(encoding="utf-8", errors="replace")
        adapter_text = adapter.read_text(encoding="utf-8", errors="replace")
        return "auto_thread_free_response" in config_text and all(
            marker in adapter_text
            for marker in ("auto_thread_free_response", "DISCORD_AUTO_THREAD_FREE_RESPONSE")
        )
    if patch.name == "hermes-discord-admin.patch":
        tool = repo / "tools" / "discord_tool.py"
        if not tool.exists():
            return False
        text = tool.read_text(encoding="utf-8", errors="replace")
        return all(
            action in text
            for action in (
                "create_channel",
                "edit_channel",
                "move_channel",
                "set_channel_permission",
                "delete_channel_permission",
                "delete_channel",
            )
        )
    return False


def patch_state(repo: Path, patch: Path) -> str:
    if run_git(repo, "apply", "--reverse", "--check", str(patch)):
        return "applied"
    if semantic_patch_present(repo, patch):
        return "applied"
    if run_git(repo, "apply", "--check", str(patch)):
        return "pending"
    return "incompatible"


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def channel_count(value: Any) -> int:
    if isinstance(value, list):
        return len([v for v in value if str(v).strip()])
    if isinstance(value, str):
        return len([v for v in value.split(",") if v.strip()])
    return 0


def inspect_config(home: Path, require_smart: bool = False) -> tuple[list[str], dict[str, Any]]:
    config = load_yaml(home / "config.yaml")
    discord: dict[str, Any] = {}
    approvals: dict[str, Any] = {}
    discord_raw = config.get("discord")
    approvals_raw = config.get("approvals")
    if isinstance(discord_raw, dict):
        discord = discord_raw
    if isinstance(approvals_raw, dict):
        approvals = approvals_raw
    issues = [key for key, expected in REQUIRED_DISCORD.items() if discord.get(key) is not expected]
    count = channel_count(discord.get("free_response_channels"))
    if count == 0:
        issues.append("free_response_channels")
    mode = approvals.get("mode", "manual")
    if require_smart and mode != "smart":
        issues.append("approvals.mode")
    return issues, {
        "free_response_channel_count": count,
        "allowed_channel_restriction": channel_count(discord.get("allowed_channels")) > 0,
        "approvals_mode": mode,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hermes-repo", default=str(Path.home() / ".hermes" / "hermes-agent"))
    parser.add_argument("--hermes-home", action="append", help="Hermes profile home; repeat as needed")
    parser.add_argument("--pack-dir", default=str(Path(__file__).resolve().parent.parent))
    parser.add_argument("--require-smart-approvals", action="store_true")
    args = parser.parse_args()

    repo = Path(args.hermes_repo).expanduser().resolve()
    pack = Path(args.pack_dir).expanduser().resolve()
    homes = [Path(v).expanduser().resolve() for v in (args.hermes_home or [str(Path.home() / ".hermes")])]
    failed = False

    if not run_git(repo, "rev-parse", "--is-inside-work-tree"):
        print("hermes_repo=missing")
        return 2

    for patch in sorted((pack / "patches").glob("*.patch")):
        state = patch_state(repo, patch)
        print(f"patch={patch.name} state={state}")
        if state != "applied":
            failed = True

    for index, home in enumerate(homes, start=1):
        issues, summary = inspect_config(home, args.require_smart_approvals)
        print(f"profile_index={index} free_response_channel_count={summary['free_response_channel_count']}")
        print(f"profile_index={index} allowed_channel_restriction={str(summary['allowed_channel_restriction']).lower()}")
        print(f"profile_index={index} approvals_mode={summary['approvals_mode']}")
        if issues:
            print(f"profile_index={index} status=needs-attention fields={','.join(issues)}")
            failed = True
        else:
            print(f"profile_index={index} status=ready")

    print("live_discord_test_required=true")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
