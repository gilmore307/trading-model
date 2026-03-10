from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry
from src.notify.openclaw_notify import OpenClawNotifier
from src.review.execute_usdt_reset import execute_plan
from src.review.flatten_all import flatten_all_positions
from src.review.prepare_usdt_reset import build_reset_plan
from src.review.reset_weekly import perform_reset
from src.runtime_mode import set_mode

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)
OUT = REPORTS / 'latest-reset-orchestrator.json'


def _price_to_usdt(client, asset: str) -> float:
    if asset == 'USDT':
        return 1.0
    symbol = f'{asset}/USDT'
    ticker = client.spot_exchange.fetch_ticker(symbol)
    return float(ticker.get('last') or ticker.get('bid') or ticker.get('ask') or 0.0)


def equity_report(settings: Settings) -> dict:
    registry = OkxClientRegistry(settings)
    seen: set[str] = set()
    accounts: list[dict] = []
    below_threshold: list[dict] = []
    for strategy in settings.strategies:
        client = registry.for_strategy(strategy)
        if client.account_alias in seen:
            continue
        seen.add(client.account_alias)
        balance = client.spot_exchange.fetch_balance()
        total = balance.get('total') or {}
        asset_rows = []
        equity_usdt = 0.0
        for asset, amount in sorted(total.items()):
            amt = float(amount or 0.0)
            if amt == 0.0:
                continue
            try:
                px = _price_to_usdt(client, asset)
            except Exception:
                px = 0.0 if asset != 'USDT' else 1.0
            value_usdt = amt * px if asset != 'USDT' else amt
            equity_usdt += value_usdt
            asset_rows.append({
                'asset': asset,
                'amount': amt,
                'price_usdt': px,
                'value_usdt': value_usdt,
            })
        row = {
            'account_alias': client.account_alias,
            'account_label': client.account_label,
            'equity_usdt': equity_usdt,
            'threshold_usdt': settings.reset_equity_threshold_usdt,
            'below_threshold': equity_usdt < settings.reset_equity_threshold_usdt,
            'assets': asset_rows,
        }
        if row['below_threshold']:
            below_threshold.append({
                'account_alias': client.account_alias,
                'account_label': client.account_label,
                'equity_usdt': equity_usdt,
            })
        accounts.append(row)
    return {
        'generated_at': datetime.now(UTC).isoformat(),
        'accounts': accounts,
        'threshold_usdt': settings.reset_equity_threshold_usdt,
        'all_accounts_ok': len(below_threshold) == 0,
        'below_threshold_accounts': below_threshold,
    }


def notify(settings: Settings, text: str) -> dict | None:
    if not settings.discord_channel:
        return None
    return OpenClawNotifier(target=settings.discord_channel).send(text)


def orchestrate_reset(settings: Settings) -> dict:
    flatten = flatten_all_positions(settings)
    if not flatten.get('ok'):
        note = 'OKX demo reset paused: flatten-all failed or positions remain. Please close positions manually.'
        notify(settings, note + ' Details: ' + json.dumps(flatten.get('accounts', []), ensure_ascii=False))
        payload = {
            'generated_at': datetime.now(UTC).isoformat(),
            'type': 'reset_orchestrator',
            'status': 'flatten_failed',
            'flatten': flatten,
        }
        OUT.write_text(json.dumps(payload, indent=2))
        return payload

    equity = equity_report(settings)
    if not equity.get('all_accounts_ok'):
        notify(
            settings,
            'OKX demo reset paused: one or more accounts are below the reset equity threshold. '
            'Please reset the demo accounts manually. '
            + json.dumps(equity.get('below_threshold_accounts', []), ensure_ascii=False),
        )
        payload = {
            'generated_at': datetime.now(UTC).isoformat(),
            'type': 'reset_orchestrator',
            'status': 'manual_reset_required',
            'flatten': flatten,
            'equity': equity,
        }
        OUT.write_text(json.dumps(payload, indent=2))
        return payload

    plan = build_reset_plan(settings)
    execution = execute_plan(settings)
    reset = perform_reset(settings)
    set_mode('trade', reason='reset_complete_auto_transition', actor='reset_orchestrator')
    notify(
        settings,
        'OKX demo reset completed automatically. Assets converted to USDT, bucket reset to '
        f'{settings.bucket_initial_capital_usdt} USDT, mode switched to trade.'
    )
    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'reset_orchestrator',
        'status': 'completed_auto',
        'flatten': flatten,
        'equity': equity,
        'plan': plan,
        'execution': execution,
        'reset': reset,
        'next_mode': 'trade',
    }
    OUT.write_text(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    settings = Settings.load()
    payload = orchestrate_reset(settings)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
