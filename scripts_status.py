from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.runner.live_trader import local_live_position_map, position_alignment_report
from src.runtime_mode import load_mode_state

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
state_path = ROOT / 'logs' / 'state.json'
log_path = ROOT / 'logs' / 'service' / 'daemon.log'

summary = {
    'generated_at': datetime.now(UTC).isoformat(),
    'mode': load_mode_state(),
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
    'strategy_accounts': {},
    'position_alignment': {
        'ok': None,
        'mismatches': [],
    },
}

data = None
if state_path.exists():
    data = json.loads(state_path.read_text())
    summary['state_mtime'] = datetime.fromtimestamp(state_path.stat().st_mtime, UTC).isoformat()
    summary['open_positions'] = data.get('open_positions')
    summary['bucket_count'] = len(data.get('buckets', {}))
    positions = data.get('positions', {})
    open_keys = []
    for key, value in positions.items():
        items = value if isinstance(value, list) else [value]
        open_items = [item for item in items if item.get('status') == 'open']
        if not open_items:
            continue
        open_keys.append(key)
    summary['open_position_keys'] = open_keys
    summary['local_live_positions'] = local_live_position_map(data)

try:
    settings = Settings.load()
    client_registry = OkxClientRegistry(settings)
    summary['strategy_accounts'] = client_registry.accounts_by_strategy()

    tracked_symbols_by_alias: dict[str, set[str]] = {}
    for strategy in settings.strategies:
        client = client_registry.for_strategy(strategy)
        tracked_symbols_by_alias.setdefault(client.account_alias, set())
        for symbol in settings.symbols:
            tracked_symbols_by_alias[client.account_alias].add(settings.execution_symbol(strategy, symbol))

    per_account_positions: dict[str, list[dict]] = {}
    for strategy in settings.strategies:
        client = client_registry.for_strategy(strategy)
        if client.account_alias in per_account_positions:
            continue
        per_account_positions[client.account_alias] = client.exchange.fetch_positions(sorted(tracked_symbols_by_alias[client.account_alias]))

    if data is None:
        data = {'positions': {}}
    alignment = position_alignment_report(data, per_account_positions)
    summary['exchange_live_positions'] = alignment['exchange_live_positions']
    summary['position_alignment'] = {
        'ok': alignment['ok'],
        'mismatches': alignment['mismatches'],
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
