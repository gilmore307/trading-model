"""Dataset and evaluation governance table schema."""
from __future__ import annotations

from model_governance.common.sql import DEFAULT_SCHEMA, qualified, quote_identifier

EVALUATION_TABLE_NAMES = (
    "model_dataset_request",
    "model_dataset_snapshot",
    "model_dataset_split",
    "model_eval_label",
    "model_eval_run",
    "model_promotion_metric",
)


def create_evaluation_schema_sql(schema: str = DEFAULT_SCHEMA) -> list[str]:
    """Return ordered DDL for dataset/evaluation evidence tables."""
    request = qualified(schema, "model_dataset_request")
    snapshot = qualified(schema, "model_dataset_snapshot")
    split = qualified(schema, "model_dataset_split")
    label = qualified(schema, "model_eval_label")
    run = qualified(schema, "model_eval_run")
    metric = qualified(schema, "model_promotion_metric")
    return [
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
          CHECK ("label_time" >= "available_time")
        )
        """,
        f"ALTER TABLE {label} DROP CONSTRAINT IF EXISTS \"model_eval_label_snapshot_id_label_name_target_symbol_horiz_key\"",
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
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_metric_run\" ON {metric} (\"eval_run_id\")",
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_metric_lookup\" ON {metric} (\"eval_run_id\", \"metric_name\", \"label_name\", \"horizon\", \"factor_name\")",
        _legacy_metric_copy_sql(schema),
    ]


def _legacy_metric_copy_sql(schema: str) -> str:
    q_schema = quote_identifier(schema)
    return f"""
    DO $$
    BEGIN
      IF to_regclass('{schema}.model_eval_metric') IS NOT NULL THEN
        EXECUTE 'INSERT INTO {q_schema}."model_promotion_metric" ("metric_id", "eval_run_id", "split_id", "label_name", "target_symbol", "horizon", "factor_name", "metric_name", "metric_value", "metric_payload_json", "created_at")
                 SELECT "metric_id", "eval_run_id", "split_id", "label_name", "target_symbol", "horizon", "factor_name", "metric_name", "metric_value", "metric_payload_json", "created_at"
                 FROM {q_schema}."model_eval_metric"
                 ON CONFLICT ("metric_id") DO NOTHING';
      END IF;
    END $$
    """
