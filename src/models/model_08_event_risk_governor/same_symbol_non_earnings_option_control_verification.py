"""Verify same-symbol non-earnings option-abnormality controls from local option-event receipts.

This bounded diagnostic performs no provider calls. It consumes:

- canonical earnings-calendar shells;
- existing option-event matrix rows with direction-neutral forward labels;
- local option-event completion receipts for sampled same-symbol contract/date probes.

The goal is narrower than an alpha test: determine whether same-symbol non-earnings
windows can supply verified no-option-abnormality controls under the same option-event
standard. If every sampled non-earnings contract/date emits option events, the
amplifier comparison remains blocked rather than inferred.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HORIZONS = ("1d", "5d", "10d", "14d")
METRICS = ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae")


@dataclass(frozen=True)
class SameSymbolNonEarningsOptionControlInputs:
    canonical_earnings_path: Path
    option_matrix_root: Path
    option_events_path: Path
    output_dir: Path
    control_exclusion_days: int = 3


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _fnum(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _avg(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(xs) / len(xs) if xs else None


def _hit(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(1 for value in xs if value > 0) / len(xs) if xs else None


def _parse_date(text: str) -> date | None:
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _date_distance_days(left: str, right: str) -> int | None:
    left_date = _parse_date(left)
    right_date = _parse_date(right)
    if left_date is None or right_date is None:
        return None
    return abs((left_date - right_date).days)


def _receipt_contract_count(receipt: Mapping[str, Any]) -> tuple[str, int]:
    runs = receipt.get("runs")
    run = runs[-1] if isinstance(runs, list) and runs else {}
    status = str(run.get("status") or "missing")
    row_counts = run.get("row_counts") if isinstance(run.get("row_counts"), Mapping) else {}
    count = int(float(row_counts.get("option_activity_event") or 0))
    return status, count


def _iter_contract_receipts(option_matrix_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(option_matrix_root.glob("*/*/*_events/completion_receipt.json")):
        try:
            symbol, event_date, contract_label = path.relative_to(option_matrix_root).parts[:3]
        except ValueError:
            continue
        try:
            receipt = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rows.append(
                {
                    "symbol": symbol.upper(),
                    "event_date": event_date,
                    "contract_label": contract_label,
                    "status": "invalid_receipt_json",
                    "option_event_count": 0,
                    "receipt_path": str(path),
                }
            )
            continue
        status, event_count = _receipt_contract_count(receipt)
        rows.append(
            {
                "symbol": symbol.upper(),
                "event_date": event_date,
                "contract_label": contract_label,
                "status": status,
                "option_event_count": event_count,
                "receipt_path": str(path),
            }
        )
    return rows


def _earnings_by_symbol(earnings: Sequence[Mapping[str, str]]) -> dict[str, list[str]]:
    by_symbol: dict[str, list[str]] = defaultdict(list)
    for row in earnings:
        symbol = str(row.get("symbol") or "").upper()
        event_date = str(row.get("event_date") or "")
        if symbol and event_date:
            by_symbol[symbol].append(event_date)
    return {symbol: sorted(set(dates)) for symbol, dates in by_symbol.items()}


def _nearest_earnings(symbol: str, event_date: str, earnings: Mapping[str, Sequence[str]]) -> tuple[str | None, int | None]:
    candidates: list[tuple[int, str]] = []
    for earnings_date in earnings.get(symbol, []):
        distance = _date_distance_days(event_date, earnings_date)
        if distance is not None:
            candidates.append((distance, earnings_date))
    if not candidates:
        return None, None
    distance, earnings_date = sorted(candidates)[0]
    return earnings_date, distance


def _window_role(distance: int | None, exclusion_days: int) -> str:
    if distance is None:
        return "missing_symbol_earnings_calendar"
    if distance == 0:
        return "exact_earnings_date"
    if distance <= exclusion_days:
        return "earnings_adjacent_excluded"
    return "same_symbol_non_earnings_control_candidate"


def _probe_status(probes: Sequence[Mapping[str, Any]]) -> tuple[str, dict[str, Any]]:
    attempted = len(probes)
    succeeded = sum(1 for row in probes if row.get("status") == "succeeded")
    failed = attempted - succeeded
    option_events = sum(int(float(row.get("option_event_count") or 0)) for row in probes)
    if attempted == 0:
        status = "insufficient_option_abnormality_verification"
    elif option_events and failed:
        status = "partial_contract_coverage_with_verified_option_abnormality"
    elif option_events:
        status = "verified_option_abnormality_sampled_contracts"
    elif failed:
        status = "insufficient_option_abnormality_verification"
    else:
        status = "verified_no_sampled_option_abnormality"
    return status, {
        "attempted_contract_count": attempted,
        "successful_contract_count": succeeded,
        "failed_contract_count": failed,
        "option_event_count": option_events,
    }


def _label_by_symbol_date(option_events: Sequence[Mapping[str, str]]) -> dict[tuple[str, str], dict[str, Any]]:
    labels: dict[tuple[str, str], dict[str, Any]] = {}
    for row in option_events:
        key = (str(row.get("symbol") or "").upper(), str(row.get("event_date") or ""))
        if not key[0] or not key[1] or key in labels:
            continue
        out: dict[str, Any] = {}
        for horizon in HORIZONS:
            out[f"event_abs_fwd_{horizon}"] = _fnum(row.get(f"underlying_abs_fwd_{horizon}"))
            out[f"event_directional_fwd_{horizon}"] = _fnum(row.get(f"underlying_fwd_{horizon}"))
            out[f"event_path_range_{horizon}"] = _fnum(row.get(f"underlying_path_range_{horizon}"))
            out[f"event_mfe_{horizon}"] = _fnum(row.get(f"underlying_mfe_{horizon}"))
            out[f"event_mae_{horizon}"] = _fnum(row.get(f"underlying_mae_{horizon}"))
        labels[key] = out
    return labels


def _complete_event_counts(option_events: Sequence[Mapping[str, str]]) -> dict[tuple[str, str], int]:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for row in option_events:
        if str(row.get("coverage_status") or "") != "complete":
            continue
        symbol = str(row.get("symbol") or "").upper()
        event_date = str(row.get("event_date") or "")
        if symbol and event_date:
            counts[(symbol, event_date)] += 1
    return dict(counts)


def _group(rows: Sequence[Mapping[str, Any]], fields: Sequence[str], sample: str) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row.get(field) for field in fields)].append(row)
    out: list[dict[str, Any]] = []
    for key, items in sorted(grouped.items(), key=lambda item: tuple(str(value) for value in item[0])):
        group_row: dict[str, Any] = {
            "sample": sample,
            "n_windows": len(items),
            "n_symbols": len({row.get("symbol") for row in items}),
            "attempted_contract_count": sum(int(row.get("attempted_contract_count") or 0) for row in items),
            "successful_contract_count": sum(int(row.get("successful_contract_count") or 0) for row in items),
            "failed_contract_count": sum(int(row.get("failed_contract_count") or 0) for row in items),
            "option_event_count": sum(int(row.get("option_event_count") or 0) for row in items),
            "complete_option_event_count": sum(int(row.get("complete_option_event_count") or 0) for row in items),
        }
        group_row.update({field: value for field, value in zip(fields, key)})
        for horizon in HORIZONS:
            for metric in METRICS:
                values = [_fnum(row.get(f"event_{metric}_{horizon}")) for row in items]
                group_row[f"avg_event_{metric}_{horizon}"] = _avg(values)
                group_row[f"positive_rate_event_{metric}_{horizon}"] = _hit(values)
        out.append(group_row)
    return out


def summarize_same_symbol_non_earnings_option_controls(inputs: SameSymbolNonEarningsOptionControlInputs) -> dict[str, Any]:
    earnings = _read_csv(inputs.canonical_earnings_path)
    option_events = _read_csv(inputs.option_events_path)
    receipts = _iter_contract_receipts(inputs.option_matrix_root)
    earnings_dates = _earnings_by_symbol(earnings)
    labels = _label_by_symbol_date(option_events)
    complete_counts = _complete_event_counts(option_events)

    probes_by_key: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in receipts:
        probes_by_key[(str(row.get("symbol") or "").upper(), str(row.get("event_date") or ""))].append(row)

    rows: list[dict[str, Any]] = []
    for (symbol, event_date), probes in sorted(probes_by_key.items()):
        nearest_date, distance = _nearest_earnings(symbol, event_date, earnings_dates)
        role = _window_role(distance, inputs.control_exclusion_days)
        verification_status, metrics = _probe_status(probes)
        rows.append(
            {
                "symbol": symbol,
                "event_date": event_date,
                "nearest_earnings_date": nearest_date,
                "nearest_earnings_distance_days": distance,
                "window_role": role,
                "verification_status": verification_status,
                "complete_option_event_count": complete_counts.get((symbol, event_date), 0),
                "control_exclusion_days": inputs.control_exclusion_days,
                **metrics,
                **labels.get((symbol, event_date), {}),
            }
        )

    group_stats: list[dict[str, Any]] = []
    group_stats.extend(_group(rows, ["window_role"], "by_window_role"))
    group_stats.extend(_group(rows, ["window_role", "verification_status"], "by_window_role_and_verification"))

    non_earnings_rows = [row for row in rows if row["window_role"] == "same_symbol_non_earnings_control_candidate"]
    clean_non_earnings = [row for row in non_earnings_rows if row["verification_status"] == "verified_no_sampled_option_abnormality"]
    abnormal_non_earnings = [row for row in non_earnings_rows if "verified_option_abnormality" in str(row["verification_status"])]
    exact_earnings_abnormal = [row for row in rows if row["window_role"] == "exact_earnings_date" and "verified_option_abnormality" in str(row["verification_status"])]

    if clean_non_earnings and (abnormal_non_earnings or exact_earnings_abnormal):
        status = "sampled_same_symbol_control_split_available_not_promotion_evidence"
    elif non_earnings_rows and not clean_non_earnings:
        status = "blocked_no_verified_same_symbol_non_earnings_no_option_abnormality_controls"
    elif not non_earnings_rows:
        status = "blocked_no_same_symbol_non_earnings_windows_in_source_matrix"
    else:
        status = "blocked_no_verified_option_abnormality_rows_for_comparison"

    report = {
        "schema": "same_symbol_non_earnings_option_control_verification_v1",
        "status": status,
        "provider_calls_performed_by_study": 0,
        "provider_calls_referenced_from_option_matrix_receipts": len(receipts),
        "canonical_earnings_count": len(earnings),
        "option_matrix_window_count": len(rows),
        "same_symbol_non_earnings_window_count": len(non_earnings_rows),
        "same_symbol_non_earnings_verified_no_abnormality_count": len(clean_non_earnings),
        "same_symbol_non_earnings_verified_abnormality_count": len(abnormal_non_earnings),
        "exact_earnings_verified_abnormality_count": len(exact_earnings_abnormal),
        "control_exclusion_days": inputs.control_exclusion_days,
        "sample_scope_note": "No-option verification covers only sampled same-symbol contract/date probes under the option-event standard, not the full option chain.",
        "interpretation": [
            "This reroutes the blocked earnings+option comparison to same-symbol non-earnings candidate windows instead of probing more earnings dates.",
            "Direction-neutral forward labels are recorded first; signed direction remains secondary and no alpha promotion is inferred.",
            "If no sampled non-earnings windows are verified as no-option-abnormality, the option-abnormality amplifier comparison remains structurally blocked.",
        ],
        "group_stats": group_stats,
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "same_symbol_non_earnings_option_control_rows.csv", rows)
    _write_csv(inputs.output_dir / "same_symbol_non_earnings_option_control_group_stats.csv", group_stats)
    _write_json(inputs.output_dir / "report.json", report)
    (inputs.output_dir / "README.md").write_text(
        f"""# Same-symbol non-earnings option-control verification

This artifact checks whether existing local option-event receipts can provide same-symbol non-earnings no-option-abnormality controls under the same option-event standard.

- Canonical earnings shells: {len(earnings)}
- Option matrix symbol/date windows: {len(rows)}
- Same-symbol non-earnings candidate windows: {len(non_earnings_rows)}
- Verified no sampled option-abnormality non-earnings controls: {len(clean_non_earnings)}
- Status: `{status}`

The study performs no provider calls. It references existing option-event completion receipts only. No-option verification remains sampled-contract evidence, not full-chain proof.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["SameSymbolNonEarningsOptionControlInputs", "summarize_same_symbol_non_earnings_option_controls"]
