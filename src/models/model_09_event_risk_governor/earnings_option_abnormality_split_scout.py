"""Earnings/guidance plus option-abnormality split scout.

This diagnostic performs no provider calls. It joins canonical earnings-calendar
shells to an already-reviewed option-abnormality evidence artifact and records
whether the available artifact can support the requested comparison:

- earnings/guidance with verified option abnormality;
- earnings/guidance with verified no option abnormality.

If the reviewed option artifact does not cover an earnings date, the row stays
`not_option_covered`. If all covered earnings rows have abnormal option events,
the amplifier comparison remains blocked rather than inferred.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HORIZONS = (1, 5, 10, 14)
METRICS = ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae")


@dataclass(frozen=True)
class EarningsOptionSplitInputs:
    canonical_earnings_path: Path
    option_events_path: Path
    option_report_path: Path
    output_dir: Path


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


def _load_option_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _option_events_by_key(option_events: Sequence[Mapping[str, str]]) -> dict[tuple[str, str], list[Mapping[str, str]]]:
    out: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in option_events:
        out[(str(row.get("symbol") or "").upper(), str(row.get("event_date") or ""))].append(row)
    return dict(out)


def _coverage_symbols(option_events: Sequence[Mapping[str, str]]) -> set[str]:
    return {str(row.get("symbol") or "").upper() for row in option_events if row.get("symbol")}


def _representative_event_values(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    if not rows:
        return values
    row = rows[0]
    for horizon in HORIZONS:
        values[f"event_abs_fwd_{horizon}d"] = _fnum(row.get(f"underlying_abs_fwd_{horizon}d"))
        values[f"event_directional_fwd_{horizon}d"] = _fnum(row.get(f"underlying_fwd_{horizon}d"))
        values[f"event_path_range_{horizon}d"] = _fnum(row.get(f"underlying_path_range_{horizon}d"))
        values[f"event_mfe_{horizon}d"] = _fnum(row.get(f"underlying_mfe_{horizon}d"))
        values[f"event_mae_{horizon}d"] = _fnum(row.get(f"underlying_mae_{horizon}d"))
    return values


def run_earnings_option_split_scout(inputs: EarningsOptionSplitInputs) -> dict[str, Any]:
    earnings = _read_csv(inputs.canonical_earnings_path)
    option_events = _read_csv(inputs.option_events_path)
    option_report = _load_option_report(inputs.option_report_path)
    requested_dates = set(option_report.get("event_dates_requested") or [])
    covered_symbols = _coverage_symbols(option_events)
    by_key = _option_events_by_key(option_events)

    rows: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []
    for event in earnings:
        symbol = str(event.get("symbol") or "").upper()
        event_date = str(event.get("event_date") or "")
        option_covered = symbol in covered_symbols and event_date in requested_dates
        events = by_key.get((symbol, event_date), []) if option_covered else []
        complete_events = [row for row in events if str(row.get("coverage_status") or "") == "complete"]
        if not option_covered:
            split_status = "not_option_covered"
        elif complete_events:
            split_status = "earnings_with_verified_option_abnormality"
        else:
            split_status = "earnings_with_verified_no_option_abnormality"
        representative = _representative_event_values(complete_events or events)
        row = {
            "symbol": symbol,
            "event_date": event_date,
            "event_id": event.get("event_id"),
            "event_name": event.get("event_name"),
            "option_coverage_verified": option_covered,
            "split_status": split_status,
            "option_event_count": len(events),
            "complete_option_event_count": len(complete_events),
            "direction_hypothesis_count": len({row.get("direction_hypothesis") for row in complete_events if row.get("direction_hypothesis")}),
            **representative,
        }
        rows.append(row)
        counts: dict[str, int] = defaultdict(int)
        for option_event in complete_events:
            counts[str(option_event.get("direction_hypothesis") or "missing")] += 1
        for direction, count in sorted(counts.items()):
            direction_rows.append({"symbol": symbol, "event_date": event_date, "direction_hypothesis": direction, "complete_event_count": count})

    groups: list[dict[str, Any]] = []
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_status[str(row["split_status"])].append(row)
    for status, items in sorted(by_status.items()):
        item: dict[str, Any] = {"group": status, "n_events": len(items), "n_symbols": len({row["symbol"] for row in items})}
        for horizon in HORIZONS:
            for metric in METRICS:
                key = f"event_{metric}_{horizon}d"
                item[f"avg_{key}"] = _avg(_fnum(row.get(key)) for row in items)
                item[f"positive_rate_{key}"] = _hit(_fnum(row.get(key)) for row in items)
        groups.append(item)

    with_abnormality = len(by_status.get("earnings_with_verified_option_abnormality", []))
    without_abnormality = len(by_status.get("earnings_with_verified_no_option_abnormality", []))
    if with_abnormality and without_abnormality:
        status = "diagnostic_split_available_not_promotion_evidence"
    elif with_abnormality and not without_abnormality:
        status = "blocked_no_verified_earnings_without_option_abnormality_controls"
    else:
        status = "blocked_no_verified_earnings_with_option_abnormality_rows"

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_option_abnormality_split_rows.csv", rows)
    _write_csv(inputs.output_dir / "earnings_option_abnormality_direction_counts.csv", direction_rows)
    _write_csv(inputs.output_dir / "earnings_option_abnormality_group_stats.csv", groups)
    report = {
        "schema": "earnings_option_abnormality_split_scout_v1",
        "status": status,
        "provider_calls_performed_by_study": 0,
        "canonical_earnings_count": len(rows),
        "option_covered_earnings_count": sum(1 for row in rows if row["option_coverage_verified"]),
        "earnings_with_verified_option_abnormality_count": with_abnormality,
        "earnings_with_verified_no_option_abnormality_count": without_abnormality,
        "not_option_covered_count": len(by_status.get("not_option_covered", [])),
        "option_source_event_dates_requested": sorted(requested_dates),
        "interpretation": [
            "Existing reviewed option matrix coverage overlaps only part of the canonical earnings shell set.",
            "The available overlap contains earnings rows with verified option abnormality but no earnings rows with verified no-option-abnormality controls.",
            "Do not claim an earnings+option amplifier edge until matched earnings-without-option-abnormality controls are acquired or verified.",
        ],
        "group_stats": groups,
    }
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance + option-abnormality split scout

This artifact joins canonical earnings shells to reviewed complete-evidence option abnormality events.

- Canonical earnings events: {len(rows)}
- Option-covered earnings events: {report['option_covered_earnings_count']}
- Earnings with verified option abnormality: {with_abnormality}
- Earnings with verified no-option-abnormality controls: {without_abnormality}
- Status: `{status}`

This is diagnostic only. The amplifier comparison is blocked until verified earnings-without-option-abnormality controls exist.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["EarningsOptionSplitInputs", "run_earnings_option_split_scout"]
