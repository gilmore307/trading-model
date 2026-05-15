"""Event-alone earnings/guidance scheduled-shell scouting study.

This module performs no provider calls. It consumes reviewed local artifacts:

- Nasdaq earnings-calendar `release_calendar.csv` rows already acquired by
  `trading-execution` calendar discovery;
- daily `equity_bar.csv` rows already acquired by `trading-data`.

It tests whether canonical earnings-calendar shells, by themselves, are
associated with forward direction-neutral price/path expansion versus
same-symbol non-earnings controls. Calendar shells are scheduling facts only;
result/guidance interpretation remains a later artifact family.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from models.model_04_event_overlay.earnings_guidance_scouting import load_calendar_events


HORIZONS = (1, 5, 10, 14)
CONTROL_EXCLUSION_DAYS = 3
DEFAULT_MAX_CONTROLS = 3


@dataclass(frozen=True)
class EventAloneInputs:
    calendar_paths: tuple[Path, ...]
    equity_bar_paths: tuple[Path, ...]
    output_dir: Path
    target_symbols: tuple[str, ...]
    max_controls_per_event: int = DEFAULT_MAX_CONTROLS
    control_exclusion_days: int = CONTROL_EXCLUSION_DAYS


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _fnum(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(xs) / len(xs) if xs else None


def _hit(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(1 for value in xs if value > 0) / len(xs) if xs else None


def _date(text: str) -> date:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date()


def _bar_date(row: Mapping[str, str]) -> date:
    return _date(str(row["timestamp"]))


def load_equity_bars(paths: Iterable[Path], target_symbols: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
    targets = {symbol.upper() for symbol in target_symbols}
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for path in paths:
        for row in _read_csv(path):
            symbol = str(row.get("symbol") or "").upper()
            if targets and symbol not in targets:
                continue
            timestamp = str(row.get("timestamp") or "")
            key = (symbol, timestamp)
            if key in seen:
                continue
            seen.add(key)
            close = _fnum(row.get("bar_close"))
            high = _fnum(row.get("bar_high"))
            low = _fnum(row.get("bar_low"))
            if close is None or high is None or low is None:
                continue
            by_symbol[symbol].append(
                {
                    "symbol": symbol,
                    "date": _bar_date(row),
                    "timestamp": timestamp,
                    "close": close,
                    "high": high,
                    "low": low,
                }
            )
    for rows in by_symbol.values():
        rows.sort(key=lambda row: row["date"])
    return dict(by_symbol)


def _baseline_index(rows: Sequence[Mapping[str, Any]], event_date: date) -> int | None:
    previous = None
    for idx, row in enumerate(rows):
        if row["date"] >= event_date:
            return previous if previous is not None else idx
        previous = idx
    return previous


def _label(rows: Sequence[Mapping[str, Any]], baseline_index: int) -> dict[str, Any]:
    baseline = float(rows[baseline_index]["close"])
    out: dict[str, Any] = {
        "baseline_date": rows[baseline_index]["date"].isoformat(),
        "baseline_close": baseline,
    }
    for horizon in HORIZONS:
        end_index = baseline_index + horizon
        if end_index >= len(rows):
            out[f"abs_fwd_{horizon}d"] = None
            out[f"directional_fwd_{horizon}d"] = None
            out[f"path_range_{horizon}d"] = None
            out[f"mfe_{horizon}d"] = None
            out[f"mae_{horizon}d"] = None
            continue
        window = rows[baseline_index + 1 : end_index + 1]
        forward_close = float(rows[end_index]["close"])
        max_high = max(float(row["high"]) for row in window)
        min_low = min(float(row["low"]) for row in window)
        directional = forward_close / baseline - 1.0
        mfe = max_high / baseline - 1.0
        mae = min_low / baseline - 1.0
        out[f"abs_fwd_{horizon}d"] = abs(directional)
        out[f"directional_fwd_{horizon}d"] = directional
        out[f"path_range_{horizon}d"] = mfe - mae
        out[f"mfe_{horizon}d"] = mfe
        out[f"mae_{horizon}d"] = mae
    return out


def _near_event(candidate: date, event_dates: Sequence[date], exclusion_days: int) -> bool:
    return any(abs((candidate - event_date).days) <= exclusion_days for event_date in event_dates)


def _select_controls(
    rows: Sequence[Mapping[str, Any]],
    *,
    event_date: date,
    event_dates: Sequence[date],
    exclusion_days: int,
    max_controls: int,
) -> list[int]:
    candidates: list[tuple[int, int, bool]] = []
    for idx, row in enumerate(rows):
        candidate_date = row["date"]
        if _near_event(candidate_date, event_dates, exclusion_days):
            continue
        if idx + max(HORIZONS) >= len(rows):
            continue
        distance = abs((candidate_date - event_date).days)
        if distance == 0 or distance > 60:
            continue
        same_weekday = candidate_date.weekday() == event_date.weekday()
        candidates.append((idx, distance, same_weekday))
    same_weekday = [item for item in candidates if item[2]]
    pool = same_weekday if len(same_weekday) >= max_controls else candidates
    pool.sort(key=lambda item: (item[1], rows[item[0]]["date"]))
    return [idx for idx, _, _ in pool[:max_controls]]


def _prefix(prefix: str, row: Mapping[str, Any]) -> dict[str, Any]:
    return {f"{prefix}_{key}": value for key, value in row.items() if key not in {"baseline_date", "baseline_close"}}


def build_event_and_control_windows(inputs: EventAloneInputs) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    calendar_events = load_calendar_events(inputs.calendar_paths, inputs.target_symbols)
    bars = load_equity_bars(inputs.equity_bar_paths, inputs.target_symbols)
    event_dates_by_symbol: dict[str, list[date]] = defaultdict(list)
    for event in calendar_events:
        event_dates_by_symbol[str(event["symbol"])].append(_date(str(event["event_date"])))

    event_windows: list[dict[str, Any]] = []
    control_windows: list[dict[str, Any]] = []
    pair_rows: list[dict[str, Any]] = []
    for event in calendar_events:
        symbol = str(event["symbol"])
        rows = bars.get(symbol, [])
        event_date = _date(str(event["event_date"]))
        baseline_index = _baseline_index(rows, event_date) if rows else None
        if baseline_index is None or baseline_index + max(HORIZONS) >= len(rows):
            continue
        event_label = _label(rows, baseline_index)
        event_row = {
            "symbol": symbol,
            "event_date": event_date.isoformat(),
            "event_name": event.get("event_name", ""),
            "event_id": event.get("event_id", ""),
            "event_phase": event.get("event_phase", "scheduled_shell"),
            "lifecycle_class": event.get("lifecycle_class", "scheduled_known_outcome_later"),
            "baseline_date": event_label["baseline_date"],
            "baseline_close": event_label["baseline_close"],
            **_prefix("event", event_label),
        }
        event_windows.append(event_row)
        controls = _select_controls(
            rows,
            event_date=event_date,
            event_dates=event_dates_by_symbol[symbol],
            exclusion_days=inputs.control_exclusion_days,
            max_controls=inputs.max_controls_per_event,
        )
        control_labels = []
        for control_index in controls:
            control_label = _label(rows, control_index)
            control_row = {
                "symbol": symbol,
                "event_date": event_date.isoformat(),
                "control_date": control_label["baseline_date"],
                "event_id": event.get("event_id", ""),
                "control_type": "same_symbol_verified_non_earnings_calendar_shell",
                "baseline_close": control_label["baseline_close"],
                **_prefix("control", control_label),
            }
            control_windows.append(control_row)
            control_labels.append(control_label)
        pair: dict[str, Any] = {
            "symbol": symbol,
            "event_date": event_date.isoformat(),
            "event_id": event.get("event_id", ""),
            "event_name": event.get("event_name", ""),
            "control_count": len(control_labels),
            "event_baseline_date": event_label["baseline_date"],
        }
        for horizon in HORIZONS:
            for metric in ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae"):
                event_value = _fnum(event_label.get(f"{metric}_{horizon}d"))
                control_avg = _avg(_fnum(label.get(f"{metric}_{horizon}d")) for label in control_labels)
                pair[f"event_{metric}_{horizon}d"] = event_value
                pair[f"control_avg_{metric}_{horizon}d"] = control_avg
                pair[f"delta_{metric}_{horizon}d"] = None if event_value is None or control_avg is None else event_value - control_avg
        pair_rows.append(pair)
    return event_windows, control_windows, pair_rows


def _group(pair_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = [row for row in pair_rows if int(row.get("control_count") or 0) > 0]
    item: dict[str, Any] = {
        "sample": "earnings_guidance_scheduled_shell_event_alone",
        "n_events": len(rows),
        "n_symbols": len({row.get("symbol") for row in rows}),
        "avg_control_count": _avg(_fnum(row.get("control_count")) for row in rows),
    }
    for horizon in HORIZONS:
        for metric in ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae"):
            deltas = [_fnum(row.get(f"delta_{metric}_{horizon}d")) for row in rows]
            item[f"avg_delta_{metric}_{horizon}d"] = _avg(deltas)
            item[f"positive_delta_rate_{metric}_{horizon}d"] = _hit(deltas)
            item[f"event_avg_{metric}_{horizon}d"] = _avg(_fnum(row.get(f"event_{metric}_{horizon}d")) for row in rows)
            item[f"control_avg_{metric}_{horizon}d"] = _avg(_fnum(row.get(f"control_avg_{metric}_{horizon}d")) for row in rows)
    return [item]


def run_event_alone_study(inputs: EventAloneInputs) -> dict[str, Any]:
    event_windows, control_windows, pair_rows = build_event_and_control_windows(inputs)
    group_stats = _group(pair_rows)
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_event_windows.csv", event_windows)
    _write_csv(inputs.output_dir / "earnings_guidance_event_controls.csv", control_windows)
    _write_csv(inputs.output_dir / "earnings_guidance_event_control_pairs.csv", pair_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_event_alone_group_stats.csv", group_stats)
    report = {
        "schema": "earnings_guidance_event_alone_scouting_study_v1",
        "status": "diagnostic_scouting_not_promotion_evidence",
        "provider_calls_performed_by_study": 0,
        "calendar_artifact_count": len(inputs.calendar_paths),
        "equity_bar_artifact_count": len(inputs.equity_bar_paths),
        "target_symbols": list(inputs.target_symbols),
        "event_window_count": len(event_windows),
        "control_window_count": len(control_windows),
        "paired_event_count": sum(1 for row in pair_rows if int(row.get("control_count") or 0) > 0),
        "group_stats": group_stats,
        "interpretation": [
            "This is an event-alone scheduled-shell test; it does not include official result/guidance interpretation.",
            "Controls are same-symbol dates outside Nasdaq earnings-calendar shell exclusion windows; option-abnormality absence is not verified in this study.",
            "Use this only as the first earnings/guidance family scout before adding result/guidance interpretation and option-control verification.",
        ],
    }
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance event-alone scouting study

This artifact tests canonical Nasdaq earnings-calendar shells against same-symbol non-earnings controls using daily equity bars.

- Events: {len(event_windows)}
- Controls: {len(control_windows)}
- Paired events: {report['paired_event_count']}

This is diagnostic scouting only. Calendar shells contain no result/guidance facts, and option-abnormality absence is not verified for controls.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["EventAloneInputs", "load_equity_bars", "build_event_and_control_windows", "run_event_alone_study"]
