"""Point-in-time expectation baseline readiness for earnings/guidance events.

This module does not fetch provider data and does not create signed claims. It
validates whether separately acquired baseline artifacts are acceptable for
future beat/miss or guidance-surprise interpretation.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class ExpectationBaselineInputs:
    interpretation_rows_path: Path
    output_dir: Path
    baseline_manifest_path: Path | None = None


ACCEPTED_BASELINE_TYPES = {
    "eps_consensus",
    "revenue_consensus",
    "prior_company_guidance",
    "guidance_consensus_or_analyst_range",
}

SIGNED_REQUIRED_BASELINE_TYPES = {
    "eps_consensus",
    "revenue_consensus",
    "prior_company_guidance_or_guidance_consensus",
}


REQUIRED_BASELINE_FIELDS = (
    "event_id",
    "symbol",
    "baseline_type",
    "source_name",
    "source_ref",
    "captured_at",
    "as_of_time",
)


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


def _parse_dateish(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for candidate in (text, text[:10]):
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            continue
    return None


def _load_baselines(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict):
        rows = payload.get("baseline_artifacts") or payload.get("baselines") or []
    else:
        rows = []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _validate_baseline(row: Mapping[str, Any], event: Mapping[str, str]) -> tuple[str, str]:
    missing = [field for field in REQUIRED_BASELINE_FIELDS if not row.get(field)]
    if missing:
        return "rejected_missing_required_fields", ";".join(missing)
    baseline_type = str(row.get("baseline_type"))
    if baseline_type not in ACCEPTED_BASELINE_TYPES:
        return "rejected_unaccepted_baseline_type", baseline_type
    event_date = _parse_dateish(event.get("event_date"))
    captured_date = _parse_dateish(str(row.get("captured_at") or ""))
    as_of_date = _parse_dateish(str(row.get("as_of_time") or ""))
    if event_date is None or captured_date is None or as_of_date is None:
        return "rejected_unparseable_point_in_time_clock", "event_date_or_baseline_clock"
    # With date-only earnings event rows, require baseline evidence to predate the
    # event date. Same-day evidence may be after release and must use timestamped
    # clocks in a future artifact before acceptance.
    if captured_date >= event_date or as_of_date >= event_date:
        return "rejected_not_point_in_time_before_event", f"event_date={event_date};captured_at={captured_date};as_of_time={as_of_date}"
    return "accepted_point_in_time_expectation_baseline", ""


def _missing_types(accepted_types: set[str]) -> list[str]:
    missing: list[str] = []
    if "eps_consensus" not in accepted_types:
        missing.append("eps_consensus")
    if "revenue_consensus" not in accepted_types:
        missing.append("revenue_consensus")
    if not ({"prior_company_guidance", "guidance_consensus_or_analyst_range"} & accepted_types):
        missing.append("prior_company_guidance_or_guidance_consensus")
    return missing


def run_expectation_baseline_readiness(inputs: ExpectationBaselineInputs) -> dict[str, Any]:
    events = _read_csv(inputs.interpretation_rows_path)
    raw_baselines = _load_baselines(inputs.baseline_manifest_path)
    baselines_by_event: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in raw_baselines:
        baselines_by_event[str(row.get("event_id") or "")].append(row)

    baseline_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event.get("event_id") or "")
        accepted_types: set[str] = set()
        accepted_refs: list[str] = []
        rejected_count = 0
        for baseline in baselines_by_event.get(event_id, []):
            status, note = _validate_baseline(baseline, event)
            if status == "accepted_point_in_time_expectation_baseline":
                accepted_types.add(str(baseline.get("baseline_type")))
                accepted_refs.append(str(baseline.get("source_ref")))
            else:
                rejected_count += 1
            baseline_rows.append({
                "event_id": event_id,
                "symbol": event.get("symbol"),
                "event_date": event.get("event_date"),
                "baseline_type": baseline.get("baseline_type", ""),
                "source_name": baseline.get("source_name", ""),
                "source_ref": baseline.get("source_ref", ""),
                "captured_at": baseline.get("captured_at", ""),
                "as_of_time": baseline.get("as_of_time", ""),
                "baseline_acceptance_status": status,
                "baseline_acceptance_note": note,
            })
        missing = _missing_types(accepted_types)
        if not baselines_by_event.get(event_id):
            status = "missing_point_in_time_expectation_baseline"
        elif missing:
            status = "partial_point_in_time_expectation_baseline"
        else:
            status = "accepted_point_in_time_expectation_baseline_set"
        event_rows.append({
            "symbol": event.get("symbol"),
            "event_id": event_id,
            "event_date": event.get("event_date"),
            "reviewed_guidance_interpretation_status": event.get("reviewed_guidance_interpretation_status"),
            "expectation_baseline_status": status,
            "accepted_baseline_type_count": len(accepted_types),
            "accepted_baseline_types": ";".join(sorted(accepted_types)),
            "missing_required_baseline_types": ";".join(missing),
            "accepted_baseline_refs": ";".join(accepted_refs),
            "rejected_baseline_artifact_count": rejected_count,
            "beat_miss_readiness": "blocked_missing_or_partial_expectation_baseline" if missing else "baseline_ready_result_metric_review_still_required",
            "guidance_surprise_readiness": "blocked_missing_or_partial_expectation_baseline" if missing else "baseline_ready_guidance_comparison_review_still_required",
            "signed_direction_readiness": "blocked_missing_or_partial_expectation_baseline" if missing else "baseline_ready_but_signed_claim_still_requires_result_guidance_comparison",
            "provider_calls_performed_by_study": 0,
        })

    counts = Counter(str(row["expectation_baseline_status"]) for row in event_rows)
    accepted_sets = counts.get("accepted_point_in_time_expectation_baseline_set", 0)
    partial_sets = counts.get("partial_point_in_time_expectation_baseline", 0)
    missing_sets = counts.get("missing_point_in_time_expectation_baseline", 0)
    report = {
        "schema": "earnings_guidance_expectation_baseline_readiness_v1",
        "status": "blocked_missing_point_in_time_expectation_baselines" if accepted_sets == 0 else "partial_expectation_baseline_coverage_review_required",
        "provider_calls_performed_by_study": 0,
        "event_count": len(event_rows),
        "baseline_artifact_count": len(raw_baselines),
        "accepted_baseline_set_event_count": accepted_sets,
        "partial_baseline_event_count": partial_sets,
        "missing_baseline_event_count": missing_sets,
        "signed_direction_ready_count": 0,
        "expectation_baseline_status_counts": dict(sorted(counts.items())),
        "accepted_baseline_types": sorted(ACCEPTED_BASELINE_TYPES),
        "baseline_acceptance_requirements": [
            "baseline artifact must identify event_id and symbol",
            "baseline_type must be one of the accepted baseline types",
            "source_name and source_ref must preserve provenance",
            "captured_at and as_of_time must be parseable point-in-time clocks",
            "with date-only event clocks, captured_at and as_of_time must predate event_date; same-day baselines require timestamped release clocks before acceptance",
            "signed beat/miss or guidance surprise still requires reviewed actual/result or guidance comparison after baselines are accepted",
        ],
        "interpretation": [
            "This scout validates baseline readiness only and performs no provider calls.",
            "No signed claim is unlocked without point-in-time consensus/prior-guidance baselines and reviewed result/guidance comparisons.",
            "Missing upstream values are preserved as missing/partial rather than inferred from official text or market reaction.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_expectation_baseline_rows.csv", event_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_expectation_baseline_artifacts.csv", baseline_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_expectation_baseline_group_stats.csv", [{"expectation_baseline_status": key, "n_events": value} for key, value in sorted(counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance expectation baseline readiness

This no-provider artifact validates whether point-in-time expectation baselines are available for earnings/guidance interpretation.

- Events: {len(event_rows)}
- Baseline artifacts supplied: {len(raw_baselines)}
- Accepted complete baseline sets: {accepted_sets}
- Partial baseline events: {partial_sets}
- Missing baseline events: {missing_sets}
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: expectation baselines are a prerequisite gate. Official result text and partial guidance context do not establish beat/miss, guidance raise/cut, or signed direction without accepted point-in-time baselines.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["ExpectationBaselineInputs", "run_expectation_baseline_readiness"]
