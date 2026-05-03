"""Persistence SQL helpers for promotion review and activation."""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from model_governance.common.sql import DEFAULT_SCHEMA, database_url, json_literal, qualified, quote_identifier, run_psql, sql_literal
from model_governance.schema import create_governance_schema_sql

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
    "model_promotion_metric": (
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
    "model_promotion_metric": ("metric_id",),
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
    """Render SQL that persists evidence, a promotion decision, and optional activation."""
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
        "model_promotion_metric",
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
        f"SET {quote_identifier('candidate_status')} = {sql_literal(status)},\n"
        f"    {quote_identifier('status_detail')} = {sql_literal('Promotion decision persisted: ' + str(decision_row.get('promotion_decision_id')))}\n"
        f"WHERE {quote_identifier('promotion_candidate_id')} = {sql_literal(str(candidate_row['promotion_candidate_id']))}"
    )


def _activation_updates(
    schema: str,
    config_row: Mapping[str, Any],
    decision_row: Mapping[str, Any],
) -> list[str]:
    model_id = str(config_row["model_id"])
    config_version_id = str(config_row["config_version_id"])
    decision_id = str(decision_row["promotion_decision_id"])
    activated_by = decision_row.get("decided_by")
    detail = f"Activated by promotion decision {decision_id}"
    config_table = qualified(schema, "model_config_version")
    activation_table = qualified(schema, "model_promotion_activation")
    active_config_subquery = (
        f"SELECT {quote_identifier('config_version_id')} FROM {config_table}\n"
        f"WHERE {quote_identifier('model_id')} = {sql_literal(model_id)}\n"
        f"  AND {quote_identifier('config_status')} = 'active'\n"
        f"ORDER BY {quote_identifier('created_at')} DESC\n"
        f"LIMIT 1"
    )
    activation_id = "mpact_" + decision_id.removeprefix("mpdec_")
    return [
        (
            f"INSERT INTO {activation_table} (\n"
            f"  {quote_identifier('activation_id')}, {quote_identifier('model_id')}, {quote_identifier('from_config_version_id')},\n"
            f"  {quote_identifier('to_config_version_id')}, {quote_identifier('promotion_decision_id')}, {quote_identifier('activated_by')},\n"
            f"  {quote_identifier('activation_status')}, {quote_identifier('activation_payload_json')}, {quote_identifier('status_detail')}\n"
            f")\n"
            f"VALUES (\n"
            f"  {sql_literal(activation_id)}, {sql_literal(model_id)}, ({active_config_subquery}),\n"
            f"  {sql_literal(config_version_id)}, {sql_literal(decision_id)}, {sql_literal(activated_by)},\n"
            f"  'activated', {json_literal({'activation_policy': 'accepted_promotion_decision'})}::jsonb, {sql_literal(detail)}\n"
            f")\n"
            f"ON CONFLICT ({quote_identifier('activation_id')}) DO NOTHING"
        ),
        (
            f"UPDATE {config_table}\n"
            f"SET {quote_identifier('config_status')} = 'retired',\n"
            f"    {quote_identifier('retired_at')} = NOW(),\n"
            f"    {quote_identifier('status_detail')} = 'Retired by newer accepted promotion'\n"
            f"WHERE {quote_identifier('model_id')} = {sql_literal(model_id)}\n"
            f"  AND {quote_identifier('config_version_id')} <> {sql_literal(config_version_id)}\n"
            f"  AND {quote_identifier('config_status')} = 'active'"
        ),
        (
            f"UPDATE {config_table}\n"
            f"SET {quote_identifier('config_status')} = 'active',\n"
            f"    {quote_identifier('retired_at')} = NULL,\n"
            f"    {quote_identifier('status_detail')} = {sql_literal(detail)}\n"
            f"WHERE {quote_identifier('config_version_id')} = {sql_literal(config_version_id)}"
        ),
    ]


def _is_accepted_approval(decision_row: Mapping[str, Any]) -> bool:
    return decision_row.get("decision_type") == "approve" and decision_row.get("decision_status") == "accepted"


def _sql_value(column: str, value: Any) -> str:
    if column in _JSON_COLUMNS:
        return json_literal({} if value is None else value) + "::jsonb"
    return sql_literal(value)


__all__ = ["database_url", "render_promotion_persistence_sql", "run_psql"]
