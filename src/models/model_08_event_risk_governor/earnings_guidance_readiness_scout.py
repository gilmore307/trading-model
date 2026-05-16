"""Readiness audit for official earnings/guidance interpretation.

This local scout performs no provider calls. It consumes the official SEC result
artifact scout output and records whether the earnings/guidance family has the
minimum upstream evidence required for signed guidance/result claims.

The purpose is deliberately conservative: distinguish partial official result
context from true guidance surprise / expectation-ready evidence.
"""
from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HORIZONS = (1, 5, 10, 14)
LABEL_METRICS = ("abs_fwd", "directional_fwd", "path_range", "mfe", "mae")


@dataclass(frozen=True)
class GuidanceReadinessInputs:
    interpreted_events_path: Path
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


def _float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(xs) / len(xs) if xs else None


def _positive_rate(values: Iterable[float | None]) -> float | None:
    xs = [value for value in values if value is not None]
    return sum(1 for value in xs if value > 0) / len(xs) if xs else None


def _label_fields(row: Mapping[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for horizon in HORIZONS:
        suffix = f"{horizon}d"
        for metric in LABEL_METRICS:
            source = f"event_{metric}_{suffix}"
            out[source] = _float(row.get(source))
    return out


def _count_int(row: Mapping[str, str], key: str) -> int:
    try:
        return int(float(row.get(key) or 0))
    except (TypeError, ValueError):
        return 0


def _readiness_row(row: Mapping[str, str]) -> dict[str, Any]:
    result_present = row.get("official_result_artifact_status") == "present"
    result_metric_count = _count_int(row, "result_metric_count")
    guidance_status = row.get("guidance_status") or "missing_official_guidance_interpretation"
    official_guidance_ready = guidance_status not in {"", "missing", "missing_official_guidance_interpretation"}
    expectation_ready = False
    signed_ready = result_present and official_guidance_ready and expectation_ready
    if signed_ready:
        readiness = "signed_direction_ready"
    elif result_present and result_metric_count > 0:
        readiness = "partial_result_context_only"
    elif result_present:
        readiness = "official_result_artifact_only"
    else:
        readiness = "missing_official_result_artifact"

    return {
        "symbol": row.get("symbol"),
        "event_id": row.get("event_id"),
        "event_date": row.get("event_date"),
        "event_name": row.get("event_name"),
        "lifecycle_class": row.get("lifecycle_class"),
        "official_result_artifact_status": row.get("official_result_artifact_status") or "missing",
        "result_interpretation_status": row.get("result_interpretation_status") or "missing",
        "result_metric_count": result_metric_count,
        "result_direction_score": _float(row.get("result_direction_score")),
        "guidance_status": guidance_status,
        "official_company_guidance_artifact_status": "missing",
        "guidance_interpretation_status": "missing_official_company_guidance_interpretation",
        "expectation_baseline_status": "missing_consensus_or_accepted_expectation_baseline",
        "signed_direction_readiness": "ready" if signed_ready else "blocked_missing_guidance_and_expectation_baseline",
        "event_risk_context_readiness": readiness,
        "promotion_readiness": "blocked_not_promotion_evidence",
        **_label_fields(row),
    }


def _group_stats(rows: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or "missing")].append(row)
    out: list[dict[str, Any]] = []
    for group, items in sorted(groups.items()):
        item: dict[str, Any] = {
            key: group,
            "n_events": len(items),
            "n_symbols": len({row.get("symbol") for row in items}),
        }
        for horizon in HORIZONS:
            for metric in LABEL_METRICS:
                name = f"event_{metric}_{horizon}d"
                values = [_float(row.get(name)) for row in items]
                item[f"avg_{name}"] = _avg(values)
                item[f"positive_rate_{name}"] = _positive_rate(values)
        out.append(item)
    return out


def run_guidance_readiness_scout(inputs: GuidanceReadinessInputs) -> dict[str, Any]:
    source_rows = _read_csv(inputs.interpreted_events_path)
    readiness_rows = [_readiness_row(row) for row in source_rows]
    context_counts = Counter(str(row.get("event_risk_context_readiness") or "missing") for row in readiness_rows)
    signed_ready_count = sum(1 for row in readiness_rows if row.get("signed_direction_readiness") == "ready")
    guidance_ready_count = sum(1 for row in readiness_rows if row.get("guidance_interpretation_status") != "missing_official_company_guidance_interpretation")
    expectation_ready_count = sum(1 for row in readiness_rows if row.get("expectation_baseline_status") != "missing_consensus_or_accepted_expectation_baseline")
    group_stats = _group_stats(readiness_rows, "event_risk_context_readiness")
    report = {
        "schema": "earnings_guidance_readiness_scout_v1",
        "status": "blocked_missing_guidance_and_expectation_baselines",
        "provider_calls_performed_by_study": 0,
        "event_count": len(readiness_rows),
        "official_result_artifact_count": sum(1 for row in readiness_rows if row.get("official_result_artifact_status") == "present"),
        "partial_result_context_count": context_counts.get("partial_result_context_only", 0),
        "official_result_artifact_only_count": context_counts.get("official_result_artifact_only", 0),
        "official_guidance_interpretation_count": guidance_ready_count,
        "expectation_baseline_count": expectation_ready_count,
        "signed_direction_ready_count": signed_ready_count,
        "interpretation": [
            "Official SEC result artifacts provide partial point-in-time result context, not guidance surprise.",
            "No official company guidance release/transcript interpretation is present in the local artifact set.",
            "No consensus or accepted expectation baseline is present, so beat/miss and signed-direction claims remain invalid.",
            "The earnings/guidance family remains direction-neutral event-risk scouting, not promotion evidence.",
        ],
        "group_stats": group_stats,
    }
    inputs.output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(inputs.output_dir / "earnings_guidance_readiness_rows.csv", readiness_rows)
    _write_csv(inputs.output_dir / "earnings_guidance_readiness_group_stats.csv", group_stats)
    (inputs.output_dir / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (inputs.output_dir / "README.md").write_text(
        f"""# Earnings/guidance official-guidance readiness scout

This artifact audits whether the current official result-artifact scout has enough point-in-time evidence for signed earnings/guidance claims.

- Events: {len(readiness_rows)}
- Official result artifacts present: {report['official_result_artifact_count']}
- Partial result context rows: {report['partial_result_context_count']}
- Official guidance interpretations: {guidance_ready_count}
- Expectation baselines: {expectation_ready_count}
- Signed-direction ready rows: {signed_ready_count}
- Status: `{report['status']}`

Conclusion: current evidence supports only partial direction-neutral event-risk context. Official guidance interpretation and expectation baselines remain missing.
""",
        encoding="utf-8",
    )
    return report


__all__ = ["GuidanceReadinessInputs", "run_guidance_readiness_scout"]
