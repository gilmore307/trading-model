from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime
from typing import Any

from src.review.aggregator import aggregate_from_execution_history
from src.review.framework import ReviewWindow, build_review_plan
from src.review.performance import build_performance_snapshot


@dataclass(slots=True)
class ReviewReport:
    meta: dict[str, Any]
    sections: list[dict[str, Any]]
    compare_snapshot: dict[str, Any] | None
    metrics: dict[str, Any]
    parameter_candidates: dict[str, list[dict[str, Any]]]
    decisions: list[dict[str, Any]]
    notes: list[str]


def build_report_scaffold(window: ReviewWindow, compare_snapshot: dict[str, Any] | None = None, metrics_by_account: dict[str, dict[str, Any]] | None = None, history_path: str | None = None) -> dict[str, Any]:
    plan = build_review_plan(window)
    cadence = plan['cadence']

    sections = [
        {
            'key': 'market_regime_summary',
            'title': 'Market Regime Summary',
            'status': 'placeholder',
            'items': [],
        },
        {
            'key': 'account_comparison',
            'title': 'Account Comparison',
            'status': 'ready' if compare_snapshot is not None else 'placeholder',
            'items': [] if compare_snapshot is None else compare_snapshot.get('accounts', []),
        },
        {
            'key': 'router_composite_review',
            'title': 'Router Composite Review',
            'status': 'ready' if compare_snapshot is not None else 'placeholder',
            'items': [] if compare_snapshot is None else compare_snapshot.get('highlights', []),
        },
        {
            'key': 'parameter_review',
            'title': 'Parameter Review',
            'status': 'placeholder',
            'items': [],
        },
    ]

    if cadence == 'quarterly':
        sections.append(
            {
                'key': 'structural_review',
                'title': 'Structural Review',
                'status': 'placeholder',
                'items': [],
            }
        )

    aggregated_metrics = metrics_by_account
    if history_path is not None:
        aggregated_metrics = aggregate_from_execution_history(history_path, metrics_by_account)
    performance_snapshot = build_performance_snapshot(aggregated_metrics)

    report = ReviewReport(
        meta={
            'cadence': cadence,
            'label': plan['label'],
            'window_start': plan['window_start'],
            'window_end': plan['window_end'],
            'generated_at': datetime.now(UTC).isoformat(),
            'focus_areas': plan['focus_areas'],
            'adjustment_policy': plan['adjustment_policy'],
        },
        sections=sections,
        compare_snapshot=compare_snapshot,
        metrics={
            'performance': performance_snapshot,
            'risk': [],
            'fees': [],
            'regime_quality': [],
        },
        parameter_candidates={
            'auto_candidate_params': [{'name': name, 'status': 'pending_data'} for name in plan['adjustment_policy']['auto_candidate_params']],
            'discuss_first_params': [{'name': name, 'status': 'pending_data'} for name in plan['adjustment_policy']['discuss_first_params']],
            'structural_params': [{'name': name, 'status': 'pending_discussion'} for name in plan['adjustment_policy']['structural_params']],
        },
        decisions=[],
        notes=plan['notes'],
    )
    return asdict(report)
