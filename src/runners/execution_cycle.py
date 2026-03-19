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
ANOMALY_HISTORY_PATH = OUT_DIR / 'execution-anomalies.jsonl'
REGIME_HISTORY_PATH = OUT_DIR / 'regime-local-history.jsonl'


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
    meta = ((result.local_position.meta if result.local_position is not None else None) or {})
    if str(meta.get('strategy_stats_eligible') or '').lower() == 'false':
        return {
            'strategy_stats_eligible': False,
            'strategy_stats_reason': meta.get('strategy_stats_reason') or 'execution_recovery',
        }
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


def _feature_snapshot(result: ExecutionCycleResult) -> dict[str, Any]:
    return {
        'background_4h': {
            'regime': result.regime_output.background_4h.get('primary'),
            'confidence': result.regime_output.background_4h.get('confidence'),
            'tradable': result.regime_output.background_4h.get('tradable'),
            'adx': result.regime_output.background_features.get('adx'),
            'ema20_slope': result.regime_output.background_features.get('ema20_slope'),
            'ema50_slope': result.regime_output.background_features.get('ema50_slope'),
        },
        'primary_15m': {
            'regime': result.regime_output.primary_15m.get('primary'),
            'confidence': result.regime_output.primary_15m.get('confidence'),
            'tradable': result.regime_output.primary_15m.get('tradable'),
            'adx': result.regime_output.primary_features.get('adx'),
            'vwap_deviation_z': result.regime_output.primary_features.get('vwap_deviation_z'),
            'bollinger_bandwidth_pct': result.regime_output.primary_features.get('bollinger_bandwidth_pct'),
            'realized_vol_pct': result.regime_output.primary_features.get('realized_vol_pct'),
            'funding_pctile': result.regime_output.primary_features.get('funding_pctile'),
            'oi_accel': result.regime_output.primary_features.get('oi_accel'),
            'basis_deviation_pct': result.regime_output.primary_features.get('basis_deviation_pct'),
        },
        'override_1m': {
            'regime': None if result.regime_output.override_1m is None else result.regime_output.override_1m.get('primary'),
            'confidence': None if result.regime_output.override_1m is None else result.regime_output.override_1m.get('confidence'),
            'tradable': None if result.regime_output.override_1m is None else result.regime_output.override_1m.get('tradable'),
            'vwap_deviation_z': result.regime_output.override_features.get('vwap_deviation_z'),
            'trade_burst_score': result.regime_output.override_features.get('trade_burst_score'),
            'liquidation_spike_score': result.regime_output.override_features.get('liquidation_spike_score'),
            'orderbook_imbalance': result.regime_output.override_features.get('orderbook_imbalance'),
            'realized_vol_pct': result.regime_output.override_features.get('realized_vol_pct'),
        },
    }


def build_execution_artifact(result: ExecutionCycleResult) -> dict[str, Any]:
    payload = asdict(result)
    payload['artifact_type'] = 'execution_cycle'
    payload['recorded_at'] = datetime.now(UTC).isoformat()
    payload['compare_snapshot'] = build_compare_snapshot(result)
    payload['feature_snapshot'] = _feature_snapshot(result)
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
        'route_strategy_family': result.regime_output.route_decision.get('strategy_family'),
        'route_account': result.regime_output.route_decision.get('account'),
        'route_trade_enabled': result.regime_output.route_decision.get('trade_enabled'),
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


def _build_regime_local_artifact(result: ExecutionCycleResult, artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get('summary') if isinstance(artifact.get('summary'), dict) else {}
    return {
        'artifact_type': 'regime_local_cycle',
        'recorded_at': artifact.get('recorded_at'),
        'symbol': summary.get('symbol'),
        'runtime_mode': summary.get('runtime_mode'),
        'final_regime': summary.get('regime'),
        'final_confidence': summary.get('confidence'),
        'background_regime': ((artifact.get('feature_snapshot') or {}).get('background_4h') or {}).get('regime'),
        'primary_regime': ((artifact.get('feature_snapshot') or {}).get('primary_15m') or {}).get('regime'),
        'override_regime': ((artifact.get('feature_snapshot') or {}).get('override_1m') or {}).get('regime'),
        'route_strategy_family': summary.get('route_strategy_family'),
        'route_account': summary.get('route_account'),
        'route_trade_enabled': summary.get('route_trade_enabled'),
        'plan_action': summary.get('plan_action'),
        'plan_account': summary.get('plan_account'),
        'plan_reason': summary.get('plan_reason'),
        'strategy_stats_eligible': summary.get('strategy_stats_eligible'),
        'strategy_stats_reason': summary.get('strategy_stats_reason'),
        'account_metrics': summary.get('account_metrics'),
        'feature_snapshot': artifact.get('feature_snapshot'),
    }


def _build_anomaly_artifact(result: ExecutionCycleResult, artifact: dict[str, Any]) -> dict[str, Any] | None:
    summary = artifact.get('summary') if isinstance(artifact.get('summary'), dict) else {}
    if bool(summary.get('strategy_stats_eligible', True)):
        return None
    local = result.local_position
    meta = (local.meta if local is not None else {}) or {}
    recovery_type = meta.get('execution_recovery') or summary.get('strategy_stats_reason')
    return {
        'artifact_type': 'execution_anomaly',
        'recorded_at': artifact.get('recorded_at'),
        'runtime_mode': summary.get('runtime_mode'),
        'symbol': summary.get('symbol'),
        'account': summary.get('plan_account') or (None if result.receipt is None else result.receipt.account),
        'plan_action': summary.get('plan_action'),
        'strategy_stats_reason': summary.get('strategy_stats_reason'),
        'execution_recovery': recovery_type,
        'execution_recovery_detail': meta.get('execution_recovery_detail'),
        'route_enabled': summary.get('route_enabled'),
        'route_frozen_reason': summary.get('route_frozen_reason'),
        'receipt_mode': summary.get('receipt_mode'),
        'receipt_accepted': summary.get('receipt_accepted'),
        'policy_action': summary.get('policy_action'),
        'policy_reason': summary.get('policy_reason'),
        'local_position_status': None if local is None else local.status.value,
        'local_position_reason': None if local is None else local.reason,
        'account_metrics': summary.get('account_metrics'),
    }


def persist_execution_artifact(result: ExecutionCycleResult) -> dict[str, Any]:
    artifact = build_execution_artifact(result)
    LATEST_PATH.write_text(json.dumps(artifact, indent=2, default=_json_default, ensure_ascii=False))
    with HISTORY_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(artifact, default=_json_default, ensure_ascii=False) + '\n')
    regime_local = _build_regime_local_artifact(result, artifact)
    with REGIME_HISTORY_PATH.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(regime_local, default=_json_default, ensure_ascii=False) + '\n')
    anomaly = _build_anomaly_artifact(result, artifact)
    if anomaly is not None:
        with ANOMALY_HISTORY_PATH.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(anomaly, default=_json_default, ensure_ascii=False) + '\n')
    return artifact


def main() -> None:
    pipeline = ExecutionPipeline()
    result = pipeline.run_cycle(exchange_snapshot=None)
    artifact = persist_execution_artifact(result)
    print(json.dumps(artifact, indent=2, default=_json_default, ensure_ascii=False))


if __name__ == '__main__':
    main()
