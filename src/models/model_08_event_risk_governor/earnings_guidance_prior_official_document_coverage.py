"""Coverage check for prior official guidance candidate documents."""
from __future__ import annotations

import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PriorOfficialDocumentCoverageInputs:
    source_rows_path: Path
    document_root: Path
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


def _metadata_by_accession(root: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for path in sorted(root.glob("*/runs/*/saved/sec_filing_document.csv")):
        for row in _read_csv(path):
            row = dict(row)
            row["metadata_path"] = str(path)
            rows[str(row.get("accession_number") or "")] = row
    return rows


def _resolve_text_path(metadata_path: Path, document_text_path: str) -> Path:
    candidate = Path(document_text_path)
    if candidate.is_absolute() and candidate.exists():
        return candidate
    # First resolve relative to trading-data repo root when paths begin with storage/.
    repo_root = Path("/root/projects/trading-data")
    repo_candidate = repo_root / candidate
    if "[truncated]" not in document_text_path and repo_candidate.exists():
        return repo_candidate
    metadata_candidate = metadata_path.parent / candidate
    if "[truncated]" not in document_text_path and metadata_candidate.exists():
        return metadata_candidate
    # The SEC feed stores long text paths in compact CSV metadata, where long
    # values may be truncated for preview safety. Recover from the stable run
    # layout instead of trusting the truncated display path.
    run_dir = metadata_path.parent.parent
    return run_dir / "cleaned" / "sec_filing_document_text.txt"


def run_prior_official_document_coverage(inputs: PriorOfficialDocumentCoverageInputs) -> dict[str, Any]:
    source_rows = _read_csv(inputs.source_rows_path)
    metadata = _metadata_by_accession(inputs.document_root)
    rows: list[dict[str, Any]] = []
    for source in source_rows:
        accession = str(source.get("prior_accession_number") or "")
        meta = metadata.get(accession)
        if meta is None:
            status = "missing_prior_official_document_text"
            text_present = False
            text_path = ""
            text_length = ""
        else:
            text_path_obj = _resolve_text_path(Path(meta["metadata_path"]), str(meta.get("document_text_path") or ""))
            text_present = text_path_obj.exists() and text_path_obj.stat().st_size > 0
            status = "prior_official_document_text_present_uninterpreted" if text_present else "missing_prior_official_document_text"
            text_path = str(text_path_obj)
            text_length = meta.get("text_length", "")
        rows.append(
            {
                "symbol": source.get("symbol"),
                "event_id": source.get("event_id"),
                "event_date": source.get("event_date"),
                "prior_accession_number": accession,
                "prior_filing_date": source.get("prior_filing_date"),
                "prior_form": source.get("prior_form"),
                "prior_primary_document": source.get("prior_primary_document"),
                "prior_official_document_coverage_status": status,
                "prior_document_text_present": text_present,
                "prior_document_text_path": text_path,
                "prior_document_text_length": text_length,
                "accepted_prior_guidance_baseline_count": 0,
                "signed_direction_ready": False,
                "provider_calls_performed_by_study": 0,
            }
        )
    counts = Counter(str(row["prior_official_document_coverage_status"]) for row in rows)
    present = counts.get("prior_official_document_text_present_uninterpreted", 0)
    report = {
        "schema": "earnings_guidance_prior_official_document_coverage_v1",
        "status": "blocked_prior_guidance_documents_present_uninterpreted" if present else "blocked_missing_prior_official_document_text",
        "provider_calls_performed_by_study": 0,
        "event_count": len(rows),
        "prior_official_document_text_present_event_count": present,
        "accepted_prior_guidance_baseline_count": 0,
        "signed_direction_ready_count": 0,
        "prior_official_document_coverage_status_counts": dict(sorted(counts.items())),
        "interpretation": [
            "Prior official document text coverage is necessary for prior-company-guidance baselines, but not sufficient.",
            "Documents remain uninterpreted until reviewed guidance extraction creates accepted prior-guidance baseline rows.",
            "No signed guidance-surprise or alpha claim is unlocked by document coverage alone.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_official_document_coverage_rows.csv", rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_official_document_coverage_group_stats.csv", [{"prior_official_document_coverage_status": key, "n_events": value} for key, value in sorted(counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Prior official guidance document coverage

This no-provider artifact checks whether selected prior official guidance source candidates have local official document text.

- Events: {len(rows)}
- Prior official document text present: {present}
- Accepted prior guidance baselines: 0
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: prior official documents are now available for review, but guidance-baseline interpretation is still required.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["PriorOfficialDocumentCoverageInputs", "run_prior_official_document_coverage"]
