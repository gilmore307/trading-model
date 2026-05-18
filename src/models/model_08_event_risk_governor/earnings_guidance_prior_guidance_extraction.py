"""Extract reviewed prior-company-guidance baseline context from official filings.

This no-provider pass consumes selected prior official document text. It accepts
only explicit guidance/outlook sections as prior-company-guidance baseline
context and rejects generic forward-looking/safe-harbor language. It does not
compare to current results, infer raise/cut, or emit signed claims.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PriorGuidanceExtractionInputs:
    coverage_rows_path: Path
    output_dir: Path


ACCEPT_PATTERNS = (
    r"\b(outlook|guidance)\b.{0,300}\b(expect|estimated|expects|forecast|project|anticipate|target)\b",
    r"\b(unit\s+\d?q\s+\d{4}\s+outlook)\b",
    r"\bother guidance\b",
)
REJECT_PATTERNS = (
    r"forward-looking statements?",
    r"actual results (?:could|may|might) differ",
    r"risk factors?",
    r"safe harbor",
    r"words or phrases such as",
    r"expectations, estimates, and projections",
    r"not necessarily indicative",
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


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _window(text: str, start: int, end: int, radius: int = 500) -> str:
    return text[max(0, start - radius): min(len(text), end + radius)].strip()


def _is_rejected(span: str) -> bool:
    lowered = span.lower()
    return any(re.search(pattern, lowered) for pattern in REJECT_PATTERNS)


def _extract_spans(text: str) -> list[dict[str, Any]]:
    lowered = text.lower()
    spans: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pattern in ACCEPT_PATTERNS:
        for match in re.finditer(pattern, lowered, flags=re.IGNORECASE):
            span = _window(text, match.start(), match.end())
            key = span[:240]
            if key in seen:
                continue
            seen.add(key)
            if _is_rejected(span):
                continue
            spans.append({
                "span_index": len(spans) + 1,
                "matched_pattern": pattern,
                "evidence_text": span,
                "evidence_confidence_score": 0.72,
                "prior_guidance_baseline_status": "accepted_prior_company_guidance_context_baseline",
                "baseline_type": "prior_company_guidance",
            })
    return spans


def run_prior_guidance_extraction(inputs: PriorGuidanceExtractionInputs) -> dict[str, Any]:
    coverage_rows = _read_csv(inputs.coverage_rows_path)
    event_rows: list[dict[str, Any]] = []
    span_rows: list[dict[str, Any]] = []
    for row in coverage_rows:
        text_path = Path(str(row.get("prior_document_text_path") or ""))
        spans: list[dict[str, Any]] = []
        if row.get("prior_official_document_coverage_status") == "prior_official_document_text_present_uninterpreted" and text_path.exists():
            spans = _extract_spans(_clean_text(text_path.read_text(encoding="utf-8", errors="ignore")))
        if spans:
            status = "accepted_prior_company_guidance_context_baseline"
            review_status = "reviewed_prior_guidance_context"
        elif row.get("prior_official_document_coverage_status") == "prior_official_document_text_present_uninterpreted":
            status = "reviewed_no_prior_guidance_context_found"
            review_status = "reviewed_rejected_or_missing_guidance_context"
        else:
            status = "missing_prior_official_document_text"
            review_status = "insufficient_evidence"
        for span in spans:
            span_rows.append({
                "symbol": row.get("symbol"),
                "event_id": row.get("event_id"),
                "event_date": row.get("event_date"),
                "prior_accession_number": row.get("prior_accession_number"),
                "prior_filing_date": row.get("prior_filing_date"),
                "prior_form": row.get("prior_form"),
                "prior_primary_document": row.get("prior_primary_document"),
                **span,
            })
        event_rows.append({
            "symbol": row.get("symbol"),
            "event_id": row.get("event_id"),
            "event_date": row.get("event_date"),
            "prior_accession_number": row.get("prior_accession_number"),
            "prior_filing_date": row.get("prior_filing_date"),
            "prior_form": row.get("prior_form"),
            "prior_primary_document": row.get("prior_primary_document"),
            "prior_guidance_baseline_status": status,
            "review_status": review_status,
            "accepted_prior_guidance_span_count": len(spans),
            "baseline_type": "prior_company_guidance" if spans else "missing",
            "guidance_surprise_readiness": "blocked_pending_current_guidance_comparison" if spans else "blocked_missing_prior_guidance_baseline_context",
            "signed_direction_readiness": "blocked_pending_current_guidance_comparison_and_revenue_consensus" if spans else "blocked_missing_prior_guidance_baseline_context",
            "provider_calls_performed_by_study": 0,
        })
    counts = Counter(str(row["prior_guidance_baseline_status"]) for row in event_rows)
    accepted_events = counts.get("accepted_prior_company_guidance_context_baseline", 0)
    report = {
        "schema": "earnings_guidance_prior_guidance_extraction_v1",
        "status": "partial_prior_guidance_baseline_context_extracted" if accepted_events else "blocked_no_prior_guidance_baseline_context_extracted",
        "provider_calls_performed_by_study": 0,
        "event_count": len(event_rows),
        "accepted_prior_guidance_baseline_event_count": accepted_events,
        "accepted_prior_guidance_span_count": len(span_rows),
        "signed_direction_ready_count": 0,
        "prior_guidance_baseline_status_counts": dict(sorted(counts.items())),
        "interpretation": [
            "Accepted prior-company-guidance context is baseline evidence only, not a guidance surprise label.",
            "Current guidance/result comparison is still required before raise/cut or signed direction can be reviewed.",
            "Revenue consensus remains a separate baseline gap.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_baseline_rows.csv", event_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_baseline_spans.csv", span_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_baseline_group_stats.csv", [{"prior_guidance_baseline_status": key, "n_events": value} for key, value in sorted(counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Prior official guidance baseline extraction

This no-provider artifact extracts reviewed prior-company-guidance context from selected prior official filing documents.

- Events: {len(event_rows)}
- Accepted prior guidance baseline events: {accepted_events}
- Accepted prior guidance spans: {len(span_rows)}
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: accepted prior guidance context is baseline evidence only. Current guidance comparison and revenue consensus remain unresolved.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["PriorGuidanceExtractionInputs", "run_prior_guidance_extraction"]
