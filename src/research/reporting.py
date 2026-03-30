from __future__ import annotations

from typing import Any

from src.research.evaluators import build_regime_quality_summary, build_regime_separability_summary, build_strategy_ranking_summary, build_strategy_regime_matrix
from src.research.grid_search import rank_parameter_candidates
from src.research.market_state import build_ma_candidate_dataset, build_ma_performance_cube, build_market_state_rows
from src.research.parameter_spaces import parameter_space_for


def build_research_report(rows: list[dict[str, Any]], *, forward_field: str = 'fwd_ret_1h', forward_fields: list[str] | None = None) -> dict[str, Any]:
    strategy_regime_matrix = build_strategy_regime_matrix(rows, forward_field=forward_field)
    strategy_ranking = build_strategy_ranking_summary(strategy_regime_matrix)
    parameter_search_preview: dict[str, list[dict[str, Any]]] = {}
    for regime, ranking in strategy_ranking.items():
        if not ranking:
            continue
        top_strategy = ranking[0].get('strategy')
        if not top_strategy:
            continue
        space = parameter_space_for(top_strategy)
        if not space:
            continue
        parameter_search_preview[regime] = rank_parameter_candidates(
            regime=regime,
            strategy=top_strategy,
            space=space,
            rows=rows,
            forward_field=forward_field,
            limit=3,
        )
    return {
        'summary': {
            'row_count': len(rows),
            'forward_field': forward_field,
            'forward_fields': forward_fields or ['fwd_ret_15m', 'fwd_ret_1h', 'fwd_ret_4h'],
        },
        'regime_quality': build_regime_quality_summary(rows, forward_fields=forward_fields),
        'regime_separability': build_regime_separability_summary(rows),
        'strategy_regime_matrix': strategy_regime_matrix,
        'strategy_ranking': strategy_ranking,
        'parameter_search_preview': parameter_search_preview,
    }


def build_market_state_report(candles: list[dict[str, Any]], ma_variants: list[dict[str, Any]], *, horizon_bars: int = 60) -> dict[str, Any]:
    state_rows = build_market_state_rows(candles)
    candidate_rows = build_ma_candidate_dataset(candles, ma_variants, horizon_bars=horizon_bars)
    cube = build_ma_performance_cube(state_rows, candidate_rows)
    state_counts: dict[str, int] = {}
    for row in state_rows:
        state = row.get('market_state')
        if not state:
            continue
        state_counts[state] = state_counts.get(state, 0) + 1
    return {
        'summary': {
            'state_row_count': len(state_rows),
            'candidate_row_count': len(candidate_rows),
            'horizon_bars': horizon_bars,
        },
        'state_counts': state_counts,
        'performance_cube': cube,
    }


def build_family_market_state_report(state_rows: list[dict[str, Any]], utility_rows: list[dict[str, Any]]) -> dict[str, Any]:
    state_by_ts = {row.get('ts'): row for row in state_rows if row.get('ts') is not None}
    grouped: dict[tuple[str, str, str], list[float]] = {}
    counts: dict[tuple[str, str, str], int] = {}
    family_state_scores: dict[tuple[str, str], dict[str, Any]] = {}

    for row in utility_rows:
        ts = row.get('ts')
        state = state_by_ts.get(ts, {}).get('market_state')
        family = row.get('family')
        parameter_region = row.get('parameter_region')
        utility = row.get('utility_1h')
        if state is None or family is None or parameter_region is None or utility is None:
            continue
        key = (state, family, parameter_region)
        grouped.setdefault(key, []).append(float(utility))
        counts[key] = counts.get(key, 0) + 1

        family_key = (state, family)
        bucket = family_state_scores.setdefault(family_key, {'sum_utility': 0.0, 'count': 0, 'positive': 0})
        bucket['sum_utility'] += float(utility)
        bucket['count'] += 1
        if float(utility) > 0:
            bucket['positive'] += 1

    cube_rows = []
    for (state, family, parameter_region), values in sorted(grouped.items()):
        cube_rows.append({
            'market_state': state,
            'family': family,
            'parameter_region': parameter_region,
            'sample_count': counts[(state, family, parameter_region)],
            'avg_utility_1h': sum(values) / len(values),
            'positive_rate': sum(1 for x in values if x > 0) / len(values),
        })

    family_state_summary: dict[str, list[dict[str, Any]]] = {}
    for (state, family), bucket in sorted(family_state_scores.items()):
        row = {
            'family': family,
            'sample_count': bucket['count'],
            'avg_utility_1h': bucket['sum_utility'] / bucket['count'],
            'positive_rate': bucket['positive'] / bucket['count'],
        }
        family_state_summary.setdefault(state, []).append(row)

    for state, rows in family_state_summary.items():
        rows.sort(key=lambda row: row['avg_utility_1h'], reverse=True)

    state_counts: dict[str, int] = {}
    for row in state_rows:
        state = row.get('market_state')
        if state:
            state_counts[state] = state_counts.get(state, 0) + 1

    return {
        'summary': {
            'state_row_count': len(state_rows),
            'utility_row_count': len(utility_rows),
        },
        'state_counts': state_counts,
        'family_state_summary': family_state_summary,
        'performance_cube': {
            'summary': {
                'state_count': len({row['market_state'] for row in cube_rows}),
                'family_count': len({row['family'] for row in cube_rows}),
                'parameter_region_count': len({row['parameter_region'] for row in cube_rows}),
                'cell_count': len(cube_rows),
                'utility_field': 'utility_1h',
            },
            'rows': cube_rows,
        },
    }
