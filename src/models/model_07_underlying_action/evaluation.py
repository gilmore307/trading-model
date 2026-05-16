"""Local evaluation-label helpers for conceptual Layer 6 UnderlyingActionModel.

These helpers are deliberately offline-only. They join realized outcome rows to
already-emitted ``underlying_action_plan`` rows and derive plan-quality labels
without changing inference payloads.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Mapping


def build_plan_quality_labels(
    plan_rows: Iterable[Mapping[str, Any]],
    outcome_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Build deterministic plan-quality labels for Layer 7 plan rows.

    Outcome rows join by ``underlying_action_plan_ref`` when supplied, otherwise
    by ``target_candidate_id`` + ``available_time``. Expected outcome fields are
    optional; missing values produce ``None`` labels rather than fabricated
    evidence.
    """

    outcomes = {_outcome_key(row): row for row in outcome_rows}
    labels: list[dict[str, Any]] = []
    for plan in plan_rows:
        outcome = outcomes.get(_plan_key(plan), {})
        plan_payload = plan.get("underlying_action_plan") if isinstance(plan.get("underlying_action_plan"), Mapping) else {}
        action_type = str(plan_payload.get("planned_underlying_action_type") or plan.get("7_resolved_underlying_action_type") or "")
        entry_hit = _bool_or_none(outcome.get("entry_price_hit") or outcome.get("entry_price_hit_label"))
        target_before_stop = _target_before_stop(outcome)
        stop_before_target = None if target_before_stop is None else not target_before_stop
        realized_return = _float_or_none(outcome.get("realized_underlying_return") or outcome.get("realized_return"))
        slippage = _float_or_none(outcome.get("slippage_pct") or outcome.get("slippage")) or 0.0
        spread = _float_or_none(outcome.get("spread_cost_pct") or outcome.get("spread_cost")) or 0.0
        slippage_adjusted = None if realized_return is None else realized_return - abs(slippage)
        spread_adjusted = None if realized_return is None else realized_return - abs(slippage) - abs(spread)
        no_trade_like = action_type in {"no_trade", "maintain", "bearish_underlying_path_but_no_short_allowed"}
        labels.append(
            {
                "underlying_action_plan_ref": plan.get("underlying_action_plan_ref"),
                "target_candidate_id": plan.get("target_candidate_id"),
                "available_time": plan.get("available_time"),
                "planned_underlying_action_type": action_type,
                "planned_entry_fill_probability_label": entry_hit,
                "entry_price_hit_label": entry_hit,
                "target_price_hit_before_stop_label": target_before_stop,
                "stop_price_hit_before_target_label": stop_before_target,
                "realized_underlying_return_after_entry": realized_return,
                "realized_net_underlying_utility": spread_adjusted,
                "realized_max_favorable_excursion": _float_or_none(outcome.get("realized_max_favorable_excursion")),
                "realized_max_adverse_excursion": _float_or_none(outcome.get("realized_max_adverse_excursion")),
                "realized_holding_time_to_target": _float_or_none(outcome.get("realized_holding_time_to_target")),
                "realized_holding_time_to_stop": _float_or_none(outcome.get("realized_holding_time_to_stop")),
                "no_trade_opportunity_cost": _positive(realized_return) if no_trade_like else None,
                "bad_trade_avoidance_value": _positive(-realized_return) if no_trade_like and realized_return is not None else None,
                "no_trade_missed_positive_utility_rate": _indicator(no_trade_like and (spread_adjusted or 0.0) > 0.0),
                "no_trade_avoided_negative_utility_rate": _indicator(no_trade_like and (spread_adjusted or 0.0) < 0.0),
                "slippage_adjusted_return": slippage_adjusted,
                "spread_adjusted_return": spread_adjusted,
                "reward_risk_realized_ratio": _reward_risk(outcome),
            }
        )
    return labels


def _plan_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    ref = row.get("underlying_action_plan_ref")
    if ref:
        return ("ref", ref)
    return ("candidate_time", row.get("target_candidate_id"), row.get("available_time"))


def _outcome_key(row: Mapping[str, Any]) -> tuple[Any, ...]:
    ref = row.get("underlying_action_plan_ref")
    if ref:
        return ("ref", ref)
    return ("candidate_time", row.get("target_candidate_id"), row.get("available_time"))


def _target_before_stop(row: Mapping[str, Any]) -> bool | None:
    explicit = _bool_or_none(row.get("target_price_hit_before_stop") or row.get("target_price_hit_before_stop_label"))
    if explicit is not None:
        return explicit
    target_time = _parse_time(row.get("target_hit_time"))
    stop_time = _parse_time(row.get("stop_hit_time"))
    if target_time is None and stop_time is None:
        return None
    if target_time is None:
        return False
    if stop_time is None:
        return True
    return target_time <= stop_time


def _reward_risk(row: Mapping[str, Any]) -> float | None:
    mfe = _float_or_none(row.get("realized_max_favorable_excursion"))
    mae = _float_or_none(row.get("realized_max_adverse_excursion"))
    if mfe is None or mae is None or mae == 0:
        return None
    return round(abs(mfe) / abs(mae), 6)


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _bool_or_none(value: Any) -> bool | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y"}:
        return True
    if text in {"0", "false", "no", "n"}:
        return False
    return None


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _positive(value: float | None) -> float | None:
    if value is None:
        return None
    return max(float(value), 0.0)


def _indicator(value: bool) -> int:
    return 1 if value else 0
