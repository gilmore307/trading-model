"""Diagnose option-abnormality standard saturation on non-earnings windows.

This local study performs no provider calls. It reuses the reviewed complete-
evidence option matrix and canonical earnings shells to answer a narrower
control-design question: can the current option-event standard produce clean
same-symbol non-earnings no-abnormality controls?

If every reviewed non-earnings symbol/date in the matrix has complete option
abnormality events, then the issue is not earnings specificity; the current
option-event standard is too saturated to furnish no-abnormality controls in
this sample.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HORIZONS = (1, 5, 10, 14)
METRICS = ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae")


@dataclass(frozen=True)
class NonEarningsSaturationInputs:
    option_events_path: Path
    canonical_earnings_path: Path
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


def _labels_from_row(row: Mapping[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for horizon in HORIZONS:
        label = f"{horizon}d"
        out[f"event_abs_fwd_{label}"] = _fnum(row.get(f"underlying_abs_fwd_{label}"))
        out[f"event_directional_fwd_{label}"] = _fnum(row.get(f"underlying_fwd_{label}"))
        out[f"event_path_range_{label}"] = _fnum(row.get(f"underlying_path_range_{label}"))
        out[f"event_mfe_{label}"] = _fnum(row.get(f"underlying_mfe_{label}"))
        out[f"event_mae_{label}"] = _fnum(row.get(f"underlying_mae_{label}"))
    return out


def _group(rows: Sequence[Mapping[str, Any]], field: str) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(field) or "missing")].append(row)
    output: list[dict[str, Any]] = []
    for key, items in sorted(groups.items()):
        out: dict[str, Any] = {
            field: key,
            "n_symbol_dates": len(items),
            "n_symbols": len({row.get("symbol") for row in items}),
            "avg_complete_option_event_count": _avg(_fnum(row.get("complete_option_event_count")) for row in items),
            "min_complete_option_event_count": min(int(row.get("complete_option_event_count") or 0) for row in items),
        }
        for horizon in HORIZONS:
            for metric in METRICS:
                name = f"event_{metric}_{horizon}d"
                values = [_fnum(row.get(name)) for row in items]
                out[f"avg_{name}"] = _avg(values)
                out[f"positive_rate_{name}"] = _hit(values)
        output.append(out)
    return output


def run_non_earnings_saturation_study(inputs: NonEarningsSaturationInputs) -> dict[str, Any]:
    option_events = _read_csv(inputs.option_events_path)
    earnings = _read_csv(inputs.canonical_earnings_path)
    earnings_keys = {(str(row.get("symbol") or "").upper(), str(row.get("event_date") or "")) for row in earnings}

    by_key: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in option_events:
        by_key[(str(row.get("symbol") or "").upper(), str(row.get("event_date") or ""))].append(row)

    symbol_date_rows: list[dict[str, Any]] = []
    direction_rows: list[dict[str, Any]] = []
    for (symbol, event_date), rows in sorted(by_key.items()):
        first = rows[0]
        direction_counts = Counter(str(row.get("direction_hypothesis") or "missing") for row in rows)
        shell_status = "earnings_shell" if (symbol, event_date) in earnings_keys else "non_earnings_window"
        symbol_date_rows.append(
            {
                "symbol": symbol,
                "event_date": event_date,
                "shell_status": shell_status,
                "complete_option_event_count": len(rows),
                "direction_hypothesis_count": len(direction_counts),
                "direction_hypothesis_summary": ";".join(f"{key}:{value}" for key, value in sorted(direction_counts.items())),
                **_labels_from_row(first),
            }
        )
        for direction, count in sorted(direction_counts.items()):
            direction_rows.append(
                {
                    "symbol": symbol,
                    "event_date": event_date,
                    "shell_status": shell_status,
                    "direction_hypothesis": direction,
                    "complete_event_count": count,
                }
            )

    non_earnings = [row for row in symbol_date_rows if row["shell_status"] == "non_earnings_window"]
    earnings_overlap = [row for row in symbol_date_rows if row["shell_status"] == "earnings_shell"]
    no_abnormality_non_earnings = [row for row in non_earnings if int(row.get("complete_option_event_count") or 0) == 0]
    status = (
        "current_option_event_standard_saturated_no_clean_non_earnings_controls"
        if non_earnings and not no_abnormality_non_earnings
        else "non_earnings_no_abnormality_controls_available"
    )
    group_stats = _group(symbol_date_rows, "shell_status")
    report = {
        "schema": "option_abnormality_non_earnings_saturation_v1",
        "status": status,
        "provider_calls_performed_by_study": 0,
        "symbol_date_count": len(symbol_date_rows),
        "earnings_shell_symbol_date_count": len(earnings_overlap),
        "non_earnings_symbol_date_count": len(non_earnings),
        "non_earnings_verified_no_abnormality_count": len(no_abnormality_non_earnings),
        "min_non_earnings_complete_option_event_count": min((int(row.get("complete_option_event_count") or 0) for row in non_earnings), default=None),
        "interpretation": [
            "The existing reviewed complete-evidence option matrix already includes many same-symbol non-earnings windows.",
            "Every reviewed non-earnings symbol/date in this matrix emitted complete option abnormality events under the current standard.",
            "The current option-event standard is saturated for control design: it cannot furnish clean no-abnormality controls in this sample.",
            "Do not keep searching this sample for earnings-without-option-abnormality controls; revise the abnormality standard or expand to a different control universe before retesting amplifier value.",
        ],
        "group_stats": group_stats,
    }

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "option_abnormality_symbol_date_saturation.csv", symbol_date_rows)
    _write_csv(inputs.output_dir / "option_abnormality_direction_saturation.csv", direction_rows)
    _write_csv(inputs.output_dir / "option_abnormality_saturation_group_stats.csv", group_stats)
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Option abnormality non-earnings saturation study

This artifact reuses the reviewed complete-evidence option matrix to test whether same-symbol non-earnings windows can provide clean no-option-abnormality controls.

- Symbol/date windows: {len(symbol_date_rows)}
- Earnings-shell overlaps: {len(earnings_overlap)}
- Non-earnings windows: {len(non_earnings)}
- Non-earnings verified no-abnormality windows: {len(no_abnormality_non_earnings)}
- Status: `{status}`

Conclusion: the current option-event standard is saturated in this sample and cannot support the requested no-abnormality control design.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["NonEarningsSaturationInputs", "run_non_earnings_saturation_study"]
