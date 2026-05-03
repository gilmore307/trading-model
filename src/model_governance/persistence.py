"""Persistence SQL helpers for model governance and promotion rows.

These helpers deliberately render explicit SQL so the model promotion path can be
reviewed in dry-run mode before a PostgreSQL mutation is made. They do not
select model candidates themselves; they only persist already-built evidence,
candidates, and decisions.
"""
from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .schema import DEFAULT_SCHEMA, create_governance_schema_sql, qualified, quote_identifier

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")

_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "model_dataset_request": (
        "request_id",
        "model_id",
        "purpose",
        "required_data_start_time",
        "required_data_end_time",
        "required_source_key",
        "required_feature_key",
        "request_status",
        "request_payload_json",
        "completed_at",
        "status_detail",
    ),
    "model_dataset_snapshot": (
        "snapshot_id",
        "model_id",
        "request_id",
        "feature_schema",
        "feature_table",
        "data_start_time",
        "data_end_time",
        "feature_row_count",
        "feature_data_hash",
        "model_config_hash",
        "snapshot_payload_json",
    ),
    "model_dataset_split": (
        "split_id",
        "snapshot_id",
        "split_name",
        "split_start_time",
        "split_end_time",
        "split_order",
        "split_payload_json",
    ),
    "model_eval_label": (
        "label_id",
        "snapshot_id",
        "label_name",
        "target_symbol",
        "horizon",
        "available_time",
        "label_time",
        "label_value",
        "label_payload_json",
    ),
    "model_eval_run": (
        "eval_run_id",
        "model_id",
        "snapshot_id",
        "run_name",
        "model_version",
        "config_hash",
        "run_status",
        "run_payload_json",
        "completed_at",
        "status_detail",
    ),
    "model_eval_metric": (
        "metric_id",
        "eval_run_id",
        "split_id",
        "label_name",
        "target_symbol",
        "horizon",
        "factor_name",
        "metric_name",
        "metric_value",
        "metric_payload_json",
    ),
    "model_config_version": (
        "config_version_id",
        "model_id",
        "model_version",
        "config_hash",
        "config_status",
        "config_payload_json",
        "retired_at",
        "status_detail",
    ),
    "model_promotion_candidate": (
        "promotion_candidate_id",
        "model_id",
        "config_version_id",
        "eval_run_id",
        "candidate_status",
        "proposed_by",
        "candidate_payload_json",
        "status_detail",
    ),
    "model_promotion_decision": (
        "promotion_decision_id",
        "promotion_candidate_id",
        "decision_type",
        "decision_status",
        "decided_by",
        "decision_payload_json",
        "status_detail",
    ),
}

_PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "model_dataset_request": ("request_id",),
    "model_dataset_snapshot": ("snapshot_id",),
    "model_dataset_split": ("split_id",),
    "model_eval_label": ("label_id",),
    "model_eval_run": ("eval_run_id",),
    "model_eval_metric": ("metric_id",),
    "model_config_version": ("config_version_id",),
    "model_promotion_candidate": ("promotion_candidate_id",),
    "model_promotion_decision": ("promotion_decision_id",),
}

_JSON_COLUMNS = {
    "request_payload_json",
    "snapshot_payload_json",
    "split_payload_json",
    "label_payload_json",
    "run_payload_json",
    "metric_payload_json",
    "config_payload_json",
    "candidate_payload_json",
    "decision_payload_json",
}

_STATUS_FOR_DECISION = {
    "accepted": "accepted",
    "rejected": "rejected",
    "deferred": "deferred",
}


def database_url(explicit: str | None = None) -> str:
    """Resolve the PostgreSQL URL using the repository-standard secret lookup."""
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def run_psql(database_url_value: str, sql: str) -> None:
    """Run SQL through psql inside one transaction."""
    subprocess.run(
        ["psql", database_url_value, "-v", "ON_ERROR_STOP=1", "-q"],
        input=f"BEGIN;\n{sql}\nCOMMIT;\n",
        text=True,
        check=True,
    )


