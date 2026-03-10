from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

from src.config.settings import Settings

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT = ROOT / 'reports' / 'changes' / 'latest-review-workflow.json'

settings = Settings.load()
payload = {
    'generated_at': datetime.now(UTC).isoformat(),
    'strategy_accounts': {strategy: settings.account_for_strategy(strategy).alias for strategy in settings.strategies},
    'modes': ['develop', 'review', 'reset', 'trade'],
    'steps': [
        {'order': 1, 'name': 'enter_review_or_reset_mode', 'owner': 'daemon', 'status': 'implemented'},
        {'order': 2, 'name': 'keep_recording_market_data', 'owner': 'live_trader --market-only', 'status': 'implemented'},
        {'order': 3, 'name': 'flatten_all_positions_before_non_trade_actions', 'owner': 'flatten_all', 'status': 'implemented'},
        {'order': 4, 'name': 'discord_alert_if_flatten_failed', 'owner': 'flatten_all', 'status': 'implemented'},
        {'order': 5, 'name': 'generate_review_report', 'owner': 'review_runner', 'status': 'implemented'},
        {'order': 6, 'name': 'auto_transition_review_to_reset', 'owner': 'daemon', 'status': 'implemented'},
        {'order': 7, 'name': 'check_per_account_equity_threshold', 'owner': 'reset_orchestrator', 'status': 'implemented'},
        {'order': 8, 'name': 'discord_alert_if_manual_demo_reset_required', 'owner': 'reset_orchestrator', 'status': 'implemented'},
        {'order': 9, 'name': 'convert_assets_to_usdt_via_spot_cash', 'owner': 'execute_usdt_reset', 'status': 'implemented'},
        {'order': 10, 'name': 'reset_local_virtual_account_fixed_bucket_20000', 'owner': 'reset_weekly', 'status': 'implemented'},
        {'order': 11, 'name': 'auto_transition_reset_to_trade', 'owner': 'reset_orchestrator', 'status': 'implemented'},
        {'order': 12, 'name': 'develop_mode_blocks_trade_and_review', 'owner': 'daemon', 'status': 'implemented'},
    ]
}
OUT.write_text(json.dumps(payload, indent=2))
print(json.dumps(payload, indent=2))
