"""Exercise installer preflight and idempotence against real disposable Git repos."""
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATCH_NAMES = (
    "hermes-discord-admin.patch",
    "discord-native-thread-auto-rename.patch",
)


@pytest.fixture
def installation(tmp_path):
    pack = tmp_path / "pack"
    repo = tmp_path / "repo"
    (pack / "scripts").mkdir(parents=True)
    (pack / "patches").mkdir()
    repo.mkdir()
    shutil.copy2(ROOT / "scripts/apply-discord-admin-pack.sh", pack / "scripts")
    shutil.copy2(ROOT / "scripts/check-native-threading.py", pack / "scripts")
    (repo / "hermes_cli").mkdir()
    (repo / "hermes_cli/config_defaults.py").write_text('DEFAULT_CONFIG = {"free_response_auto_thread": False}\n')
    (repo / "plugins/platforms/discord").mkdir(parents=True)
    (repo / "plugins/platforms/discord/adapter.py").write_text(
        'def _discord_free_response_auto_thread():\n    return "DISCORD_FREE_RESPONSE_AUTO_THREAD"\n'
    )
    subprocess.run(["git", "init", str(repo)], check=True, capture_output=True)
    for index, name in enumerate(PATCH_NAMES):
        (repo / f"feature-{index}").write_text("old\n")
        (pack / "patches" / name).write_text(
            f"diff --git a/feature-{index} b/feature-{index}\n"
            f"--- a/feature-{index}\n+++ b/feature-{index}\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )
    return pack, repo


def install(pack, repo):
    return subprocess.run(
        ["bash", str(pack / "scripts/apply-discord-admin-pack.sh"), str(repo)],
        text=True, capture_output=True,
    )


def test_installer_applies_once_then_is_noop(installation):
    pack, repo = installation
    first = install(pack, repo)
    assert first.returncode == 0, first.stderr
    second = install(pack, repo)
    assert second.returncode == 0, second.stderr
    assert second.stdout.count("already applied:") == len(PATCH_NAMES)
    assert all((repo / f"feature-{i}").read_text() == "new\n" for i in range(len(PATCH_NAMES)))


@pytest.mark.parametrize("legacy", [False, True])
def test_installer_refuses_missing_native_or_retired_patch(installation, legacy):
    pack, repo = installation
    adapter = repo / "plugins/platforms/discord/adapter.py"
    adapter.write_text(adapter.read_text() + '\nDISCORD_AUTO_THREAD_FREE_RESPONSE = True\n' if legacy else '')
    result = install(pack, repo)
    assert result.returncode != 0
    assert all((repo / f"feature-{i}").read_text() == "old\n" for i in range(len(PATCH_NAMES)))


def test_late_incompatible_patch_does_not_partially_apply(installation):
    pack, repo = installation
    (repo / "feature-1").write_text("incompatible\n")
    result = install(pack, repo)
    assert result.returncode != 0
    assert "No patches were applied" in result.stderr
    assert (repo / "feature-0").read_text() == "old\n"
    assert (repo / "feature-1").read_text() == "incompatible\n"
