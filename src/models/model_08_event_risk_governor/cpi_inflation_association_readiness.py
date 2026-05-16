"""CPI/inflation local association-control readiness.

This module runs the next safe local slice after generic event-price readiness:
it focuses on the `cpi_inflation_release` family, scans existing local macro
calendar artifacts, builds exploratory event labels from local ETF bars, and
adds simple same-month matched-control diagnostics.

It deliberately does not fetch providers, train/activate models, mutate broker
or account state, or delete artifacts. A one-month local CPI sample stays
underpowered even when control labels are available.
"""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence, TextIO

from models.model_08_event_risk_governor.event_price_association_readiness import (
    CPI_KEYWORDS,
    CandidateEvent,
    PriceLabel,
    _bar_path,
    _contains_any,
    _daily_bars,
    _fnum,
    _parse_date,
    _read_csv,
    _read_macro_events,
    _text,
)

CONTRACT_TYPE = "cpi_inflation_association_readiness_v1"
DEFAULT_DATA_ROOT = Path("/root/projects/trading-data")
DEFAULT_OUTPUT_DIR = Path("storage/cpi_inflation_association_readiness_20260516")
DEFAULT_PRICE_SYMBOLS = ("TLT", "XLF", "XLK", "HYG", "XLE")
DEFAULT_HORIZONS = (1, 5)
DEFAULT_CONTROL_WINDOW_DAYS = 7
MIN_EVENT_MONTHS_FOR_STUDY = 12
MIN_EVENT_LABELS_FOR_STUDY = 60


@dataclass(frozen=True)
class ControlLabel:
    family_key: str
    event_key: str
    symbol: str
    control_date: str
    horizon_days: int
    baseline_close: float
    forward_close: float
    directional_return: float
    absolute_return: float
    path_range: float
    control_role: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EventControlComparison:
    family_key: str
    event_key: str
    symbol: str
    horizon_days: int
    event_return: float | None
    control_count: int
    control_mean_return: float | None
    control_stdev_return: float | None
    event_minus_control_mean: float | None
    z_score_vs_controls: float | None
    comparison_status: str

    def to_row(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CpiAssociationReadiness:
    contract_type: str
    generated_at_utc: str
    calendar_months_available: tuple[str, ...]
    price_symbols: tuple[str, ...]
    horizons: tuple[int, ...]
    event_count: int
    event_label_count: int
    control_label_count: int
    comparison_count: int
    readiness_status: str
    association_study_status: str
    blocker_codes: tuple[str, ...]
    candidate_events: tuple[CandidateEvent, ...]
    event_labels: tuple[PriceLabel, ...]
    control_labels: tuple[ControlLabel, ...]
    comparisons: tuple[EventControlComparison, ...]
    provider_calls: int = 0
    model_activation_performed: bool = False
    broker_execution_performed: bool = False
    account_mutation_performed: bool = False
    artifact_deletion_performed: bool = False

    @property
    def summary(self) -> dict[str, Any]:
        comparable = [item for item in self.comparisons if item.comparison_status == "comparison_available"]
        return {
            "contract_type": self.contract_type,
            "calendar_month_count": len(self.calendar_months_available),
            "calendar_months_available": list(self.calendar_months_available),
            "event_count": self.event_count,
            "event_label_count": self.event_label_count,
            "control_label_count": self.control_label_count,
            "comparison_count": self.comparison_count,
            "comparison_available_count": len(comparable),
            "readiness_status": self.readiness_status,
            "association_study_status": self.association_study_status,
            "blocker_codes": list(self.blocker_codes),
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_type": self.contract_type,
            "generated_at_utc": self.generated_at_utc,
            "calendar_months_available": list(self.calendar_months_available),
            "price_symbols": list(self.price_symbols),
            "horizons": list(self.horizons),
            "event_count": self.event_count,
            "event_label_count": self.event_label_count,
            "control_label_count": self.control_label_count,
            "comparison_count": self.comparison_count,
            "readiness_status": self.readiness_status,
            "association_study_status": self.association_study_status,
            "blocker_codes": list(self.blocker_codes),
            "candidate_events": [item.to_row() for item in self.candidate_events],
            "event_labels": [item.to_row() for item in self.event_labels],
            "control_labels": [item.to_row() for item in self.control_labels],
            "comparisons": [item.to_row() for item in self.comparisons],
            "summary": self.summary,
            "provider_calls": self.provider_calls,
            "model_activation_performed": self.model_activation_performed,
            "broker_execution_performed": self.broker_execution_performed,
            "account_mutation_performed": self.account_mutation_performed,
            "artifact_deletion_performed": self.artifact_deletion_performed,
        }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], *, fieldnames: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _calendar_months(data_root: Path) -> tuple[str, ...]:
    root = data_root / "storage/monthly_backfill_v1/trading_economics_calendar_web"
    months = sorted({path.relative_to(root).parts[0] for path in root.glob("*/runs/*/saved/trading_economics_calendar_event.csv")})
    return tuple(months)


