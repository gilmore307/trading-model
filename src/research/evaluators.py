from __future__ import annotations

from collections import defaultdict
from itertools import combinations
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


DEFAULT_SEPARABILITY_FIELDS = [
    'background_features.adx',
    'background_features.ema20_slope',
    'background_features.ema50_slope',
    'primary_features.adx',
    'primary_features.vwap_deviation_z',
    'primary_features.bollinger_bandwidth_pct',
    'primary_features.realized_vol_pct',
    'primary_features.funding_pctile',
    'primary_features.oi_accel',
    'primary_features.basis_deviation_pct',
    'override_features.vwap_deviation_z',
    'override_features.trade_burst_score',
    'override_features.liquidation_spike_score',
    'override_features.orderbook_imbalance',
    'override_features.realized_vol_pct',
]


def _extract_nested(row: dict[str, Any], path: str) -> Any:
    current: Any = row
    for part in path.split('.'):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def build_regime_separability_summary(rows: list[dict[str, Any]], *, feature_fields: list[str] | None = None) -> dict[str, Any]:
    feature_fields = feature_fields or DEFAULT_SEPARABILITY_FIELDS
    buckets: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))

    for row in rows:
        regime = row.get('final_regime') or 'unknown'
        for field in feature_fields:
            buckets[regime][field].append(_extract_nested(row, field))

    feature_means: dict[str, dict[str, float | None]] = {}
    for regime, metrics in buckets.items():
        feature_means[regime] = {field: _mean(values) for field, values in metrics.items()}

    pairwise_distance: dict[str, dict[str, Any]] = {}
    regimes = sorted(feature_means)
    for left, right in combinations(regimes, 2):
        comparable = []
        for field in feature_fields:
            lv = feature_means[left].get(field)
            rv = feature_means[right].get(field)
            if lv is None or rv is None:
                continue
            comparable.append(abs(float(lv) - float(rv)))
        distance = sum(comparable) / len(comparable) if comparable else None
        pairwise_distance[f'{left}__vs__{right}'] = {
            'distance': distance,
            'comparable_feature_count': len(comparable),
        }

    ranked_overlap = sorted(
        (
            {'pair': pair, **values}
            for pair, values in pairwise_distance.items()
            if values.get('distance') is not None
        ),
        key=lambda item: item['distance'],
    )

    return {
        'feature_fields': feature_fields,
        'feature_means_by_regime': feature_means,
        'pairwise_distance': pairwise_distance,
        'closest_pairs': ranked_overlap[:5],
    }


def build_strategy_ranking_summary(matrix: dict[str, dict[str, dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    summary: dict[str, list[dict[str, Any]]] = {}
    for regime, strategies in matrix.items():
        ranked = sorted(
            (
                {
                    'strategy': strategy,
                    'avg_enter_forward_return': row.get('avg_enter_forward_return'),
                    'enter_rate': row.get('enter_rate'),
                    'avg_score': row.get('avg_score'),
                }
                for strategy, row in strategies.items()
            ),
            key=lambda item: (
                float('-inf') if item.get('avg_enter_forward_return') is None else item.get('avg_enter_forward_return'),
                item.get('enter_rate') or 0.0,
                float('-inf') if item.get('avg_score') is None else item.get('avg_score'),
            ),
            reverse=True,
        )
        summary[regime] = ranked
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
