"""SQL schema helpers for generic model governance tables.

The tables in this module live in the ``trading_model`` schema by default and
are shared by model layers. They govern model data requests, reproducible
snapshots, time-series splits, evaluation labels, evaluation runs, and metrics.
Production model output tables remain model-specific.
"""
from __future__ import annotations

import re
from typing import Any

DEFAULT_SCHEMA = "trading_model"
TABLE_NAMES = (
    "model_dataset_request",
    "model_dataset_snapshot",
    "model_dataset_split",
    "model_eval_label",
    "model_eval_run",
    "model_eval_metric",
)

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def quote_identifier(identifier: str) -> str:
    """Return a safely quoted SQL identifier.

    The helper intentionally accepts only ordinary snake_case-ish identifiers so
    callers cannot smuggle SQL into schema/table names.
    """
    if not _IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def qualified(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def create_governance_schema_sql(schema: str = DEFAULT_SCHEMA) -> list[str]:
    """Return ordered DDL statements for the model governance schema."""
    q_schema = quote_identifier(schema)
    request = qualified(schema, "model_dataset_request")
    snapshot = qualified(schema, "model_dataset_snapshot")
    split = qualified(schema, "model_dataset_split")
    label = qualified(schema, "model_eval_label")
    run = qualified(schema, "model_eval_run")
    metric = qualified(schema, "model_eval_metric")

    return [
        f"CREATE SCHEMA IF NOT EXISTS {q_schema}",
        f"""
        CREATE TABLE IF NOT EXISTS {request} (
          "request_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "purpose" TEXT NOT NULL,
          "required_data_start_time" TIMESTAMPTZ NOT NULL,
          "required_data_end_time" TIMESTAMPTZ NOT NULL,
          "required_source_key" TEXT,
          "required_feature_key" TEXT,
          "request_status" TEXT NOT NULL DEFAULT 'requested',
          "request_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "requested_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "completed_at" TIMESTAMPTZ,
          "status_detail" TEXT,
          CHECK ("required_data_end_time" >= "required_data_start_time")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_dataset_request_model_status\" ON {request} (\"model_id\", \"request_status\")",
        f"""
        CREATE TABLE IF NOT EXISTS {snapshot} (
          "snapshot_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "request_id" TEXT REFERENCES {request} ("request_id"),
          "feature_schema" TEXT NOT NULL,
          "feature_table" TEXT NOT NULL,
          "data_start_time" TIMESTAMPTZ NOT NULL,
          "data_end_time" TIMESTAMPTZ NOT NULL,
          "feature_row_count" BIGINT,
          "feature_data_hash" TEXT,
          "model_config_hash" TEXT,
          "snapshot_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          CHECK ("data_end_time" >= "data_start_time")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_dataset_snapshot_model_time\" ON {snapshot} (\"model_id\", \"data_start_time\", \"data_end_time\")",
        f"""
        CREATE TABLE IF NOT EXISTS {split} (
          "split_id" TEXT PRIMARY KEY,
          "snapshot_id" TEXT NOT NULL REFERENCES {snapshot} ("snapshot_id"),
          "split_name" TEXT NOT NULL,
          "split_start_time" TIMESTAMPTZ NOT NULL,
          "split_end_time" TIMESTAMPTZ NOT NULL,
          "split_order" INTEGER NOT NULL DEFAULT 0,
          "split_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          UNIQUE ("snapshot_id", "split_name"),
          CHECK ("split_end_time" >= "split_start_time")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_dataset_split_snapshot_order\" ON {split} (\"snapshot_id\", \"split_order\")",
        f"""
        CREATE TABLE IF NOT EXISTS {label} (
          "label_id" TEXT PRIMARY KEY,
          "snapshot_id" TEXT NOT NULL REFERENCES {snapshot} ("snapshot_id"),
          "label_name" TEXT NOT NULL,
          "target_symbol" TEXT NOT NULL DEFAULT '',
          "horizon" TEXT NOT NULL,
          "available_time" TIMESTAMPTZ NOT NULL,
          "label_time" TIMESTAMPTZ NOT NULL,
          "label_value" DOUBLE PRECISION,
          "label_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          UNIQUE ("snapshot_id", "label_name", "target_symbol", "horizon", "available_time"),
          CHECK ("label_time" >= "available_time")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_eval_label_lookup\" ON {label} (\"snapshot_id\", \"label_name\", \"horizon\", \"available_time\")",
        f"""
        CREATE TABLE IF NOT EXISTS {run} (
          "eval_run_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "snapshot_id" TEXT NOT NULL REFERENCES {snapshot} ("snapshot_id"),
          "run_name" TEXT,
          "model_version" TEXT,
          "config_hash" TEXT,
          "run_status" TEXT NOT NULL DEFAULT 'running',
          "run_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "started_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "completed_at" TIMESTAMPTZ,
          "status_detail" TEXT
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_eval_run_model_status\" ON {run} (\"model_id\", \"run_status\")",
        f"CREATE INDEX IF NOT EXISTS \"idx_model_eval_run_snapshot\" ON {run} (\"snapshot_id\")",
        f"""
        CREATE TABLE IF NOT EXISTS {metric} (
          "metric_id" TEXT PRIMARY KEY,
          "eval_run_id" TEXT NOT NULL REFERENCES {run} ("eval_run_id"),
          "split_id" TEXT REFERENCES {split} ("split_id"),
          "label_name" TEXT,
          "target_symbol" TEXT NOT NULL DEFAULT '',
          "horizon" TEXT,
          "factor_name" TEXT,
          "metric_name" TEXT NOT NULL,
          "metric_value" DOUBLE PRECISION,
          "metric_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_eval_metric_run\" ON {metric} (\"eval_run_id\")",
        f"CREATE INDEX IF NOT EXISTS \"idx_model_eval_metric_lookup\" ON {metric} (\"eval_run_id\", \"metric_name\", \"label_name\", \"horizon\", \"factor_name\")",
    ]


def ensure_model_governance_schema(cursor: Any, *, schema: str = DEFAULT_SCHEMA) -> None:
    """Create the generic governance/evaluation tables if they do not exist."""
    for statement in create_governance_schema_sql(schema):
        cursor.execute(statement)
