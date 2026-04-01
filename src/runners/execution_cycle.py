from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.execution.pipeline import ExecutionCycleResult, ExecutionPipeline, ParallelExecutionCycleResult
from src.review.account_metrics import build_account_metrics_from_cycle
from src.review.compare import build_compare_snapshot
from src.runtime.log_paths import RUNTIME_DIR, dated_jsonl_path
from src.strategies.executors import build_shadow_plans


OUT_DIR = RUNTIME_DIR
LATEST_PATH = OUT_DIR / 'latest-execution-cycle.json'
LATEST_PARALLEL_PATH = OUT_DIR / 'latest-parallel-execution-cycle.json'
HISTORY_PATH = lambda: dated_jsonl_path('execution-cycles')
PARALLEL_HISTORY_PATH = lambda: dated_jsonl_path('parallel-execution-cycles')
ANOMALY_HISTORY_PATH = lambda: dated_jsonl_path('execution-anomalies')
REGIME_HISTORY_PATH = lambda: dated_jsonl_path('regime-local-history')
STRATEGY_ACTIVITY_PATH = lambda: dated_jsonl_path('strategy-activity-history')


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
            'scores': result.regime_output.background_4h.get('scores'),
            'tradable': result.regime_output.background_4h.get('tradable'),
            'adx': result.regime_output.background_features.get('adx'),
            'last_price': result.regime_output.background_features.get('last_price'),
            'ema20_slope': result.regime_output.background_features.get('ema20_slope'),
            'ema50_slope': result.regime_output.background_features.get('ema50_slope'),
        },
        'primary_15m': {
            'regime': result.regime_output.primary_15m.get('primary'),
            'confidence': result.regime_output.primary_15m.get('confidence'),
            'scores': result.regime_output.primary_15m.get('scores'),
            'tradable': result.regime_output.primary_15m.get('tradable'),
            'adx': result.regime_output.primary_features.get('adx'),
            'last_price': result.regime_output.primary_features.get('last_price'),
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
            'scores': None if result.regime_output.override_1m is None else result.regime_output.override_1m.get('scores'),
            'tradable': None if result.regime_output.override_1m is None else result.regime_output.override_1m.get('tradable'),
            'last_price': result.regime_output.override_features.get('last_price'),
            'vwap_deviation_z': result.regime_output.override_features.get('vwap_deviation_z'),
            'trade_burst_score': result.regime_output.override_features.get('trade_burst_score'),
            'liquidation_spike_score': result.regime_output.override_features.get('liquidation_spike_score'),
            'orderbook_imbalance': result.regime_output.override_features.get('orderbook_imbalance'),
            'realized_vol_pct': result.regime_output.override_features.get('realized_vol_pct'),
        },
    }


def _verification_snapshot(result: ExecutionCycleResult) -> dict[str, Any]:
    local = result.local_position
    meta = ((local.meta if local is not None else None) or {})
    hint = meta.get('last_verification_hint') if isinstance(meta.get('last_verification_hint'), dict) else {}
    attempts = hint.get('verification_attempts') or []
    trade_confirmed_attempts = [row for row in attempts if isinstance(row, dict) and bool(row.get('trade_confirmed'))]
    return {
        'entry_verified_hint': bool(hint.get('verified_entry')),
        'entry_trade_confirmed': bool(trade_confirmed_attempts),
        'entry_verification_attempt_count': len(attempts),
        'entry_trade_confirmed_attempt_count': len(trade_confirmed_attempts),
        'entry_verification_attempts': attempts,
        'local_position_reason': None if local is None else local.reason,
        'local_position_status': None if local is None else local.status.value,
    }


