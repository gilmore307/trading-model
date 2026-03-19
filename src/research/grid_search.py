from __future__ import annotations

from itertools import product
from typing import Any, Iterable


def generate_parameter_combinations(space: dict[str, list[Any]]) -> list[dict[str, Any]]:
    if not space:
        return [{}]
    keys = list(space.keys())
    values = [space[key] for key in keys]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def filter_rows_for_regime(rows: list[dict[str, Any]], regime: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get('final_regime') == regime]


def build_parameter_search_plan(*, regime: str, strategy: str, space: dict[str, list[Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    combinations = generate_parameter_combinations(space)
    scoped_rows = filter_rows_for_regime(rows, regime)
    return {
        'regime': regime,
        'strategy': strategy,
        'parameter_count': len(space),
        'combination_count': len(combinations),
        'sample_count': len(scoped_rows),
        'parameters': list(space.keys()),
        'combinations_preview': combinations[:10],
    }
