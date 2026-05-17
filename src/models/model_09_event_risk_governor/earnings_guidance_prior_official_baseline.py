"""Audit prior official filings as guidance-baseline source candidates.

This no-provider model-side audit consumes already acquired SEC submission rows and
selects pre-event official filings that can seed a future prior-company-guidance
baseline route. It does not fetch documents, interpret guidance, or make signed
claims.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PriorOfficialBaselineInputs:
    interpretation_rows_path: Path
    sec_submission_root: Path
    output_dir: Path
    lookback_days: int = 180


ACCEPTED_FORMS = {"8-K", "10-Q", "10-K"}
PREFERRED_FORM_RANK = {"8-K": 0, "10-Q": 1, "10-K": 2}


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


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _submission_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in sorted(root.glob("*/runs/*/saved/sec_submission.csv")):
        symbol = path.parts[-5]
        for row in _read_csv(path):
            row = dict(row)
            row["symbol"] = symbol
            row["submission_csv_path"] = str(path)
            rows.append(row)
    return rows


def _candidate_score(row: Mapping[str, str], current_event_date: date) -> tuple[int, int]:
    filing_date = _parse_date(row.get("filing_date")) or date.min
    days_before = (current_event_date - filing_date).days
    return (PREFERRED_FORM_RANK.get(str(row.get("form")), 9), days_before)


def _select_candidate(event: Mapping[str, str], submissions: Sequence[Mapping[str, str]], lookback_days: int) -> Mapping[str, str] | None:
    event_date = _parse_date(event.get("event_date"))
    if event_date is None:
        return None
    earliest = event_date - timedelta(days=lookback_days)
    candidates = []
    for row in submissions:
        filing_date = _parse_date(row.get("filing_date"))
        if filing_date is None:
            continue
        if str(row.get("form")) not in ACCEPTED_FORMS:
            continue
        if not (earliest <= filing_date < event_date):
            continue
        if not row.get("accession_number") or not row.get("primary_document"):
            continue
        candidates.append(row)
    if not candidates:
        return None
    return sorted(candidates, key=lambda row: _candidate_score(row, event_date))[0]


def _task_key(row: Mapping[str, Any]) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "")
    accession = str(row.get("prior_accession_number") or "")
    document = str(row.get("prior_primary_document") or "")
    return {
        "task_id": f"prior_guidance_sec_filing_document_{symbol}_{accession.replace('-', '')}",
        "feed": "08_feed_sec_company_financials",
        "output_root": f"storage/earnings_guidance_prior_official_guidance_document_text_q4_2025_20260515/{symbol}",
        "params": {
            "data_kind": "sec_filing_document",
            "cik": str(row.get("cik") or ""),
            "accession_number": accession,
            "document_name": document,
            "baseline_capture_mode": "prior_company_guidance_official_document_candidate",
            "current_event_id": str(row.get("event_id") or ""),
            "current_event_date": str(row.get("event_date") or ""),
        },
        "manager_controls": {
            "provider_calls_required_for_document_fetch": 1,
            "model_activation_performed": False,
            "broker_execution_performed": False,
            "signed_claims_unlocked": False,
        },
    }


def run_prior_official_baseline_audit(inputs: PriorOfficialBaselineInputs) -> dict[str, Any]:
    events = _read_csv(inputs.interpretation_rows_path)
    submissions = _submission_rows(inputs.sec_submission_root)
    by_symbol: dict[str, list[dict[str, str]]] = {}
    for row in submissions:
        by_symbol.setdefault(str(row.get("symbol") or ""), []).append(row)
    audit_rows: list[dict[str, Any]] = []
    task_keys: list[dict[str, Any]] = []
    for event in events:
        symbol = str(event.get("symbol") or "")
        selected = _select_candidate(event, by_symbol.get(symbol, []), inputs.lookback_days)
        if selected is None:
            status = "missing_prior_official_guidance_source_candidate"
            row = {
                "symbol": symbol,
                "event_id": event.get("event_id"),
                "event_date": event.get("event_date"),
                "prior_official_guidance_source_status": status,
                "provider_calls_performed_by_study": 0,
                "signed_direction_ready": False,
            }
        else:
            status = "candidate_prior_official_guidance_source_selected"
            row = {
                "symbol": symbol,
                "event_id": event.get("event_id"),
                "event_date": event.get("event_date"),
                "prior_official_guidance_source_status": status,
                "cik": selected.get("cik"),
                "prior_accession_number": selected.get("accession_number"),
                "prior_filing_date": selected.get("filing_date"),
                "prior_report_date": selected.get("report_date"),
                "prior_form": selected.get("form"),
                "prior_primary_document": selected.get("primary_document"),
                "prior_primary_doc_description": selected.get("primary_doc_description"),
                "prior_submission_csv_path": selected.get("submission_csv_path"),
                "provider_calls_performed_by_study": 0,
                "signed_direction_ready": False,
            }
            task_keys.append(_task_key(row))
        audit_rows.append(row)
    status_counts = Counter(str(row["prior_official_guidance_source_status"]) for row in audit_rows)
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_official_baseline_source_rows.csv", audit_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_official_baseline_source_group_stats.csv", [{"prior_official_guidance_source_status": key, "n_events": value} for key, value in sorted(status_counts.items())])
    with (inputs.output_dir / "prior_official_guidance_document_task_keys.jsonl").open("w", encoding="utf-8") as handle:
        for payload in task_keys:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    report = {
        "schema": "earnings_guidance_prior_official_baseline_source_audit_v1",
        "status": "candidate_prior_official_guidance_sources_identified" if task_keys else "blocked_missing_prior_official_guidance_source_candidates",
        "provider_calls_performed_by_study": 0,
        "event_count": len(events),
        "sec_submission_row_count": len(submissions),
        "candidate_source_event_count": len(task_keys),
        "signed_direction_ready_count": 0,
        "prior_official_guidance_source_status_counts": dict(sorted(status_counts.items())),
        "interpretation": [
            "Selected prior official filings are source candidates for prior-company-guidance baselines only.",
            "Document fetch, reviewed guidance extraction, and point-in-time comparison are still required before any guidance surprise or signed claim.",
            "Provider calls reported here are zero because this audit consumes already acquired SEC submission rows.",
        ],
    }
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Prior official guidance baseline source audit

This no-provider audit selects pre-event official SEC filings as prior-company-guidance baseline source candidates.

- Events: {len(events)}
- SEC submission rows consumed: {len(submissions)}
- Candidate prior official source events: {len(task_keys)}
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: candidates identify official documents to fetch and review. They do not establish guidance surprise or signed direction.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["PriorOfficialBaselineInputs", "run_prior_official_baseline_audit"]
