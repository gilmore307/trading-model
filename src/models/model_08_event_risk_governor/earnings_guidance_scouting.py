"""Earnings/guidance scouting controls for event-risk layer research.

This module performs no provider calls. It consumes reviewed local artifacts:

- matched option-abnormality windows and controls;
- Nasdaq earnings-calendar `release_calendar.csv` rows already acquired by
  `trading-execution` calendar discovery.

The output is diagnostic scouting evidence only. It is not model promotion,
training data activation, or an event-risk intervention.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


TARGET_SYMBOLS_DEFAULT = ("AAPL", "MSFT", "NVDA", "AMD", "JPM", "XOM", "CVX", "LLY", "PFE", "COIN", "TSLA", "RKLB")
HORIZONS = ("1d", "5d", "10d", "14d")
METRICS = ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae")


@dataclass(frozen=True)
class StudyInputs:
    abnormal_windows_path: Path
    control_windows_path: Path
    calendar_paths: tuple[Path, ...]
    output_dir: Path
    target_symbols: tuple[str, ...] = TARGET_SYMBOLS_DEFAULT


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


def _date_from_iso(text: str) -> str:
    if not text:
        return ""
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return text[:10]


def _calendar_symbol(event_name: str) -> str:
    return str(event_name or "").split(" ", 1)[0].strip().upper()


def load_calendar_events(paths: Iterable[Path], target_symbols: Iterable[str]) -> list[dict[str, Any]]:
    targets = {symbol.upper() for symbol in target_symbols}
    events: list[dict[str, Any]] = []
    for path in paths:
        for row in _read_csv(path):
            if row.get("calendar_source") != "nasdaq_earnings_calendar":
                continue
            symbol = _calendar_symbol(row.get("event_name", ""))
            if targets and symbol not in targets:
                continue
            release_time = row.get("release_time", "")
            events.append(
                {
                    "symbol": symbol,
                    "event_date": _date_from_iso(release_time),
                    "release_time": release_time,
                    "event_name": row.get("event_name", ""),
                    "event_id": row.get("event_id", ""),
                    "calendar_source": row.get("calendar_source", ""),
                    "source_url": row.get("source_url", ""),
                    "event_phase": "scheduled_shell",
                    "lifecycle_class": "scheduled_known_outcome_later",
                    "result_fields": "not_available_from_calendar_shell",
                    "source_priority": "approved_calendar",
                    "source_artifact_path": str(path),
                }
            )
    events.sort(key=lambda row: (row["event_date"], row["symbol"], row["event_name"]))
    return events


def _calendar_index(events: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    return {(str(row.get("symbol") or "").upper(), str(row.get("event_date") or "")) for row in events}


def _recompute_window_pairs(abnormal_rows: Sequence[Mapping[str, str]], control_rows: Sequence[Mapping[str, str]], calendar_index: set[tuple[str, str]]) -> list[dict[str, Any]]:
    controls_by_window: dict[tuple[str, str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in control_rows:
        key = (row["symbol"].upper(), row["event_date"], row["direction_hypothesis"])
        controls_by_window[key].append(row)

    out: list[dict[str, Any]] = []
    for event in abnormal_rows:
        symbol = event["symbol"].upper()
        event_date = event["event_date"]
        direction = event["direction_hypothesis"]
        key = (symbol, event_date, direction)
        candidate_controls = controls_by_window.get(key, [])
        verified_non_earnings_controls = [row for row in candidate_controls if (symbol, row.get("control_date", "")) not in calendar_index]
        earnings_control_dates = sorted({row.get("control_date", "") for row in candidate_controls if (symbol, row.get("control_date", "")) in calendar_index})
        row: dict[str, Any] = {
            "symbol": symbol,
            "event_date": event_date,
            "direction_hypothesis": direction,
            "direction_sign": event.get("direction_sign", ""),
            "event_count": event.get("event_count", ""),
            "event_has_canonical_earnings_shell": (symbol, event_date) in calendar_index,
            "verified_non_earnings_control_count": len(verified_non_earnings_controls),
            "candidate_control_count": len(candidate_controls),
            "candidate_earnings_control_count": len(candidate_controls) - len(verified_non_earnings_controls),
            "candidate_earnings_control_dates": ";".join(earnings_control_dates),
            "control_verification_scope": "nasdaq_earnings_calendar_dates_only",
            "no_option_abnormality_controls_verified": False,
        }
        for horizon in HORIZONS:
            for metric in METRICS:
                event_value = _fnum(event.get(f"event_{metric}_{horizon}"))
                control_values = [_fnum(control.get(f"control_{metric}_{horizon}")) for control in verified_non_earnings_controls]
                control_avg = _avg(control_values)
                row[f"event_{metric}_{horizon}"] = event_value
                row[f"verified_control_avg_{metric}_{horizon}"] = control_avg
                row[f"delta_{metric}_{horizon}"] = None if event_value is None or control_avg is None else event_value - control_avg
        out.append(row)
    return out


def _group(rows: Sequence[Mapping[str, Any]], fields: Sequence[str], sample: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field) for field in fields)].append(row)
    out: list[dict[str, Any]] = []
    for key, group_rows in sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0])):
        item: dict[str, Any] = {
            "sample": sample,
            "n_windows": len(group_rows),
            "n_symbols": len({row.get("symbol") for row in group_rows}),
            "n_event_count_sum": sum(int(float(row.get("event_count") or 0)) for row in group_rows),
            "avg_verified_non_earnings_control_count": _avg([_fnum(row.get("verified_non_earnings_control_count")) for row in group_rows]),
            "windows_with_verified_non_earnings_controls": sum(1 for row in group_rows if int(row.get("verified_non_earnings_control_count") or 0) > 0),
        }
        item.update({field: value for field, value in zip(fields, key)})
        for horizon in ("5d", "10d", "14d"):
            for metric in ("abs_fwd", "directional_fwd", "path_range"):
                deltas = [_fnum(row.get(f"delta_{metric}_{horizon}")) for row in group_rows]
                item[f"avg_delta_{metric}_{horizon}"] = _avg(deltas)
                item[f"positive_delta_rate_{metric}_{horizon}"] = _hit(deltas)
                item[f"event_avg_{metric}_{horizon}"] = _avg([_fnum(row.get(f"event_{metric}_{horizon}")) for row in group_rows])
                item[f"verified_control_avg_{metric}_{horizon}"] = _avg([_fnum(row.get(f"verified_control_avg_{metric}_{horizon}")) for row in group_rows])
        out.append(item)
    return out


def run_study(inputs: StudyInputs) -> dict[str, Any]:
    abnormal_rows = _read_csv(inputs.abnormal_windows_path)
    control_rows = _read_csv(inputs.control_windows_path)
    calendar_events = load_calendar_events(inputs.calendar_paths, inputs.target_symbols)
    calendar_idx = _calendar_index(calendar_events)
    pairs = _recompute_window_pairs(abnormal_rows, control_rows, calendar_idx)
    group_stats: list[dict[str, Any]] = []
    group_stats.extend(_group(pairs, ["event_has_canonical_earnings_shell"], "by_canonical_earnings_shell"))
    group_stats.extend(_group(pairs, ["event_has_canonical_earnings_shell", "direction_hypothesis"], "by_canonical_earnings_shell_and_direction"))

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "canonical_earnings_calendar_events.csv", calendar_events)
    _write_csv(inputs.output_dir / "earnings_guidance_window_pairs.csv", pairs)
    _write_csv(inputs.output_dir / "earnings_guidance_group_stats.csv", group_stats)

    by_shell = {str(row.get("event_has_canonical_earnings_shell")): row for row in group_stats if row["sample"] == "by_canonical_earnings_shell"}
    shell_true = by_shell.get("True")
    shell_false = by_shell.get("False")
    report = {
        "schema": "earnings_guidance_event_family_scouting_study_v1",
        "status": "diagnostic_scouting_not_promotion_evidence",
        "provider_calls_performed_by_study": 0,
        "source_abnormal_windows": str(inputs.abnormal_windows_path),
        "source_control_windows": str(inputs.control_windows_path),
        "source_calendar_artifacts": [str(path) for path in inputs.calendar_paths],
        "target_symbols": list(inputs.target_symbols),
        "calendar_event_count": len(calendar_events),
        "abnormal_window_count": len(pairs),
        "canonical_earnings_shell_window_count": sum(1 for row in pairs if row["event_has_canonical_earnings_shell"]),
        "verified_non_earnings_control_window_count": sum(1 for row in pairs if int(row["verified_non_earnings_control_count"] or 0) > 0),
        "group_stats": group_stats,
        "headline": {
            "canonical_earnings_shell": shell_true,
            "non_earnings_event_dates": shell_false,
        },
        "interpretation": [
            "Canonical Nasdaq earnings-calendar shells are sparse in the tested option-abnormality event dates.",
            "The canonical earnings-shell slice is useful as an event-family scout but remains far below coverage gates and cannot promote EventRiskGovernor behavior.",
            "Verified non-earnings controls can now be separated by calendar shell, but no-option-abnormality controls remain unverified until option-event feeds are queried for control dates.",
        ],
        "promotion_boundary": "Scouting evidence only. Calendar shells do not contain result/guidance facts, SEC/company result interpretation is not yet joined, and no-option-abnormality controls are not independently verified.",
    }
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme = f"""# Earnings/guidance event-family scouting study

This artifact reruns the event-risk amplifier question using canonical Nasdaq earnings-calendar shells instead of Alpaca headline-keyword family labels.

## Inputs

- Abnormal option windows: `{inputs.abnormal_windows_path}`
- Matched controls: `{inputs.control_windows_path}`
- Calendar artifacts: `{len(inputs.calendar_paths)}` reviewed `release_calendar.csv` files

## Result

- Calendar events for target symbols: {len(calendar_events)}
- Abnormal windows tested: {len(pairs)}
- Windows on canonical earnings-shell dates: {report['canonical_earnings_shell_window_count']}
- Windows with verified non-earnings controls: {report['verified_non_earnings_control_window_count']}

This remains diagnostic only. It proves the shell/result/control separation can be enforced, but does not yet prove an event-layer model edge.
"""
    (inputs.output_dir / "README.md").write_text(readme, encoding="utf-8")
    return report


__all__ = ["StudyInputs", "load_calendar_events", "run_study"]
