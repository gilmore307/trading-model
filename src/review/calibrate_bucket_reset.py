from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings
from src.review.windows import current_bj_week_window
from src.runner.live_trader import ensure_bucket, position_key
from src.storage.state import StateStore

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
LOGS = ROOT / 'logs'
ARCHIVE = LOGS / 'archive'
ARCHIVE.mkdir(parents=True, exist_ok=True)
REPORTS = ROOT / 'reports' / 'changes'
REPORTS.mkdir(parents=True, exist_ok=True)


def perform_calibrate_bucket_reset(settings: Settings) -> dict:
    state_path = LOGS / 'state.json'
    store = StateStore(state_path)
    old_state = store.load() if state_path.exists() else {
        'positions': {}, 'last_signals': {}, 'history': [], 'buckets': {}
    }

    if state_path.exists():
        archive_path = ARCHIVE / f"state.pre-calibrate-bucket-reset.{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
        archive_path.write_text(json.dumps(old_state, indent=2))

    new_state = {
        'positions': {},
        'last_signals': {},
        'history': old_state.get('history', []),
        'buckets': {},
        'open_positions': 0,
        'calibrate_bucket_reset': {
            'at': datetime.now(UTC).isoformat(),
            'window': current_bj_week_window().end_bj.isoformat(),
            'strategy_accounts': {strategy: settings.account_for_strategy(strategy).alias for strategy in settings.strategies},
        },
    }

    for symbol in settings.symbols:
        for strategy in settings.strategies:
            key = position_key(strategy, symbol)
            ensure_bucket(new_state, key, strategy, symbol, settings.bucket_initial_capital_usdt)

    store.save(new_state)

    change = {
        'type': 'calibrate_bucket_reset',
        'generated_at': datetime.now(UTC).isoformat(),
        'bucket_initial_capital_usdt': settings.bucket_initial_capital_usdt,
        'buffer_capital_usdt': settings.buffer_capital_usdt,
        'symbols': settings.symbols,
        'strategies': settings.strategies,
        'strategy_accounts': {strategy: settings.account_for_strategy(strategy).alias for strategy in settings.strategies},
    }
    out = REPORTS / 'latest-calibrate-bucket-reset.json'
    out.write_text(json.dumps(change, indent=2))
    return change


def main() -> None:
    settings = Settings.load()
    change = perform_calibrate_bucket_reset(settings)
    print(json.dumps(change, indent=2))


if __name__ == '__main__':
    main()
