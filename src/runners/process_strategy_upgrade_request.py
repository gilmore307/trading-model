from __future__ import annotations

import json
from pathlib import Path

from src.config.settings import Settings
from src.state.store import LiveStateStore
from src.runtime.workflows import OkxWorkflowHooks, run_strategy_upgrade_event

OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
UPGRADE_REQUEST_PATH = OUT_DIR / 'latest-strategy-upgrade-request.json'
PROCESSED_PATH = OUT_DIR / 'latest-strategy-upgrade-result.json'
HANDOVER_MARKER_PATH = OUT_DIR / 'latest-strategy-handover-marker.json'


def _decide_position_handover(open_positions: list[dict], *, requested_version: str | None) -> dict:
    if not open_positions:
        return {
            'handover_action': 'no_open_position',
            'reason': 'no_open_positions_detected_at_request_processing_time',
            'target_version': requested_version,
        }

    owners = sorted({str(row.get('position_owner') or row.get('route') or 'unknown') for row in open_positions})
    if len(owners) == 1:
        return {
            'handover_action': 'transfer_ownership',
            'reason': 'single_position_owner_detected; reuse_strategy_switch_handling',
            'target_version': requested_version,
            'current_owner': owners[0],
        }
    return {
        'handover_action': 'close_and_wait',
        'reason': 'multiple_or_ambiguous_position_owners_detected',
        'target_version': requested_version,
        'current_owners': owners,
    }


def main() -> None:
    if not UPGRADE_REQUEST_PATH.exists():
        print(json.dumps({'status': 'no_request'}, ensure_ascii=False))
        return
    request = json.loads(UPGRADE_REQUEST_PATH.read_text(encoding='utf-8'))
    state = LiveStateStore().load()
    open_positions = []
    for row in state.positions.values():
        if row is None:
            continue
        size = float(row.size or 0.0)
        ledger_open_size = float(row.ledger_open_size or 0.0)
        if size <= 0.0 and ledger_open_size <= 0.0:
            continue
        open_positions.append({
            'account': row.account,
            'symbol': row.symbol,
            'route': row.route,
            'side': row.side,
            'size': size,
            'ledger_open_size': ledger_open_size,
            'position_owner': (row.meta or {}).get('position_owner', row.route),
        })
    settings = Settings.load()
    settings.ensure_demo_only()
    payload = run_strategy_upgrade_event(hooks=OkxWorkflowHooks(settings))
    handover_decision = _decide_position_handover(open_positions, requested_version=request.get('active_strategy_version'))
    handover_marker = {
        'observed_at': request.get('observed_at'),
        'active_strategy_version': request.get('active_strategy_version'),
        'previous_version': request.get('previous_version'),
        'handover_action': handover_decision.get('handover_action'),
        'handover_reason': handover_decision.get('reason'),
        'position_handover_policy': request.get('position_handover_policy') or 'strategy_switch_handling',
    }
    HANDOVER_MARKER_PATH.write_text(json.dumps(handover_marker, ensure_ascii=False, default=str, indent=2), encoding='utf-8')
    result = {
        'status': 'processed',
        'request': request,
        'position_handover_observation': {
            'open_position_count': len(open_positions),
            'open_positions': open_positions,
            'policy': request.get('position_handover_policy') or 'strategy_switch_handling',
        },
        'position_handover_decision': handover_decision,
        'position_handover_marker': handover_marker,
        'result': payload,
    }
    PROCESSED_PATH.write_text(json.dumps(result, ensure_ascii=False, default=str, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, default=str, indent=2))


if __name__ == '__main__':
    main()
