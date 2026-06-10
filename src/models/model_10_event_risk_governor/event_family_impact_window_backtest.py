"""Event-family impact-window backtest for EventRiskGovernor.

This contract learns candidate impact windows from event-aligned price paths
and controls. It can run a small built-in verifier sample or reviewed local
event/price input files; it does not call providers, train models, activate
models, mutate broker/account state, or delete artifacts. Real input runs still
require review before they can become promotion evidence.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Mapping, Sequence, TextIO

from model_runtime.config import model_storage_root

CONTRACT_TYPE = "event_family_impact_window_backtest"
SUMMARY_CONTRACT_TYPE = "event_family_impact_window_backtest_summary"
DEFAULT_OUTPUT_DIR = model_storage_root() / "event_family_impact_window_backtest_20260610"


@dataclass(frozen=True)
class DailyBar:
    symbol: str
    day: date
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class EventInstance:
    family_key: str
    event_temporal_form: str
    event_date: date
    event_ref: str
    source_ref: str


@dataclass(frozen=True)
class CandidateWindow:
    window_label: str
    start_offset_days: int
    end_offset_days: int

    @property
    def length_days(self) -> int:
        return self.end_offset_days - self.start_offset_days + 1


@dataclass(frozen=True)
class WindowScore:
    window_label: str
    start_offset_days: int
    end_offset_days: int
    length_days: int
    event_sample_count: int
    control_sample_count: int
    event_mean_abs_return: float | None
    control_mean_abs_return: float | None
    event_mean_path_range: float | None
    control_mean_path_range: float | None
    event_mean_risk_mass: float | None
    control_mean_risk_mass: float | None
    abs_return_delta: float | None
    path_range_delta: float | None
    risk_mass_delta: float | None
    selection_score: float

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ImpactWindowBacktestRow:
    family_key: str
    event_temporal_form: str
    event_count: int
    symbol_count: int
    candidate_window_count: int
    selected_window_label: str
    selected_window_start_offset_days: int
    selected_window_end_offset_days: int
    selected_window_length_days: int
    selection_score: float
    path_range_delta: float | None
    abs_return_delta: float | None
    control_sample_count: int
    parameterization_status: str
    layer_4_projection_type: str
    event_family_impact_parameterization: dict[str, Any]
    runner_up_window_label: str
    runner_up_selection_score: float
    evidence_note: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)

    def csv_row(self) -> dict[str, str]:
        row = self.to_row()
        out: dict[str, str] = {}
        for key, value in row.items():
            if isinstance(value, (dict, list, tuple)):
                out[key] = json.dumps(value, sort_keys=True)
            elif value is None:
                out[key] = ""
            else:
                out[key] = str(value)
        return out


@dataclass(frozen=True)
class EventFamilyImpactWindowBacktest:
    contract_type: str
    generated_at_utc: str
    family_rows: tuple[ImpactWindowBacktestRow, ...]
    candidate_scores_by_family: dict[str, tuple[WindowScore, ...]]
    input_scope: str = "sample_contract_verifier"
    source_event_paths: tuple[str, ...] = ()
    source_bar_paths: tuple[str, ...] = ()
    provider_calls: int = 0
    model_training_performed: bool = False
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "contract_type": SUMMARY_CONTRACT_TYPE,
            "generated_at_utc": self.generated_at_utc,
            "family_count": len(self.family_rows),
            "selected_windows": {
                row.family_key: {
                    "event_temporal_form": row.event_temporal_form,
                    "selected_window_label": row.selected_window_label,
                    "selection_score": row.selection_score,
                }
                for row in self.family_rows
            },
            "selection_method": "enumerate_candidate_windows_and_select_highest_event_vs_control_risk_delta_penalized_by_window_length",
            "input_scope": self.input_scope,
            "source_event_paths": list(self.source_event_paths),
            "source_bar_paths": list(self.source_bar_paths),
            "sample_scope_note": _scope_note(self.input_scope),
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "family_rows": [row.to_row() for row in self.family_rows],
            "candidate_scores_by_family": {
                family: [score.to_row() for score in scores]
                for family, scores in sorted(self.candidate_scores_by_family.items())
            },
            "summary": self.summary,
            "input_scope": self.input_scope,
            "source_event_paths": list(self.source_event_paths),
            "source_bar_paths": list(self.source_bar_paths),
            "provider_calls": self.provider_calls,
            "model_training_performed": self.model_training_performed,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _scope_note(input_scope: str) -> str:
    if input_scope == "real_input_backtest":
        return "Reviewed local event and price input contract run; not accepted promotion evidence until review."
    return "Synthetic small-sample contract verifier; not accepted real-market promotion evidence."


DEFAULT_CANDIDATE_WINDOWS = (
    CandidateWindow("minus_10_to_plus_3", -10, 3),
    CandidateWindow("minus_7_to_plus_3", -7, 3),
    CandidateWindow("minus_7_to_event", -7, 0),
    CandidateWindow("minus_5_to_plus_5", -5, 5),
    CandidateWindow("minus_3_to_plus_3", -3, 3),
    CandidateWindow("minus_3_to_event", -3, 0),
    CandidateWindow("minus_2_to_plus_2", -2, 2),
    CandidateWindow("minus_1_to_plus_1", -1, 1),
    CandidateWindow("event_day_only", 0, 0),
    CandidateWindow("event_to_plus_1", 0, 1),
    CandidateWindow("event_to_plus_3", 0, 3),
)


def _date_range(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _bars_by_symbol(bars: Sequence[DailyBar]) -> dict[str, dict[date, DailyBar]]:
    by_symbol: dict[str, dict[date, DailyBar]] = defaultdict(dict)
    for bar in bars:
        by_symbol[bar.symbol][bar.day] = bar
    return dict(by_symbol)


def _window_metrics(symbol_bars: Mapping[date, DailyBar], start: date, end: date) -> dict[str, float] | None:
    window = [symbol_bars[day] for day in _date_range(start, end) if day in symbol_bars]
    if len(window) != (end - start).days + 1:
        return None
    first = window[0]
    last = window[-1]
    if first.open <= 0:
        return None
    total_return = last.close / first.open - 1.0
    return {
        "abs_return": abs(total_return),
        "path_range": (max(bar.high for bar in window) - min(bar.low for bar in window)) / first.open,
        "risk_mass": sum((bar.high - bar.low) / bar.open for bar in window if bar.open > 0),
    }


def _event_exclusion_days(instances: Sequence[EventInstance], *, radius_days: int = 14) -> set[date]:
    excluded: set[date] = set()
    for instance in instances:
        for day in _date_range(instance.event_date - timedelta(days=radius_days), instance.event_date + timedelta(days=radius_days)):
            excluded.add(day)
    return excluded


def _control_metrics(
    *,
    symbol_bars: Mapping[date, DailyBar],
    window: CandidateWindow,
    excluded_days: set[date],
) -> list[dict[str, float]]:
    days = sorted(symbol_bars)
    out: list[dict[str, float]] = []
    for start in days:
        end = start + timedelta(days=window.length_days - 1)
        if any(day in excluded_days for day in _date_range(start, end)):
            continue
        metrics = _window_metrics(symbol_bars, start, end)
        if metrics is not None:
            out.append(metrics)
    return out


def _mean_or_none(values: Sequence[float]) -> float | None:
    return mean(values) if values else None


def _delta(left: float | None, right: float | None) -> float | None:
    return None if left is None or right is None else left - right


def _score_window(
    *,
    instances: Sequence[EventInstance],
    bars_by_symbol: Mapping[str, Mapping[date, DailyBar]],
    window: CandidateWindow,
) -> WindowScore:
    event_metrics: list[dict[str, float]] = []
    for instance in instances:
        start = instance.event_date + timedelta(days=window.start_offset_days)
        end = instance.event_date + timedelta(days=window.end_offset_days)
        for symbol_bars in bars_by_symbol.values():
            metrics = _window_metrics(symbol_bars, start, end)
            if metrics is not None:
                event_metrics.append(metrics)
    excluded = _event_exclusion_days(instances)
    control_metrics = [
        metrics
        for symbol_bars in bars_by_symbol.values()
        for metrics in _control_metrics(symbol_bars=symbol_bars, window=window, excluded_days=excluded)
    ]
    event_abs = _mean_or_none([item["abs_return"] for item in event_metrics])
    control_abs = _mean_or_none([item["abs_return"] for item in control_metrics])
    event_range = _mean_or_none([item["path_range"] for item in event_metrics])
    control_range = _mean_or_none([item["path_range"] for item in control_metrics])
    event_risk_mass = _mean_or_none([item["risk_mass"] for item in event_metrics])
    control_risk_mass = _mean_or_none([item["risk_mass"] for item in control_metrics])
    abs_delta = _delta(event_abs, control_abs)
    range_delta = _delta(event_range, control_range)
    risk_mass_delta = _delta(event_risk_mass, control_risk_mass)
    raw_score = (risk_mass_delta or 0.0) + 0.5 * (range_delta or 0.0) + 0.5 * (abs_delta or 0.0)
    score = raw_score / math.sqrt(max(1, window.length_days))
    return WindowScore(
        window_label=window.window_label,
        start_offset_days=window.start_offset_days,
        end_offset_days=window.end_offset_days,
        length_days=window.length_days,
        event_sample_count=len(event_metrics),
        control_sample_count=len(control_metrics),
        event_mean_abs_return=event_abs,
        control_mean_abs_return=control_abs,
        event_mean_path_range=event_range,
        control_mean_path_range=control_range,
        event_mean_risk_mass=event_risk_mass,
        control_mean_risk_mass=control_risk_mass,
        abs_return_delta=abs_delta,
        path_range_delta=range_delta,
        risk_mass_delta=risk_mass_delta,
        selection_score=score,
    )


def _impact_parameterization(
    row: WindowScore,
    temporal_form: str,
    *,
    parameterization_status: str,
    impact_scope_parameter: str,
) -> dict[str, Any]:
    if temporal_form == "scheduled_data_release_event":
        curve = {
            "pre_event_component": "learned_anticipation_window",
            "event_time_component": "release_shock",
            "post_event_component": "learned_absorption_or_followthrough_decay",
        }
        schedule_type = "scheduled_release_calendar"
    elif temporal_form == "scheduled_calendar_event":
        curve = {
            "pre_event_component": "learned_calendar_positioning_window",
            "event_time_component": "calendar_mechanics",
            "post_event_component": "learned_calendar_effect_decay",
        }
        schedule_type = "scheduled_periodic_calendar"
    elif temporal_form == "continuous_or_regime_event":
        curve = {
            "pre_event_component": "not_calendar_defined",
            "event_time_component": "state_persistence",
            "post_event_component": "learned_resolution_or_decay",
        }
        schedule_type = "unscheduled_continuous"
    else:
        curve = {
            "pre_event_component": "not_calendar_defined",
            "event_time_component": "learned_shock_onset",
            "post_event_component": "learned_shock_absorption_or_followthrough",
        }
        schedule_type = "unscheduled"
    return {
        "parameterization_status": parameterization_status,
        "temporal_form": temporal_form,
        "schedule_type": schedule_type,
        "selected_effect_window": {
            "start_offset_days": row.start_offset_days,
            "end_offset_days": row.end_offset_days,
            "window_label": row.window_label,
        },
        "impact_curve_components": curve,
        "impact_scope_parameter": impact_scope_parameter,
        "severity_model": "event_vs_control_abs_return_plus_path_range_delta",
        "layer_4_projection_type": "event_family_impact_state_projection",
    }


def build_event_family_impact_window_backtest(
    *,
    event_instances: Sequence[EventInstance],
    bars: Sequence[DailyBar],
    candidate_windows: Sequence[CandidateWindow] = DEFAULT_CANDIDATE_WINDOWS,
    generated_at_utc: str | None = None,
    input_scope: str = "sample_contract_verifier",
    source_event_paths: Sequence[str] = (),
    source_bar_paths: Sequence[str] = (),
    parameterization_status: str = "sample_backtest_selected",
    evidence_note: str = "Selected from candidate windows using sample event-vs-control price-path deltas; not real-market promotion evidence.",
    impact_scope_parameter: str = "sample_symbol_path",
) -> EventFamilyImpactWindowBacktest:
    generated = generated_at_utc or datetime.now(UTC).isoformat()
    if not event_instances:
        raise ValueError("event_instances must contain at least one event")
    if not bars:
        raise ValueError("bars must contain at least one price bar")
    bars_by_symbol = _bars_by_symbol(bars)
    family_instances: dict[str, list[EventInstance]] = defaultdict(list)
    for instance in event_instances:
        family_instances[instance.family_key].append(instance)
    rows: list[ImpactWindowBacktestRow] = []
    scores_by_family: dict[str, tuple[WindowScore, ...]] = {}
    for family_key, instances in sorted(family_instances.items()):
        scores = tuple(
            sorted(
                (
                    _score_window(instances=instances, bars_by_symbol=bars_by_symbol, window=window)
                    for window in candidate_windows
                ),
                key=lambda item: (item.selection_score, -item.length_days, item.window_label),
                reverse=True,
            )
        )
        selected = scores[0]
        runner_up = scores[1] if len(scores) > 1 else selected
        temporal_form = instances[0].event_temporal_form
        row_status = parameterization_status
        row_evidence_note = evidence_note
        if selected.event_sample_count == 0 or selected.control_sample_count == 0:
            row_status = "insufficient_event_or_control_samples"
            row_evidence_note = "No complete event/control windows for the selected candidate; no impact-window parameterization claim."
        rows.append(
            ImpactWindowBacktestRow(
                family_key=family_key,
                event_temporal_form=temporal_form,
                event_count=len(instances),
                symbol_count=len(bars_by_symbol),
                candidate_window_count=len(candidate_windows),
                selected_window_label=selected.window_label,
                selected_window_start_offset_days=selected.start_offset_days,
                selected_window_end_offset_days=selected.end_offset_days,
                selected_window_length_days=selected.length_days,
                selection_score=selected.selection_score,
                path_range_delta=selected.path_range_delta,
                abs_return_delta=selected.abs_return_delta,
                control_sample_count=selected.control_sample_count,
                parameterization_status=row_status,
                layer_4_projection_type="event_family_impact_state_projection",
                event_family_impact_parameterization=_impact_parameterization(
                    selected,
                    temporal_form,
                    parameterization_status=row_status,
                    impact_scope_parameter=impact_scope_parameter,
                ),
                runner_up_window_label=runner_up.window_label,
                runner_up_selection_score=runner_up.selection_score,
                evidence_note=row_evidence_note,
            )
        )
        scores_by_family[family_key] = scores
    return EventFamilyImpactWindowBacktest(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated,
        family_rows=tuple(rows),
        candidate_scores_by_family=scores_by_family,
        input_scope=input_scope,
        source_event_paths=tuple(source_event_paths),
        source_bar_paths=tuple(source_bar_paths),
    )


def build_sample_event_family_impact_window_backtest(*, generated_at_utc: str | None = None) -> EventFamilyImpactWindowBacktest:
    return build_event_family_impact_window_backtest(
        event_instances=_sample_event_instances(),
        bars=_sample_bars(),
        generated_at_utc=generated_at_utc,
    )


def _parse_date(value: str) -> date:
    raw = value.strip()
    if not raw:
        raise ValueError("empty date value")
    try:
        return date.fromisoformat(raw[:10])
    except ValueError as exc:
        raise ValueError(f"invalid ISO date value {value!r}") from exc


def _parse_optional_datetime(value: str) -> datetime | None:
    raw = value.strip()
    if not raw:
        return None
    raw = raw.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _required_field(row: Mapping[str, str], aliases: Sequence[str]) -> str:
    for alias in aliases:
        value = row.get(alias)
        if value not in (None, ""):
            return str(value)
    raise ValueError(f"missing required field; expected one of {', '.join(aliases)}")


def _float_field(row: Mapping[str, str], aliases: Sequence[str]) -> float:
    raw = _required_field(row, aliases)
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid numeric field {raw!r}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite numeric field {raw!r}")
    return value


def load_event_instances_from_csv(paths: Sequence[Path]) -> tuple[EventInstance, ...]:
    events: list[EventInstance] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                event_ref = row.get("event_ref") or row.get("event_id") or f"{path}:{len(events) + 1}"
                source_ref = row.get("source_ref") or row.get("source_path") or str(path)
                events.append(
                    EventInstance(
                        family_key=_required_field(row, ("family_key", "event_family_key", "family")),
                        event_temporal_form=_required_field(row, ("event_temporal_form", "temporal_form")),
                        event_date=_parse_date(_required_field(row, ("event_date", "scheduled_date", "published_date", "date", "event_time", "published_time"))),
                        event_ref=event_ref,
                        source_ref=source_ref,
                    )
                )
    if not events:
        raise ValueError("event CSV inputs produced zero event instances")
    return tuple(events)


def load_daily_bars_from_csv(paths: Sequence[Path]) -> tuple[DailyBar, ...]:
    day_rows: dict[tuple[str, date], list[tuple[datetime | None, float, float, float, float]]] = defaultdict(list)
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                symbol = _required_field(row, ("symbol", "ticker", "asset"))
                raw_time = _required_field(row, ("timestamp", "time", "bar_time", "day", "date"))
                dt = _parse_optional_datetime(raw_time)
                day = dt.date() if dt is not None else _parse_date(raw_time)
                day_rows[(symbol, day)].append(
                    (
                        dt,
                        _float_field(row, ("open", "bar_open")),
                        _float_field(row, ("high", "bar_high")),
                        _float_field(row, ("low", "bar_low")),
                        _float_field(row, ("close", "bar_close")),
                    )
                )
    bars: list[DailyBar] = []
    for (symbol, day), rows in sorted(day_rows.items()):
        ordered = sorted(rows, key=lambda item: item[0].isoformat() if item[0] is not None else "")
        bars.append(
            DailyBar(
                symbol=symbol,
                day=day,
                open=ordered[0][1],
                high=max(row[2] for row in ordered),
                low=min(row[3] for row in ordered),
                close=ordered[-1][4],
            )
        )
    if not bars:
        raise ValueError("bar CSV inputs produced zero daily bars")
    return tuple(bars)


def build_real_input_event_family_impact_window_backtest(
    *,
    event_paths: Sequence[Path],
    bar_paths: Sequence[Path],
    generated_at_utc: str | None = None,
) -> EventFamilyImpactWindowBacktest:
    return build_event_family_impact_window_backtest(
        event_instances=load_event_instances_from_csv(event_paths),
        bars=load_daily_bars_from_csv(bar_paths),
        generated_at_utc=generated_at_utc,
        input_scope="real_input_backtest",
        source_event_paths=tuple(str(path) for path in event_paths),
        source_bar_paths=tuple(str(path) for path in bar_paths),
        parameterization_status="real_input_backtest_selected",
        evidence_note="Selected from candidate windows using reviewed local event inputs and point-in-time price paths; requires review before promotion-evidence use.",
        impact_scope_parameter="point_in_time_price_path",
    )


def _sample_event_instances() -> tuple[EventInstance, ...]:
    return (
        EventInstance("cpi_inflation_release", "scheduled_data_release_event", date(2021, 1, 20), "sample_cpi_20210120", "sample://cpi/2021-01-20"),
        EventInstance("cpi_inflation_release", "scheduled_data_release_event", date(2021, 2, 17), "sample_cpi_20210217", "sample://cpi/2021-02-17"),
        EventInstance("cpi_inflation_release", "scheduled_data_release_event", date(2021, 3, 17), "sample_cpi_20210317", "sample://cpi/2021-03-17"),
        EventInstance("triple_witching_calendar", "scheduled_calendar_event", date(2021, 3, 19), "sample_witching_20210319", "sample://triple-witching/2021-03-19"),
        EventInstance("triple_witching_calendar", "scheduled_calendar_event", date(2021, 6, 18), "sample_witching_20210618", "sample://triple-witching/2021-06-18"),
        EventInstance("triple_witching_calendar", "scheduled_calendar_event", date(2021, 9, 17), "sample_witching_20210917", "sample://triple-witching/2021-09-17"),
        EventInstance("breaking_news_shock", "instantaneous_unscheduled_event", date(2021, 2, 3), "sample_news_20210203", "sample://breaking-news/2021-02-03"),
        EventInstance("breaking_news_shock", "instantaneous_unscheduled_event", date(2021, 5, 11), "sample_news_20210511", "sample://breaking-news/2021-05-11"),
        EventInstance("breaking_news_shock", "instantaneous_unscheduled_event", date(2021, 8, 24), "sample_news_20210824", "sample://breaking-news/2021-08-24"),
    )


def _sample_bars() -> tuple[DailyBar, ...]:
    impact_by_day: dict[date, float] = defaultdict(float)
    close_shift_by_day: dict[date, float] = defaultdict(float)
    for instance in _sample_event_instances():
        if instance.family_key == "cpi_inflation_release":
            for offset in range(-7, 4):
                day = instance.event_date + timedelta(days=offset)
                impact_by_day[day] += 0.018 + abs(offset) * 0.0006
                close_shift_by_day[day] += -0.0025 * (offset + 8)
        elif instance.family_key == "triple_witching_calendar":
            for offset in range(-2, 3):
                day = instance.event_date + timedelta(days=offset)
                impact_by_day[day] += 0.022 - abs(offset) * 0.002
                close_shift_by_day[day] += 0.004 * ((offset % 2) * 2 - 1)
        elif instance.family_key == "breaking_news_shock":
            day = instance.event_date
            impact_by_day[day] += 0.06
            close_shift_by_day[day] += -0.035
    bars: list[DailyBar] = []
    for symbol, base in (("SPY", 100.0), ("QQQ", 120.0)):
        for idx, day in enumerate(_date_range(date(2021, 1, 1), date(2021, 10, 15))):
            drift = idx * 0.015
            open_price = base + drift
            close_price = open_price * (1.0 + close_shift_by_day[day])
            normal_range = 0.002
            impact_range = impact_by_day[day]
            high = max(open_price, close_price) * (1.0 + normal_range + impact_range)
            low = min(open_price, close_price) * (1.0 - normal_range - impact_range)
            bars.append(DailyBar(symbol=symbol, day=day, open=open_price, high=high, low=low, close=close_price))
    return tuple(bars)


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames or sorted({key for row in rows for key in row.keys()}))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_event_family_impact_window_backtest_artifacts(backtest: EventFamilyImpactWindowBacktest, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "event_family_impact_window_backtest.json").write_text(
        json.dumps(backtest.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "event_family_impact_window_backtest_summary.json").write_text(
        json.dumps(backtest.summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    fields = list(
        ImpactWindowBacktestRow("", "", 0, 0, 0, "", 0, 0, 0, 0.0, None, None, 0, "", "", {}, "", 0.0, "").csv_row().keys()
    )
    _write_csv(output_dir / "event_family_impact_window_backtest.csv", [row.csv_row() for row in backtest.family_rows], fieldnames=fields)
    score_rows = [
        {"family_key": family_key, **score.to_row()}
        for family_key, scores in sorted(backtest.candidate_scores_by_family.items())
        for score in scores
    ]
    _write_csv(output_dir / "event_family_impact_window_candidate_scores.csv", score_rows)
    (output_dir / "README.md").write_text(
        f"""# Event-family impact-window backtest

Contract: `{backtest.contract_type}`

Input scope: `{backtest.input_scope}`

This artifact validates the Layer 10 event-family impact-parameter contract. It enumerates candidate windows and selects the highest event-vs-control risk-delta window for CPI-style scheduled data releases, triple-witching-style scheduled calendar events, and breaking-news-style unscheduled shocks.

It performs no provider calls, model training, activation, broker/account mutation, destructive SQL, or artifact deletion. It is not accepted promotion evidence until reviewed.
""",
        encoding="utf-8",
    )


def write_backtest(backtest: EventFamilyImpactWindowBacktest, *, output: TextIO) -> None:
    json.dump(backtest.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "CandidateWindow",
    "DailyBar",
    "EventFamilyImpactWindowBacktest",
    "EventInstance",
    "ImpactWindowBacktestRow",
    "WindowScore",
    "build_event_family_impact_window_backtest",
    "build_real_input_event_family_impact_window_backtest",
    "build_sample_event_family_impact_window_backtest",
    "load_daily_bars_from_csv",
    "load_event_instances_from_csv",
    "write_backtest",
    "write_event_family_impact_window_backtest_artifacts",
]
