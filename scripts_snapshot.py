from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, UTC
import os
import tempfile

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
logs = ROOT / 'logs'
state_path = logs / 'state.json'
health_path = logs / 'service' / 'health.json'
out_path = logs / 'service' / 'snapshot.json'

def atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, prefix=path.name + '.', suffix='.tmp', delete=False) as tmp:
        json.dump(payload, tmp, indent=2)
        tmp.write('\n')
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def is_test_position_key(value: str | None) -> bool:
    return bool(value and value.startswith('test:'))


snapshot = {
    'generated_at': datetime.now(UTC).isoformat(),
    'health': None,
    'state_summary': {
        'open_positions': 0,
        'bucket_count': 0,
        'open_positions_detail': [],
    },
}

if health_path.exists():
    try:
        snapshot['health'] = json.loads(health_path.read_text())
    except Exception:
        snapshot['health'] = None

if state_path.exists():
    data = json.loads(state_path.read_text())
    prod_open_positions = 0
    prod_bucket_count = len([key for key in data.get('buckets', {}) if not is_test_position_key(key)])
    snapshot['state_summary']['bucket_count'] = prod_bucket_count
    for key, value in data.get('positions', {}).items():
        if is_test_position_key(key):
            continue
        items = value if isinstance(value, list) else [value]
        for item in items:
            if item.get('status') == 'open':
                prod_open_positions += 1
                snapshot['state_summary']['open_positions_detail'].append({
                    'position_key': key,
                    'account_alias': item.get('account_alias', 'default'),
                    'account_label': item.get('account_label'),
                    'side': item.get('side'),
                    'symbol': item.get('symbol'),
                    'strategy': item.get('strategy'),
                    'notional_usdt': item.get('notional_usdt'),
                    'margin_required_usdt': item.get('margin_required_usdt'),
                    'amount': item.get('amount'),
                    'requested_amount': item.get('requested_amount'),
                    'leverage': item.get('leverage'),
                })

    snapshot['state_summary']['open_positions'] = prod_open_positions

atomic_write_json(out_path, snapshot)
print(json.dumps(snapshot, indent=2))