def _build_attribution_snapshot(result: ExecutionCycleResult) -> dict[str, Any]:
    receipt = result.receipt
    local = result.local_position
    ledger = None if local is None else {
        'open_leg_ids': [leg.leg_id for leg in local.open_legs],
        'closed_leg_ids': [leg.leg_id for leg in local.closed_legs],
        'pending_exit_leg_ids': [] if local.pending_exit is None else [alloc.leg_id for alloc in local.pending_exit.allocations],
    }
    raw = {} if receipt is None or not isinstance(receipt.raw, dict) else receipt.raw
    return {
        'account': None if receipt is None else receipt.account,
        'execution_id': None if receipt is None else receipt.execution_id,
        'client_order_id': None if receipt is None else receipt.client_order_id,
        'order_id': None if receipt is None else receipt.order_id,
        'trade_ids': None if receipt is None else receipt.trade_ids,
        'trade_count': 0 if receipt is None or receipt.trade_ids is None else len(receipt.trade_ids),
        'fee_source': 'fill_aggregation' if raw.get('fill_count') else ('order_payload' if raw.get('fee_usdt') is not None else None),
        'realized_pnl_source': 'fill_aggregation' if raw.get('fill_count') else ('order_payload' if raw.get('realized_pnl_usdt') is not None else None),
        'equity_source': 'balance_summary' if raw.get('equity_end_usdt') is not None or raw.get('equity_usdt') is not None else None,
        'ledger': ledger,
        'pending_exit_allocations': [] if local is None or local.pending_exit is None else [
            {
                'leg_id': alloc.leg_id,
                'requested_size': alloc.requested_size,
                'closed_size': alloc.closed_size,
                'trade_ids': alloc.trade_ids,
                'fee_usdt': alloc.fee_usdt,
                'realized_pnl_usdt': alloc.realized_pnl_usdt,
            }
            for alloc in local.pending_exit.allocations
        ],
    }


