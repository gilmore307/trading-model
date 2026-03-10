from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, UTC

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
logs = ROOT / 'logs'
state_path = logs / 'state.json'
health_path = logs / 'service' / 'health.json'
out_path = logs / 'service' / 'snapshot.json'

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
    snapshot['health'] = json.loads(health_path.read_text())

if state_path.exists():
    data = json.loads(state_path.read_text())
    snapshot['state_summary']['open_positions'] = data.get('open_positions', 0)
    snapshot['state_summary']['bucket_count'] = len(data.get('buckets', {}))
    for key, value in data.get('positions', {}).items():
        items = value if isinstance(value, list) else [value]
        for item in items:
            if item.get('status') == 'open':
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

out_path.write_text(json.dumps(snapshot, indent=2))
print(json.dumps(snapshot, indent=2))
