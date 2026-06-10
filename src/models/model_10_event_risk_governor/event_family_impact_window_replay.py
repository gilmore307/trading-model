"""Apply reviewed impact-window event context to replay decision rows.

This module joins frozen replay decision rows to the Layer 10 real-input
impact-window artifact, then runs the EventRiskGovernor generator over the
point-in-time visible events. It writes model evidence artifacts only; it does
not mutate SQL, train or activate models, call providers, or touch broker state.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo

from model_runtime.config import model_storage_root, component_storage_root
from models.model_10_event_risk_governor import generate_rows
from models.model_10_event_risk_governor.event_family_impact_window_backtest import DEFAULT_CANDIDATE_WINDOWS

ET = ZoneInfo("America/New_York")
DEFAULT_REPLAY_RUN_ID = "model_group_replay_20260609T060059Z"
DEFAULT_FOLD_ID = "fold_2016-01_2016-06"
DEFAULT_DATASET_ROOT = component_storage_root("replay") / "promotion_replay_candidate_policy"
DEFAULT_REPLAY_DECISION_ROWS = DEFAULT_DATASET_ROOT / "replay_execution_runs" / DEFAULT_REPLAY_RUN_ID / "decision_rows.jsonl"
DEFAULT_IMPACT_WINDOW_ROOT = model_storage_root() / "event_family_impact_window_real_input_backtest_20260610"
DEFAULT_EVENT_CSV = DEFAULT_IMPACT_WINDOW_ROOT / "inputs" / "reviewed_event_instances.csv"
DEFAULT_IMPACT_WINDOW_SUMMARY = DEFAULT_IMPACT_WINDOW_ROOT / "backtest" / "event_family_impact_window_backtest_summary.json"
DEFAULT_OUTPUT_DIR = model_storage_root() / "event_family_impact_window_replay_20260610" / DEFAULT_FOLD_ID / DEFAULT_REPLAY_RUN_ID

SCHEDULED_FORMS = {"scheduled_data_release_event", "scheduled_calendar_event"}


@dataclass(frozen=True)
class ReplayRunResult:
    summary_path: str
    input_rows_path: str
    model_rows_path: str
    overlay_rows_path: str
    decision_row_count: int
    model_row_count: int
    visible_event_decision_count: int
    matched_event_counts_by_family: dict[str, int]
    fold_id: str
    replay_run_id: str
    provider_calls: int = 0
    sql_writes: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False
    evidence_status: str = "replay_overlay_evidence_not_promotion_approval"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_time(value: Any) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ET)
    return parsed.astimezone(ET)


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ET)
    return value.astimezone(ET).isoformat()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            text = line.strip()
            if text:
                rows.append(json.loads(text))
    return rows


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), sort_keys=True) + "\n")


def _window_offsets(summary_path: Path) -> dict[str, tuple[int, int, str]]:
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    labels = {window.window_label: (window.start_offset_days, window.end_offset_days) for window in DEFAULT_CANDIDATE_WINDOWS}
    output: dict[str, tuple[int, int, str]] = {}
    for family, row in payload.get("selected_windows", {}).items():
        label = str(row["selected_window_label"])
        if label not in labels:
            raise ValueError(f"unknown impact-window label for {family}: {label}")
        start, end = labels[label]
        output[str(family)] = (start, end, label)
    return output


def _event_time(event_date: date, family_key: str) -> datetime:
    if family_key == "cpi_inflation_release":
        clock = time(8, 30)
    elif family_key == "triple_witching_calendar":
        clock = time(16, 0)
    else:
        clock = time(9, 30)
    return datetime.combine(event_date, clock, tzinfo=ET)


def _event_category(family_key: str) -> str:
    return {
        "cpi_inflation_release": "macro_cpi_inflation_release",
        "triple_witching_calendar": "market_structure_option_expiry_triple_witching",
        "breaking_news_shock": "market_breaking_news_shock",
    }.get(family_key, family_key)


def _native_scope(family_key: str) -> str:
    return {
        "cpi_inflation_release": "macro",
        "triple_witching_calendar": "market_structure",
        "breaking_news_shock": "market",
    }.get(family_key, "market")


def _available_time(event_dt: datetime, window_start: date, temporal_form: str) -> datetime:
    if temporal_form in SCHEDULED_FORMS:
        return datetime.combine(window_start, time(0, 0), tzinfo=ET)
    return event_dt


def _load_events(event_csv: Path, summary_path: Path) -> list[dict[str, Any]]:
    offsets = _window_offsets(summary_path)
    events: list[dict[str, Any]] = []
    with event_csv.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            family = str(row["family_key"])
            if family not in offsets:
                continue
            start_offset, end_offset, window_label = offsets[family]
            event_day = date.fromisoformat(str(row["event_date"])[:10])
            event_dt = _event_time(event_day, family)
            window_start = event_day + timedelta(days=start_offset)
            window_end = event_day + timedelta(days=end_offset)
            available = _available_time(event_dt, window_start, str(row["event_temporal_form"]))
            events.append(
                {
                    "event_id": row.get("event_ref") or f"{family}_{event_day:%Y%m%d}",
                    "canonical_event_id": row.get("event_ref") or f"{family}_{event_day:%Y%m%d}",
                    "event_family_key": family,
                    "event_category_type": _event_category(family),
                    "event_native_scope_type": _native_scope(family),
                    "event_temporal_form": row["event_temporal_form"],
                    "event_time": _iso(event_dt),
                    "available_time": _iso(available),
                    "window_start_date": window_start.isoformat(),
                    "window_end_date": window_end.isoformat(),
                    "selected_window_label": window_label,
                    "source_ref": row.get("source_ref"),
                    "event_intensity_score": 0.65 if family in {"cpi_inflation_release", "triple_witching_calendar"} else 0.75,
                    "uncertainty_score": 0.25 if family in {"cpi_inflation_release", "triple_witching_calendar"} else 0.45,
                    "direction_bias_score": 0.0,
                    "source_quality_score": 0.8,
                    "dedup_status": "new_information",
                }
            )
    return events


def _events_for_decision(decision_time: datetime, events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    decision_day = decision_time.date()
    visible: list[dict[str, Any]] = []
    for event in events:
        window_start = date.fromisoformat(str(event["window_start_date"]))
        window_end = date.fromisoformat(str(event["window_end_date"]))
        if not (window_start <= decision_day <= window_end):
            continue
        if _parse_time(event["available_time"]) > decision_time:
            continue
        visible.append(dict(event))
    return visible


def _target_context_state(decision: Mapping[str, Any]) -> dict[str, Any]:
    layer_diagnostics = decision.get("model_layer_diagnostics") if isinstance(decision.get("model_layer_diagnostics"), Mapping) else {}
    action_scores = (
        layer_diagnostics.get("model_08_underlying_action", {}).get("dominant_horizon_scores", {})
        if isinstance(layer_diagnostics.get("model_08_underlying_action"), Mapping)
        else {}
    )
    return {
        "3_target_direction_score_1D": action_scores.get("action_direction_score", 0.0),
        "3_target_direction_score_1W": action_scores.get("action_direction_score", 0.0),
    }


def _generator_input(decision: Mapping[str, Any], events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    decision_time = _parse_time(decision.get("replay_time_pointer") or decision.get("timestamp"))
    model_refs = decision.get("model_layer_refs") if isinstance(decision.get("model_layer_refs"), Mapping) else {}
    return {
        "available_time": _iso(decision_time),
        "tradeable_time": _iso(decision_time),
        "target_candidate_id": str(decision.get("target_ref") or "target"),
        "symbol_for_join_only": decision.get("target_ref"),
        "asset_class": decision.get("asset_class"),
        "asset_expression_route": decision.get("asset_expression_route"),
        "underlying_action_plan_ref": model_refs.get("model_08_underlying_action"),
        "target_context_state": _target_context_state(decision),
        "event_rows": list(events),
    }


def _excess_return(decision: Mapping[str, Any]) -> float | None:
    try:
        return float(decision.get("realized_return") or 0.0) - float(decision.get("cost") or 0.0) - float(decision.get("baseline_return") or 0.0)
    except (TypeError, ValueError):
        return None


def _summarize(
    *,
    decision_rows: Sequence[Mapping[str, Any]],
    input_rows: Sequence[Mapping[str, Any]],
    model_rows: Sequence[Mapping[str, Any]],
    overlay_rows: Sequence[Mapping[str, Any]],
    fold_id: str,
    replay_run_id: str,
    replay_decision_rows: Path,
    event_csv: Path,
    impact_window_summary: Path,
) -> dict[str, Any]:
    family_counts: Counter[str] = Counter()
    visible_rows = 0
    event_excess: list[float] = []
    no_event_excess: list[float] = []
    accepted_with_event = 0
    for decision, input_row in zip(decision_rows, input_rows):
        events = input_row.get("event_rows") if isinstance(input_row.get("event_rows"), list) else []
        if events:
            visible_rows += 1
            if decision.get("decision_status") == "accepted":
                accepted_with_event += 1
            value = _excess_return(decision)
            if value is not None:
                event_excess.append(value)
        else:
            value = _excess_return(decision)
            if value is not None:
                no_event_excess.append(value)
        for event in events:
            family_counts[str(event.get("event_family_key") or "unknown")] += 1
    return {
        "contract_type": "event_family_impact_window_replay_overlay_summary",
        "fold_id": fold_id,
        "replay_run_id": replay_run_id,
        "decision_row_count": len(decision_rows),
        "input_row_count": len(input_rows),
        "model_row_count": len(model_rows),
        "overlay_row_count": len(overlay_rows),
        "visible_event_decision_count": visible_rows,
        "accepted_decision_with_event_count": accepted_with_event,
        "matched_event_counts_by_family": dict(sorted(family_counts.items())),
        "event_decision_mean_excess_return": round(sum(event_excess) / len(event_excess), 8) if event_excess else None,
        "no_event_decision_mean_excess_return": round(sum(no_event_excess) / len(no_event_excess), 8) if no_event_excess else None,
        "source_refs": {
            "replay_decision_rows": str(replay_decision_rows),
            "event_csv": str(event_csv),
            "impact_window_summary": str(impact_window_summary),
        },
        "point_in_time_note": "Scheduled events may be visible before event date; unscheduled breaking-news shocks become visible only at event time.",
        "provider_calls": 0,
        "sql_writes": 0,
        "model_training_performed": False,
        "model_activation_performed": False,
        "broker_execution_performed": False,
        "account_mutation_performed": False,
        "artifact_deletion_performed": False,
        "evidence_status": "replay_overlay_evidence_not_promotion_approval",
    }


def build_impact_window_replay_artifacts(
    *,
    replay_decision_rows: Path = DEFAULT_REPLAY_DECISION_ROWS,
    event_csv: Path = DEFAULT_EVENT_CSV,
    impact_window_summary: Path = DEFAULT_IMPACT_WINDOW_SUMMARY,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    fold_id: str = DEFAULT_FOLD_ID,
    replay_run_id: str = DEFAULT_REPLAY_RUN_ID,
) -> ReplayRunResult:
    decision_rows = _read_jsonl(replay_decision_rows)
    events = _load_events(event_csv, impact_window_summary)
    input_rows: list[dict[str, Any]] = []
    for decision in decision_rows:
        decision_time = _parse_time(decision.get("replay_time_pointer") or decision.get("timestamp"))
        matched_events = _events_for_decision(decision_time, events)
        input_rows.append(_generator_input(decision, matched_events))
    model_rows = generate_rows(input_rows)

    overlay_rows: list[dict[str, Any]] = []
    for decision, input_row, model_row in zip(decision_rows, input_rows, model_rows):
        diagnostics = model_row.get("event_risk_governor_diagnostics") if isinstance(model_row.get("event_risk_governor_diagnostics"), Mapping) else {}
        overlay_rows.append(
            {
                "contract_type": "event_family_impact_window_replay_overlay_row",
                "fold_id": fold_id,
                "replay_run_id": replay_run_id,
                "decision_id": decision.get("decision_id"),
                "target_ref": decision.get("target_ref"),
                "replay_time_pointer": decision.get("replay_time_pointer") or decision.get("timestamp"),
                "decision_status": decision.get("decision_status"),
                "prediction_score": decision.get("prediction_score"),
                "outcome_label": decision.get("outcome_label"),
                "realized_return": decision.get("realized_return"),
                "cost": decision.get("cost"),
                "excess_return": _excess_return(decision),
                "visible_event_count": diagnostics.get("visible_event_count", 0),
                "visible_event_ids": diagnostics.get("visible_event_ids", []),
                "visible_event_families": [event.get("event_family_key") for event in input_row.get("event_rows", [])],
                "event_context_vector_ref": model_row.get("event_context_vector_ref"),
                "10_event_presence_score_1D": model_row.get("10_event_presence_score_1D"),
                "10_event_timing_proximity_score_1D": model_row.get("10_event_timing_proximity_score_1D"),
                "10_event_intensity_score_1D": model_row.get("10_event_intensity_score_1D"),
                "10_event_gap_risk_score_1D": model_row.get("10_event_gap_risk_score_1D"),
                "10_event_reversal_risk_score_1D": model_row.get("10_event_reversal_risk_score_1D"),
                "10_event_underlying_impact_score_1D": model_row.get("10_event_underlying_impact_score_1D"),
                "10_event_option_impact_score_1D": model_row.get("10_event_option_impact_score_1D"),
            }
        )

    input_path = output_dir / "layer_10_replay_input_rows.jsonl"
    model_path = output_dir / "model_10_event_risk_governor_rows.jsonl"
    overlay_path = output_dir / "decision_event_overlay_rows.jsonl"
    summary_path = output_dir / "event_family_impact_window_replay_summary.json"
    _write_jsonl(input_path, input_rows)
    _write_jsonl(model_path, model_rows)
    _write_jsonl(overlay_path, overlay_rows)
    summary = _summarize(
        decision_rows=decision_rows,
        input_rows=input_rows,
        model_rows=model_rows,
        overlay_rows=overlay_rows,
        fold_id=fold_id,
        replay_run_id=replay_run_id,
        replay_decision_rows=replay_decision_rows,
        event_csv=event_csv,
        impact_window_summary=impact_window_summary,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (output_dir / "README.md").write_text(
        "# Event-family impact-window replay overlay\n\n"
        "This artifact applies the reviewed local Layer 10 impact-window event context to frozen replay decision rows. "
        "It is replay overlay evidence only, not promotion approval, model activation, broker execution, or SQL mutation.\n",
        encoding="utf-8",
    )
    return ReplayRunResult(
        summary_path=str(summary_path),
        input_rows_path=str(input_path),
        model_rows_path=str(model_path),
        overlay_rows_path=str(overlay_path),
        decision_row_count=len(decision_rows),
        model_row_count=len(model_rows),
        visible_event_decision_count=int(summary["visible_event_decision_count"]),
        matched_event_counts_by_family=dict(summary["matched_event_counts_by_family"]),
        fold_id=fold_id,
        replay_run_id=replay_run_id,
    )


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "ReplayRunResult",
    "build_impact_window_replay_artifacts",
]
