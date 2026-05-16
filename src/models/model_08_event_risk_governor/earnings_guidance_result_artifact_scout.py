"""Official result-artifact scouting for earnings/guidance events.

The study performs no provider calls. It consumes already-acquired local SEC
submission/companyfacts artifacts and canonical earnings scheduled-shell event
windows. SEC filings/facts are official result artifacts, but this scout does
not claim consensus beat/miss or guidance surprise because those require
additional point-in-time consensus/company-guidance sources.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


RESULT_FORMS = {"8-K", "10-Q", "10-K", "10-Q/A", "10-K/A"}
RESULT_WINDOW_BEFORE_DAYS = 1
RESULT_WINDOW_AFTER_DAYS = 21
REVENUE_TAGS = ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet")
INCOME_TAGS = ("NetIncomeLoss", "ProfitLoss")
EPS_TAGS = ("EarningsPerShareDiluted", "EarningsPerShareBasic")
METRIC_TAG_GROUPS = {
    "revenue": REVENUE_TAGS,
    "net_income": INCOME_TAGS,
    "eps": EPS_TAGS,
}


@dataclass(frozen=True)
class ResultArtifactInputs:
    event_windows_path: Path
    sec_submission_paths: tuple[Path, ...]
    sec_company_fact_paths: tuple[Path, ...]
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


def _date(text: Any) -> date | None:
    if text in (None, ""):
        return None
    try:
        return date.fromisoformat(str(text)[:10])
    except ValueError:
        return None


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _avg(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(xs) / len(xs) if xs else None


def _positive_rate(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(1 for value in xs if value > 0) / len(xs) if xs else None


def _symbol_from_path(path: Path) -> str:
    parts = [part.upper() for part in path.parts]
    for marker in ("SEC_SUBMISSION", "SEC_COMPANY_FACT"):
        if marker in parts:
            idx = parts.index(marker)
            if idx + 1 < len(parts):
                return parts[idx + 1]
    for part in reversed(parts):
        if part in {"AAPL", "MSFT", "NVDA", "AMD", "JPM", "XOM", "CVX", "LLY", "PFE", "COIN", "TSLA", "RKLB"}:
            return part
    return ""


def load_submissions(paths: Iterable[Path]) -> dict[str, list[dict[str, Any]]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        symbol = _symbol_from_path(path)
        for row in _read_csv(path):
            filing_date = _date(row.get("filing_date"))
            if filing_date is None:
                continue
            item = dict(row)
            item["symbol"] = symbol
            item["filing_date_obj"] = filing_date
            by_symbol[symbol].append(item)
    for rows in by_symbol.values():
        rows.sort(key=lambda row: (row["filing_date_obj"], row.get("accession_number") or ""))
    return dict(by_symbol)


def load_facts(paths: Iterable[Path]) -> dict[str, list[dict[str, Any]]]:
    by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for path in paths:
        symbol = _symbol_from_path(path)
        for row in _read_csv(path):
            tag = row.get("tag") or ""
            if not any(tag in tags for tags in METRIC_TAG_GROUPS.values()):
                continue
            filed = _date(row.get("filed"))
            fy = _int(row.get("fy"))
            value = _float(row.get("value"))
            if filed is None or fy is None or value is None:
                continue
            item = dict(row)
            item.update({"symbol": symbol, "filed_obj": filed, "fy_int": fy, "value_float": value})
            by_symbol[symbol].append(item)
    return dict(by_symbol)


def _candidate_filings(submissions: Sequence[Mapping[str, Any]], event_date: date) -> list[Mapping[str, Any]]:
    start = event_date - timedelta(days=RESULT_WINDOW_BEFORE_DAYS)
    end = event_date + timedelta(days=RESULT_WINDOW_AFTER_DAYS)
    rows = [row for row in submissions if row.get("form") in RESULT_FORMS and start <= row["filing_date_obj"] <= end]
    rows.sort(key=lambda row: (0 if row.get("form") == "8-K" else 1, abs((row["filing_date_obj"] - event_date).days), row["filing_date_obj"]))
    return rows


def _fact_for_accession(facts: Sequence[Mapping[str, Any]], accession: str, tags: Sequence[str]) -> Mapping[str, Any] | None:
    rows = [row for row in facts if row.get("accession_number") == accession and row.get("tag") in tags]
    if not rows:
        return None
    rows.sort(key=lambda row: (row.get("fy_int") or 0, str(row.get("end") or "")), reverse=True)
    return rows[0]


def _prior_fact(facts: Sequence[Mapping[str, Any]], current: Mapping[str, Any], tags: Sequence[str]) -> Mapping[str, Any] | None:
    fy = current.get("fy_int")
    if not isinstance(fy, int):
        return None
    fp = current.get("fp")
    filed = current.get("filed_obj")
    rows = [
        row
        for row in facts
        if row.get("tag") in tags
        and row.get("fp") == fp
        and row.get("fy_int") == fy - 1
        and row.get("filed_obj") <= filed
    ]
    if not rows:
        return None
    rows.sort(key=lambda row: (row.get("filed_obj"), str(row.get("end") or "")), reverse=True)
    return rows[0]


def _metric_rows(symbol: str, event_id: str, filing: Mapping[str, Any] | None, facts: Sequence[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if filing is None:
        return [], {"result_metric_count": 0, "positive_metric_count": 0, "negative_metric_count": 0, "result_direction_score": None}
    accession = str(filing.get("accession_number") or "")
    rows: list[dict[str, Any]] = []
    signs: list[float] = []
    for metric, tags in METRIC_TAG_GROUPS.items():
        current = _fact_for_accession(facts, accession, tags)
        prior = _prior_fact(facts, current, tags) if current is not None else None
        current_value = _float(current.get("value_float")) if current else None
        prior_value = _float(prior.get("value_float")) if prior else None
        yoy_change = None
        yoy_change_pct = None
        direction = "missing"
        if current_value is not None and prior_value not in (None, 0):
            yoy_change = current_value - prior_value
            yoy_change_pct = yoy_change / abs(prior_value)
            direction = "positive" if yoy_change > 0 else "negative" if yoy_change < 0 else "flat"
            signs.append(1.0 if yoy_change > 0 else -1.0 if yoy_change < 0 else 0.0)
        rows.append({
            "symbol": symbol,
            "event_id": event_id,
            "metric": metric,
            "current_tag": current.get("tag") if current else "missing",
            "current_fy": current.get("fy") if current else "",
            "current_fp": current.get("fp") if current else "",
            "current_filed": current.get("filed") if current else "",
            "current_end": current.get("end") if current else "",
            "current_value": current_value,
            "prior_value": prior_value,
            "yoy_change": yoy_change,
            "yoy_change_pct": yoy_change_pct,
            "direction": direction,
            "source_accession_number": accession,
        })
    return rows, {
        "result_metric_count": len(signs),
        "positive_metric_count": sum(1 for sign in signs if sign > 0),
        "negative_metric_count": sum(1 for sign in signs if sign < 0),
        "result_direction_score": _avg(signs),
    }


def run_result_artifact_scout(inputs: ResultArtifactInputs) -> dict[str, Any]:
    events = _read_csv(inputs.event_windows_path)
    submissions = load_submissions(inputs.sec_submission_paths)
    facts = load_facts(inputs.sec_company_fact_paths)
    interpreted: list[dict[str, Any]] = []
    filing_rows: list[dict[str, Any]] = []
    metric_rows: list[dict[str, Any]] = []
    for event in events:
        symbol = str(event.get("symbol") or "").upper()
        event_date = _date(event.get("event_date"))
        if event_date is None:
            continue
        candidates = _candidate_filings(submissions.get(symbol, []), event_date)
        selected = candidates[0] if candidates else None
        rows: list[dict[str, Any]] = []
        summary: dict[str, Any] = {"result_metric_count": 0, "positive_metric_count": 0, "negative_metric_count": 0, "result_direction_score": None}
        # Prefer the official filing in the window that actually carries XBRL result facts.
        # Same-day 8-Ks often establish release visibility, while the 10-Q/10-K may carry
        # the machine-readable result values a few days later. Both remain PIT artifacts;
        # the chosen interpretation filing is the one with the most available metrics.
        for candidate in candidates:
            candidate_rows, candidate_summary = _metric_rows(symbol, str(event.get("event_id") or ""), candidate, facts.get(symbol, []))
            candidate_count = int(candidate_summary.get("result_metric_count") or 0)
            selected_count = int(summary.get("result_metric_count") or 0)
            if selected is None or candidate_count > selected_count:
                selected = candidate
                rows = candidate_rows
                summary = candidate_summary
        if selected:
            filing_rows.append({
                "symbol": symbol,
                "event_id": event.get("event_id"),
                "event_date": event_date.isoformat(),
                "filing_date": selected.get("filing_date"),
                "report_date": selected.get("report_date"),
                "form": selected.get("form"),
                "accession_number": selected.get("accession_number"),
                "primary_document": selected.get("primary_document"),
                "primary_doc_description": selected.get("primary_doc_description"),
                "candidate_count": len(candidates),
                "selected_for": "official_result_metric_interpretation" if int(summary.get("result_metric_count") or 0) > 0 else "official_result_artifact_visibility",
            })
        metric_rows.extend(rows)
        metric_count = int(summary["result_metric_count"] or 0)
        if selected is None:
            interpretation_status = "missing_official_result_artifact"
        elif metric_count >= 2:
            interpretation_status = "partial_official_result_interpretation"
        else:
            interpretation_status = "official_result_artifact_only"
        interpreted.append({
            **event,
            "official_result_artifact_status": "present" if selected else "missing",
            "result_interpretation_status": interpretation_status,
            "result_filing_form": selected.get("form") if selected else "",
            "result_filing_date": selected.get("filing_date") if selected else "",
            "result_accession_number": selected.get("accession_number") if selected else "",
            "result_metric_count": summary["result_metric_count"],
            "positive_metric_count": summary["positive_metric_count"],
            "negative_metric_count": summary["negative_metric_count"],
            "result_direction_score": summary["result_direction_score"],
            "guidance_status": "missing_official_guidance_interpretation",
        })
    groups: list[dict[str, Any]] = []
    by_status: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_score: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in interpreted:
        by_status[str(row["result_interpretation_status"])].append(row)
        score = _float(row.get("result_direction_score"))
        bucket = "positive_result_score" if score is not None and score > 0 else "negative_result_score" if score is not None and score < 0 else "missing_or_flat_result_score"
        by_score[bucket].append(row)
    for group_name, rows in {**by_status, **by_score}.items():
        item: dict[str, Any] = {"group": group_name, "n_events": len(rows), "n_symbols": len({row.get("symbol") for row in rows})}
        for horizon in (1, 5, 10, 14):
            for metric in ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae"):
                item[f"avg_event_{metric}_{horizon}d"] = _avg(_float(row.get(f"event_{metric}_{horizon}d")) for row in rows)
                item[f"positive_rate_event_{metric}_{horizon}d"] = _positive_rate(_float(row.get(f"event_{metric}_{horizon}d")) for row in rows)
        groups.append(item)
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_result_interpreted_events.csv", interpreted)
    _write_csv(inputs.output_dir / "official_result_filing_rows.csv", filing_rows)
    _write_csv(inputs.output_dir / "official_result_metric_rows.csv", metric_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_result_group_stats.csv", groups)
    report = {
        "schema": "earnings_guidance_result_artifact_scout_v1",
        "status": "diagnostic_scouting_not_promotion_evidence",
        "provider_calls_performed_by_study": 0,
        "event_count": len(interpreted),
        "official_result_artifact_count": sum(1 for row in interpreted if row["official_result_artifact_status"] == "present"),
        "partial_result_interpretation_count": sum(1 for row in interpreted if row["result_interpretation_status"] == "partial_official_result_interpretation"),
        "guidance_interpretation_count": 0,
        "sec_submission_artifact_count": len(inputs.sec_submission_paths),
        "sec_company_fact_artifact_count": len(inputs.sec_company_fact_paths),
        "interpretation": [
            "SEC submissions/companyfacts are official result artifacts, but this scout only derives simple reported-metric YoY direction when facts are available.",
            "Consensus beat/miss and guidance surprise remain missing; do not use this as signed-alpha evidence.",
            "JPM-style very large SEC companyfacts artifacts may be unavailable/truncated locally; missing metrics are recorded as partial/missing rather than fabricated.",
        ],
        "group_stats": groups,
    }
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance result-artifact scout

This artifact joins canonical earnings scheduled-shell windows to official SEC submission/companyfacts artifacts.

- Events: {report['event_count']}
- Official result artifacts found: {report['official_result_artifact_count']}
- Partial official result interpretations: {report['partial_result_interpretation_count']}
- Guidance interpretations: 0

This is scouting only. It does not include consensus beat/miss, official guidance parsing, or option-abnormality control verification.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["ResultArtifactInputs", "run_result_artifact_scout"]
