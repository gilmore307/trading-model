"""Audit model output/support tables for empty and sparse columns.

The audit is intentionally read-only. The default table set covers only the
current six model output/support surfaces. Retained ten-layer tables remain
available as an explicit migration-source audit scope, not as current outputs.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

CURRENT_MODEL_OUTPUT_TABLES: tuple[str, ...] = (
    "model_01_background_context",
    "model_01_background_context_explainability",
    "model_01_background_context_diagnostics",
    "model_02_target_state",
    "model_02_target_state_explainability",
    "model_02_target_state_diagnostics",
    "model_03_event_state",
    "model_03_event_state_explainability",
    "model_03_event_state_diagnostics",
    "model_04_unified_decision",
    "model_04_unified_decision_explainability",
    "model_04_unified_decision_diagnostics",
    "model_05_option_expression",
    "model_05_option_expression_explainability",
    "model_05_option_expression_diagnostics",
    "model_06_residual_event_governance",
    "model_06_residual_event_governance_explainability",
    "model_06_residual_event_governance_diagnostics",
)

RETAINED_MIGRATION_MODEL_OUTPUT_TABLES: tuple[str, ...] = (
    "m01_market_regime_model_generation",
    "m01_market_regime_model_generation_explainability",
    "m01_market_regime_model_generation_diagnostics",
    "m02_sector_context_model_generation",
    "m02_sector_context_model_generation_explainability",
    "m02_sector_context_model_generation_diagnostics",
    "model_03_target_state_vector",
    "model_03_target_state_vector_explainability",
    "model_03_target_state_vector_diagnostics",
    "model_04_event_failure_risk",
    "model_04_event_failure_risk_explainability",
    "model_04_event_failure_risk_diagnostics",
    "model_05_alpha_confidence",
    "model_05_alpha_confidence_explainability",
    "model_05_alpha_confidence_diagnostics",
    "model_06_dynamic_risk_policy",
    "model_06_dynamic_risk_policy_explainability",
    "model_06_dynamic_risk_policy_diagnostics",
    "model_07_position_projection",
    "model_07_position_projection_explainability",
    "model_07_position_projection_diagnostics",
    "model_08_underlying_action",
    "model_08_underlying_action_explainability",
    "model_08_underlying_action_diagnostics",
    "model_05_option_expression",
    "model_05_option_expression_explainability",
    "model_05_option_expression_diagnostics",
    "model_06_residual_event_governance",
    "model_06_residual_event_governance_explainability",
    "model_06_residual_event_governance_diagnostics",
)

MODEL_OUTPUT_TABLES: tuple[str, ...] = CURRENT_MODEL_OUTPUT_TABLES
ALL_MODEL_OUTPUT_TABLES: tuple[str, ...] = CURRENT_MODEL_OUTPUT_TABLES + RETAINED_MIGRATION_MODEL_OUTPUT_TABLES

IDENTITY_COLUMN_HINTS = {
    "available_time",
    "tradeable_time",
    "target_candidate_id",
    "model_id",
    "model_layer",
    "model_version",
}

OPTIONAL_EVIDENCE_HINTS = (
    "selected_contract_ref",
    "option_chain_snapshot_ref",
    "option_quote_available_time",
    "underlying_quote_snapshot_ref",
    "event_strategy_failure_gate_ref",
    "event_failure_evidence_packet_ref",
    "pending_position_state_ref",
    "current_position_state_ref",
)

SUPPORT_PAYLOAD_COLUMNS = {"explanation_payload_json", "diagnostic_payload_json"}

DATA_ACCUMULATION_SCORE_COLUMNS = {
    "1_market_trend_quality_score",
    "1_breadth_participation_score",
    "2_sector_trend_stability_score",
    "2_sector_transition_risk_score",
    "2_sector_internal_dispersion_score",
    "2_sector_crowding_risk_score",
}

OPTIONAL_SELECTION_COLUMNS = {
    "2_sector_handoff_rank",
}


@dataclass(frozen=True)
class ColumnAudit:
    column: str
    non_null_count: int
    null_count: int
    null_rate: float
    classification: str
    recommended_action: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "non_null_count": self.non_null_count,
            "null_count": self.null_count,
            "null_rate": self.null_rate,
            "classification": self.classification,
            "recommended_action": self.recommended_action,
        }


def audit_rows(
    table: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    columns: Sequence[str] | None = None,
    estimated_total_rows: int | None = None,
) -> dict[str, Any]:
    """Classify column population for one table from already-fetched rows."""

    ordered_columns = list(columns or _columns_from_rows(rows))
    sample_count = len(rows)
    column_reports = [
        _audit_column(table, column, rows, sample_count=sample_count)
        for column in ordered_columns
    ]
    all_null = [report for report in column_reports if report.classification.startswith("all_null")]
    sparse = [report for report in column_reports if report.classification == "sparse_data_gap"]
    populated = [report for report in column_reports if report.classification == "populated"]
    return {
        "table": table,
        "estimated_total_rows": estimated_total_rows,
        "sampled_rows": sample_count,
        "column_count": len(ordered_columns),
        "all_null_column_count": len(all_null),
        "sparse_column_count": len(sparse),
        "populated_column_count": len(populated),
        "all_null_columns": [report.as_dict() for report in all_null],
        "sparse_columns": [report.as_dict() for report in sparse],
    }


def audit_database(
    cursor: Any,
    *,
    schema: str = "trading_model",
    tables: Sequence[str] = MODEL_OUTPUT_TABLES,
    sample_limit: int = 5000,
) -> dict[str, Any]:
    """Run a read-only bounded-row audit for model output/support tables."""

    reports: list[dict[str, Any]] = []
    for table in tables:
        if not _table_exists(cursor, schema=schema, table=table):
            reports.append({
                "table": table,
                "status": "missing_table",
                "estimated_total_rows": 0,
                "sampled_rows": 0,
                "column_count": 0,
                "all_null_column_count": 0,
                "sparse_column_count": 0,
                "populated_column_count": 0,
                "all_null_columns": [],
                "sparse_columns": [],
            })
            continue
        columns = _table_columns(cursor, schema=schema, table=table)
        estimated_total = _estimated_rows(cursor, schema=schema, table=table)
        rows = _recent_rows(cursor, schema=schema, table=table, columns=columns, sample_limit=sample_limit)
        report = audit_rows(table, rows, columns=columns, estimated_total_rows=estimated_total)
        report["status"] = "sampled" if rows else "empty_table"
        reports.append(report)

    summary = {
        "table_count": len(reports),
        "missing_table_count": sum(1 for report in reports if report.get("status") == "missing_table"),
        "empty_table_count": sum(1 for report in reports if report.get("status") == "empty_table"),
        "tables_with_all_null_columns": sum(1 for report in reports if report.get("all_null_column_count", 0) > 0),
        "all_null_column_count": sum(int(report.get("all_null_column_count", 0)) for report in reports),
        "sparse_column_count": sum(int(report.get("sparse_column_count", 0)) for report in reports),
    }
    return {
        "contract_type": "model_output_table_quality_audit",
        "schema": schema,
        "sample_limit": sample_limit,
        "summary": summary,
        "tables": reports,
        "cleanup_sql_review_required": cleanup_sql_for_reports(reports, schema=schema),
    }


def cleanup_sql_for_reports(reports: Sequence[Mapping[str, Any]], *, schema: str = "trading_model") -> list[str]:
    """Return review-only DROP COLUMN statements for stale all-null columns."""

    statements: list[str] = []
    for report in reports:
        table = str(report.get("table") or "")
        for column_report in report.get("all_null_columns") or []:
            if not isinstance(column_report, Mapping):
                continue
            if column_report.get("recommended_action") != "review_drop_or_stop_emitting_column":
                continue
            column = str(column_report.get("column") or "")
            if not table or not column:
                continue
            statements.append(f'ALTER TABLE "{schema}"."{table}" DROP COLUMN IF EXISTS "{column}";')
    return statements


def _columns_from_rows(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    columns: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for column in row:
            if column not in seen:
                columns.append(str(column))
                seen.add(str(column))
    return columns


def _audit_column(table: str, column: str, rows: Sequence[Mapping[str, Any]], *, sample_count: int) -> ColumnAudit:
    non_null_count = sum(1 for row in rows if _is_non_empty(row.get(column)))
    null_count = max(sample_count - non_null_count, 0)
    null_rate = 1.0 if sample_count == 0 else round(null_count / sample_count, 6)
    classification, action = _classify(table, column, sample_count, non_null_count)
    return ColumnAudit(column, non_null_count, null_count, null_rate, classification, action)


def _classify(table: str, column: str, sample_count: int, non_null_count: int) -> tuple[str, str]:
    if sample_count == 0:
        return "no_rows_sampled", "generate_or_backfill_upstream_rows"
    if non_null_count > 0:
        if non_null_count < sample_count:
            return "sparse_data_gap", "keep_and_monitor_data_coverage"
        return "populated", "keep"
    if column in IDENTITY_COLUMN_HINTS or column.endswith("_ref"):
        if any(hint in column for hint in OPTIONAL_EVIDENCE_HINTS):
            return "all_null_optional_evidence", "keep_as_explicit_missing_evidence_marker"
        return "all_null_reference_gap", "repair_upstream_handoff_or_backfill_reference"
    if column in SUPPORT_PAYLOAD_COLUMNS:
        return "all_null_support_payload_error", "repair_support_payload_generation"
    if column in DATA_ACCUMULATION_SCORE_COLUMNS:
        return "all_null_data_accumulation_gap", "backfill_longer_history_or_keep_missing_until_evidence_matures"
    if column in OPTIONAL_SELECTION_COLUMNS:
        return "all_null_optional_selection", "keep_as_explicit_no_selected_or_watch_rows_marker"
    if any(hint in column for hint in OPTIONAL_EVIDENCE_HINTS):
        return "all_null_optional_evidence", "keep_as_explicit_missing_evidence_marker"
    if table.endswith("_diagnostics"):
        return "all_null_diagnostic_gap", "repair_diagnostic_generation_or_stop_emitting_column"
    if table.endswith("_explainability"):
        return "all_null_explainability_gap", "repair_explainability_generation_or_stop_emitting_column"
    if len(column) > 2 and column[0].isdigit() and column[1] == "_":
        return "all_null_score_gap", "repair_generator_or_upstream_data"
    return "all_null_stale_or_unused_column", "review_drop_or_stop_emitting_column"


def _is_non_empty(value: Any) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return bool(value)
    return True


def _table_exists(cursor: Any, *, schema: str, table: str) -> bool:
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"{schema}.{table}",))
    row = cursor.fetchone()
    if isinstance(row, Mapping):
        return row.get("table_ref") is not None
    return bool(row and row[0] is not None)


def _table_columns(cursor: Any, *, schema: str, table: str) -> list[str]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )
    return [str(row["column_name"] if isinstance(row, Mapping) else row[0]) for row in cursor.fetchall()]


def _estimated_rows(cursor: Any, *, schema: str, table: str) -> int:
    cursor.execute(
        """
        SELECT COALESCE(s.n_live_tup, c.reltuples, 0)::bigint AS estimated_rows
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
        WHERE n.nspname = %s AND c.relname = %s
        """,
        (schema, table),
    )
    row = cursor.fetchone()
    if not row:
        return 0
    return int(row["estimated_rows"] if isinstance(row, Mapping) else row[0])


def _recent_rows(cursor: Any, *, schema: str, table: str, columns: Sequence[str], sample_limit: int) -> list[dict[str, Any]]:
    if not columns or sample_limit <= 0:
        return []
    column_sql = ", ".join(f'"{column}"' for column in columns)
    if "available_time" in columns:
        cursor.execute(
            f'SELECT {column_sql} FROM "{schema}"."{table}" TABLESAMPLE SYSTEM (10) LIMIT %s',
            (sample_limit,),
        )
        sampled_rows = [dict(row) if isinstance(row, Mapping) else dict(zip(columns, row)) for row in cursor.fetchall()]
        if sampled_rows:
            return sampled_rows
    cursor.execute(
        f'SELECT {column_sql} FROM "{schema}"."{table}" LIMIT %s',
        (sample_limit,),
    )
    return [dict(row) if isinstance(row, Mapping) else dict(zip(columns, row)) for row in cursor.fetchall()]


def dump_audit_json(audit: Mapping[str, Any]) -> str:
    return json.dumps(audit, indent=2, sort_keys=True, default=str) + "\n"


__all__ = [
    "ALL_MODEL_OUTPUT_TABLES",
    "CURRENT_MODEL_OUTPUT_TABLES",
    "MODEL_OUTPUT_TABLES",
    "RETAINED_MIGRATION_MODEL_OUTPUT_TABLES",
    "DATA_ACCUMULATION_SCORE_COLUMNS",
    "audit_database",
    "audit_rows",
    "cleanup_sql_for_reports",
    "dump_audit_json",
]
