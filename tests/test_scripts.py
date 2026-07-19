from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def run_script(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / name), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def load_script(name: str):
    path = ROOT / "scripts" / name
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_configure_command_lane_sets_smart_approvals_without_logging_identifier(tmp_path: Path):
    home = tmp_path / "profile"
    result = run_script(
        "configure-discord-threading.py",
        "--hermes-home",
        str(home),
        "--channel",
        "CHANNEL_ALPHA",
        "--restrict-to-configured-channels",
        "--approvals-mode",
        "smart",
    )
    assert result.returncode == 0, result.stderr
    assert "CHANNEL_ALPHA" not in result.stdout
    config = yaml.safe_load((home / "config.yaml").read_text())
    assert config["discord"]["free_response_channels"] == ["CHANNEL_ALPHA"]
    assert config["discord"]["allowed_channels"] == ["CHANNEL_ALPHA"]
    assert config["discord"]["auto_thread_free_response"] is True
    assert config["approvals"]["mode"] == "smart"


def test_config_lock_reapplies_values_without_printing_values(tmp_path: Path):
    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text("discord:\n  auto_thread: false\n")
    lock = tmp_path / "lock.yaml"
    lock.write_text(
        yaml.safe_dump(
            {
                "profiles": {
                    "default": {
                        "home": str(home),
                        "values": {
                            "discord.auto_thread": True,
                            "discord.free_response_channels": ["CHANNEL_ALPHA"],
                            "approvals.mode": "smart",
                        },
                    }
                }
            }
        )
    )
    result = run_script("apply-config-lock.py", "--lock", str(lock))
    assert result.returncode == 0, result.stderr
    assert "CHANNEL_ALPHA" not in result.stdout
    config = yaml.safe_load((home / "config.yaml").read_text())
    assert config["discord"]["auto_thread"] is True
    assert config["approvals"]["mode"] == "smart"


def test_doctor_config_inspection_reports_counts_not_identifiers(tmp_path: Path):
    module = load_script("discord-pack-doctor.py")
    home = tmp_path / "profile"
    home.mkdir()
    (home / "config.yaml").write_text(
        yaml.safe_dump(
            {
                "discord": {
                    "require_mention": True,
                    "auto_thread": True,
                    "auto_thread_free_response": True,
                    "free_response_channels": ["CHANNEL_ALPHA"],
                },
                "approvals": {"mode": "smart"},
            }
        )
    )
    issues, summary = module.inspect_config(home, require_smart=True)
    assert issues == []
    assert summary["free_response_channel_count"] == 1
    assert "CHANNEL_ALPHA" not in repr(summary)


def test_doctor_recognizes_semantically_applied_patches(tmp_path: Path):
    module = load_script("discord-pack-doctor.py")
    (tmp_path / "hermes_cli").mkdir()
    (tmp_path / "plugins" / "platforms" / "discord").mkdir(parents=True)
    (tmp_path / "tools").mkdir()
    (tmp_path / "hermes_cli" / "config.py").write_text("auto_thread_free_response = False\n")
    (tmp_path / "plugins" / "platforms" / "discord" / "adapter.py").write_text(
        "auto_thread_free_response DISCORD_AUTO_THREAD_FREE_RESPONSE\n"
    )
    (tmp_path / "tools" / "discord_tool.py").write_text(
        "create_channel edit_channel move_channel set_channel_permission "
        "delete_channel_permission delete_channel\n"
    )
    assert module.semantic_patch_present(
        tmp_path, Path("discord-free-response-auto-thread.patch")
    )
    assert module.semantic_patch_present(tmp_path, Path("hermes-discord-admin.patch"))


def test_privacy_scanner_passes_working_tree():
    result = run_script("privacy_scan.py", "--repo", str(ROOT), "--surface", "working")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "findings=0" in result.stdout
