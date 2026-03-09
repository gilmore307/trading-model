from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient
from src.storage.state import StateStore

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def main() -> None:
    settings = Settings.load()
    client = OkxClient(settings)
    store = StateStore(LOGS / 'state.json')
    state = store.load()

    syms = sorted({settings.execution_symbol(strategy, symbol) for strategy in settings.strategies for symbol in settings.symbols})
    exchange_positions = client.exchange.fetch_positions(syms)
    live_open = {
        p.get('symbol'): float(p.get('contracts') or 0)
        for p in exchange_positions
        if p.get('contracts') and float(p.get('contracts')) != 0
    }

    closed_keys = []
    buckets = state.get('buckets', {})
    for key, value in list(state.get('positions', {}).items()):
        items = value if isinstance(value, list) else [value]
        updated_items = []
        released_usdt = 0.0
        for item in items:
            if item.get('status') != 'open':
                updated_items.append(item)
                continue
            symbol = item.get('symbol')
            if symbol not in live_open:
                released_usdt += float(item.get('notional_usdt') or 0.0)
                updated_items.append({
                    **item,
                    'status': 'closed',
                    'exit_reason': 'reconcile_exchange_no_position',
                    'exit_bar_id': int(datetime.now(UTC).timestamp() * 1000),
                })
            else:
                updated_items.append(item)
        if released_usdt > 0:
            closed_keys.append({'position_key': key, 'released_usdt': released_usdt})
            bucket = buckets.get(key, {})
            buckets[key] = {
                **bucket,
                'available_usdt': float(bucket.get('available_usdt', 0.0)) + released_usdt,
                'allocated_usdt': max(0.0, float(bucket.get('allocated_usdt', 0.0)) - released_usdt),
            }
        state['positions'][key] = updated_items

    store.save(state)
    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'reconcile_state',
        'live_open_symbols': live_open,
        'closed_keys': closed_keys,
    }
    out = REPORTS / 'latest-reconcile-state.json'
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
