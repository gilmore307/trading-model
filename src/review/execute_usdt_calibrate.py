from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.exchange.okx_client import OkxClientRegistry

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
PLAN = ROOT / 'reports' / 'changes' / 'prepare-usdt-calibrate-plan.json'
OUT = ROOT / 'reports' / 'changes' / 'latest-usdt-calibrate-execution.json'


def execute_plan(settings: Settings) -> dict:
    if not PLAN.exists():
        payload = {
            'generated_at': datetime.now(UTC).isoformat(),
            'type': 'execute_usdt_calibrate',
            'status': 'missing_plan',
            'plan_exists': False,
        }
        OUT.write_text(json.dumps(payload, indent=2))
        return payload

    client_registry = OkxClientRegistry(settings)
    plan = json.loads(PLAN.read_text())
    account_results = []

    for account_plan in plan.get('accounts', []):
        account_alias = account_plan['account_alias']
        account_label = account_plan.get('account_label')
        client = None
        for strategy in settings.strategies:
            candidate = client_registry.for_strategy(strategy)
            if candidate.account_alias == account_alias:
                client = candidate
                break
        if client is None:
            account_results.append({
                'account_alias': account_alias,
                'account_label': account_label,
                'ok': False,
                'error': 'account_not_found_in_registry',
                'results': [],
            })
            continue

        results = []
        all_ok = True
        for action in account_plan.get('actions', []):
            asset = action['asset']
            free = float(action['free'])
            try:
                result = client.convert_asset_to_usdt(asset, free)
                results.append({'asset': asset, 'ok': True, 'result': result})
            except Exception as exc:
                all_ok = False
                results.append({'asset': asset, 'ok': False, 'error': str(exc)})
        account_results.append({
            'account_alias': account_alias,
            'account_label': account_label,
            'ok': all_ok,
            'results': results,
        })

    payload = {
        'generated_at': datetime.now(UTC).isoformat(),
        'type': 'execute_usdt_calibrate',
        'status': 'completed',
        'plan_exists': True,
        'strategy_accounts': client_registry.accounts_by_strategy(),
        'accounts': account_results,
    }
    OUT.write_text(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    settings = Settings.load()
    payload = execute_plan(settings)
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
