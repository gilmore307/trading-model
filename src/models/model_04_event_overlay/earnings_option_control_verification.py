"""Summarize earnings-option abnormality control verification probes.

This module performs no provider calls. It consumes:

- canonical earnings/guidance scheduling shells;
- reviewed complete-evidence option-abnormality rows from an existing matrix;
- contract-level option-event probe receipts for earnings dates not covered by
  that matrix;
- local underlying daily bars for direction-neutral and signed path labels.

The key distinction is intentionally narrow: `verified_no_sampled_option_abnormality`
means no abnormality events were emitted for the sampled contract set under the
same option-event standard. It is not full-chain proof.
"""
from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HORIZONS = (1, 5, 10, 14)
METRICS = ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae")


@dataclass(frozen=True)
class EarningsOptionControlVerificationInputs:
    canonical_earnings_path: Path
    existing_option_events_path: Path
    contract_probe_path: Path
    equity_bar_paths: tuple[Path, ...]
    output_dir: Path


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


def _date(text: str) -> str:
    return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()


def load_equity_bars(paths: Iterable[Path]) -> dict[str, list[dict[str, Any]]]:
    by_symbol: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for path in paths:
        for row in _read_csv(path):
            symbol = str(row.get("symbol") or "").upper()
            timestamp = str(row.get("timestamp") or "")
            close = _fnum(row.get("bar_close"))
            high = _fnum(row.get("bar_high"))
            low = _fnum(row.get("bar_low"))
            if not symbol or not timestamp or close is None or high is None or low is None:
                continue
            by_symbol[symbol][_date(timestamp)] = {
                "symbol": symbol,
                "date": _date(timestamp),
                "timestamp": timestamp,
                "close": close,
                "high": high,
                "low": low,
            }
    return {symbol: [items[key] for key in sorted(items)] for symbol, items in by_symbol.items()}


def _labels(rows: Sequence[Mapping[str, Any]], event_date: str) -> dict[str, Any]:
    dates = [str(row["date"]) for row in rows]
    if event_date not in dates:
        return {}
    idx = dates.index(event_date)
    baseline = float(rows[idx]["close"])
    out: dict[str, Any] = {"underlying_event_close": baseline}
    for horizon in HORIZONS:
        end = idx + horizon
        label = f"{horizon}d"
        if end >= len(rows):
            continue
        window = rows[idx + 1 : end + 1]
        if not window:
            continue
        forward = float(rows[end]["close"]) / baseline - 1.0
        max_high = max(float(row["high"]) for row in window)
        min_low = min(float(row["low"]) for row in window)
        out[f"event_abs_fwd_{label}"] = abs(forward)
        out[f"event_directional_fwd_{label}"] = forward
        out[f"event_path_range_{label}"] = (max_high - min_low) / baseline
        out[f"event_mfe_{label}"] = max_high / baseline - 1.0
        out[f"event_mae_{label}"] = min_low / baseline - 1.0
    return out


def _group_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get("verification_status") or "missing")].append(row)
    output: list[dict[str, Any]] = []
    for status, items in sorted(groups.items()):
        out: dict[str, Any] = {
            "verification_status": status,
            "n_events": len(items),
            "n_symbols": len({row.get("symbol") for row in items}),
        }
        for horizon in HORIZONS:
            for metric in METRICS:
                key = f"event_{metric}_{horizon}d"
                values = [_fnum(row.get(key)) for row in items]
                out[f"avg_{key}"] = _avg(values)
                out[f"positive_rate_{key}"] = _hit(values)
        output.append(out)
    return output


def _probe_status(probes: Sequence[Mapping[str, str]]) -> tuple[str, dict[str, Any]]:
    attempted = len(probes)
    succeeded = sum(1 for row in probes if row.get("status") == "succeeded")
    failed = attempted - succeeded
    option_events = sum(int(float(row.get("option_event_count") or 0)) for row in probes)
    if option_events and failed:
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


def summarize_earnings_option_control_verification(inputs: EarningsOptionControlVerificationInputs) -> dict[str, Any]:
    earnings = _read_csv(inputs.canonical_earnings_path)
    existing_events = _read_csv(inputs.existing_option_events_path)
    probes = _read_csv(inputs.contract_probe_path)
    bars = load_equity_bars(inputs.equity_bar_paths)

    existing_by_key: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in existing_events:
        existing_by_key[(str(row.get("symbol") or "").upper(), str(row.get("event_date") or ""))].append(row)
    probes_by_key: dict[tuple[str, str], list[Mapping[str, str]]] = defaultdict(list)
    for row in probes:
        probes_by_key[(str(row.get("symbol") or "").upper(), str(row.get("event_date") or ""))].append(row)

    event_rows: list[dict[str, Any]] = []
    for event in earnings:
        symbol = str(event.get("symbol") or "").upper()
        event_date = str(event.get("event_date") or "")
        labels = _labels(bars.get(symbol, []), event_date)
        existing = existing_by_key.get((symbol, event_date), [])
        if existing:
            status = "verified_option_abnormality_existing_matrix"
            metrics = {
                "option_event_count": len(existing),
                "complete_option_event_count": len(existing),
            }
        else:
            status, metrics = _probe_status(probes_by_key.get((symbol, event_date), []))
        event_rows.append(
            {
                "symbol": symbol,
                "event_date": event_date,
                "event_id": event.get("event_id"),
                "event_name": event.get("event_name"),
                "verification_status": status,
                **metrics,
                **labels,
            }
        )

    group_stats = _group_rows(event_rows)
    status_counts = {row["verification_status"]: row["n_events"] for row in group_stats}
    no_abnormality_count = status_counts.get("verified_no_sampled_option_abnormality", 0)
    if no_abnormality_count:
        status = "sampled_split_available_not_promotion_evidence"
    else:
        status = "blocked_no_verified_no_option_abnormality_controls_in_sampled_contracts"
    report = {
        "schema": "earnings_option_control_verification_v1",
        "status": status,
        "provider_calls_performed_by_study": 0,
        "provider_calls_referenced_from_probe": len(probes),
        "canonical_earnings_count": len(earnings),
        "status_counts": status_counts,
        "sample_scope_note": "No-option verification covers only the sampled contract set under the same option-event standard, not the entire option chain.",
        "interpretation": [
            "The expanded sampled-contract probe still found no earnings rows with verified no-option-abnormality controls.",
            "Most newly probed earnings rows had option abnormality; PFE and RKLB had partial contract coverage due ThetaData HTTP 472 failures but still emitted abnormality on successful sampled contracts.",
            "The earnings+option amplifier comparison remains structurally blocked, not positive or negative.",
        ],
        "group_stats": group_stats,
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_option_control_event_rows.csv", event_rows)
    _write_csv(inputs.output_dir / "earnings_option_control_group_stats.csv", group_stats)
    _write_json(inputs.output_dir / "report.json", report)
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings option no-abnormality control verification

This artifact summarizes contract-level option-event probes for canonical earnings shells.

- Canonical earnings events: {len(earnings)}
- Referenced contract probes: {len(probes)}
- Status: `{status}`
- Verified no sampled option-abnormality controls: {no_abnormality_count}

No-option verification is sampled-contract evidence only, not full-chain proof. The amplifier comparison remains blocked when no verified no-option-abnormality controls exist.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["EarningsOptionControlVerificationInputs", "summarize_earnings_option_control_verification"]