def build_execution_artifact(result: ExecutionCycleResult) -> dict[str, Any]:
    payload = asdict(result)
    payload['artifact_type'] = 'execution_cycle'
    payload['recorded_at'] = datetime.now(UTC).isoformat()
    payload['compare_snapshot'] = build_compare_snapshot(result)
    payload['feature_snapshot'] = _feature_snapshot(result)
    payload['shadow_plans'] = build_shadow_plans(result.regime_output)
    payload['verification_snapshot'] = _verification_snapshot(result)
    payload['attribution_snapshot'] = _build_attribution_snapshot(result)
    payload['ledger_snapshot'] = None if result.local_position is None else {
        'open_legs': [
            {
                'leg_id': leg.leg_id,
                'execution_id': leg.execution_id,
                'client_order_id': leg.client_order_id,
                'order_id': leg.order_id,
                'trade_ids': leg.trade_ids,
                'side': leg.side,
                'requested_size': leg.requested_size,
                'filled_size': leg.filled_size,
                'remaining_size': leg.remaining_size,
                'status': leg.status,
                'reason': leg.reason,
            }
            for leg in result.local_position.open_legs
        ],
        'closed_legs': [
            {
                'leg_id': leg.leg_id,
                'execution_id': leg.execution_id,
                'client_order_id': leg.client_order_id,
                'order_id': leg.order_id,
                'trade_ids': leg.trade_ids,
                'side': leg.side,
                'requested_size': leg.requested_size,
                'filled_size': leg.filled_size,
                'remaining_size': leg.remaining_size,
                'status': leg.status,
                'close_execution_id': leg.close_execution_id,
                'close_client_order_id': leg.close_client_order_id,
                'close_order_id': leg.close_order_id,
                'close_trade_ids': leg.close_trade_ids,
            }
            for leg in result.local_position.closed_legs
        ],
        'pending_exit': None if result.local_position.pending_exit is None else {
            'execution_id': result.local_position.pending_exit.execution_id,
            'client_order_id': result.local_position.pending_exit.client_order_id,
            'order_id': result.local_position.pending_exit.order_id,
            'trade_ids': result.local_position.pending_exit.trade_ids,
            'requested_size': result.local_position.pending_exit.requested_size,
            'side': result.local_position.pending_exit.side,
            'status': result.local_position.pending_exit.status,
            'reason': result.local_position.pending_exit.reason,
            'allocations': [
                {
                    'leg_id': alloc.leg_id,
                    'requested_size': alloc.requested_size,
                    'closed_size': alloc.closed_size,
                    'trade_ids': alloc.trade_ids,
                    'fee_usdt': alloc.fee_usdt,
                    'realized_pnl_usdt': alloc.realized_pnl_usdt,
                }
                for alloc in result.local_position.pending_exit.allocations
            ],
        },
    }
    balance_summary = _balance_summary_for_result(result)
    stats_summary = _strategy_stats_summary(result)
    ledger_open_size = 0.0 if result.local_position is None else float(result.local_position.ledger_open_size or 0.0)
    position_size = 0.0 if result.local_position is None else float(result.local_position.size or 0.0)
    payload['summary'] = {
        'symbol': result.regime_output.symbol,
        'execution_id': None if result.receipt is None else result.receipt.execution_id,
        'client_order_id': None if result.receipt is None else result.receipt.client_order_id,
        'order_id': None if result.receipt is None else result.receipt.order_id,
        'trade_ids': None if result.receipt is None else result.receipt.trade_ids,
        'entry_verified_hint': payload['verification_snapshot'].get('entry_verified_hint'),
        'entry_trade_confirmed': payload['verification_snapshot'].get('entry_trade_confirmed'),
        'entry_verification_attempt_count': payload['verification_snapshot'].get('entry_verification_attempt_count'),
        'open_leg_count': 0 if result.local_position is None else len(result.local_position.open_legs),
        'closed_leg_count': 0 if result.local_position is None else len(result.local_position.closed_legs),
        'pending_exit_leg_count': 0 if result.local_position is None or result.local_position.pending_exit is None else len(result.local_position.pending_exit.allocations),
        'ledger_open_size': ledger_open_size,
        'position_size': position_size,
        'position_ledger_diff': position_size - ledger_open_size,
        'runtime_mode': result.runtime_state.get('mode'),
        'active_strategy_version': result.active_strategy.get('version'),
        'active_strategy_updated_at': result.active_strategy.get('updated_at'),
        'active_strategy_source': result.active_strategy.get('source'),
        'active_strategy_family': (result.active_strategy.get('metadata') or {}).get('family'),
        'active_strategy_config_path': (result.active_strategy.get('metadata') or {}).get('config_path'),
        'active_strategy_promoted_at': (result.active_strategy.get('metadata') or {}).get('promoted_at'),
        'active_strategy_promotion_note': (result.active_strategy.get('metadata') or {}).get('promotion_note'),
        'regime': result.regime_output.final_decision.get('primary'),
        'confidence': result.regime_output.final_decision.get('confidence'),
        'plan_action': result.plan.action,
        'plan_account': result.plan.account,
        'plan_reason': result.plan.reason,
        'route_strategy_family': result.regime_output.route_decision.get('strategy_family'),
        'route_account': result.regime_output.route_decision.get('account'),
        'route_trade_enabled': result.regime_output.route_decision.get('trade_enabled'),
        'trade_enabled': result.decision_trace.pipeline_trade_enabled,
        'pipeline_entered': result.decision_trace.pipeline_entered,
        'submission_allowed': result.decision_trace.submission_allowed,
        'submission_attempted': result.decision_trace.submission_attempted,
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
        'composite_switch_action': result.router_composite.get('switch_action'),
        'receipt_mode': None if result.receipt is None else result.receipt.mode,
        'receipt_accepted': None if result.receipt is None else result.receipt.accepted,
        'alignment_ok': None if result.reconcile_result is None else result.reconcile_result.alignment.ok,
        'policy_action': None if result.reconcile_result is None else result.reconcile_result.policy.action,
        'policy_reason': None if result.reconcile_result is None else result.reconcile_result.policy.reason,
        'account_metrics': build_account_metrics_from_cycle(receipt=result.receipt, reconcile_result=result.reconcile_result, balance_summary=balance_summary, local_position=result.local_position),
        'attribution_trade_count': payload['attribution_snapshot'].get('trade_count'),
        'attribution_fee_source': payload['attribution_snapshot'].get('fee_source'),
        'attribution_realized_pnl_source': payload['attribution_snapshot'].get('realized_pnl_source'),
        'attribution_equity_source': payload['attribution_snapshot'].get('equity_source'),
        'position_open_during_cycle': bool(position_size > 0.0 or ledger_open_size > 0.0),
        **stats_summary,
    }
    return payload


