from __future__ import annotations

from itertools import product
from typing import Any

from src.research.evaluators import build_strategy_regime_matrix


def generate_parameter_combinations(space: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not space:
        return [{}]
    keys = list(space.keys())
    values = [space[key] for key in keys]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def filter_rows_for_regime(rows: list[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get('final_regime') == regime]


def score_strategy_configuration(*, rows: list[dict[str, Any]], regime: str, strategy: str, forward_field: str = 'fwd_ret_1h') -> dict[str, Any]:
    scoped_rows = filter_rows_for_regime(rows, regime)
    matrix = build_strategy_regime_matrix(scoped_rows, forward_field=forward_field)
    stats = (matrix.get(regime) or {}).get(strategy) or {}
    avg_enter = stats.get('avg_enter_forward_return')
    enter_rate = stats.get('enter_rate') or 0.0
    positive_rate = stats.get('positive_forward_rate')
    avg_score = stats.get('avg_score')
    objective = 0.0
    if avg_enter is not None:
        objective += float(avg_enter) * 100.0
    objective += float(enter_rate) * 10.0
    if positive_rate is not None:
        objective += float(positive_rate) * 5.0
    if avg_score is not None:
        objective += float(avg_score)
    return {
        'regime': regime,
        'strategy': strategy,
        'forward_field': forward_field,
        'stats': stats,
        'objective_score': objective,
    }


def build_parameter_search_plan(*, regime: str, strategy: str, space: dict[str, list[Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    combinations = generate_parameter_combinations(space)
    scoped_rows = filter_rows_for_regime(rows, regime)
    baseline = score_strategy_configuration(rows=rows, regime=regime, strategy=strategy)
    return {
        'regime': regime,
        'strategy': strategy,
        'parameter_count': len(space),
        'combination_count': len(combinations),
        'sample_count': len(scoped_rows),
        'parameters': list(space.keys()),
        'combinations_preview': combinations[:10],
        'baseline_score': baseline,
    }
