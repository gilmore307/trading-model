from __future__ import annotations

from collections import defaultdict
from typing import Any


def _positive_rate(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(1 for v in nums if v > 0) / len(nums)


def _mean(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def build_regime_quality_summary(rows: list[dict[str, Any]], *, forward_fields: list[str] | None = None) -> dict[str, dict[str, Any]]:
    forward_fields = forward_fields or ['fwd_ret_15m', 'fwd_ret_1h', 'fwd_ret_4h']
    buckets: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for row in rows:
        regime = row.get('final_regime') or 'unknown'
        buckets[regime]['sample_count'].append(1)
        buckets[regime]['confidence'].append(row.get('final_confidence'))
        for field in forward_fields:
            buckets[regime][field].append(row.get(field))

    summary: dict[str, dict[str, Any]] = {}
    for regime, metrics in buckets.items():
        sample_count = len(metrics['sample_count'])
        summary[regime] = {
            'sample_count': sample_count,
            'avg_confidence': _mean(metrics['confidence']),
        }
        for field in forward_fields:
            summary[regime][f'avg_{field}'] = _mean(metrics[field])
            summary[regime][f'positive_rate_{field}'] = _positive_rate(metrics[field])
    return summary


def build_strategy_regime_matrix(rows: list[dict[str, Any]], *, forward_field: str = 'fwd_ret_1h') -> dict[str, dict[str, dict[str, Any]]]:
    buckets: dict[str, dict[str, dict[str, list]]] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for row in rows:
        regime = row.get('final_regime') or 'unknown'
        shadow_plans = row.get('shadow_plans') or {}
        fwd = row.get(forward_field)
        for strategy_name, plan in shadow_plans.items():
            metrics = buckets[regime][strategy_name]
            action = plan.get('action')
            metrics['actions'].append(action)
            metrics['scores'].append(plan.get('score'))
            metrics['forward_returns'].append(fwd)
            if action == 'enter':
                metrics['enter_forward_returns'].append(fwd)
            if action == 'arm':
                metrics['arm_forward_returns'].append(fwd)
            metrics['sample_count'].append(1)

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for regime, by_strategy in buckets.items():
        matrix[regime] = {}
        for strategy_name, metrics in by_strategy.items():
            sample_count = len(metrics['sample_count'])
            actions = metrics['actions']
            forward_returns = [float(v) for v in metrics['forward_returns'] if v is not None]
            positive_forward_rate = _positive_rate(metrics['forward_returns'])
            matrix[regime][strategy_name] = {
                'sample_count': sample_count,
                'enter_rate': (sum(1 for a in actions if a == 'enter') / sample_count) if sample_count else 0.0,
                'arm_rate': (sum(1 for a in actions if a == 'arm') / sample_count) if sample_count else 0.0,
                'watch_rate': (sum(1 for a in actions if a == 'watch') / sample_count) if sample_count else 0.0,
                'hold_rate': (sum(1 for a in actions if a == 'hold') / sample_count) if sample_count else 0.0,
                'avg_score': _mean(metrics['scores']),
                'avg_forward_return': _mean(metrics['forward_returns']),
                'avg_enter_forward_return': _mean(metrics['enter_forward_returns']),
                'avg_arm_forward_return': _mean(metrics['arm_forward_returns']),
                'positive_forward_rate': positive_forward_rate,
            }
    return matrix