def _build_strategy_activity_artifacts(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    summary = artifact.get('summary') if isinstance(artifact.get('summary'), dict) else {}
    for strategy_name, plan in (artifact.get('shadow_plans') or {}).items():
        if not isinstance(plan, dict):
            continue
        rows.append({
            'artifact_type': 'strategy_activity',
            'recorded_at': artifact.get('recorded_at'),
            'symbol': summary.get('symbol'),
            'runtime_mode': summary.get('runtime_mode'),
            'active_strategy_version': summary.get('active_strategy_version'),
            'active_strategy_family': summary.get('active_strategy_family'),
            'final_regime': summary.get('regime'),
            'strategy_name': strategy_name,
            'action': plan.get('action'),
            'side': plan.get('side'),
            'account': plan.get('account'),
            'reason': plan.get('reason'),
            'size': plan.get('size'),
            'selected_strategy_family': summary.get('route_strategy_family'),
            'composite_switch_action': summary.get('composite_switch_action'),
            'selected_plan_action': summary.get('plan_action'),
            'strategy_stats_eligible': summary.get('strategy_stats_eligible'),
        })
    return rows


def _build_regime_local_artifact(result: ExecutionCycleResult, artifact: dict[str, Any]) -> dict[str, Any]:
    summary = artifact.get('summary') if isinstance(artifact.get('summary'), dict) else {}
    return {
        'artifact_type': 'regime_local_cycle',
        'recorded_at': artifact.get('recorded_at'),
        'symbol': summary.get('symbol'),
        'runtime_mode': summary.get('runtime_mode'),
        'active_strategy_version': summary.get('active_strategy_version'),
        'active_strategy_family': summary.get('active_strategy_family'),
        'active_strategy_config_path': summary.get('active_strategy_config_path'),
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
        'shadow_plans': artifact.get('shadow_plans'),
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
        'active_strategy_version': summary.get('active_strategy_version'),
        'active_strategy_family': summary.get('active_strategy_family'),
        'symbol': summary.get('symbol'),
        'account': summary.get('plan_account') or (None if result.receipt is None else result.receipt.account),
        'plan_action': summary.get('plan_action'),
        'execution_id': summary.get('execution_id'),
        'client_order_id': summary.get('client_order_id'),
        'order_id': summary.get('order_id'),
        'trade_ids': summary.get('trade_ids'),
        'attribution_trade_count': summary.get('attribution_trade_count'),
        'attribution_fee_source': summary.get('attribution_fee_source'),
        'attribution_realized_pnl_source': summary.get('attribution_realized_pnl_source'),
        'attribution_equity_source': summary.get('attribution_equity_source'),
        'strategy_stats_reason': summary.get('strategy_stats_reason'),
        'entry_verified_hint': summary.get('entry_verified_hint'),
        'entry_trade_confirmed': summary.get('entry_trade_confirmed'),
        'entry_verification_attempt_count': summary.get('entry_verification_attempt_count'),
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
    with HISTORY_PATH().open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(artifact, default=_json_default, ensure_ascii=False) + '\n')
    regime_local = _build_regime_local_artifact(result, artifact)
    with REGIME_HISTORY_PATH().open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(regime_local, default=_json_default, ensure_ascii=False) + '\n')
    activity_rows = _build_strategy_activity_artifacts(artifact)
    if activity_rows:
        with STRATEGY_ACTIVITY_PATH().open('a', encoding='utf-8') as handle:
            for row in activity_rows:
                handle.write(json.dumps(row, default=_json_default, ensure_ascii=False) + '\n')
    anomaly = _build_anomaly_artifact(result, artifact)
    if anomaly is not None:
        with ANOMALY_HISTORY_PATH().open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(anomaly, default=_json_default, ensure_ascii=False) + '\n')
    return artifact


