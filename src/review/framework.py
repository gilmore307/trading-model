from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any


class ReviewCadence(StrEnum):
    WEEKLY = 'weekly'
    MONTHLY = 'monthly'
    QUARTERLY = 'quarterly'


@dataclass(slots=True)
class ReviewWindow:
    cadence: ReviewCadence
    window_start: datetime
    window_end: datetime
    label: str


@dataclass(slots=True)
class AdjustmentPolicy:
    auto_candidate_params: list[str]
    discuss_first_params: list[str]
    structural_params: list[str]


@dataclass(slots=True)
class ReviewPlan:
    cadence: str
    label: str
    window_start: str
    window_end: str
    focus_areas: list[str]
    adjustment_policy: dict[str, list[str]]
    notes: list[str]


WEEKLY_AUTO_CANDIDATES = [
    'confidence_gate',
    'cooldown_seconds',
    'entry_threshold',
    'add_position_threshold',
    'fee_burden_frequency_gate',
]

MONTHLY_DISCUSS_FIRST = [
    'trend_follow_through_thresholds',
    'meanrev_reversion_thresholds',
    'compression_breakout_thresholds',
    'crowded_reversal_thresholds',
    'shock_event_thresholds',
    'leverage_scaling',
    'stop_take_profile',
    'router_switch_gating',
]

STRUCTURAL_PARAMS = [
    'regime_taxonomy',
    'strategy_account_set',
    'review_metric_system',
    'risk_framework',
    'rl_training_objective',
]


def _saturday_midnight(dt: datetime) -> datetime:
    dt = dt.astimezone(UTC)
    weekday = dt.weekday()  # Mon=0 ... Sun=6
    days_since_saturday = (weekday - 5) % 7
    saturday = datetime(dt.year, dt.month, dt.day, tzinfo=UTC) - timedelta(days=days_since_saturday)
    return saturday


def build_weekly_window(now: datetime) -> ReviewWindow:
    now = now.astimezone(UTC)
    end = _saturday_midnight(now)
    start = end - timedelta(days=7)
    return ReviewWindow(
        cadence=ReviewCadence.WEEKLY,
        window_start=start,
        window_end=end,
        label=f'weekly:{start.date()}->{end.date()}',
    )


def build_monthly_window(previous_review_end: datetime, current_review_end: datetime) -> ReviewWindow:
    return ReviewWindow(
        cadence=ReviewCadence.MONTHLY,
        window_start=previous_review_end.astimezone(UTC),
        window_end=current_review_end.astimezone(UTC),
        label=f'monthly:{previous_review_end.date()}->{current_review_end.date()}',
    )


def build_quarterly_window(previous_review_end: datetime, current_review_end: datetime) -> ReviewWindow:
    return ReviewWindow(
        cadence=ReviewCadence.QUARTERLY,
        window_start=previous_review_end.astimezone(UTC),
        window_end=current_review_end.astimezone(UTC),
        label=f'quarterly:{previous_review_end.date()}->{current_review_end.date()}',
    )


def adjustment_policy_for(cadence: ReviewCadence) -> AdjustmentPolicy:
    if cadence == ReviewCadence.WEEKLY:
        return AdjustmentPolicy(
            auto_candidate_params=WEEKLY_AUTO_CANDIDATES,
            discuss_first_params=[],
            structural_params=[],
        )
    if cadence == ReviewCadence.MONTHLY:
        return AdjustmentPolicy(
            auto_candidate_params=WEEKLY_AUTO_CANDIDATES,
            discuss_first_params=MONTHLY_DISCUSS_FIRST,
            structural_params=[],
        )
    return AdjustmentPolicy(
        auto_candidate_params=WEEKLY_AUTO_CANDIDATES,
        discuss_first_params=MONTHLY_DISCUSS_FIRST,
        structural_params=STRUCTURAL_PARAMS,
    )


def build_review_plan(window: ReviewWindow) -> dict[str, Any]:
    policy = adjustment_policy_for(window.cadence)
    if window.cadence == ReviewCadence.WEEKLY:
        focus = [
            'account comparison for the completed trading week',
            'router/composite vs single-strategy state and attribution review',
            'small threshold/cooldown/frequency calibration candidates',
            'fee burden and trading frequency adjustment suggestions',
        ]
        notes = ['weekly review should prefer small safe adjustments, not structural changes']
    elif window.cadence == ReviewCadence.MONTHLY:
        focus = [
            'multi-week strategy stability review',
            'regime recognition quality review',
            'strategy-internal parameter discussion',
            'router/composite ownership-aware comparison over the monthly interval',
        ]
        notes = ['monthly review is the primary parameter-discussion layer; recommendations should usually require confirmation before live adoption']
    else:
        focus = [
            'quarter-scale regime taxonomy and strategy fitness review',
            'review framework and risk model review',
            'ML/RL roadmap and training objective review',
            'structural system changes and deprecation candidates',
        ]
        notes = ['quarterly review may discuss structural changes, but should preserve auditability and comparability across periods']

    plan = ReviewPlan(
        cadence=window.cadence.value,
        label=window.label,
        window_start=window.window_start.isoformat(),
        window_end=window.window_end.isoformat(),
        focus_areas=focus,
        adjustment_policy=asdict(policy),
        notes=notes,
    )
    return asdict(plan)
