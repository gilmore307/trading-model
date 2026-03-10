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
    'modes': ['develop', 'test', 'review', 'calibrate', 'reset', 'trade'],
    'steps': [
        {'order': 1, 'name': 'enter_review_calibrate_or_reset_mode', 'owner': 'daemon', 'status': 'implemented'},
        {'order': 2, 'name': 'keep_recording_market_data', 'owner': 'live_trader --market-only', 'status': 'implemented'},
        {'order': 3, 'name': 'flatten_all_positions_before_non_trade_actions', 'owner': 'flatten_all', 'status': 'implemented'},
        {'order': 4, 'name': 'discord_alert_if_flatten_failed', 'owner': 'flatten_all', 'status': 'implemented'},
        {'order': 5, 'name': 'generate_review_report', 'owner': 'review_runner', 'status': 'implemented'},
        {'order': 6, 'name': 'auto_transition_review_to_calibrate', 'owner': 'daemon', 'status': 'implemented'},
        {'order': 7, 'name': 'check_per_account_equity_threshold', 'owner': 'calibrate_orchestrator', 'status': 'implemented'},
        {'order': 8, 'name': 'discord_alert_if_manual_demo_account_reset_required_before_calibrate', 'owner': 'calibrate_orchestrator', 'status': 'implemented'},
        {'order': 9, 'name': 'convert_assets_to_usdt_via_spot_cross_for_calibrate', 'owner': 'execute_usdt_calibrate', 'status': 'implemented'},
        {'order': 10, 'name': 'calibrate_bucket_reset_local_virtual_account_fixed_bucket_20000', 'owner': 'calibrate_bucket_reset', 'status': 'implemented'},
        {'order': 11, 'name': 'auto_transition_calibrate_to_trade', 'owner': 'calibrate_orchestrator', 'status': 'implemented'},
        {'order': 12, 'name': 'auto_transition_reset_to_test', 'owner': 'fresh_reset', 'status': 'implemented'},
        {'order': 13, 'name': 'run_buffer_funded_test_stress_mode_on_breakout_xrp', 'owner': 'test_mode', 'status': 'implemented'},
        {'order': 14, 'name': 'auto_transition_test_to_develop', 'owner': 'daemon', 'status': 'implemented'},
        {'order': 15, 'name': 'develop_mode_blocks_trade_and_review', 'owner': 'daemon', 'status': 'implemented'},
    ]
}
OUT.write_text(json.dumps(payload, indent=2))
print(json.dumps(payload, indent=2))
