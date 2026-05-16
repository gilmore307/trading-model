"""Candidate guidance-evidence scout for official earnings documents.

This scout performs no provider calls. It scans already-acquired official SEC
filing/release text artifacts for guidance/outlook-like evidence spans. It does
not produce accepted guidance interpretation, beat/miss, raise/cut, or signed
claims; candidates remain review-required until an accepted interpretation
standard and point-in-time expectation baseline are available.
"""
from __future__ import annotations

import csv
import html
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


GUIDANCE_TERMS = (
    "guidance",
    "outlook",
    "expect",
    "expects",
    "expected",
    "forecast",
    "forecasts",
    "project",
    "projects",
    "projected",
    "anticipate",
    "anticipates",
    "full year",
    "next quarter",
    "fiscal 2026",
    "revenue guidance",
)

BOILERPLATE_TERMS = (
    "forward-looking statement",
    "forward looking statement",
    "actual results",
    "risk factors",
    "uncertainties",
    "could differ",
    "may differ",
    "sec filings",
    "undertake no obligation",
    "safe harbor",
)

MAX_SPANS_PER_EVENT = 8
MAX_SNIPPET_CHARS = 420


@dataclass(frozen=True)
class GuidanceTextCandidateInputs:
    interpreted_events_path: Path
    result_filings_path: Path
    input_document_manifest_path: Path
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


def _key(accession_number: Any, document_name: Any) -> tuple[str, str]:
    return (str(accession_number or "").strip(), str(document_name or "").strip())


def _resolve_text_path(metadata_path: Path, value: str) -> Path:
    raw = Path(value)
    if raw.is_absolute():
        return raw
    for parent in (metadata_path.parent, *metadata_path.parents):
        candidate = parent / raw
        if candidate.exists():
            return candidate
    return raw


