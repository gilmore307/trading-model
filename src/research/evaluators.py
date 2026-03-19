from __future__ import annotations

from collections import defaultdict
from typing import Any


def _mean(values: list[float | None]) -> float | None:
    nums = [float(v) for v in values if v is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


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
            metrics['sample_count'].append(1)

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    for regime, by_strategy in buckets.items():
        matrix[regime] = {}
        for strategy_name, metrics in by_strategy.items():
            sample_count = len(metrics['sample_count'])
            actions = metrics['actions']
            matrix[regime][strategy_name] = {
                'sample_count': sample_count,
                'enter_rate': (sum(1 for a in actions if a == 'enter') / sample_count) if sample_count else 0.0,
                'arm_rate': (sum(1 for a in actions if a == 'arm') / sample_count) if sample_count else 0.0,
                'watch_rate': (sum(1 for a in actions if a == 'watch') / sample_count) if sample_count else 0.0,
                'hold_rate': (sum(1 for a in actions if a == 'hold') / sample_count) if sample_count else 0.0,
                'avg_score': _mean(metrics['scores']),
                'avg_forward_return': _mean(metrics['forward_returns']),
            }
    return matrix
