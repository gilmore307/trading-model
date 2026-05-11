"""Persistence helpers for model evaluation governance artifacts.

The model repository owns the model-side dataset/evaluation evidence tables.  These
helpers intentionally persist only governance/evaluation rows; they do not create
manager promotion decisions, activation records, rollback records, broker orders,
or account mutations.
"""
from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from psycopg.types.json import Jsonb

from model_governance.common.sql import DEFAULT_SCHEMA, database_url, qualified, quote_identifier
from model_governance.schema import ensure_model_governance_schema

EVALUATION_TABLE_ORDER: tuple[str, ...] = (
    "model_dataset_request",
    "model_dataset_snapshot",
    "model_dataset_split",
    "model_eval_label",
    "model_eval_run",
    "model_promotion_metric",
)

TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
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
        "started_at",
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
}

PRIMARY_KEYS: dict[str, tuple[str, ...]] = {
    "model_dataset_request": ("request_id",),
    "model_dataset_snapshot": ("snapshot_id",),
    "model_dataset_split": ("split_id",),
    "model_eval_label": ("label_id",),
    "model_eval_run": ("eval_run_id",),
    "model_promotion_metric": ("metric_id",),
}

JSON_COLUMNS = {
    "request_payload_json",
    "snapshot_payload_json",
    "split_payload_json",
    "label_payload_json",
    "run_payload_json",
    "metric_payload_json",
}


def load_artifact_tables(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Load artifact JSON produced by model evaluation scripts.

    Supported shapes:
    - direct table mapping: ``{"model_dataset_snapshot": [...]}``
    - wrapped payload: ``{"tables": {"model_dataset_snapshot": [...]}}``
    """

    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, Mapping) and isinstance(payload.get("tables"), Mapping):
        payload = payload["tables"]
    if not isinstance(payload, Mapping):
        raise ValueError(f"{path} must contain an object of evaluation table rows")
    tables: dict[str, list[dict[str, Any]]] = {}
    for table in EVALUATION_TABLE_ORDER:
        rows = payload.get(table, [])
        if rows is None:
            rows = []
        if not isinstance(rows, list):
            raise ValueError(f"{path}:{table} must be a list")
        tables[table] = [normalize_row(table, row) for row in rows if isinstance(row, Mapping)]
    _fill_contextual_defaults(tables)
    return tables


def normalize_row(table: str, row: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize known legacy/script row aliases to SQL table columns."""

    if table not in TABLE_COLUMNS:
        raise ValueError(f"unsupported evaluation table: {table}")
    raw = dict(row)
    if table == "model_eval_label":
        payload = _json_payload(raw.get("label_payload_json"))
        raw["horizon"] = raw.get("horizon") or raw.get("label_horizon")
        raw["available_time"] = raw.get("available_time") or payload.get("feature_available_time") or raw.get("label_available_time")
        raw["label_time"] = raw.get("label_time") or raw.get("label_available_time")
        raw["target_symbol"] = raw.get("target_symbol") or ""
        raw["label_payload_json"] = payload
    elif table == "model_eval_run":
        raw["run_status"] = raw.get("run_status") or raw.get("eval_status")
        raw["run_payload_json"] = _json_payload(raw.get("run_payload_json") or raw.get("eval_payload_json"))
        raw["started_at"] = raw.get("started_at") or raw.get("eval_started_at")
        raw["completed_at"] = raw.get("completed_at") or raw.get("eval_completed_at")
    elif table == "model_promotion_metric":
        raw["target_symbol"] = raw.get("target_symbol") or ""
        raw["metric_payload_json"] = _json_payload(raw.get("metric_payload_json"))
    elif table == "model_dataset_request":
        raw["request_payload_json"] = _json_payload(raw.get("request_payload_json"))
    elif table == "model_dataset_snapshot":
        raw["snapshot_payload_json"] = _json_payload(raw.get("snapshot_payload_json"))
    elif table == "model_dataset_split":
        raw["split_payload_json"] = _json_payload(raw.get("split_payload_json"))
    return {column: raw.get(column) for column in TABLE_COLUMNS[table]}


def persist_artifact_tables(
    tables: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    database_url_value: str | None = None,
    schema: str = DEFAULT_SCHEMA,
) -> dict[str, int]:
    """Idempotently upsert model evaluation artifacts into PostgreSQL."""

    import psycopg

    counts: dict[str, int] = {}
    with psycopg.connect(database_url(database_url_value)) as connection:
        with connection.cursor() as cursor:
            ensure_model_governance_schema(cursor, schema=schema)
            normalized_tables = {table: [normalize_row(table, row) for row in tables.get(table, [])] for table in EVALUATION_TABLE_ORDER}
            _fill_contextual_defaults(normalized_tables)
            for table in EVALUATION_TABLE_ORDER:
                normalized_rows = normalized_tables[table]
                counts[table] = _upsert_rows(cursor, schema=schema, table=table, rows=normalized_rows)
        connection.commit()
    return counts


def _fill_contextual_defaults(tables: dict[str, list[dict[str, Any]]]) -> None:
    """Fill safe defaults that require neighboring table context.

    Older Layer 1/2 scripts emitted ``model_eval_run`` rows without timestamps.
    The evaluation schema has a database default for ``started_at``, but our
    idempotent upsert uses explicit column lists. Use the frozen snapshot end
    time as the stable evaluation start/completion timestamp when the source
    artifact does not provide one.
    """

    snapshot_end_by_id = {
        str(row.get("snapshot_id")): row.get("data_end_time")
        for row in tables.get("model_dataset_snapshot", [])
        if row.get("snapshot_id") and row.get("data_end_time")
    }
    for row in tables.get("model_eval_run", []):
        fallback = snapshot_end_by_id.get(str(row.get("snapshot_id")))
        if row.get("started_at") is None and fallback is not None:
            row["started_at"] = fallback
        if row.get("completed_at") is None and fallback is not None:
            row["completed_at"] = fallback


def _upsert_rows(cursor: Any, *, schema: str, table: str, rows: Sequence[Mapping[str, Any]]) -> int:
    if not rows:
        return 0
    columns = TABLE_COLUMNS[table]
    primary_keys = PRIMARY_KEYS[table]
    q_table = qualified(schema, table)
    quoted_columns = ", ".join(quote_identifier(column) for column in columns)
    placeholders = ", ".join("%s" for _ in columns)
    update_columns = [column for column in columns if column not in primary_keys]
    update_sql = ", ".join(f"{quote_identifier(column)} = EXCLUDED.{quote_identifier(column)}" for column in update_columns)
    conflict_sql = ", ".join(quote_identifier(column) for column in primary_keys)
    sql = f"""
        INSERT INTO {q_table} ({quoted_columns})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_sql}) DO UPDATE SET {update_sql}
    """
    values = [tuple(_sql_value(column, row.get(column)) for column in columns) for row in rows]
    cursor.executemany(sql, values)
    return len(values)


def _json_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, str):
        parsed = json.loads(value)
        return dict(parsed) if isinstance(parsed, Mapping) else {"value": parsed}
    if isinstance(value, Mapping):
        return dict(value)
    return {"value": value}


def _sql_value(column: str, value: Any) -> Any:
    if column in JSON_COLUMNS:
        return Jsonb(_json_payload(value))
    return value


__all__ = [
    "EVALUATION_TABLE_ORDER",
    "load_artifact_tables",
    "normalize_row",
    "persist_artifact_tables",
]
