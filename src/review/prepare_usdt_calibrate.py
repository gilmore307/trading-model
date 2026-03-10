from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT_DIR = ROOT / 'reports' / 'changes'
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_ASSETS = ['BTC', 'ETH', 'SOL', 'OKB', 'USDC']
PAIR_MAP = {
    'BTC': 'BTC/USDT',
    'ETH': 'ETH/USDT',
    'SOL': 'SOL/USDT',
    'OKB': 'OKB/USDT',
    'USDC': 'USDC/USDT',
}


def build_calibrate_plan(settings: Settings) -> dict:
    client_registry = OkxClientRegistry(settings)
    accounts = []

    seen_aliases = set()
    for strategy in settings.strategies:
        client = client_registry.for_strategy(strategy)
        if client.account_alias in seen_aliases:
            continue
        seen_aliases.add(client.account_alias)
        balance = client.exchange.fetch_balance()
        actions = []
        for asset in TARGET_ASSETS:
            free_amt = float(((balance.get('free', {}) or {}).get(asset)) or 0.0)
            if free_amt <= 0:
                continue
            actions.append({
                'account_alias': client.account_alias,
                'account_label': client.account_label,
                'asset': asset,
                'free': free_amt,
                'pair': PAIR_MAP.get(asset),
                'side': 'sell',
                'note': 'convert to USDT before weekly calibrate bucket reset',
            })
        accounts.append({
            'account_alias': client.account_alias,
            'account_label': client.account_label,
            'actions': actions,
        })

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'prepare_usdt_calibrate_plan',
        'strategy_accounts': client_registry.accounts_by_strategy(),
        'accounts': accounts,
    }
    out = OUT_DIR / 'prepare-usdt-calibrate-plan.json'
    out.write_text(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    settings = Settings.load()
    payload = build_calibrate_plan(settings)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
