from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, UTC

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
state_path = ROOT / 'logs' / 'state.json'
log_path = ROOT / 'logs' / 'service' / 'daemon.log'

summary = {
    'generated_at': datetime.now(UTC).isoformat(),
    'state_exists': state_path.exists(),
    'log_exists': log_path.exists(),
    'state_mtime': None,
    'open_positions': None,
    'bucket_count': None,
    'open_position_keys': [],
    'last_cycle_status': None,
    'last_cycle_marker': None,
    'last_log_lines': [],
}

if state_path.exists():
    data = json.loads(state_path.read_text())
    summary['state_mtime'] = datetime.fromtimestamp(state_path.stat().st_mtime, UTC).isoformat()
    summary['open_positions'] = data.get('open_positions')
    summary['bucket_count'] = len(data.get('buckets', {}))
    positions = data.get('positions', {})
    open_keys = []
    for key, value in positions.items():
        items = value if isinstance(value, list) else [value]
        if any(item.get('status') == 'open' for item in items):
            open_keys.append(key)
    summary['open_position_keys'] = open_keys

if log_path.exists():
    lines = log_path.read_text().splitlines()
    summary['last_log_lines'] = lines[-10:]
    for line in reversed(lines):
        if 'cycle_ok' in line:
            summary['last_cycle_status'] = 'ok'
            summary['last_cycle_marker'] = line
            break
        if 'cycle_error' in line:
            summary['last_cycle_status'] = 'error'
            summary['last_cycle_marker'] = line
            break
        if 'cycle_skip' in line:
            summary['last_cycle_status'] = 'skip'
            summary['last_cycle_marker'] = line
            break

print(json.dumps(summary, indent=2))
