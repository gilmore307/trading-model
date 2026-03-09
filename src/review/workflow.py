from __future__ import annotations

import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path('/root/.openclaw/workspace/projects/okx-trading')
OUT = ROOT / 'reports' / 'changes' / 'latest-review-workflow.json'

payload = {
    'generated_at': datetime.now(UTC).isoformat(),
    'steps': [
        {'order': 1, 'name': 'pause_trading_keep_data', 'owner': 'daemon', 'status': 'implemented'},
        {'order': 2, 'name': 'generate_review_report', 'owner': 'review_runner', 'status': 'implemented'},
        {'order': 3, 'name': 'prepare_usdt_reset_plan', 'owner': 'prepare_usdt_reset', 'status': 'implemented'},
        {'order': 4, 'name': 'user_resets_okx_demo_account', 'owner': 'user', 'status': 'manual'},
        {'order': 5, 'name': 'convert_primary_assets_to_usdt', 'owner': 'execute_usdt_reset', 'status': 'partial'},
        {'order': 6, 'name': 'reset_local_virtual_account', 'owner': 'reset_weekly', 'status': 'implemented'},
        {'order': 7, 'name': 'apply_parameter_changes_and_log', 'owner': 'log_parameter_change', 'status': 'implemented_scaffold'},
        {'order': 8, 'name': 'resume_trade_mode', 'owner': 'daemon', 'status': 'implemented'},
    ]
}
OUT.write_text(json.dumps(payload, indent=2))
print(json.dumps(payload, indent=2))