def _cpi_events_for_month(data_root: Path, month: str) -> list[CandidateEvent]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in _read_macro_events(data_root, month):
        text = _text(row, "event", "source_event_type")
        if _contains_any(text, CPI_KEYWORDS):
            grouped.setdefault(str(row.get("event_time") or ""), []).append(row)
    events: list[CandidateEvent] = []
    for event_time, items in sorted(grouped.items()):
        names = ";".join(str(item.get("event") or "") for item in items)
        surprises: list[str] = []
        for item in items:
            actual = _fnum(item.get("actual"))
            consensus = _fnum(item.get("consensus"))
            if actual is not None and consensus is not None:
                surprises.append(f"{item.get('event')} actual_minus_consensus={actual - consensus:g}")
        events.append(
            CandidateEvent(
                family_key="cpi_inflation_release",
                event_key=f"cpi_inflation_release:{event_time}",
                event_time=event_time,
                event_name=names,
                source_ref=";".join(sorted({str(item.get("_source_ref") or "") for item in items})),
                source_type="trading_economics_calendar_web",
                evidence_text="; ".join(surprises) if surprises else names,
                scope="macro",
                pit_status="calendar_timestamp_actual_previous_consensus_present",
                canonical_status="candidate_macro_release_not_official_source_canonicalized",
            )
        )
    return events


def _event_month(event: CandidateEvent) -> str:
    day = _parse_date(event.event_time)
    return f"{day.year:04d}-{day.month:02d}"


def _baseline_index(rows: Sequence[Mapping[str, Any]], event_day: date) -> int | None:
    previous: int | None = None
    for idx, row in enumerate(rows):
        if row["date"] >= event_day:
            return idx if row["date"] == event_day else previous
        previous = idx
    return previous


def _price_label_for(
    *,
    family_key: str,
    event_key: str,
    symbol: str,
    rows: Sequence[Mapping[str, Any]],
    baseline_index: int,
    horizon: int,
) -> PriceLabel | None:
    if baseline_index >= len(rows):
        return None
    baseline = float(rows[baseline_index]["close"])
    end = baseline_index + horizon
    if end >= len(rows):
        return PriceLabel(
            family_key=family_key,
            event_key=event_key,
            symbol=symbol,
            baseline_date=rows[baseline_index]["date"].isoformat(),
            baseline_close=baseline,
            horizon_days=horizon,
            forward_close=None,
            directional_return=None,
            absolute_return=None,
            path_range=None,
        )
    window = rows[baseline_index + 1 : end + 1]
    forward_close = float(rows[end]["close"])
    directional = forward_close / baseline - 1.0
    return PriceLabel(
        family_key=family_key,
        event_key=event_key,
        symbol=symbol,
        baseline_date=rows[baseline_index]["date"].isoformat(),
        baseline_close=baseline,
        horizon_days=horizon,
        forward_close=forward_close,
        directional_return=directional,
        absolute_return=abs(directional),
        path_range=max(float(row["high"]) for row in window) / baseline - min(float(row["low"]) for row in window) / baseline,
    )


def _control_label_for(
    *,
    family_key: str,
    event_key: str,
    symbol: str,
    rows: Sequence[Mapping[str, Any]],
    baseline_index: int,
    horizon: int,
    role: str,
) -> ControlLabel | None:
    label = _price_label_for(
        family_key=family_key,
        event_key=event_key,
        symbol=symbol,
        rows=rows,
        baseline_index=baseline_index,
        horizon=horizon,
    )
    if label is None or label.forward_close is None or label.directional_return is None or label.absolute_return is None or label.path_range is None:
        return None
    return ControlLabel(
        family_key=family_key,
        event_key=event_key,
        symbol=symbol,
        control_date=label.baseline_date,
        horizon_days=horizon,
        baseline_close=label.baseline_close,
        forward_close=label.forward_close,
        directional_return=label.directional_return,
        absolute_return=label.absolute_return,
        path_range=label.path_range,
        control_role=role,
    )