def build_parallel_execution_artifact(result: ParallelExecutionCycleResult) -> dict[str, Any]:
    per_strategy = {name: build_execution_artifact(row) for name, row in result.results.items()}
    primary = next(iter(per_strategy.values()), None)
    payload = {
        'artifact_type': 'parallel_execution_cycle',
        'recorded_at': datetime.now(UTC).isoformat(),
        'regime_output': _json_default(result.regime_output.observed_at) if False else None,
        'symbol': result.regime_output.symbol,
        'runtime_state': result.runtime_state,
        'active_strategy': result.active_strategy,
        'shared_regime': {
            'final_regime': result.regime_output.final_decision.get('primary'),
            'confidence': result.regime_output.final_decision.get('confidence'),
            'decision_summary': result.regime_output.decision_summary,
        },
        'results': per_strategy,
        'live_positions': result.live_positions,
        'router_composite': result.router_composite,
        'summary': {
            'runtime_mode': result.runtime_state.get('mode'),
            'active_strategy_version': (result.active_strategy or {}).get('version'),
            'active_strategy_family': ((result.active_strategy or {}).get('metadata') or {}).get('family'),
            'active_strategy_config_path': ((result.active_strategy or {}).get('metadata') or {}).get('config_path'),
            'symbol': result.regime_output.symbol,
            'regime': result.regime_output.final_decision.get('primary'),
            'strategy_results': {
                name: {
                    'plan_action': artifact.get('summary', {}).get('plan_action'),
                    'plan_account': artifact.get('summary', {}).get('plan_account'),
                    'receipt_accepted': artifact.get('summary', {}).get('receipt_accepted'),
                    'block_reason': artifact.get('summary', {}).get('block_reason'),
                    'policy_reason': artifact.get('summary', {}).get('policy_reason'),
                    'strategy_stats_eligible': artifact.get('summary', {}).get('strategy_stats_eligible'),
                }
                for name, artifact in per_strategy.items()
            },
            'entered_accounts': [artifact.get('summary', {}).get('plan_account') for artifact in per_strategy.values() if artifact.get('summary', {}).get('submission_attempted')],
            'accepted_accounts': [artifact.get('summary', {}).get('plan_account') for artifact in per_strategy.values() if artifact.get('summary', {}).get('receipt_accepted')],
            'blocked_accounts': [artifact.get('summary', {}).get('plan_account') for artifact in per_strategy.values() if artifact.get('summary', {}).get('block_reason')],
            'primary_summary': None if primary is None else primary.get('summary'),
        },
    }
    return payload


def persist_parallel_execution_artifact(result: ParallelExecutionCycleResult) -> dict[str, Any]:
    artifact = build_parallel_execution_artifact(result)
    LATEST_PARALLEL_PATH.write_text(json.dumps(artifact, indent=2, default=_json_default, ensure_ascii=False))
    with PARALLEL_HISTORY_PATH().open('a', encoding='utf-8') as handle:
        handle.write(json.dumps(artifact, default=_json_default, ensure_ascii=False) + '\n')
    for row in result.results.values():
        persist_execution_artifact(row)
    return artifact


def main() -> None:
    pipeline = ExecutionPipeline()
    result = pipeline.run_cycle(exchange_snapshot=None)
    artifact = persist_execution_artifact(result)
    print(json.dumps(artifact, indent=2, default=_json_default, ensure_ascii=False))


if __name__ == '__main__':
    main()
