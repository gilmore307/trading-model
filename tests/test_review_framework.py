from datetime import UTC, datetime

from src.review.framework import (
    ReviewCadence,
    adjustment_policy_for,
    build_monthly_window,
    build_quarterly_window,
    build_review_plan,
    build_weekly_window,
)


def test_build_weekly_window_uses_saturday_midnight_bounds():
    now = datetime(2026, 3, 15, 12, 0, tzinfo=UTC)  # Sunday
    window = build_weekly_window(now)
    assert window.cadence == ReviewCadence.WEEKLY
    assert window.window_start == datetime(2026, 3, 7, 0, 0, tzinfo=UTC)
    assert window.window_end == datetime(2026, 3, 14, 0, 0, tzinfo=UTC)


def test_monthly_window_uses_previous_review_boundary():
    window = build_monthly_window(
        datetime(2026, 2, 1, 0, 0, tzinfo=UTC),
        datetime(2026, 3, 1, 0, 0, tzinfo=UTC),
    )
    assert window.cadence == ReviewCadence.MONTHLY
    assert window.window_start == datetime(2026, 2, 1, 0, 0, tzinfo=UTC)
    assert window.window_end == datetime(2026, 3, 1, 0, 0, tzinfo=UTC)


def test_quarterly_plan_exposes_structural_params():
    window = build_quarterly_window(
        datetime(2026, 1, 4, 0, 0, tzinfo=UTC),
        datetime(2026, 4, 5, 0, 0, tzinfo=UTC),
    )
    plan = build_review_plan(window)
    assert plan['cadence'] == 'quarterly'
    assert 'regime_taxonomy' in plan['adjustment_policy']['structural_params']
    assert 'ML/RL roadmap and training objective review' in plan['focus_areas']


def test_monthly_policy_marks_strategy_internal_params_as_discuss_first():
    policy = adjustment_policy_for(ReviewCadence.MONTHLY)
    assert 'trend_follow_through_thresholds' in policy.discuss_first_params
    assert 'router_switch_gating' in policy.discuss_first_params
    assert policy.structural_params == []