def _bar_rows(data_root: Path, symbol: str, month: str) -> list[dict[str, Any]]:
    path = _bar_path(data_root, symbol, month)
    if path is None:
        return []
    return _daily_bars(path)


def _labels_and_controls(
    *,
    data_root: Path,
    events: Sequence[CandidateEvent],
    price_symbols: Sequence[str],
    horizons: Sequence[int],
    control_window_days: int,
) -> tuple[list[PriceLabel], list[ControlLabel], list[EventControlComparison]]:
    event_labels: list[PriceLabel] = []
    control_labels: list[ControlLabel] = []
    comparisons: list[EventControlComparison] = []
    bars_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}

    for event in events:
        event_day = _parse_date(event.event_time)
        month = _event_month(event)
        for symbol in price_symbols:
            rows = bars_by_key.setdefault((symbol, month), _bar_rows(data_root, symbol, month))
            if not rows:
                continue
            event_index = _baseline_index(rows, event_day)
            if event_index is None:
                continue
            for horizon in horizons:
                event_label = _price_label_for(
                    family_key=event.family_key,
                    event_key=event.event_key,
                    symbol=symbol,
                    rows=rows,
                    baseline_index=event_index,
                    horizon=horizon,
                )
                if event_label is not None:
                    event_labels.append(event_label)
                local_controls: list[ControlLabel] = []
                start = max(0, event_index - control_window_days)
                stop = min(len(rows) - horizon, event_index + control_window_days + 1)
                for control_index in range(start, stop):
                    if control_index == event_index:
                        continue
                    role = "pre_event_control" if control_index < event_index else "post_event_control"
                    control = _control_label_for(
                        family_key=event.family_key,
                        event_key=event.event_key,
                        symbol=symbol,
                        rows=rows,
                        baseline_index=control_index,
                        horizon=horizon,
                        role=role,
                    )
                    if control is not None:
                        local_controls.append(control)
                control_labels.extend(local_controls)
                control_returns = [item.directional_return for item in local_controls]
                event_return = event_label.directional_return if event_label is not None else None
                if event_return is None:
                    status = "blocked_missing_forward_event_label"
                    control_mean = None
                    control_stdev = None
                    diff = None
                    z_score = None
                elif not control_returns:
                    status = "blocked_missing_control_labels"
                    control_mean = None
                    control_stdev = None
                    diff = None
                    z_score = None
                else:
                    control_mean = mean(control_returns)
                    control_stdev = pstdev(control_returns) if len(control_returns) > 1 else 0.0
                    diff = event_return - control_mean
                    z_score = diff / control_stdev if control_stdev else None
                    status = "comparison_available"
                comparisons.append(
                    EventControlComparison(
                        family_key=event.family_key,
                        event_key=event.event_key,
                        symbol=symbol,
                        horizon_days=horizon,
                        event_return=event_return,
                        control_count=len(local_controls),
                        control_mean_return=control_mean,
                        control_stdev_return=control_stdev,
                        event_minus_control_mean=diff,
                        z_score_vs_controls=z_score,
                        comparison_status=status,
                    )
                )
    return event_labels, control_labels, comparisons


def _status(
    *,
    month_count: int,
    event_count: int,
    event_label_count: int,
    comparison_count: int,
) -> tuple[str, str, tuple[str, ...]]:
    blockers: list[str] = []
    if month_count < MIN_EVENT_MONTHS_FOR_STUDY:
        blockers.append("insufficient_local_cpi_calendar_months")
    if event_count < MIN_EVENT_MONTHS_FOR_STUDY:
        blockers.append("insufficient_cpi_event_count")
    if event_label_count < MIN_EVENT_LABELS_FOR_STUDY:
        blockers.append("insufficient_event_price_label_count")
    if comparison_count == 0:
        blockers.append("missing_matched_control_comparisons")
    blockers.extend(
        [
            "needs_official_source_canonicalization",
            "needs_market_sector_target_state_controls",
            "needs_preaccepted_surprise_definition",
        ]
    )
    if event_count and comparison_count:
        readiness = "local_event_labels_and_controls_available_but_underpowered"
        study_status = "underpowered_cpi_scouting_only"
    elif event_count:
        readiness = "local_events_available_but_controls_missing"
        study_status = "blocked_missing_control_comparisons"
    else:
        readiness = "blocked_missing_local_cpi_events"
        study_status = "blocked_missing_local_cpi_calendar_events"
    return readiness, study_status, tuple(dict.fromkeys(blockers))


