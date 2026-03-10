from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.execution.executor import realized_pnl_from_prices
from src.runner.live_trader import account_symbol_key
from src.storage.state import StateStore


def _latest_close_price(account_alias: str, symbol: str) -> float | None:
    symbol_key = symbol.replace('/', '_').replace(':', '_')
    path = LOGS / 'market-data' / 'ohlc' / '1m' / f'{account_alias}_{symbol_key}.jsonl'
    if not path.exists():
        return None
    last = None
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                last = row
            except Exception:
                continue
    if not last:
        return None
    return last.get('close')

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
    history = updated_state.setdefault('history', [])
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
            item_status = item.get('status')
            if item_status not in {'open', 'closed', 'exit_verifying', 'entry_incomplete'}:
                updated_items.append(item)
                continue

            item_symbol = item.get('symbol')
            item_side = item.get('side')
            item_account_alias = item.get('account_alias', 'default')
            live_for_item = live_open.get(account_symbol_key(item_account_alias, item_symbol)) if item_symbol else None

            if item_status == 'closed' and live_for_item is not None:
                updated_items.append({
                    **item,
                    'status': 'reconcile_mismatch',
                    'reconcile_reason': 'closed_but_exchange_position_exists',
                    'last_confirmed_live_contracts': float(live_for_item.get('contracts') or 0.0),
                    'last_confirmed_live_side': live_for_item.get('side'),
                    'last_exchange_observed_at': datetime.now(UTC).isoformat(),
                })
                history.append({
                    'event_id': f"{item.get('trade_id') or item.get('position_key') or key}:reconcile_mismatch:{now_bar_id}",
                    'trade_id': item.get('trade_id') or item.get('position_key') or key,
                    'type': 'reconcile_mismatch',
                    'position_key': item.get('position_key') or key,
                    'symbol': item_symbol,
                    'strategy': item.get('strategy'),
                    'side': item_side,
                    'reason': 'closed_but_exchange_position_exists',
                    'bar_id': now_bar_id,
                    'mode': 'reconcile',
                    'exchange_contracts': float(live_for_item.get('contracts') or 0.0),
                    'exchange_side': live_for_item.get('side'),
                    'account_alias': item_account_alias,
                    'account_label': item.get('account_label'),
                })
                continue

            if item_status == 'closed':
                updated_items.append(item)
                continue

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
                exit_reference_price = _latest_close_price(item_account_alias, item_symbol) if item_symbol else None
                realized_pnl_usdt = realized_pnl_from_prices(
                    item.get('side'),
                    item.get('amount') or item.get('requested_amount'),
                    item.get('reference_price'),
                    exit_reference_price,
                )
                updated_items.append({
                    **item,
                    'trade_id': item.get('trade_id'),
                    'status': 'closed',
                    'exit_reason': exit_reason,
                    'exit_bar_id': now_bar_id,
                    'exit_reference_price': exit_reference_price,
                    'exit_fee_usdt': None,
                    'realized_pnl_usdt': realized_pnl_usdt,
                })
                history.append({
                    'event_id': f"{item.get('trade_id') or item.get('position_key') or key}:reconcile_exit:{now_bar_id}",
                    'trade_id': item.get('trade_id') or item.get('position_key') or key,
                    'type': 'exit',
                    'position_key': item.get('position_key') or key,
                    'symbol': item_symbol,
                    'strategy': item.get('strategy'),
                    'side': None,
                    'reason': exit_reason,
                    'bar_id': now_bar_id,
                    'mode': 'reconcile',
                    'released_usdt': float(item.get('margin_required_usdt') or item.get('notional_usdt') or 0.0),
                    'tracked_amount': item.get('amount') or item.get('requested_amount'),
                    'realized_pnl_usdt': realized_pnl_usdt,
                    'venue_order_id': None,
                    'venue_status': 'reconcile',
                    'venue_order_side': None,
                    'venue_ccxt_symbol': item_symbol,
                    'requested_amount': item.get('requested_amount') or item.get('amount'),
                    'executed_amount': item.get('amount') or item.get('requested_amount'),
                    'reference_price': exit_reference_price,
                    'fee_usdt': None,
                    'account_alias': item_account_alias,
                    'account_label': item.get('account_label'),
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
            realized_total = sum(float(item.get('realized_pnl_usdt') or 0.0) for item in updated_items if item.get('status') == 'closed')
            buckets[key] = {
                **bucket,
                'available_usdt': float(bucket.get('available_usdt', 0.0)) + released_usdt,
                'allocated_usdt': max(0.0, float(bucket.get('allocated_usdt', 0.0)) - released_usdt),
                'realized_pnl_usdt': realized_total,
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
