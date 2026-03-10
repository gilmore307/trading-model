from __future__ import annotations

import json
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.review.calibrate_bucket_reset import perform_calibrate_bucket_reset
from src.runtime_guards import assert_single_okx_trading_daemon_context, current_daemon_pid
from src.runtime_mode import set_mode

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports'
BACKUPS = ROOT / 'backups'
CHANGES = REPORTS / 'changes'
SERVICE_LOGS = LOGS / 'service'
MARKET_DATA = LOGS / 'market-data'
ARCHIVE = LOGS / 'archive'
OUT = CHANGES / 'latest-fresh-reset.json'


def _rm_contents(path: Path) -> list[str]:
    removed: list[str] = []
    if not path.exists():
        return removed
    for child in sorted(path.iterdir()):
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed.append(str(child.relative_to(ROOT)))
    return removed


def backup_current_data(ts: str) -> dict:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    backup_path = BACKUPS / f'fresh-reset-{ts}.tgz'
    with tarfile.open(backup_path, 'w:gz') as tar:
        for rel in ['logs', 'reports']:
            path = ROOT / rel
            if path.exists():
                tar.add(path, arcname=rel)
    return {
        'path': str(backup_path),
        'exists': backup_path.exists(),
        'size_bytes': backup_path.stat().st_size if backup_path.exists() else 0,
    }


def clear_runtime_data() -> dict:
    LOGS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    CHANGES.mkdir(parents=True, exist_ok=True)
    SERVICE_LOGS.mkdir(parents=True, exist_ok=True)
    MARKET_DATA.mkdir(parents=True, exist_ok=True)
    ARCHIVE.mkdir(parents=True, exist_ok=True)

    removed = {
        'logs_archive': _rm_contents(ARCHIVE),
        'logs_market_data': _rm_contents(MARKET_DATA),
        'logs_service': [],
        'reports_changes': _rm_contents(CHANGES),
        'reports_root_files': [],
    }

    for child in sorted(SERVICE_LOGS.iterdir()):
        if child.name == 'daemon.pid':
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()
        removed['logs_service'].append(str(child.relative_to(ROOT)))

    for path in sorted(REPORTS.iterdir()):
        if path.name == 'changes':
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed['reports_root_files'].append(str(path.relative_to(ROOT)))

    state_path = LOGS / 'state.json'
    if state_path.exists():
        state_path.unlink()
        removed['state_json'] = 'logs/state.json'
    else:
        removed['state_json'] = None

    return removed


def fresh_reset() -> dict:
    assert_single_okx_trading_daemon_context(allow_current_run_daemon_pid=current_daemon_pid())
    ts = datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')
    backup = backup_current_data(ts)
    removed = clear_runtime_data()
    settings = Settings.load()
    calibrate_bucket_reset = perform_calibrate_bucket_reset(settings)
    set_mode('test', reason='reset_complete_auto_transition', actor='fresh_reset')

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'fresh_reset',
        'backup': backup,
        'removed': removed,
        'calibrate_bucket_reset': calibrate_bucket_reset,
        'next_mode': 'test',
    }
    CHANGES.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    payload = fresh_reset()
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