def render_promotion_persistence_sql(
    *,
    evaluation_artifacts: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    config_version_row: Mapping[str, Any],
    promotion_candidate_row: Mapping[str, Any],
    promotion_decision_row: Mapping[str, Any],
    schema: str = DEFAULT_SCHEMA,
    include_schema_ddl: bool = True,
    activate_approved_config: bool = False,
) -> str:
    """Render SQL that persists evaluation evidence and one promotion decision.

    If ``activate_approved_config`` is true, an accepted approval updates the
    associated ``model_config_version`` row to ``active`` and retires any other
    currently-active config row for the same model. Deferred/rejected decisions
    never change the active config.
    """
    statements: list[str] = []
    if include_schema_ddl:
        statements.extend(statement.strip().rstrip(";") for statement in create_governance_schema_sql(schema))

    artifacts = evaluation_artifacts or {}
    for table in (
        "model_dataset_request",
        "model_dataset_snapshot",
        "model_dataset_split",
        "model_eval_label",
        "model_eval_run",
        "model_eval_metric",
    ):
        for row in artifacts.get(table, ()):  # type: ignore[arg-type]
            statements.append(_upsert_statement(schema, table, row))

    statements.append(_upsert_statement(schema, "model_config_version", config_version_row))
    statements.append(_upsert_statement(schema, "model_promotion_candidate", promotion_candidate_row))
    statements.append(_upsert_statement(schema, "model_promotion_decision", promotion_decision_row))
    statements.append(_candidate_status_update(schema, promotion_candidate_row, promotion_decision_row))
    if activate_approved_config and _is_accepted_approval(promotion_decision_row):
        statements.extend(_activation_updates(schema, config_version_row, promotion_decision_row))
    return "\n\n".join(statement.rstrip(";") + ";" for statement in statements) + "\n"


def _upsert_statement(schema: str, table: str, row: Mapping[str, Any]) -> str:
    columns = _TABLE_COLUMNS[table]
    primary_keys = set(_PRIMARY_KEYS[table])
    q_table = qualified(schema, table)
    quoted_columns = ", ".join(quote_identifier(column) for column in columns)
    values = ", ".join(_sql_value(column, row.get(column)) for column in columns)
    update_columns = [column for column in columns if column not in primary_keys]
    update_sql = ", ".join(f"{quote_identifier(column)} = EXCLUDED.{quote_identifier(column)}" for column in update_columns)
    conflict_columns = ", ".join(quote_identifier(column) for column in _PRIMARY_KEYS[table])
    return f"INSERT INTO {q_table} ({quoted_columns})\nVALUES ({values})\nON CONFLICT ({conflict_columns}) DO UPDATE SET {update_sql}"


def _candidate_status_update(
    schema: str,
    candidate_row: Mapping[str, Any],
    decision_row: Mapping[str, Any],
) -> str:
    status = _STATUS_FOR_DECISION.get(str(decision_row.get("decision_status")), "proposed")
    return (
        f"UPDATE {qualified(schema, 'model_promotion_candidate')}\n"
        f"SET {quote_identifier('candidate_status')} = {_sql_literal(status)},\n"
        f"    {quote_identifier('status_detail')} = {_sql_literal('Promotion decision persisted: ' + str(decision_row.get('promotion_decision_id')))}\n"
        f"WHERE {quote_identifier('promotion_candidate_id')} = {_sql_literal(str(candidate_row['promotion_candidate_id']))}"
    )


def _activation_updates(
    schema: str,
    config_row: Mapping[str, Any],
    decision_row: Mapping[str, Any],
) -> list[str]:
    model_id = str(config_row["model_id"])
    config_version_id = str(config_row["config_version_id"])
    detail = f"Activated by promotion decision {decision_row['promotion_decision_id']}"
    table = qualified(schema, "model_config_version")
    return [
        (
            f"UPDATE {table}\n"
            f"SET {quote_identifier('config_status')} = 'retired',\n"
            f"    {quote_identifier('retired_at')} = NOW(),\n"
            f"    {quote_identifier('status_detail')} = 'Retired by newer accepted promotion'\n"
            f"WHERE {quote_identifier('model_id')} = {_sql_literal(model_id)}\n"
            f"  AND {quote_identifier('config_version_id')} <> {_sql_literal(config_version_id)}\n"
            f"  AND {quote_identifier('config_status')} = 'active'"
        ),
        (
            f"UPDATE {table}\n"
            f"SET {quote_identifier('config_status')} = 'active',\n"
            f"    {quote_identifier('retired_at')} = NULL,\n"
            f"    {quote_identifier('status_detail')} = {_sql_literal(detail)}\n"
            f"WHERE {quote_identifier('config_version_id')} = {_sql_literal(config_version_id)}"
        ),
    ]


def _is_accepted_approval(decision_row: Mapping[str, Any]) -> bool:
    return decision_row.get("decision_type") == "approve" and decision_row.get("decision_status") == "accepted"


def _sql_value(column: str, value: Any) -> str:
    if column in _JSON_COLUMNS:
        return _json_literal({} if value is None else value) + "::jsonb"
    return _sql_literal(value)


def _json_literal(value: Any) -> str:
    return _sql_literal(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str))


def _sql_literal(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int | float) and not isinstance(value, bool):
        return repr(value)
    return "'" + str(value).replace("'", "''") + "'"
