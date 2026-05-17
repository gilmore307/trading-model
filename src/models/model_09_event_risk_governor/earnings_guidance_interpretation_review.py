"""Conservative review of official earnings/guidance candidate spans.

This review consumes candidate spans extracted from official document text. It is
not a signed outcome model and performs no provider calls. It separates partial
future operating/financial context from rejected boilerplate/accounting/risk
language, while keeping expectation baselines and signed-direction readiness
blocked.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GuidanceInterpretationReviewInputs:
    candidate_rows_path: Path
    candidate_spans_path: Path
    output_dir: Path


REJECT_PATTERNS = (
    r"forward-looking statements?",
    r"actual results (?:could|may|might) differ",
    r"risk factors?",
    r"safe harbor",
    r"not necessarily indicative",
    r"expected credit losses?",
    r"expected return on plan assets?",
    r"recent accounting guidance",
    r"the guidance requires",
    r"foreign currency",
    r"hedging transactions?",
    r"goodwill was primarily attributed",
    r"not expected to be deductible",
    r"deferred tax",
    r"expected resale value guarantee",
    r"pension benefits?",
    r"postretirement benefits?",
    r"operating lease obligations?",
    r"future minimum lease payments?",
)

PARTIAL_CONTEXT_PATTERNS = (
    r"we expect (?:to recognize|costs?|cloud service agreements|[^.]{0,80}\$)",
    r"we do not anticipate any material near-term financial impacts?",
    r"expected to enable",
    r"expected benefits and impacts",
    r"longer-term revenue expectations?",
    r"anticipated benefits and projected synergies",
    r"expected to be recognized in the next 12 months",
    r"expected to be recognized over",
    r"expected commercial projections",
    r"expected to have a material impact",
    r"future related revenue growth expectations?",
)

NEGATIVE_CONTEXT_PATTERNS = (
    r"no assurance",
    r"may not achieve expected returns",
    r"competition to intensify",
    r"could adversely impact",
    r"potential failure to achieve expected",
)

POSITIVE_CONTEXT_PATTERNS = (
    r"expected to enable",
    r"anticipated benefits",
    r"projected synergies",
    r"margin improvement",
    r"revenue to increase",
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


def _matches(text: str, patterns: Sequence[str]) -> list[str]:
    lowered = text.lower()
    return [pattern for pattern in patterns if re.search(pattern, lowered)]


def _direction_bias(text: str) -> float:
    if _matches(text, NEGATIVE_CONTEXT_PATTERNS):
        return -0.25
    if _matches(text, POSITIVE_CONTEXT_PATTERNS):
        return 0.25
    return 0.0


def _classify_span(span: Mapping[str, str]) -> dict[str, Any]:
    text = span.get("evidence_text") or ""
    if span.get("candidate_class") == "boilerplate_or_safe_harbor" or _matches(text, REJECT_PATTERNS):
        status = "rejected_boilerplate_accounting_or_risk_language"
        interpretation_type = "none"
        confidence = 0.85
        direction = 0.0
    elif _matches(text, PARTIAL_CONTEXT_PATTERNS):
        status = "partial_official_guidance_context_reviewed"
        interpretation_type = "future_operating_or_financial_context"
        confidence = 0.65
        direction = _direction_bias(text)
    else:
        status = "rejected_generic_expectation_language"
        interpretation_type = "none"
        confidence = 0.7
        direction = 0.0
    return {
        "symbol": span.get("symbol"),
        "event_id": span.get("event_id"),
        "event_date": span.get("event_date"),
        "result_accession_number": span.get("result_accession_number"),
        "result_primary_document": span.get("result_primary_document"),
        "span_index": span.get("span_index"),
        "reviewed_guidance_span_status": status,
        "guidance_interpretation_type": interpretation_type,
        "direction_bias_score": direction,
        "evidence_confidence_score": confidence,
        "matched_terms": span.get("matched_terms"),
        "review_notes": "candidate span is review evidence only; expectation baseline missing",
        "evidence_text": text,
    }


def _event_summary(candidate_row: Mapping[str, str], reviewed_spans: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    partial = [row for row in reviewed_spans if row.get("reviewed_guidance_span_status") == "partial_official_guidance_context_reviewed"]
    rejected = [row for row in reviewed_spans if str(row.get("reviewed_guidance_span_status") or "").startswith("rejected_")]
    if partial:
        status = "partial_official_guidance_context_reviewed"
        review_status = "reviewed_partial_context"
        direction = sum(float(row.get("direction_bias_score") or 0) for row in partial) / len(partial)
        confidence = sum(float(row.get("evidence_confidence_score") or 0) for row in partial) / len(partial)
    elif rejected:
        status = "reviewed_no_accepted_guidance_context"
        review_status = "reviewed_rejected_candidates"
        direction = 0.0
        confidence = 0.7
    else:
        status = "insufficient_candidate_evidence"
        review_status = "insufficient_evidence"
        direction = 0.0
        confidence = 0.0
    return {
        "symbol": candidate_row.get("symbol"),
        "event_id": candidate_row.get("event_id"),
        "event_date": candidate_row.get("event_date"),
        "event_name": candidate_row.get("event_name"),
        "result_accession_number": candidate_row.get("result_accession_number"),
        "result_primary_document": candidate_row.get("result_primary_document"),
        "reviewed_guidance_interpretation_status": status,
        "review_status": review_status,
        "partial_guidance_context_span_count": len(partial),
        "rejected_candidate_span_count": len(rejected),
        "direction_bias_score": direction,
        "evidence_confidence_score": confidence,
        "accepted_guidance_raise_cut_status": "missing_not_established",
        "beat_miss_status": "missing_expectation_baseline",
        "expectation_baseline_status": "missing_consensus_or_accepted_expectation_baseline",
        "signed_direction_readiness": "blocked_missing_expectation_baseline",
        "event_risk_governor_readiness": "direction_neutral_context_only" if partial else "not_actionable_guidance_context",
        "provider_calls_performed_by_study": 0,
    }


def run_guidance_interpretation_review(inputs: GuidanceInterpretationReviewInputs) -> dict[str, Any]:
    candidate_rows = _read_csv(inputs.candidate_rows_path)
    spans = _read_csv(inputs.candidate_spans_path)
    reviewed_spans = [_classify_span(span) for span in spans]
    spans_by_event: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in reviewed_spans:
        spans_by_event[str(row.get("event_id") or "")].append(row)
    event_rows = [_event_summary(row, spans_by_event.get(str(row.get("event_id") or ""), [])) for row in candidate_rows]
    status_counts = Counter(str(row.get("reviewed_guidance_interpretation_status") or "missing") for row in event_rows)
    partial_count = status_counts.get("partial_official_guidance_context_reviewed", 0)
    report = {
        "schema": "earnings_guidance_interpretation_review_v1",
        "status": "blocked_missing_expectation_baselines_for_signed_claims",
        "provider_calls_performed_by_study": 0,
        "event_count": len(event_rows),
        "partial_guidance_context_event_count": partial_count,
        "reviewed_no_accepted_guidance_context_event_count": status_counts.get("reviewed_no_accepted_guidance_context", 0),
        "accepted_guidance_raise_cut_count": 0,
        "expectation_baseline_count": 0,
        "signed_direction_ready_count": 0,
        "reviewed_guidance_interpretation_status_counts": dict(sorted(status_counts.items())),
        "interpretation": [
            "Partial official guidance context means a reviewed future operating/financial context span exists, not that guidance was raised/cut or beat/miss was established.",
            "Generic safe-harbor, accounting guidance, pension/lease/accounting estimates, and risk language are rejected for guidance interpretation.",
            "No signed earnings/guidance claim is allowed because point-in-time expectation baselines remain missing.",
            "EventRiskGovernor consumption remains direction-neutral context only unless a later reviewed policy explicitly accepts stronger intervention evidence.",
        ],
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_interpretation_review_rows.csv", event_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_interpretation_review_spans.csv", reviewed_spans)
    _write_csv(inputs.output_dir / "earnings_guidance_interpretation_review_group_stats.csv", [{"reviewed_guidance_interpretation_status": key, "n_events": value} for key, value in sorted(status_counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance interpretation review

This no-provider artifact reviews guidance/outlook-like candidate spans from official SEC documents.

- Events: {len(event_rows)}
- Partial official guidance-context events: {partial_count}
- Reviewed no accepted guidance-context events: {report['reviewed_no_accepted_guidance_context_event_count']}
- Accepted guidance raise/cut rows: 0
- Expectation baselines: 0
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: this creates reviewed partial context only. Signed earnings/guidance claims remain blocked until point-in-time expectation baselines exist.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["GuidanceInterpretationReviewInputs", "run_guidance_interpretation_review"]
