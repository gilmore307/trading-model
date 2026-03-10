from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.notify.openclaw_notify import OpenClawNotifier

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def flatten_all_positions(settings: Settings) -> dict:
    registry = OkxClientRegistry(settings)
    seen: set[str] = set()
    accounts: list[dict] = []
    failed = False

    for strategy in settings.strategies:
        client = registry.for_strategy(strategy)
        if client.account_alias in seen:
            continue
        seen.add(client.account_alias)
        exchange = client.exchange
        exchange.load_markets()
        account_result = {
            'account_alias': client.account_alias,
            'account_label': client.account_label,
            'cancelled_orders': [],
            'closed_positions': [],
            'remaining_positions': [],
        }
        try:
            open_orders = exchange.fetch_open_orders()
        except Exception as exc:
            failed = True
            account_result['cancelled_orders'].append({'ok': False, 'error': f'fetch_open_orders:{exc}'})
            open_orders = []
        for order in open_orders:
            try:
                response = exchange.cancel_order(order['id'], order.get('symbol'))
                account_result['cancelled_orders'].append({
                    'ok': True,
                    'id': order.get('id'),
                    'symbol': order.get('symbol'),
                    'response_id': response.get('id'),
                })
            except Exception as exc:
                failed = True
                account_result['cancelled_orders'].append({
                    'ok': False,
                    'id': order.get('id'),
                    'symbol': order.get('symbol'),
                    'error': str(exc),
                })
        try:
            positions = exchange.fetch_positions()
        except Exception as exc:
            failed = True
            account_result['closed_positions'].append({'ok': False, 'error': f'fetch_positions:{exc}'})
            positions = []
        for position in positions:
            info = position.get('info') or {}
            if info.get('instType') != 'SWAP':
                continue
            contracts = float(position.get('contracts') or 0.0)
            if contracts == 0:
                continue
            side = position.get('side')
            symbol = position.get('symbol')
            order_side = 'sell' if side == 'long' else 'buy'
            try:
                amount = float(exchange.amount_to_precision(symbol, abs(contracts)))
                response = exchange.create_order(symbol, 'market', order_side, amount, None, {'tdMode': 'cross', 'reduceOnly': True})
                account_result['closed_positions'].append({
                    'ok': True,
                    'symbol': symbol,
                    'side': side,
                    'contracts': contracts,
                    'order_side': order_side,
                    'amount': amount,
                    'order_id': response.get('id'),
                })
            except Exception as exc:
                failed = True
                account_result['closed_positions'].append({
                    'ok': False,
                    'symbol': symbol,
                    'side': side,
                    'contracts': contracts,
                    'order_side': order_side,
                    'error': str(exc),
                })
        try:
            remaining = exchange.fetch_positions()
        except Exception as exc:
            failed = True
            account_result['remaining_positions'].append({'ok': False, 'error': f'refetch_positions:{exc}'})
            remaining = []
        for position in remaining:
            info = position.get('info') or {}
            contracts = float(position.get('contracts') or 0.0)
            if contracts == 0:
                continue
            account_result['remaining_positions'].append({
                'symbol': position.get('symbol'),
                'side': position.get('side'),
                'contracts': contracts,
                'instType': info.get('instType'),
                'instId': info.get('instId'),
            })
            failed = True
        accounts.append(account_result)

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'flatten_all',
        'ok': not failed,
        'accounts': accounts,
    }
    (REPORTS / 'latest-flatten-all.json').write_text(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    settings = Settings.load()
    payload = flatten_all_positions(settings)
    if not payload['ok'] and settings.discord_channel:
        notifier = OpenClawNotifier(target=settings.discord_channel)
        notifier.send(
            'OKX demo flatten-all requires manual intervention. Remaining or failed items: '
            + json.dumps(payload['accounts'], ensure_ascii=False)
        )
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
