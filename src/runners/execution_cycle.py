from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.execution.pipeline import ExecutionCycleResult, ExecutionPipeline


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
LATEST_PATH = OUT_DIR / 'latest-execution-cycle.json'
HISTORY_PATH = OUT_DIR / 'execution-cycles.jsonl'


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)


def build_execution_artifact(result: ExecutionCycleResult) -> dict[str, Any]:
    payload = asdict(result)
    payload['artifact_type'] = 'execution_cycle'
    payload['recorded_at'] = datetime.now(UTC).isoformat()
    payload['summary'] = {
        'symbol': result.regime_output.symbol,
        'runtime_mode': result.runtime_state.get('mode'),
        'regime': result.regime_output.final_decision.get('primary'),
        'confidence': result.regime_output.final_decision.get('confidence'),
        'plan_action': result.plan.action,
        'plan_account': result.plan.account,
        'plan_reason': result.plan.reason,
        'trade_enabled': result.decision_trace.pipeline_trade_enabled,
        'allow_reason': result.decision_trace.allow_reason,
        'block_reason': result.decision_trace.block_reason,
        'diagnostics': list(result.decision_trace.diagnostics),
        'route_enabled': None if result.route_state is None else result.route_state.get('enabled'),
        'route_frozen_reason': None if result.route_state is None else result.route_state.get('frozen_reason'),
        'live_position_count': len(result.live_positions),
        'receipt_mode': None if result.receipt is None else result.receipt.mode,
        'receipt_accepted': None if result.receipt is None else result.receipt.accepted,
        'alignment_ok': None if result.reconcile_result is None else result.reconcile_result.alignment.ok,
        'policy_action': None if result.reconcile_result is None else result.reconcile_result.policy.action,
        'policy_reason': None if result.reconcile_result is None else result.reconcile_result.policy.reason,
    }
    return payload


def persist_execution_artifact(result: ExecutionCycleResult) -> dict[str, Any]:
    artifact = build_execution_artifact(result)
    LATEST_PATH.write_text(json.dumps(artifact, indent=2, default=_json_default, ensure_ascii=False))
    with HISTORY_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(artifact, default=_json_default, ensure_ascii=False) + '\n')
    return artifact


def main() -> None:
    pipeline = ExecutionPipeline()
    result = pipeline.run_cycle(exchange_snapshot=None)
    artifact = persist_execution_artifact(result)
    print(json.dumps(artifact, indent=2, default=_json_default, ensure_ascii=False))


if __name__ == '__main__':
    main()