def _load_document_rows(manifest_path: Path) -> dict[tuple[str, str], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for item in manifest.get("document_metadata", []):
        metadata_path = Path(str(item.get("metadata_path") or ""))
        if not metadata_path.exists():
            continue
        for row in _read_csv(metadata_path):
            key = _key(row.get("accession_number"), row.get("document_name"))
            if not all(key):
                continue
            text_path = _resolve_text_path(metadata_path, str(row.get("document_text_path") or ""))
            merged = dict(row)
            merged["metadata_path"] = str(metadata_path)
            merged["resolved_document_text_path"] = str(text_path)
            out[key] = merged
    return out


def _plain_text(raw: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", raw, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence_windows(text: str) -> Iterable[tuple[int, int, str]]:
    pattern = re.compile(r"[^.!?;]{0,520}(?:[.!?;]|$)")
    for match in pattern.finditer(text):
        sentence = match.group(0).strip()
        if len(sentence) < 30:
            continue
        yield match.start(), match.end(), sentence


def _matched_terms(sentence: str, terms: Sequence[str]) -> list[str]:
    lowered = sentence.lower()
    return [term for term in terms if term in lowered]


def _is_boilerplate(sentence: str) -> bool:
    lowered = sentence.lower()
    return any(term in lowered for term in BOILERPLATE_TERMS)


def _candidate_spans(text: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    for start, end, sentence in _sentence_windows(text):
        terms = _matched_terms(sentence, GUIDANCE_TERMS)
        if not terms:
            continue
        boilerplate = _is_boilerplate(sentence)
        spans.append(
            {
                "span_start_char": start,
                "span_end_char": end,
                "matched_terms": ";".join(terms),
                "boilerplate_or_safe_harbor_flag": boilerplate,
                "candidate_class": "boilerplate_or_safe_harbor" if boilerplate else "candidate_guidance_or_outlook_text",
                "evidence_text": sentence[:MAX_SNIPPET_CHARS],
            }
        )
        if len(spans) >= MAX_SPANS_PER_EVENT:
            break
    return spans


def _event_rows(
    events: Sequence[Mapping[str, str]],
    filings_by_event: Mapping[str, Mapping[str, str]],
    documents_by_key: Mapping[tuple[str, str], Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    summary_rows: list[dict[str, Any]] = []
    span_rows: list[dict[str, Any]] = []
    for event in events:
        event_id = str(event.get("event_id") or "")
        filing = filings_by_event.get(event_id, {})
        accession = filing.get("accession_number") or event.get("result_accession_number") or ""
        document_name = filing.get("primary_document") or ""
        document = documents_by_key.get(_key(accession, document_name), {})
        text_path = Path(str(document.get("resolved_document_text_path") or ""))
        text_status = "present" if text_path.exists() else "missing"
        spans: list[dict[str, Any]] = []
        if text_path.exists():
            spans = _candidate_spans(_plain_text(text_path.read_text(encoding="utf-8", errors="ignore")))
        non_boilerplate = [span for span in spans if not span["boilerplate_or_safe_harbor_flag"]]
        boilerplate = [span for span in spans if span["boilerplate_or_safe_harbor_flag"]]
        if text_status == "missing":
            status = "missing_official_document_text"
        elif non_boilerplate:
            status = "candidate_guidance_text_present_review_required"
        elif boilerplate:
            status = "boilerplate_or_safe_harbor_only_review_required"
        else:
            status = "no_candidate_guidance_text_found"
        summary = {
            "symbol": event.get("symbol"),
            "event_id": event_id,
            "event_date": event.get("event_date"),
            "event_name": event.get("event_name"),
            "result_accession_number": accession,
            "result_primary_document": document_name,
            "official_document_text_status": text_status,
            "candidate_guidance_span_count": len(spans),
            "non_boilerplate_candidate_guidance_span_count": len(non_boilerplate),
            "boilerplate_candidate_span_count": len(boilerplate),
            "guidance_candidate_status": status,
            "accepted_guidance_interpretation_status": "missing_reviewed_guidance_interpretation",
            "expectation_baseline_status": "missing_consensus_or_accepted_expectation_baseline",
            "signed_direction_readiness": "blocked_missing_reviewed_guidance_interpretation_or_expectation_baseline",
            "review_status": "review_required" if spans else "insufficient_evidence",
            "provider_calls_performed_by_study": 0,
        }
        summary_rows.append(summary)
        for index, span in enumerate(spans, start=1):
            span_rows.append({**{key: summary[key] for key in ("symbol", "event_id", "event_date", "result_accession_number", "result_primary_document")}, "span_index": index, **span})
    return summary_rows, span_rows


def run_guidance_text_candidate_scout(inputs: GuidanceTextCandidateInputs) -> dict[str, Any]:
    events = _read_csv(inputs.interpreted_events_path)
    filings = _read_csv(inputs.result_filings_path)
    filings_by_event = {str(row.get("event_id") or ""): row for row in filings if row.get("event_id")}
    documents_by_key = _load_document_rows(inputs.input_document_manifest_path)
    rows, spans = _event_rows(events, filings_by_event, documents_by_key)
    status_counts = Counter(str(row.get("guidance_candidate_status") or "missing") for row in rows)
    candidate_event_count = sum(1 for row in rows if row.get("guidance_candidate_status") == "candidate_guidance_text_present_review_required")
    report = {
        "schema": "earnings_guidance_text_candidate_scout_v1",
        "status": "blocked_missing_reviewed_guidance_interpretation_and_expectation_baseline",
        "provider_calls_performed_by_study": 0,
        "event_count": len(rows),
        "official_document_text_event_count": sum(1 for row in rows if row.get("official_document_text_status") == "present"),
        "candidate_guidance_text_event_count": candidate_event_count,
        "boilerplate_only_event_count": status_counts.get("boilerplate_or_safe_harbor_only_review_required", 0),
        "no_candidate_guidance_text_event_count": status_counts.get("no_candidate_guidance_text_found", 0),
        "accepted_guidance_interpretation_count": 0,
        "expectation_baseline_count": 0,
        "signed_direction_ready_count": 0,
        "guidance_candidate_status_counts": dict(sorted(status_counts.items())),
        "interpretation": [
            "Candidate guidance/outlook spans are extraction evidence only and remain review-required.",
            "Safe-harbor and forward-looking boilerplate is explicitly separated from candidate guidance text.",
            "No accepted guidance raise/cut, beat/miss, or signed-direction claim is produced by this scout.",
            "Point-in-time expectation baselines remain required before signed earnings/guidance claims.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_text_candidate_rows.csv", rows)
    _write_csv(inputs.output_dir / "earnings_guidance_text_candidate_spans.csv", spans)
    _write_csv(inputs.output_dir / "earnings_guidance_text_candidate_group_stats.csv", [{"guidance_candidate_status": key, "n_events": value} for key, value in sorted(status_counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance official text candidate scout

This no-provider artifact scans acquired official SEC document text for candidate guidance/outlook evidence spans.

- Events: {len(rows)}
- Official document text events: {report['official_document_text_event_count']}
- Candidate guidance-text events requiring review: {candidate_event_count}
- Boilerplate/safe-harbor-only events: {report['boilerplate_only_event_count']}
- No candidate guidance-text events: {report['no_candidate_guidance_text_event_count']}
- Accepted guidance interpretations: 0
- Expectation baselines: 0
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: this artifact narrows the next review queue but does not create signed earnings/guidance claims. Candidate spans require reviewed interpretation and point-in-time expectation baselines before promotion or EventRiskGovernor escalation.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["GuidanceTextCandidateInputs", "run_guidance_text_candidate_scout"]
