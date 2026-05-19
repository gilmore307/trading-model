"""Quality-gate evaluation for model output table audits."""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from typing import Any

BLOCKING_CLASSIFICATIONS = {
    "all_null_reference_gap",
    "all_null_score_gap",
    "all_null_stale_or_unused_column",
    "all_null_support_payload_error",
}

SUPPORT_GAP_CLASSIFICATIONS = {
    "all_null_diagnostic_gap",
    "all_null_explainability_gap",
}

INFO_CLASSIFICATIONS = {
    "all_null_optional_evidence",
    "all_null_optional_selection",
}

DATA_COVERAGE_CLASSIFICATIONS = {
    "all_null_data_accumulation_gap",
}


def evaluate_quality_gate(audit: Mapping[str, Any], *, strict_support: bool = False) -> dict[str, Any]:
    """Convert a table audit into a pass/block decision."""

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    infos: list[dict[str, Any]] = []
    classification_counts: Counter[str] = Counter()

    for table in audit.get("tables") or []:
        if not isinstance(table, Mapping):
            continue
        table_name = str(table.get("table") or "")
        status = table.get("status")
        if status in {"missing_table", "empty_table"}:
            blockers.append(
                {
                    "table": table_name,
                    "column": None,
                    "classification": str(status),
                    "recommended_action": "generate_or_repair_table_before_acceptance",
                }
            )
            classification_counts[str(status)] += 1
        for column in table.get("all_null_columns") or []:
            if not isinstance(column, Mapping):
                continue
            classification = str(column.get("classification") or "")
            item = {
                "table": table_name,
                "column": column.get("column"),
                "classification": classification,
                "recommended_action": column.get("recommended_action"),
            }
            classification_counts[classification] += 1
            if classification in BLOCKING_CLASSIFICATIONS or (strict_support and classification in SUPPORT_GAP_CLASSIFICATIONS):
                blockers.append(item)
            elif classification in SUPPORT_GAP_CLASSIFICATIONS or classification in DATA_COVERAGE_CLASSIFICATIONS:
                warnings.append(item)
            elif classification in INFO_CLASSIFICATIONS:
                infos.append(item)
            else:
                warnings.append(item)

        sparse_count = int(table.get("sparse_column_count") or 0)
        if sparse_count:
            warnings.append(
                {
                    "table": table_name,
                    "column": None,
                    "classification": "sparse_data_gap",
                    "recommended_action": "monitor_or_repair_upstream_coverage",
                    "column_count": sparse_count,
                }
            )
            classification_counts["sparse_data_gap"] += sparse_count

    status = "blocked" if blockers else "passed"
    return {
        "contract_type": "model_output_quality_gate",
        "source_audit_contract_type": audit.get("contract_type"),
        "schema": audit.get("schema"),
        "sample_limit": audit.get("sample_limit"),
        "status": status,
        "strict_support": strict_support,
        "summary": {
            "blocker_count": len(blockers),
            "warning_count": len(warnings),
            "info_count": len(infos),
            "classification_counts": dict(sorted(classification_counts.items())),
        },
        "blockers": blockers,
        "warnings": warnings,
        "infos": infos,
    }


def assert_quality_gate_passed(gate: Mapping[str, Any]) -> None:
    """Raise a concise error when the gate is blocked."""

    if gate.get("status") == "blocked":
        summary = gate.get("summary") if isinstance(gate.get("summary"), Mapping) else {}
        raise RuntimeError(f"model output quality gate blocked: {summary.get('blocker_count', 0)} blockers")


__all__ = [
    "BLOCKING_CLASSIFICATIONS",
    "SUPPORT_GAP_CLASSIFICATIONS",
    "DATA_COVERAGE_CLASSIFICATIONS",
    "evaluate_quality_gate",
    "assert_quality_gate_passed",
]
