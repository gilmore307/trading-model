from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClient

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
PLAN = ROOT / 'reports' / 'changes' / 'prepare-usdt-reset-plan.json'
OUT = ROOT / 'reports' / 'changes' / 'latest-usdt-reset-execution.json'


def main() -> None:
    if not PLAN.exists():
        payload = {
            'generated_at': datetime.now(UTC).isoformat(),
            'type': 'execute_usdt_reset',
            'status': 'missing_plan',
            'plan_exists': False,
        }
        OUT.write_text(json.dumps(payload, indent=2))
        print(json.dumps(payload, indent=2))
        return

    settings = Settings.load()
    client = OkxClient(settings)
    plan = json.loads(PLAN.read_text())
    results = []
    for action in plan.get('actions', []):
        asset = action['asset']
        free = float(action['free'])
        try:
            result = client.convert_asset_to_usdt(asset, free)
            results.append({'asset': asset, 'ok': True, 'result': result})
        except Exception as exc:
            results.append({'asset': asset, 'ok': False, 'error': str(exc)})

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'execute_usdt_reset',
        'status': 'completed',
        'plan_exists': True,
        'results': results,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
