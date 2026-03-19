from __future__ import annotations

from typing import Any

from src.research.evaluators import build_regime_quality_summary, build_regime_separability_summary, build_strategy_ranking_summary, build_strategy_regime_matrix


def build_research_report(rows: list[dict[str, Any]], *, forward_field: str = 'fwd_ret_1h', forward_fields: list[str] | None = None) -> dict[str, Any]:
    strategy_regime_matrix = build_strategy_regime_matrix(rows, forward_field=forward_field)
    return {
        'summary': {
            'row_count': len(rows),
            'forward_field': forward_field,
            'forward_fields': forward_fields or ['fwd_ret_15m', 'fwd_ret_1h', 'fwd_ret_4h'],
        },
        'regime_quality': build_regime_quality_summary(rows, forward_fields=forward_fields),
        'regime_separability': build_regime_separability_summary(rows),
        'strategy_regime_matrix': strategy_regime_matrix,
        'strategy_ranking': build_strategy_ranking_summary(strategy_regime_matrix),
    }
