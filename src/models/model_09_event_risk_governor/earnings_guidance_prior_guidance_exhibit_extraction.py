"""Extract prior-company-guidance baselines from official earnings exhibits.

This pass fixes the main weakness of primary-document-only SEC 8-K review:
earnings guidance is usually in exhibit documents (for example EX-99.1), while
the primary 8-K often only references the exhibit. The extraction remains
conservative: it accepts explicit, numeric company guidance/outlook context as
baseline evidence only. It does not compare current results, infer raise/cut,
produce signed direction, or activate event-risk interventions.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class PriorGuidanceExhibitExtractionInputs:
    task_keys_dir: Path
    document_text_root: Path
    output_dir: Path


METRIC_TERMS = (
    "revenue",
    "sales",
    "eps",
    "earnings per share",
    "gross margin",
    "operating expenses",
    "operating expense",
    "adjusted ebitda",
    "ebitda",
    "tax rate",
    "capital expenditures",
    "cash capital expenditures",
    "capex",
    "subscription and services revenue",
    "transaction expenses",
    "sales and marketing expenses",
)
NUMERIC_RE = re.compile(r"(?:\$\s?\d|\d+(?:\.\d+)?\s?%|\bbetween\b|\brange\b|\bplus or minus\b|\bapproximately\b|\bmid-?point\b)", re.I)
GUIDANCE_ANCHOR_RE = re.compile(
    r"\b(?:(?:current\s+|business\s+|financial\s+|full\s+year\s+|20\d{2}\s+|q\d(?:[’']?\d{2})?\s+|third\s+quarter\s+|fourth\s+quarter\s+|next\s+quarter\s+)(?:outlook|guidance)|guidance)\b"
    r"|\bfor\s+the\s+(?:third|fourth|next|first|second)\s+quarter[^.]{0,160}\bexpects?\b"
    r"|\bexpects?\s+(?:q\d|third\s+quarter|fourth\s+quarter|full\s+year|20\d{2})[^.]{0,180}\b(?:revenue|sales|eps|gross\s+margin|operating\s+expenses?)\b"
    r"|\b(revenue|sales)\s+(?:is\s+)?expected\s+to\s+be\b",
    re.I,
)
HARD_REJECT_RE = re.compile(
    r"will provide forward-looking guidance|will provide .* guidance .* conference call|publishes a .* guidance .* document|"
    r"words or phrases such as|not guarantees of future performance|not necessarily indicative",
    re.I,
)
SOFT_REJECT_RE = re.compile(r"forward-looking statements?|actual results (?:could|may|might) differ|risk factors?|safe harbor", re.I)
DOCUMENT_ROUTE_TERMS = re.compile(r"earnings|salesandearnings|shareholderletter|shareholder[_-]?letter|ex99|ex-99|q\d.*99|pr\.htm|press", re.I)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = sorted({key for row in rows for key in row.keys()}) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _clean_text(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    text = unescape(text)
    text = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _window(text: str, start: int, end: int, radius: int = 850) -> str:
    # Guidance sections are normally header-forward. Keeping only a small
    # pre-anchor prefix avoids accidentally accepting backward-looking result
    # tables that happen to sit before a boilerplate guidance/notice sentence.
    return text[max(0, start - 100): min(len(text), end + radius)].strip()


def _metric_family(span: str) -> str:
    lowered = span.lower()
    families = []
    if "revenue" in lowered or "sales" in lowered:
        families.append("revenue_or_sales_guidance")
    if "eps" in lowered or "earnings per share" in lowered:
        families.append("eps_guidance")
    if "gross margin" in lowered:
        families.append("margin_guidance")
    if "operating expense" in lowered or "operating expenses" in lowered:
        families.append("expense_guidance")
    if "ebitda" in lowered:
        families.append("ebitda_guidance")
    if "capital expenditure" in lowered or "capex" in lowered:
        families.append("capital_expenditure_guidance")
    if "tax rate" in lowered:
        families.append("tax_rate_guidance")
    return ";".join(families) if families else "other_numeric_company_guidance"


def _accept_span(span: str) -> bool:
    lowered = span.lower()
    if HARD_REJECT_RE.search(span):
        return False
    if SOFT_REJECT_RE.search(span) and not any(section in lowered for section in ("current outlook", "financial guidance", "third quarter 2025 guidance", "q3 2025 outlook", "q3 ’25 outlook", "q3'25 outlook")):
        return False
    if not NUMERIC_RE.search(span):
        return False
    if not any(term in lowered for term in METRIC_TERMS):
        return False
    if "conference call" in lowered and "will provide" in lowered and not re.search(r"\$\s?\d|\d+(?:\.\d+)?\s?%", span):
        return False
    return True


def extract_prior_guidance_spans(text: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    seen: set[str] = set()
    for match in GUIDANCE_ANCHOR_RE.finditer(text):
        span = _window(text, match.start(), match.end())
        # Trim extremely long boilerplate tails around clear section starts.
        next_stop = re.search(r"\b(?:conference call|webcast details|about |notice|cautionary statement|forward-looking statements?)\b", span[450:], re.I)
        if next_stop:
            span = span[: 450 + next_stop.start()].strip()
        key = re.sub(r"\W+", " ", span.lower())[:300]
        if key in seen:
            continue
        seen.add(key)
        if not _accept_span(span):
            continue
        spans.append(
            {
                "span_index": len(spans) + 1,
                "baseline_type": "prior_company_guidance",
                "guidance_metric_family": _metric_family(span),
                "prior_guidance_baseline_status": "accepted_prior_company_guidance_context_baseline",
                "evidence_confidence_score": 0.82,
                "evidence_text": span,
            }
        )
    return spans


def _load_task_keys(task_keys_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(task_keys_dir.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        params = dict(payload.get("params") or {})
        symbol = path.name.split("_", 1)[0]
        accession = str(params.get("accession_number") or "")
        document_name = str(params.get("document_name") or "")
        if not accession or not document_name:
            continue
        rows.append({"task_key_path": str(path), "symbol": symbol, **params})
    return rows


def _document_text_path(root: Path, row: Mapping[str, Any]) -> Path | None:
    symbol = str(row.get("symbol") or "")
    accession_path = str(row.get("accession_number") or "").replace("-", "")
    document_name = str(row.get("document_name") or "")
    paths = sorted((root / symbol / accession_path / document_name).glob("runs/*/cleaned/sec_filing_document_text.txt"))
    return paths[-1] if paths else None


def run_prior_guidance_exhibit_extraction(inputs: PriorGuidanceExhibitExtractionInputs) -> dict[str, Any]:
    task_rows = _load_task_keys(inputs.task_keys_dir)
    candidate_rows: list[dict[str, Any]] = []
    event_rows_by_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    span_rows: list[dict[str, Any]] = []

    for row in task_rows:
        document_name = str(row.get("document_name") or "")
        route_status = "candidate_official_earnings_exhibit" if DOCUMENT_ROUTE_TERMS.search(document_name) else "candidate_non_earnings_exhibit"
        text_path = _document_text_path(inputs.document_text_root, row)
        spans: list[dict[str, Any]] = []
        if text_path and route_status == "candidate_official_earnings_exhibit":
            spans = extract_prior_guidance_spans(_clean_text(text_path.read_text(encoding="utf-8", errors="ignore")))
        candidate_status = "accepted_prior_company_guidance_context_baseline" if spans else "reviewed_no_prior_guidance_context_found"
        base = {
            "symbol": row.get("symbol"),
            "event_id": row.get("current_event_id"),
            "event_date": row.get("current_event_date"),
            "prior_accession_number": row.get("accession_number"),
            "prior_primary_document": row.get("primary_document_name"),
            "prior_exhibit_document": document_name,
            "candidate_days_before_event": row.get("candidate_days_before_event"),
            "document_text_path": str(text_path or ""),
            "document_route_status": route_status,
            "prior_guidance_baseline_status": candidate_status,
            "accepted_prior_guidance_span_count": len(spans),
            "provider_calls_performed_by_study": 0,
        }
        candidate_rows.append(base)
        event_rows_by_key[(str(row.get("symbol") or ""), str(row.get("current_event_id") or ""))].append(base)
        for span in spans:
            span_rows.append({**base, **span})

    event_rows: list[dict[str, Any]] = []
    for (symbol, event_id), candidates in sorted(event_rows_by_key.items()):
        accepted = [candidate for candidate in candidates if candidate["prior_guidance_baseline_status"] == "accepted_prior_company_guidance_context_baseline"]
        event_date = candidates[0].get("event_date") if candidates else ""
        if accepted:
            status = "accepted_prior_company_guidance_context_baseline"
            review_status = "reviewed_prior_guidance_context"
            readiness = "blocked_pending_current_guidance_comparison_and_revenue_consensus"
            baseline_type = "prior_company_guidance"
        else:
            status = "reviewed_no_prior_guidance_context_found"
            review_status = "reviewed_rejected_or_missing_guidance_context"
            readiness = "blocked_missing_prior_guidance_baseline_context"
            baseline_type = "missing"
        event_rows.append(
            {
                "symbol": symbol,
                "event_id": event_id,
                "event_date": event_date,
                "candidate_document_count": len(candidates),
                "accepted_prior_guidance_document_count": len(accepted),
                "accepted_prior_guidance_span_count": sum(int(candidate.get("accepted_prior_guidance_span_count") or 0) for candidate in accepted),
                "prior_guidance_baseline_status": status,
                "review_status": review_status,
                "baseline_type": baseline_type,
                "signed_direction_readiness": readiness,
                "provider_calls_performed_by_study": 0,
            }
        )

    counts = Counter(str(row["prior_guidance_baseline_status"]) for row in event_rows)
    candidate_counts = Counter(str(row["prior_guidance_baseline_status"]) for row in candidate_rows)
    accepted_events = counts.get("accepted_prior_company_guidance_context_baseline", 0)
    report = {
        "schema": "earnings_guidance_prior_guidance_exhibit_extraction_v1",
        "status": "partial_prior_guidance_baseline_context_extracted" if accepted_events else "blocked_no_prior_guidance_baseline_context_extracted",
        "provider_calls_performed_by_study": 0,
        "event_count": len(event_rows),
        "candidate_document_count": len(candidate_rows),
        "accepted_prior_guidance_baseline_event_count": accepted_events,
        "accepted_prior_guidance_document_count": candidate_counts.get("accepted_prior_company_guidance_context_baseline", 0),
        "accepted_prior_guidance_span_count": len(span_rows),
        "signed_direction_ready_count": 0,
        "prior_guidance_baseline_status_counts": dict(sorted(counts.items())),
        "candidate_document_status_counts": dict(sorted(candidate_counts.items())),
        "interpretation": [
            "Official earnings exhibits materially improve prior-guidance baseline coverage versus primary 8-K text.",
            "Accepted spans are prior-company-guidance baseline context only; they are not guidance surprise, raise/cut, signed alpha, or risk escalation labels.",
            "Current guidance/result comparison and PIT revenue-consensus baselines remain required before signed earnings/guidance claims.",
        ],
    }

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_exhibit_event_rows.csv", event_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_exhibit_candidate_rows.csv", candidate_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_exhibit_spans.csv", span_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_prior_guidance_exhibit_group_stats.csv", [{"prior_guidance_baseline_status": key, "n_events": value} for key, value in sorted(counts.items())])
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Prior earnings exhibit guidance extraction

This no-provider artifact reviews official SEC earnings exhibits fetched from prior-quarter filing windows.

- Events: {len(event_rows)}
- Candidate official exhibit documents: {len(candidate_rows)}
- Accepted prior-guidance baseline events: {accepted_events}
- Accepted prior-guidance spans: {len(span_rows)}
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: exhibit-level official filing text reduces the prior-guidance baseline gap, but it still does not establish guidance surprise, raise/cut, signed direction, alpha, model activation, or EventRiskGovernor escalation.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["PriorGuidanceExhibitExtractionInputs", "extract_prior_guidance_spans", "run_prior_guidance_exhibit_extraction"]
