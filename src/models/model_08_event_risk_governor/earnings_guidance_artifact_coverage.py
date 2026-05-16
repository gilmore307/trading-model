"""Official document coverage gate for earnings/guidance interpretation.

This scout performs no provider calls. It checks whether the local artifact set
contains official company document text that could support guidance/outlook
interpretation. SEC submission rows and selected result filings are visibility
metadata only; they are not enough to infer guidance surprise.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuidanceArtifactCoverageInputs:
    interpreted_events_path: Path
    result_filings_path: Path
    output_dir: Path
    sec_filing_document_metadata_paths: tuple[Path, ...] = ()
    accepted_guidance_interpretation_path: Path | None = None


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


def _key(accession_number: Any, document_name: Any) -> tuple[str, str]:
    return (str(accession_number or "").strip(), str(document_name or "").strip())


def _resolve_text_path(metadata_path: Path, value: str) -> str:
    if not value:
        return ""
    raw_path = Path(value)
    if raw_path.is_absolute():
        return str(raw_path)
    for parent in (metadata_path.parent, *metadata_path.parents):
        candidate = parent / raw_path
        if candidate.exists():
            return str(candidate)
    return value


def _load_document_metadata(paths: Sequence[Path]) -> dict[tuple[str, str], dict[str, str]]:
    out: dict[tuple[str, str], dict[str, str]] = {}
    for path in paths:
        for row in _read_csv(path):
            key = _key(row.get("accession_number"), row.get("document_name"))
            if all(key):
                item = dict(row)
                item["document_text_path"] = _resolve_text_path(path, str(row.get("document_text_path") or ""))
                out[key] = item
    return out


def _load_guidance_interpretations(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    out: dict[str, dict[str, str]] = {}
    for row in _read_csv(path):
        event_id = str(row.get("event_id") or "").strip()
        if event_id:
            out[event_id] = row
    return out


def _coverage_row(
    event: Mapping[str, str],
    filing_by_event: Mapping[str, Mapping[str, str]],
    document_by_key: Mapping[tuple[str, str], Mapping[str, str]],
    guidance_by_event: Mapping[str, Mapping[str, str]],
) -> dict[str, Any]:
    event_id = str(event.get("event_id") or "")
    filing = filing_by_event.get(event_id, {})
    accession_number = filing.get("accession_number") or event.get("result_accession_number") or ""
    document_name = filing.get("primary_document") or ""
    document = document_by_key.get(_key(accession_number, document_name), {})
    local_document_present = bool(document)
    text_path = str(document.get("document_text_path") or "")
    text_path_exists = bool(text_path) and Path(text_path).exists()
    guidance = guidance_by_event.get(event_id, {})
    interpretation_status = str(guidance.get("guidance_interpretation_status") or "missing_official_company_guidance_interpretation")
    accepted_interpretation_present = interpretation_status not in {"", "missing", "missing_official_company_guidance_interpretation"}

    if accepted_interpretation_present:
        artifact_status = "accepted_guidance_interpretation_present"
    elif local_document_present and text_path_exists:
        artifact_status = "official_document_text_present_uninterpreted"
    elif accession_number and document_name:
        artifact_status = "missing_local_official_document_text_artifact"
    elif accession_number:
        artifact_status = "missing_primary_document_name"
    else:
        artifact_status = "missing_official_result_filing_reference"

    return {
        "symbol": event.get("symbol"),
        "event_id": event_id,
        "event_date": event.get("event_date"),
        "event_name": event.get("event_name"),
        "lifecycle_class": event.get("lifecycle_class"),
        "result_accession_number": accession_number,
        "result_primary_document": document_name,
        "result_form": filing.get("form") or event.get("result_filing_form"),
        "result_filing_date": filing.get("filing_date") or event.get("result_filing_date"),
        "sec_result_filing_reference_status": "present" if accession_number and document_name else "partial" if accession_number else "missing",
        "local_sec_filing_document_status": "present" if local_document_present else "missing",
        "local_document_text_path_status": "present" if text_path_exists else "missing",
        "local_document_text_length": document.get("text_length") or "",
        "local_document_text_sha256": document.get("text_sha256") or "",
        "official_guidance_artifact_status": artifact_status,
        "guidance_interpretation_status": interpretation_status,
        "expectation_baseline_status": str(guidance.get("expectation_baseline_status") or "missing_consensus_or_accepted_expectation_baseline"),
        "signed_direction_readiness": "ready" if accepted_interpretation_present and guidance.get("expectation_baseline_status") not in {None, "", "missing_consensus_or_accepted_expectation_baseline"} else "blocked_missing_guidance_interpretation_or_expectation_baseline",
        "provider_calls_performed_by_study": 0,
    }


def run_guidance_artifact_coverage_scout(inputs: GuidanceArtifactCoverageInputs) -> dict[str, Any]:
    events = _read_csv(inputs.interpreted_events_path)
    filings = _read_csv(inputs.result_filings_path)
    filing_by_event = {str(row.get("event_id") or ""): row for row in filings if row.get("event_id")}
    document_by_key = _load_document_metadata(inputs.sec_filing_document_metadata_paths)
    guidance_by_event = _load_guidance_interpretations(inputs.accepted_guidance_interpretation_path)
    rows = [_coverage_row(event, filing_by_event, document_by_key, guidance_by_event) for event in events]
    status_counts = Counter(str(row.get("official_guidance_artifact_status") or "missing") for row in rows)
    local_document_count = sum(1 for row in rows if row.get("local_sec_filing_document_status") == "present")
    accepted_guidance_count = sum(1 for row in rows if row.get("guidance_interpretation_status") != "missing_official_company_guidance_interpretation")
    expectation_count = sum(1 for row in rows if row.get("expectation_baseline_status") != "missing_consensus_or_accepted_expectation_baseline")
    signed_ready_count = sum(1 for row in rows if row.get("signed_direction_readiness") == "ready")
    report = {
        "schema": "earnings_guidance_artifact_coverage_scout_v1",
        "status": "blocked_missing_local_official_guidance_artifacts" if local_document_count == 0 else "blocked_missing_accepted_guidance_interpretation_or_expectation_baseline",
        "provider_calls_performed_by_study": 0,
        "event_count": len(rows),
        "result_filing_reference_count": sum(1 for row in rows if row.get("sec_result_filing_reference_status") == "present"),
        "local_official_document_text_artifact_count": local_document_count,
        "accepted_guidance_interpretation_count": accepted_guidance_count,
        "expectation_baseline_count": expectation_count,
        "signed_direction_ready_count": signed_ready_count,
        "official_guidance_artifact_status_counts": dict(sorted(status_counts.items())),
        "interpretation": [
            "SEC filing references identify official result-document candidates but are not themselves guidance interpretations.",
            "A local SEC/company release/exhibit/transcript text artifact is required before guidance/outlook interpretation can be attempted.",
            "Accepted guidance interpretation plus a point-in-time expectation baseline is required before any beat/miss, guidance raise/cut, or signed-direction claim.",
            "This scout performs no provider calls and records missing local artifacts explicitly rather than inferring from price reaction or normalized SEC facts.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_artifact_coverage_rows.csv", rows)
    group_rows = [{"official_guidance_artifact_status": key, "n_events": value} for key, value in sorted(status_counts.items())]
    _write_csv(inputs.output_dir / "earnings_guidance_artifact_coverage_group_stats.csv", group_rows)
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance official-artifact coverage scout

This artifact checks whether local official company documents exist for earnings/guidance interpretation.

- Events: {len(rows)}
- SEC result filing references: {report['result_filing_reference_count']}
- Local official document text artifacts: {local_document_count}
- Accepted guidance interpretations: {accepted_guidance_count}
- Expectation baselines: {expectation_count}
- Signed-direction ready rows: {signed_ready_count}
- Status: `{report['status']}`

Conclusion: filing metadata alone is not enough. Missing official document text, guidance interpretation, and expectation baselines keep earnings/guidance at direction-neutral event-risk context.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["GuidanceArtifactCoverageInputs", "run_guidance_artifact_coverage_scout"]
