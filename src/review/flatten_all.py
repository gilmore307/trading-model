from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.notify.openclaw_notify import OpenClawNotifier

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)

MAX_FLATTEN_PASSES = 3
PASS_SETTLE_SECONDS = 2.0


def _live_swap_positions(exchange) -> list[dict]:
    positions = exchange.fetch_positions()
    out = []
    for position in positions:
        info = position.get('info') or {}
        if info.get('instType') != 'SWAP':
            continue
        contracts = float(position.get('contracts') or 0.0)
        if contracts == 0:
            continue
        out.append(position)
    return out


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
            'flatten_passes': [],
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

        for pass_index in range(1, MAX_FLATTEN_PASSES + 1):
            pass_result = {
                'pass': pass_index,
                'attempted': [],
                'remaining_after_pass': [],
            }
            try:
                positions = _live_swap_positions(exchange)
            except Exception as exc:
                failed = True
                pass_result['attempted'].append({'ok': False, 'error': f'fetch_positions:{exc}'})
                account_result['flatten_passes'].append(pass_result)
                break

            if not positions:
                account_result['flatten_passes'].append(pass_result)
                break

            for position in positions:
                info = position.get('info') or {}
                contracts = float(position.get('contracts') or 0.0)
                side = position.get('side')
                symbol = position.get('symbol')
                order_side = 'sell' if side == 'long' else 'buy'
                try:
                    amount = float(exchange.amount_to_precision(symbol, abs(contracts)))
                    response = exchange.create_order(
                        symbol,
                        'market',
                        order_side,
                        amount,
                        None,
                        {'tdMode': 'cross', 'reduceOnly': True},
                    )
                    row = {
                        'ok': True,
                        'pass': pass_index,
                        'symbol': symbol,
                        'side': side,
                        'contracts': contracts,
                        'order_side': order_side,
                        'amount': amount,
                        'order_id': response.get('id'),
                    }
                    account_result['closed_positions'].append(row)
                    pass_result['attempted'].append(row)
                except Exception as exc:
                    failed = True
                    row = {
                        'ok': False,
                        'pass': pass_index,
                        'symbol': symbol,
                        'side': side,
                        'contracts': contracts,
                        'order_side': order_side,
                        'instType': info.get('instType'),
                        'instId': info.get('instId'),
                        'error': str(exc),
                    }
                    account_result['closed_positions'].append(row)
                    pass_result['attempted'].append(row)

            time.sleep(PASS_SETTLE_SECONDS)
            try:
                remaining = _live_swap_positions(exchange)
            except Exception as exc:
                failed = True
                pass_result['remaining_after_pass'].append({'ok': False, 'error': f'refetch_positions:{exc}'})
                account_result['flatten_passes'].append(pass_result)
                break

            for position in remaining:
                info = position.get('info') or {}
                pass_result['remaining_after_pass'].append({
                    'symbol': position.get('symbol'),
                    'side': position.get('side'),
                    'contracts': float(position.get('contracts') or 0.0),
                    'instType': info.get('instType'),
                    'instId': info.get('instId'),
                })

            account_result['flatten_passes'].append(pass_result)
            if not remaining:
                break

        try:
            final_remaining = _live_swap_positions(exchange)
        except Exception as exc:
            failed = True
            account_result['remaining_positions'].append({'ok': False, 'error': f'final_refetch_positions:{exc}'})
            final_remaining = []

        for position in final_remaining:
            info = position.get('info') or {}
            account_result['remaining_positions'].append({
                'symbol': position.get('symbol'),
                'side': position.get('side'),
                'contracts': float(position.get('contracts') or 0.0),
                'instType': info.get('instType'),
                'instId': info.get('instId'),
            })
            failed = True

        accounts.append(account_result)

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'flatten_all',
        'ok': not failed,
        'max_flatten_passes': MAX_FLATTEN_PASSES,
        'pass_settle_seconds': PASS_SETTLE_SECONDS,
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
