"""Assess current-vs-prior earnings/guidance comparison readiness.

This no-provider pass joins reviewed prior-company-guidance baseline context,
current official guidance-context review rows, and official result artifacts. It
only decides whether the evidence is comparable enough for a reviewed current vs
prior guidance comparison. It does not infer raise/cut, beat/miss, signed alpha,
or EventRiskGovernor escalation.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CurrentPriorComparisonReadinessInputs:
    prior_event_rows_path: Path
    prior_span_rows_path: Path
    current_review_rows_path: Path
    current_review_spans_path: Path
    result_event_rows_path: Path
    output_dir: Path


CURRENT_COMPARABLE_STATUSES = {
    "accepted_current_company_guidance_context",
    "accepted_current_comparable_guidance_context",
    "accepted_current_guidance_raise_cut_context",
}
CURRENT_PARTIAL_STATUS = "partial_official_guidance_context_reviewed"
PRIOR_ACCEPTED_STATUS = "accepted_prior_company_guidance_context_baseline"


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


def _by_event(rows: Sequence[Mapping[str, str]]) -> dict[str, list[Mapping[str, str]]]:
    grouped: dict[str, list[Mapping[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("event_id") or "")].append(row)
    return dict(grouped)


def _first(rows: Sequence[Mapping[str, str]]) -> Mapping[str, str]:
    return rows[0] if rows else {}


def _int(value: Any) -> int:
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return 0


def _current_status(current_spans: Sequence[Mapping[str, str]]) -> tuple[str, int, int]:
    comparable = [row for row in current_spans if str(row.get("reviewed_guidance_span_status") or "") in CURRENT_COMPARABLE_STATUSES]
    partial = [row for row in current_spans if str(row.get("reviewed_guidance_span_status") or "") == CURRENT_PARTIAL_STATUS]
    if comparable:
        return "accepted_current_comparable_guidance_context", len(comparable), len(partial)
    if partial:
        return "blocked_current_guidance_context_not_comparable", 0, len(partial)
    return "blocked_missing_current_comparable_guidance_context", 0, 0


def _readiness(prior_status: str, current_status: str) -> tuple[str, str, str]:
    if prior_status != PRIOR_ACCEPTED_STATUS:
        return (
            "blocked_missing_prior_guidance_baseline_context",
            "blocked_missing_prior_guidance_baseline_context",
            "Prior company-guidance baseline context is missing or rejected.",
        )
    if current_status != "accepted_current_comparable_guidance_context":
        return (
            "blocked_missing_current_comparable_guidance_context",
            "blocked_missing_current_guidance_comparison",
            "Current official text has no accepted comparable company-guidance context; partial context is not a raise/cut comparison.",
        )
    return (
        "current_prior_guidance_context_comparable_pending_pit_expectation_baselines",
        "blocked_pending_pit_expectation_baselines_and_review",
        "Current and prior guidance context is comparable, but signed direction still requires PIT expectation baselines and review.",
    )


def run_current_prior_comparison_readiness(inputs: CurrentPriorComparisonReadinessInputs) -> dict[str, Any]:
    prior_events = _read_csv(inputs.prior_event_rows_path)
    prior_spans = _read_csv(inputs.prior_span_rows_path)
    current_rows = _read_csv(inputs.current_review_rows_path)
    current_spans = _read_csv(inputs.current_review_spans_path)
    result_rows = _read_csv(inputs.result_event_rows_path)

    prior_by_event = _by_event(prior_events)
    prior_spans_by_event = _by_event(prior_spans)
    current_by_event = _by_event(current_rows)
    current_spans_by_event = _by_event(current_spans)
    result_by_event = _by_event(result_rows)
    event_ids = sorted(set(prior_by_event) | set(current_by_event) | set(result_by_event))

    event_rows: list[dict[str, Any]] = []
    for event_id in event_ids:
        prior = _first(prior_by_event.get(event_id, []))
        current = _first(current_by_event.get(event_id, []))
        result = _first(result_by_event.get(event_id, []))
        prior_status = str(prior.get("prior_guidance_baseline_status") or "missing_prior_guidance_baseline_context")
        current_status, current_comparable_count, current_partial_count = _current_status(current_spans_by_event.get(event_id, []))
        comparison_status, signed_readiness, note = _readiness(prior_status, current_status)
        symbol = prior.get("symbol") or current.get("symbol") or result.get("symbol")
        event_date = prior.get("event_date") or current.get("event_date") or result.get("event_date")
        event_rows.append(
            {
                "symbol": symbol,
                "event_id": event_id,
                "event_date": event_date,
                "prior_guidance_baseline_status": prior_status,
                "accepted_prior_guidance_span_count": _int(prior.get("accepted_prior_guidance_span_count")) or len(prior_spans_by_event.get(event_id, [])),
                "current_comparable_guidance_status": current_status,
                "current_comparable_guidance_span_count": current_comparable_count,
                "current_partial_guidance_context_span_count": current_partial_count,
                "official_result_artifact_status": result.get("official_result_artifact_status") or "missing",
                "result_metric_count": result.get("result_metric_count") or "0",
                "guidance_comparison_readiness": comparison_status,
                "accepted_guidance_raise_cut_status": "missing_not_established",
                "beat_miss_status": "missing_expectation_baseline",
                "signed_direction_readiness": signed_readiness,
                "event_risk_governor_readiness": "direction_neutral_context_only",
                "provider_calls_performed_by_study": 0,
                "review_note": note,
            }
        )

    readiness_counts = Counter(str(row["guidance_comparison_readiness"]) for row in event_rows)
    current_counts = Counter(str(row["current_comparable_guidance_status"]) for row in event_rows)
    comparable_count = readiness_counts.get("current_prior_guidance_context_comparable_pending_pit_expectation_baselines", 0)
    report = {
        "schema": "earnings_guidance_current_prior_comparison_readiness_v1",
        "status": "blocked_missing_current_comparable_guidance_context" if comparable_count == 0 else "partial_current_prior_comparison_context_only",
        "provider_calls_performed_by_study": 0,
        "event_count": len(event_rows),
        "accepted_prior_guidance_baseline_event_count": sum(1 for row in event_rows if row["prior_guidance_baseline_status"] == PRIOR_ACCEPTED_STATUS),
        "current_comparable_guidance_event_count": comparable_count,
        "current_partial_guidance_context_event_count": current_counts.get("blocked_current_guidance_context_not_comparable", 0),
        "accepted_guidance_raise_cut_count": 0,
        "signed_direction_ready_count": 0,
        "guidance_comparison_readiness_counts": dict(sorted(readiness_counts.items())),
        "current_comparable_guidance_status_counts": dict(sorted(current_counts.items())),
        "interpretation": [
            "Accepted prior-company-guidance context exists for part of the slice, but it is baseline context only.",
            "Current official primary-document review contains partial future operating/financial context but no accepted comparable current company-guidance spans.",
            "Current-vs-prior raise/cut, guidance surprise, beat/miss, signed alpha, model activation, and stronger EventRiskGovernor intervention remain blocked.",
            "The next evidence route should acquire or curate current earnings-release/exhibit/transcript guidance text and PIT expectation baselines rather than compare against post-event pages or market reaction.",
        ],
    }

    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_current_prior_comparison_readiness_rows.csv", event_rows)
    _write_csv(
        inputs.output_dir / "earnings_guidance_current_prior_comparison_readiness_group_stats.csv",
        [{"guidance_comparison_readiness": key, "n_events": value} for key, value in sorted(readiness_counts.items())],
    )
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance current-vs-prior comparison readiness

This no-provider artifact joins prior company-guidance baseline context, current official guidance-context review rows, and official result artifacts.

- Events: {len(event_rows)}
- Accepted prior-guidance baseline events: {report['accepted_prior_guidance_baseline_event_count']}
- Current comparable guidance events: {comparable_count}
- Current partial guidance-context events: {report['current_partial_guidance_context_event_count']}
- Accepted guidance raise/cut rows: 0
- Signed-direction ready rows: 0
- Status: `{report['status']}`

Conclusion: prior context is partially available, but current comparable guidance context is still missing. Signed earnings/guidance claims remain blocked.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["CurrentPriorComparisonReadinessInputs", "run_current_prior_comparison_readiness"]
