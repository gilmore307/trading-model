from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.runner.live_trader import account_symbol_key
from src.storage.state import StateStore

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def _live_position_map(per_account_positions: dict[str, list[dict]]) -> dict[str, dict]:
    live: dict[str, dict] = {}
    for account_alias, exchange_positions in per_account_positions.items():
        for position in exchange_positions:
            contracts = float(position.get('contracts') or 0)
            if contracts == 0:
                continue
            symbol = position.get('symbol')
            if not symbol:
                continue
            live[account_symbol_key(account_alias, symbol)] = {
                'account_alias': account_alias,
                'symbol': symbol,
                'contracts': abs(contracts),
                'side': position.get('side'),
                'hedged': bool(position.get('hedged')),
                'pos_side': position.get('info', {}).get('posSide'),
                'raw_pos': position.get('info', {}).get('pos'),
            }
    return live


def reconcile_snapshot(state: dict, live_open: dict[str, dict], now_bar_id: int) -> tuple[dict, list[dict], list[dict]]:
    updated_state = deepcopy(state)
    buckets = updated_state.get('buckets', {})
    closed_keys: list[dict] = []
    normalized_keys: list[dict] = []

    for key, value in list(updated_state.get('positions', {}).items()):
        items = value if isinstance(value, list) else [value]
        updated_items = []
        released_usdt = 0.0

        symbol = None
        account_alias = None
        for item in items:
            if item.get('status') == 'open' and item.get('symbol'):
                symbol = item.get('symbol')
                account_alias = item.get('account_alias', 'default')
                break
            symbol = symbol or item.get('symbol')
            account_alias = account_alias or item.get('account_alias', 'default')

        live_key = account_symbol_key(account_alias or 'default', symbol) if symbol else None
        live = live_open.get(live_key) if live_key else None
        matching_open_indexes: list[int] = []

        for item in items:
            if item.get('status') != 'open':
                updated_items.append(item)
                continue

            item_symbol = item.get('symbol')
            item_side = item.get('side')
            item_account_alias = item.get('account_alias', 'default')
            live_for_item = live_open.get(account_symbol_key(item_account_alias, item_symbol)) if item_symbol else None

            should_close = False
            exit_reason = None
            if live_for_item is None:
                should_close = True
                exit_reason = 'reconcile_exchange_no_position'
            elif item_side != live_for_item.get('side'):
                should_close = True
                exit_reason = f"reconcile_exchange_side_mismatch:{item_side}!={live_for_item.get('side')}"

            if should_close:
                released_usdt += float(item.get('margin_required_usdt') or item.get('notional_usdt') or 0.0)
                updated_items.append({
                    **item,
                    'status': 'closed',
                    'exit_reason': exit_reason,
                    'exit_bar_id': now_bar_id,
                })
                continue

            matching_open_indexes.append(len(updated_items))
            updated_items.append(dict(item))

        if matching_open_indexes and live is not None:
            live_contracts = float(live.get('contracts') or 0.0)
            per_position_amount = live_contracts / len(matching_open_indexes)
            for idx in matching_open_indexes:
                updated_items[idx]['amount'] = per_position_amount
            normalized_keys.append({
                'position_key': key,
                'account_alias': live.get('account_alias'),
                'symbol': live.get('symbol'),
                'side': live.get('side'),
                'live_contracts': live_contracts,
                'open_items': len(matching_open_indexes),
                'per_position_amount': per_position_amount,
            })

        if released_usdt > 0:
            closed_keys.append({'position_key': key, 'released_usdt': released_usdt})
            bucket = buckets.get(key, {})
            buckets[key] = {
                **bucket,
                'available_usdt': float(bucket.get('available_usdt', 0.0)) + released_usdt,
                'allocated_usdt': max(0.0, float(bucket.get('allocated_usdt', 0.0)) - released_usdt),
            }
        updated_state['positions'][key] = updated_items

    return updated_state, closed_keys, normalized_keys


def main() -> None:
    settings = Settings.load()
    client_registry = OkxClientRegistry(settings)
    store = StateStore(LOGS / 'state.json')
    state = store.load()

    per_account_positions: dict[str, list[dict]] = {}
    tracked_symbols_by_alias: dict[str, set[str]] = {}
    for strategy in settings.strategies:
        client = client_registry.for_strategy(strategy)
        tracked_symbols_by_alias.setdefault(client.account_alias, set())
        for symbol in settings.symbols:
            tracked_symbols_by_alias[client.account_alias].add(settings.execution_symbol(strategy, symbol))

    for strategy in settings.strategies:
        client = client_registry.for_strategy(strategy)
        if client.account_alias in per_account_positions:
            continue
        per_account_positions[client.account_alias] = client.exchange.fetch_positions(sorted(tracked_symbols_by_alias[client.account_alias]))

    live_open = _live_position_map(per_account_positions)
    now_bar_id = int(datetime.now(UTC).timestamp() * 1000)

    updated_state, closed_keys, normalized_keys = reconcile_snapshot(state, live_open, now_bar_id)
    store.save(updated_state)
    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'reconcile_state',
        'live_open_symbols': live_open,
        'closed_keys': closed_keys,
        'normalized_keys': normalized_keys,
    }
    out = REPORTS / 'latest-reconcile-state.json'
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
