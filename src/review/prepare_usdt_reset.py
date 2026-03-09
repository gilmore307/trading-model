from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT_DIR = ROOT / 'reports' / 'changes'
OUT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_ASSETS = ['BTC', 'ETH', 'SOL', 'USDC', 'OKB']
PAIR_MAP = {
    'BTC': 'BTC/USDT',
    'ETH': 'ETH/USDT',
    'SOL': 'SOL/USDT',
    'USDC': 'USDC/USDT',
    'OKB': 'OKB/USDT',
}


def main() -> None:
    settings = Settings.load()
    client = OkxClient(settings)
    balance = client.exchange.fetch_balance()
    actions = []
    for asset in TARGET_ASSETS:
        free_amt = float(((balance.get('free', {}) or {}).get(asset)) or 0.0)
        if free_amt <= 0:
            continue
        actions.append({
            'asset': asset,
            'free': free_amt,
            'pair': PAIR_MAP.get(asset),
            'side': 'sell',
            'note': 'convert to USDT before weekly virtual reset',
        })

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'prepare_usdt_reset_plan',
        'actions': actions,
    }
    out = OUT_DIR / 'prepare-usdt-reset-plan.json'
    out.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
