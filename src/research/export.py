from __future__ import annotations

from typing import Any


def render_research_report_markdown(report: dict[str, Any]) -> str:
    summary = report.get('summary') or {}
    regime_quality = report.get('regime_quality') or {}
    matrix = report.get('strategy_regime_matrix') or {}

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
