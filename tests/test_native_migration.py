"""Native threading migration preserves private config and explicit choices."""
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]


def run(name, *args):
    return subprocess.run([sys.executable, str(ROOT / 'scripts' / name), *map(str, args)],
                          capture_output=True, text=True)


@pytest.mark.parametrize('legacy,native', [(True, None), (False, None), (True, False)])
def test_old_lock_translation_is_idempotent_and_preserves_config(tmp_path, legacy, native):
    home = tmp_path / 'profile'
    home.mkdir()
    cfg = home / 'config.yaml'
    cfg.write_text(yaml.safe_dump({'model': {'default': 'keep-me'}, 'discord': {
        'auto_thread_free_response': legacy, 'free_response_channels': ['CHANNEL_ALPHA']}}))
    values = {'discord.auto_thread_free_response': legacy}
    if native is not None:
        values['discord.free_response_auto_thread'] = native
    lock = tmp_path / 'lock.yaml'
    lock.write_text(yaml.safe_dump({'profiles': {'default': {'home': str(home), 'values': values}}}))
    original_lock = lock.read_bytes()
    result = run('apply-config-lock.py', '--lock', lock, '--dry-run')
    assert result.returncode == 0
    assert 'auto_thread_free_response' in yaml.safe_load(cfg.read_text())['discord']
    for _ in range(2):
        result = run('apply-config-lock.py', '--lock', lock)
        assert result.returncode == 0, result.stderr
        assert 'CHANNEL_ALPHA' not in result.stdout
    data = yaml.safe_load(cfg.read_text())
    assert data['discord']['free_response_auto_thread'] is (legacy if native is None else native)
    assert 'auto_thread_free_response' not in data['discord']
    assert data['discord']['free_response_channels'] == ['CHANNEL_ALPHA']
    assert data['model']['default'] == 'keep-me'
    assert lock.read_bytes() == original_lock
    assert list(home.glob('config.yaml.pre-config-lock-*.bak'))
    assert cfg.stat().st_mode & 0o777 == 0o600


def test_capture_old_config_and_configurator_use_native_key(tmp_path):
    cfg = tmp_path / 'config.yaml'
    cfg.write_text(yaml.safe_dump({'discord': {'require_mention': True, 'auto_thread': True,
        'auto_thread_free_response': True, 'free_response_channels': ['CHANNEL_ALPHA']}}))
    lock = tmp_path / 'lock.yaml'
    result = run('capture-discord-config-lock.py', '--profile', f'default={tmp_path}', '--output', lock)
    assert result.returncode == 0, result.stderr
    values = yaml.safe_load(lock.read_text())['profiles']['default']['values']
    assert values['discord.free_response_auto_thread'] is True
    assert 'discord.auto_thread_free_response' not in values
    result = run('configure-discord-threading.py', '--hermes-home', tmp_path, '--channel', 'CHANNEL_ALPHA')
    assert result.returncode == 0, result.stderr
    data = yaml.safe_load(cfg.read_text())['discord']
    assert data['free_response_auto_thread'] is True
    assert 'auto_thread_free_response' not in data
    assert 'CHANNEL_ALPHA' not in result.stdout
