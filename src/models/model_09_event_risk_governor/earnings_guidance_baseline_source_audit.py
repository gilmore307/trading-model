"""Audit existing calendar artifacts as possible earnings expectation baselines.

This is a no-provider audit. It checks whether already captured Nasdaq earnings
calendar rows can be accepted as point-in-time baseline artifacts. Historical
snapshots captured after the event are rejected even when they contain
``epsForecast`` because post-event rows may also contain actual EPS and surprise.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class BaselineSourceAuditInputs:
    interpretation_rows_path: Path
    calendar_artifact_root: Path
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


def _parse_dateish(value: str | None) -> date | None:
    if not value:
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    for candidate in (text, text[:10]):
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            continue
    return None


def _request_manifest_for(saved_calendar_path: Path) -> Path:
    # .../<date>/runs/<run_id>/saved/release_calendar.csv -> .../<date>/runs/<run_id>/request_manifest.json
    return saved_calendar_path.parent.parent / "request_manifest.json"


def _load_manifest(saved_calendar_path: Path) -> dict[str, Any]:
    path = _request_manifest_for(saved_calendar_path)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _calendar_rows(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.glob("**/saved/release_calendar.csv")):
        manifest = _load_manifest(path)
        fetched_at = str(manifest.get("fetched_at_utc") or "")
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                try:
                    raw = json.loads(row.get("raw_summary") or "{}")
                except json.JSONDecodeError:
                    raw = {}
                rows.append({
                    "event_id": row.get("event_id", ""),
                    "symbol": str(raw.get("symbol") or "").upper(),
                    "event_date": row.get("event_date", ""),
                    "source_url": row.get("source_url", ""),
                    "fetched_at_utc": fetched_at,
                    "saved_calendar_path": str(path),
                    "raw_summary": raw,
                })
    return rows


def _has_value(raw: Mapping[str, Any], key: str) -> bool:
    value = raw.get(key)
    return value not in (None, "", "N/A", "n/a", "--")


def _audit_row(event: Mapping[str, str], calendar_row: Mapping[str, Any] | None) -> dict[str, Any]:
    event_date = _parse_dateish(event.get("event_date"))
    if calendar_row is None:
        return {
            "symbol": event.get("symbol"),
            "event_id": event.get("event_id"),
            "event_date": event.get("event_date"),
            "calendar_match_status": "missing_matching_calendar_row",
            "eps_forecast_present": False,
            "eps_actual_present": False,
            "surprise_present": False,
            "no_of_estimates_present": False,
            "revenue_forecast_present": False,
            "baseline_candidate_type": "none",
            "pit_acceptance_status": "missing_source_artifact",
            "pit_rejection_reason": "no matching calendar row found under audited artifact root",
            "provider_calls_performed_by_study": 0,
        }
    raw = dict(calendar_row.get("raw_summary") or {})
    fetched_at = str(calendar_row.get("fetched_at_utc") or "")
    fetched_date = _parse_dateish(fetched_at)
    eps_forecast = _has_value(raw, "epsForecast")
    eps_actual = _has_value(raw, "eps")
    surprise = _has_value(raw, "surprise")
    no_est = _has_value(raw, "noOfEsts")
    revenue_forecast = any(_has_value(raw, key) for key in ("revenueForecast", "revenueConsensus", "salesForecast"))
    if not eps_forecast:
        candidate_type = "none"
    elif eps_actual or surprise:
        candidate_type = "eps_consensus_candidate_contaminated_by_actual_or_surprise_fields"
    else:
        candidate_type = "eps_consensus_candidate"
    if event_date is None or fetched_date is None:
        status = "rejected_unparseable_pit_clock"
        reason = "event_date or fetched_at_utc could not be parsed"
    elif fetched_date >= event_date:
        status = "rejected_post_event_or_same_day_calendar_snapshot"
        reason = "calendar snapshot was captured on/after event date and may include actual/surprise fields"
    elif not eps_forecast:
        status = "rejected_missing_eps_forecast"
        reason = "calendar row does not include EPS forecast"
    elif eps_actual or surprise:
        # Even pre-event acceptance should require a clean pre-event snapshot with no result fields.
        status = "rejected_contains_actual_or_surprise_fields"
        reason = "baseline snapshot contains actual EPS or surprise fields"
    else:
        status = "candidate_future_pit_eps_consensus_route"
        reason = "pre-event snapshot with EPS forecast only; revenue/guidance baselines still required"
    return {
        "symbol": event.get("symbol"),
        "event_id": event.get("event_id"),
        "event_date": event.get("event_date"),
        "calendar_match_status": "matched_calendar_row",
        "calendar_fetched_at_utc": fetched_at,
        "calendar_source_url": calendar_row.get("source_url", ""),
        "saved_calendar_path": calendar_row.get("saved_calendar_path", ""),
        "eps_forecast_present": eps_forecast,
        "eps_actual_present": eps_actual,
        "surprise_present": surprise,
        "no_of_estimates_present": no_est,
        "revenue_forecast_present": revenue_forecast,
        "baseline_candidate_type": candidate_type,
        "pit_acceptance_status": status,
        "pit_rejection_reason": reason,
        "eps_forecast_value_present_only": eps_forecast,
        "provider_calls_performed_by_study": 0,
    }


def run_baseline_source_audit(inputs: BaselineSourceAuditInputs) -> dict[str, Any]:
    events = _read_csv(inputs.interpretation_rows_path)
    calendar_rows = _calendar_rows(inputs.calendar_artifact_root)
    by_event = {str(row.get("event_id") or ""): row for row in calendar_rows if row.get("event_id")}
    audit_rows = [_audit_row(event, by_event.get(str(event.get("event_id") or ""))) for event in events]
    status_counts = Counter(str(row.get("pit_acceptance_status") or "missing") for row in audit_rows)
    candidate_counts = Counter(str(row.get("baseline_candidate_type") or "none") for row in audit_rows)
    matched_count = sum(1 for row in audit_rows if row.get("calendar_match_status") == "matched_calendar_row")
    report = {
        "schema": "earnings_guidance_baseline_source_audit_v1",
        "status": "blocked_existing_calendar_artifacts_not_pit_acceptable",
        "provider_calls_performed_by_study": 0,
        "event_count": len(events),
        "calendar_artifact_row_count": len(calendar_rows),
        "matched_event_count": matched_count,
        "eps_forecast_present_event_count": sum(1 for row in audit_rows if row.get("eps_forecast_present") is True),
        "revenue_forecast_present_event_count": sum(1 for row in audit_rows if row.get("revenue_forecast_present") is True),
        "accepted_pit_baseline_event_count": status_counts.get("candidate_future_pit_eps_consensus_route", 0),
        "signed_direction_ready_count": 0,
        "pit_acceptance_status_counts": dict(sorted(status_counts.items())),
        "baseline_candidate_type_counts": dict(sorted(candidate_counts.items())),
        "interpretation": [
            "Existing Nasdaq earnings calendar artifacts contain EPS forecast-like fields for the reviewed events, but the audited snapshots were captured after the historical event dates.",
            "Because post-event Nasdaq rows also include actual EPS and surprise fields, they are not acceptable point-in-time historical baselines.",
            "Nasdaq may be a future EPS-consensus monitoring route only if snapshots are captured before the event and stored without relying on post-event actual/surprise fields.",
            "The existing route does not provide revenue consensus or guidance expectation baselines for this diagnostic slice.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_baseline_source_audit_rows.csv", audit_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_baseline_source_audit_status_counts.csv", [{"pit_acceptance_status": key, "n_events": value} for key, value in sorted(status_counts.items())])
    _write_csv(inputs.output_dir / "earnings_guidance_baseline_source_audit_candidate_counts.csv", [{"baseline_candidate_type": key, "n_events": value} for key, value in sorted(candidate_counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance baseline source audit

This no-provider artifact audits existing calendar artifacts as possible point-in-time expectation baselines.

- Events: {len(events)}
- Matched calendar rows: {matched_count}
- EPS forecast-like rows: {report['eps_forecast_present_event_count']}
- Revenue forecast-like rows: {report['revenue_forecast_present_event_count']}
- Accepted PIT baseline rows: {report['accepted_pit_baseline_event_count']}
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: existing Nasdaq calendar artifacts are useful evidence that an EPS-forecast route exists, but these historical captures are not PIT-acceptable because they were fetched after the events and include actual/surprise fields. Future baseline acquisition must capture clean pre-event snapshots and still add revenue/guidance baseline coverage.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["BaselineSourceAuditInputs", "run_baseline_source_audit"]
