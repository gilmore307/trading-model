from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient

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
    'exchange_live_positions': {},
    'local_live_positions': {},
    'position_alignment': {
        'ok': None,
        'mismatches': [],
    },
}

if state_path.exists():
    data = json.loads(state_path.read_text())
    summary['state_mtime'] = datetime.fromtimestamp(state_path.stat().st_mtime, UTC).isoformat()
    summary['open_positions'] = data.get('open_positions')
    summary['bucket_count'] = len(data.get('buckets', {}))
    positions = data.get('positions', {})
    open_keys = []
    local_live_positions: dict[str, dict] = {}
    for key, value in positions.items():
        items = value if isinstance(value, list) else [value]
        open_items = [item for item in items if item.get('status') == 'open']
        if not open_items:
            continue
        open_keys.append(key)
        symbol = open_items[0].get('symbol')
        if not symbol:
            continue
        side_set = sorted({item.get('side') for item in open_items})
        local_live_positions[symbol] = {
            'position_keys': sorted({item.get('position_key') or key for item in open_items}),
            'strategies': sorted({item.get('strategy') for item in open_items if item.get('strategy')}),
            'count': len(open_items),
            'sides': side_set,
            'amount': round(sum(float(item.get('amount') or 0.0) for item in open_items), 10),
            'notional_usdt': round(sum(float(item.get('notional_usdt') or 0.0) for item in open_items), 10),
        }
    summary['open_position_keys'] = open_keys
    summary['local_live_positions'] = local_live_positions

try:
    settings = Settings.load()
    client = OkxClient(settings)
    syms = sorted({settings.execution_symbol(strategy, symbol) for strategy in settings.strategies for symbol in settings.symbols})
    exchange_positions = client.exchange.fetch_positions(syms)
    live_positions = {}
    for position in exchange_positions:
        contracts = float(position.get('contracts') or 0.0)
        if contracts == 0:
            continue
        symbol = position.get('symbol')
        if not symbol:
            continue
        live_positions[symbol] = {
            'side': position.get('side'),
            'contracts': abs(contracts),
            'hedged': bool(position.get('hedged')),
            'pos_side': position.get('info', {}).get('posSide'),
            'raw_pos': position.get('info', {}).get('pos'),
        }
    summary['exchange_live_positions'] = live_positions

    mismatches = []
    all_symbols = sorted(set(summary['local_live_positions']) | set(live_positions))
    for symbol in all_symbols:
        local = summary['local_live_positions'].get(symbol)
        exchange = live_positions.get(symbol)
        if local is None:
            mismatches.append({
                'symbol': symbol,
                'type': 'missing_local_position',
                'exchange': exchange,
            })
            continue
        if exchange is None:
            mismatches.append({
                'symbol': symbol,
                'type': 'missing_exchange_position',
                'local': local,
            })
            continue

        local_sides = local.get('sides') or []
        if len(local_sides) != 1:
            mismatches.append({
                'symbol': symbol,
                'type': 'multiple_local_sides',
                'local': local,
                'exchange': exchange,
            })
            continue

        local_side = local_sides[0]
        local_amount = float(local.get('amount') or 0.0)
        exchange_contracts = float(exchange.get('contracts') or 0.0)
        if local_side != exchange.get('side'):
            mismatches.append({
                'symbol': symbol,
                'type': 'side_mismatch',
                'local': local,
                'exchange': exchange,
            })
            continue
        if abs(local_amount - exchange_contracts) > 1e-9:
            mismatches.append({
                'symbol': symbol,
                'type': 'amount_mismatch',
                'local': local,
                'exchange': exchange,
                'difference': round(local_amount - exchange_contracts, 10),
            })

    summary['position_alignment'] = {
        'ok': len(mismatches) == 0,
        'mismatches': mismatches,
    }
except Exception as exc:
    summary['position_alignment'] = {
        'ok': False,
        'mismatches': [{
            'type': 'exchange_check_failed',
            'error': str(exc),
        }],
    }

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
