from __future__ import annotations

from itertools import product
from typing import Any

from src.research.evaluators import build_strategy_regime_matrix
from src.research.reevaluate import reevaluate_strategy_row


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


def _score_replanned_rows(rows: list[dict[str, Any]], *, strategy: str, overrides: dict[str, Any], forward_field: str) -> dict[str, Any]:
    enter_returns: list[float] = []
    arm_returns: list[float] = []
    scores: list[float] = []
    enter_count = 0
    arm_count = 0
    for row in rows:
        plan = reevaluate_strategy_row(row=row, strategy=strategy, parameter_overrides=overrides)
        fwd = row.get(forward_field)
        if plan.score is not None:
            scores.append(float(plan.score))
        if plan.action == 'enter':
            enter_count += 1
            if fwd is not None:
                enter_returns.append(float(fwd))
        elif plan.action == 'arm':
            arm_count += 1
            if fwd is not None:
                arm_returns.append(float(fwd))
    sample_count = len(rows)
    avg_enter = sum(enter_returns) / len(enter_returns) if enter_returns else None
    positive_enter_rate = (sum(1 for v in enter_returns if v > 0) / len(enter_returns)) if enter_returns else None
    avg_score = sum(scores) / len(scores) if scores else None
    objective = 0.0
    if avg_enter is not None:
        objective += avg_enter * 100.0
    objective += (enter_count / sample_count) * 10.0 if sample_count else 0.0
    if positive_enter_rate is not None:
        objective += positive_enter_rate * 5.0
    if avg_score is not None:
        objective += avg_score
    return {
        'avg_enter_forward_return': avg_enter,
        'avg_arm_forward_return': (sum(arm_returns) / len(arm_returns)) if arm_returns else None,
        'enter_rate': (enter_count / sample_count) if sample_count else 0.0,
        'arm_rate': (arm_count / sample_count) if sample_count else 0.0,
        'avg_score': avg_score,
        'positive_enter_rate': positive_enter_rate,
        'objective_score': objective,
    }


def rank_parameter_candidates(*, regime: str, strategy: str, space: dict[str, list[Any]], rows: list[dict[str, Any]], forward_field: str = 'fwd_ret_1h', limit: int = 20) -> list[dict[str, Any]]:
    baseline = score_strategy_configuration(rows=rows, regime=regime, strategy=strategy, forward_field=forward_field)
    scoped_rows = filter_rows_for_regime(rows, regime)
    ranked = []
    for combo in generate_parameter_combinations(space):
        try:
            stats = _score_replanned_rows(scoped_rows, strategy=strategy, overrides=combo, forward_field=forward_field)
            ranked.append({
                'parameters': combo,
                'baseline_objective_score': baseline['objective_score'],
                'candidate_objective_score': stats['objective_score'],
                'candidate_stats': stats,
            })
        except NotImplementedError:
            ranked.append({
                'parameters': combo,
                'baseline_objective_score': baseline['objective_score'],
                'candidate_objective_score': baseline['objective_score'],
                'candidate_stats': baseline['stats'],
            })
    ranked.sort(key=lambda row: row['candidate_objective_score'], reverse=True)
    return ranked[:limit]


def build_parameter_search_plan(*, regime: str, strategy: str, space: dict[str, list[Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    combinations = generate_parameter_combinations(space)
    scoped_rows = filter_rows_for_regime(rows, regime)
    baseline = score_strategy_configuration(rows=rows, regime=regime, strategy=strategy)
    ranked_candidates = rank_parameter_candidates(regime=regime, strategy=strategy, space=space, rows=rows)
    return {
        'regime': regime,
        'strategy': strategy,
        'parameter_count': len(space),
        'combination_count': len(combinations),
        'sample_count': len(scoped_rows),
        'parameters': list(space.keys()),
        'combinations_preview': combinations[:10],
        'baseline_score': baseline,
        'candidate_ranking_preview': ranked_candidates,
    }
