from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.execution.pipeline import ExecutionCycleResult, ExecutionPipeline
from src.review.account_metrics import build_account_metrics_from_cycle
from src.review.compare import build_compare_snapshot


OUT_DIR = Path('/root/.openclaw/workspace/projects/crypto-trading/logs/runtime')
OUT_DIR.mkdir(parents=True, exist_ok=True)
LATEST_PATH = OUT_DIR / 'latest-execution-cycle.json'
HISTORY_PATH = OUT_DIR / 'execution-cycles.jsonl'


def _json_default(value: Any):
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat()
    return str(value)


def _balance_summary_for_result(result: ExecutionCycleResult) -> dict[str, Any] | None:
    receipt = result.receipt
    if receipt is None or not receipt.accepted or not receipt.account:
        return None
    if receipt.mode not in {'okx_demo', 'okx_live'}:
        return None
    raw = receipt.raw if isinstance(receipt.raw, dict) else {}
    summary = {
        'account_alias': raw.get('account_alias') or receipt.account,
        'account_label': raw.get('account_label'),
        'equity_usdt': raw.get('equity_end_usdt', raw.get('equity_usdt')),
        'equity_end_usdt': raw.get('equity_end_usdt', raw.get('equity_usdt')),
        'realized_pnl_usdt': raw.get('realized_pnl_usdt'),
        'unrealized_pnl_usdt': raw.get('unrealized_pnl_usdt', raw.get('pnl_usdt')),
        'pnl_usdt': raw.get('pnl_usdt'),
    }
    if summary['equity_usdt'] is not None or summary['realized_pnl_usdt'] is not None or summary['unrealized_pnl_usdt'] is not None or summary['pnl_usdt'] is not None:
        return summary
    return None


def _strategy_stats_summary(result: ExecutionCycleResult) -> dict[str, Any]:
    if result.receipt is None or not result.receipt.accepted:
        return {
            'strategy_stats_eligible': False,
            'strategy_stats_reason': 'receipt_not_accepted',
        }
    if result.reconcile_result is not None and not result.reconcile_result.alignment.ok:
        return {
            'strategy_stats_eligible': False,
            'strategy_stats_reason': result.reconcile_result.policy.reason,
        }
    return {
        'strategy_stats_eligible': True,
        'strategy_stats_reason': 'clean_execution',
    }


def build_execution_artifact(result: ExecutionCycleResult) -> dict[str, Any]:
    payload = asdict(result)
    payload['artifact_type'] = 'execution_cycle'
    payload['recorded_at'] = datetime.now(UTC).isoformat()
    payload['compare_snapshot'] = build_compare_snapshot(result)
    balance_summary = _balance_summary_for_result(result)
    stats_summary = _strategy_stats_summary(result)
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
        'composite_selected_strategy': result.router_composite.get('selected_strategy'),
        'composite_position_owner': result.router_composite.get('position_owner'),
        'composite_plan_action': result.router_composite.get('plan', {}).get('action'),
        'composite_position_side': None if result.router_composite.get('position') is None else result.router_composite.get('position', {}).get('side'),
        'receipt_mode': None if result.receipt is None else result.receipt.mode,
        'receipt_accepted': None if result.receipt is None else result.receipt.accepted,
        'alignment_ok': None if result.reconcile_result is None else result.reconcile_result.alignment.ok,
        'policy_action': None if result.reconcile_result is None else result.reconcile_result.policy.action,
        'policy_reason': None if result.reconcile_result is None else result.reconcile_result.policy.reason,
        'account_metrics': build_account_metrics_from_cycle(receipt=result.receipt, reconcile_result=result.reconcile_result, balance_summary=balance_summary),
        **stats_summary,
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