def build_cpi_inflation_association_readiness(
    *,
    data_root: Path = DEFAULT_DATA_ROOT,
    price_symbols: Sequence[str] = DEFAULT_PRICE_SYMBOLS,
    horizons: Sequence[int] = DEFAULT_HORIZONS,
    control_window_days: int = DEFAULT_CONTROL_WINDOW_DAYS,
    generated_at_utc: str | None = None,
) -> CpiAssociationReadiness:
    months = _calendar_months(data_root)
    events: list[CandidateEvent] = []
    for month in months:
        events.extend(_cpi_events_for_month(data_root, month))
    event_labels, control_labels, comparisons = _labels_and_controls(
        data_root=data_root,
        events=events,
        price_symbols=price_symbols,
        horizons=horizons,
        control_window_days=control_window_days,
    )
    readiness, study_status, blockers = _status(
        month_count=len(months),
        event_count=len(events),
        event_label_count=len([item for item in event_labels if item.directional_return is not None]),
        comparison_count=len([item for item in comparisons if item.comparison_status == "comparison_available"]),
    )
    return CpiAssociationReadiness(
        contract_type=CONTRACT_TYPE,
        generated_at_utc=generated_at_utc or datetime.now(UTC).isoformat(),
        calendar_months_available=months,
        price_symbols=tuple(price_symbols),
        horizons=tuple(horizons),
        event_count=len(events),
        event_label_count=len(event_labels),
        control_label_count=len(control_labels),
        comparison_count=len(comparisons),
        readiness_status=readiness,
        association_study_status=study_status,
        blocker_codes=blockers,
        candidate_events=tuple(events),
        event_labels=tuple(event_labels),
        control_labels=tuple(control_labels),
        comparisons=tuple(comparisons),
    )


def write_readiness_artifacts(readiness: CpiAssociationReadiness, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "cpi_inflation_association_readiness.json").write_text(
        json.dumps(readiness.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "cpi_inflation_association_summary.json").write_text(
        json.dumps(readiness.summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_csv(
        output_dir / "cpi_inflation_events.csv",
        [item.to_row() for item in readiness.candidate_events],
        fieldnames=list(CandidateEvent("", "", "", "", "", "", "", "", "", "").to_row().keys()),
    )
    _write_csv(
        output_dir / "cpi_inflation_event_labels.csv",
        [item.to_row() for item in readiness.event_labels],
        fieldnames=list(PriceLabel("", "", "", "", 0.0, 0, None, None, None, None).to_row().keys()),
    )
    _write_csv(
        output_dir / "cpi_inflation_control_labels.csv",
        [item.to_row() for item in readiness.control_labels],
        fieldnames=list(ControlLabel("", "", "", "", 0, 0.0, 0.0, 0.0, 0.0, 0.0, "").to_row().keys()),
    )
    _write_csv(
        output_dir / "cpi_inflation_event_control_comparisons.csv",
        [item.to_row() for item in readiness.comparisons],
        fieldnames=list(EventControlComparison("", "", "", 0, None, 0, None, None, None, None, "").to_row().keys()),
    )
    (output_dir / "README.md").write_text(
        f"""# CPI inflation association readiness

Contract: `{readiness.contract_type}`

This artifact scans already-local Trading Economics calendar and Alpaca ETF bar artifacts for the `cpi_inflation_release` event family.

- Calendar months available: {len(readiness.calendar_months_available)} ({', '.join(readiness.calendar_months_available) or 'none'})
- CPI event clocks: {readiness.event_count}
- Event labels: {readiness.event_label_count}
- Control labels: {readiness.control_label_count}
- Event/control comparisons: {readiness.comparison_count}
- Readiness status: `{readiness.readiness_status}`
- Association study status: `{readiness.association_study_status}`
- Provider calls: {readiness.provider_calls}
- Model activation performed: {readiness.model_activation_performed}
- Broker execution performed: {readiness.broker_execution_performed}
- Account mutation performed: {readiness.account_mutation_performed}
- Artifact deletion performed: {readiness.artifact_deletion_performed}

This is scouting/readiness only. It is not a directional-alpha, risk-promotion, or model-activation artifact.
""",
        encoding="utf-8",
    )


def write_readiness(readiness: CpiAssociationReadiness, *, output: TextIO) -> None:
    json.dump(readiness.to_dict(), output, indent=2, sort_keys=True)
    output.write("\n")


__all__ = [
    "CpiAssociationReadiness",
    "ControlLabel",
    "EventControlComparison",
    "build_cpi_inflation_association_readiness",
    "write_readiness",
    "write_readiness_artifacts",
]
