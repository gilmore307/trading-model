from __future__ import annotations

from typing import Any


def render_research_report_markdown(report: dict[str, Any]) -> str:
    summary = report.get('summary') or {}
    regime_quality = report.get('regime_quality') or {}
    matrix = report.get('strategy_regime_matrix') or {}
    separability = report.get('regime_separability') or {}
    ranking = report.get('strategy_ranking') or {}
    parameter_search_preview = report.get('parameter_search_preview') or {}

    lines: list[str] = []
    lines.append('# Regime Research Report')
    lines.append('')
    lines.append('## Summary')
    lines.append('')
    lines.append(f"- Row count: {summary.get('row_count')}")
    lines.append(f"- Forward field: {summary.get('forward_field')}")
    lines.append(f"- Forward fields: {', '.join(summary.get('forward_fields') or [])}")

    lines.append('')
    lines.append('## Regime Quality')
    if not regime_quality:
        lines.append('')
        lines.append('- No regime quality rows')
    else:
        for regime, row in regime_quality.items():
            lines.append('')
            lines.append(f"### {regime}")
            lines.append(f"- sample_count: {row.get('sample_count')}")
            lines.append(f"- avg_confidence: {row.get('avg_confidence')}")
            for key in ['avg_fwd_ret_15m', 'positive_rate_fwd_ret_15m', 'avg_fwd_ret_1h', 'positive_rate_fwd_ret_1h', 'avg_fwd_ret_4h', 'positive_rate_fwd_ret_4h']:
                if key in row:
                    lines.append(f"- {key}: {row.get(key)}")

    lines.append('')
    lines.append('')
    lines.append('## Regime Separability')
    closest_pairs = separability.get('closest_pairs') or []
    if not closest_pairs:
        lines.append('')
        lines.append('- No separability rows')
    else:
        for row in closest_pairs:
            lines.append(f"- {row.get('pair')}: distance={row.get('distance')} comparable_feature_count={row.get('comparable_feature_count')}")

    lines.append('')
    lines.append('## Strategy Ranking Summary')
    if not ranking:
        lines.append('')
        lines.append('- No ranking rows')
    else:
        for regime, rows in ranking.items():
            lines.append('')
            lines.append(f"### {regime}")
            if not rows:
                lines.append('- No ranked strategies')
                continue
            for idx, row in enumerate(rows[:3], start=1):
                lines.append(
                    f"- #{idx} {row.get('strategy')}: avg_enter_forward_return={row.get('avg_enter_forward_return')} enter_rate={row.get('enter_rate')} avg_score={row.get('avg_score')}"
                )

    lines.append('')
    lines.append('## Parameter Search Preview')
    if not parameter_search_preview:
        lines.append('')
        lines.append('- No parameter search preview rows')
    else:
        for regime, rows in parameter_search_preview.items():
            lines.append('')
            lines.append(f"### {regime}")
            for idx, row in enumerate(rows[:3], start=1):
                lines.append(
                    f"- #{idx}: candidate_objective_score={row.get('candidate_objective_score')} baseline={row.get('baseline_objective_score')} parameters={row.get('parameters')}"
                )

    lines.append('')
    lines.append('## Strategy × Regime Matrix')
    if not matrix:
        lines.append('')
        lines.append('- No strategy matrix rows')
    else:
        for regime, strategies in matrix.items():
            lines.append('')
            lines.append(f"### Regime: {regime}")
            ranked = sorted(
                strategies.items(),
                key=lambda item: (
                    -1 if item[1].get('avg_enter_forward_return') is None else item[1].get('avg_enter_forward_return'),
                    -1 if item[1].get('avg_score') is None else item[1].get('avg_score'),
                ),
                reverse=True,
            )
            for strategy, row in ranked:
                lines.append('')
                lines.append(f"#### Strategy: {strategy}")
                for key in ['sample_count', 'enter_rate', 'arm_rate', 'watch_rate', 'hold_rate', 'avg_score', 'avg_forward_return', 'avg_enter_forward_return', 'avg_arm_forward_return', 'positive_forward_rate']:
                    lines.append(f"- {key}: {row.get(key)}")

    return '\n'.join(lines).strip() + '\n'


def render_market_state_report_markdown(report: dict[str, Any]) -> str:
    summary = report.get('summary') or {}
    state_counts = report.get('state_counts') or {}
    cube = report.get('performance_cube') or {}
    rows = cube.get('rows') or []
    family_state_summary = report.get('family_state_summary') or {}

    lines: list[str] = []
    lines.append('# Market-State Report')
    lines.append('')
    lines.append('## Summary')
    lines.append('')
    if 'candidate_row_count' in summary:
        lines.append(f"- state_row_count: {summary.get('state_row_count')}")
        lines.append(f"- candidate_row_count: {summary.get('candidate_row_count')}")
        lines.append(f"- horizon_bars: {summary.get('horizon_bars')}")
    else:
        lines.append(f"- state_row_count: {summary.get('state_row_count')}")
        lines.append(f"- utility_row_count: {summary.get('utility_row_count')}")
    lines.append('')
    lines.append('## State Counts')
    if not state_counts:
        lines.append('')
        lines.append('- No state rows')
    else:
        for key, value in sorted(state_counts.items()):
            lines.append(f'- {key}: {value}')
    if family_state_summary:
        lines.append('')
        lines.append('## Family Summary by State')
        for state, family_rows in family_state_summary.items():
            lines.append('')
            lines.append(f'### {state}')
            for row in family_rows:
                lines.append(f"- {row.get('family')}: sample_count={row.get('sample_count')} avg_utility_1h={row.get('avg_utility_1h')} positive_rate={row.get('positive_rate')}")

    lines.append('')
    lines.append('## Performance Cube')
    if not rows:
        lines.append('')
        lines.append('- No cube rows')
    else:
        current_state = None
        for row in rows:
            state = row.get('market_state')
            if state != current_state:
                current_state = state
                lines.append('')
                lines.append(f'### {state}')
            lines.append(
                f"- {row.get('family')} / {row.get('parameter_region')}: sample_count={row.get('sample_count')} avg_utility_1h={row.get('avg_utility_1h')} positive_rate={row.get('positive_rate')}"
            )
    return '\n'.join(lines).strip() + '\n'
