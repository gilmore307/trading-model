"""Promotion lifecycle table schema."""
from __future__ import annotations

from model_governance.common.sql import DEFAULT_SCHEMA, qualified

PROMOTION_TABLE_NAMES = (
    "model_config_version",
    "model_promotion_candidate",
    "model_promotion_decision",
    "model_promotion_activation",
    "model_promotion_rollback",
)


def create_promotion_schema_sql(schema: str = DEFAULT_SCHEMA) -> list[str]:
    """Return ordered DDL for model config and promotion lifecycle tables."""
    run = qualified(schema, "model_eval_run")
    config_version = qualified(schema, "model_config_version")
    promotion_candidate = qualified(schema, "model_promotion_candidate")
    promotion_decision = qualified(schema, "model_promotion_decision")
    promotion_activation = qualified(schema, "model_promotion_activation")
    promotion_rollback = qualified(schema, "model_promotion_rollback")
    return [
        f"""
        CREATE TABLE IF NOT EXISTS {config_version} (
          "config_version_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "model_version" TEXT,
          "config_hash" TEXT NOT NULL,
          "config_status" TEXT NOT NULL DEFAULT 'proposed',
          "config_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "created_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "retired_at" TIMESTAMPTZ,
          "status_detail" TEXT,
          UNIQUE ("model_id", "config_hash")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_config_version_model_status\" ON {config_version} (\"model_id\", \"config_status\")",
        f"""
        CREATE TABLE IF NOT EXISTS {promotion_candidate} (
          "promotion_candidate_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "config_version_id" TEXT NOT NULL REFERENCES {config_version} ("config_version_id"),
          "eval_run_id" TEXT NOT NULL REFERENCES {run} ("eval_run_id"),
          "candidate_status" TEXT NOT NULL DEFAULT 'proposed',
          "proposed_by" TEXT,
          "proposed_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "candidate_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "status_detail" TEXT,
          UNIQUE ("model_id", "config_version_id", "eval_run_id")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_candidate_model_status\" ON {promotion_candidate} (\"model_id\", \"candidate_status\")",
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_candidate_eval_run\" ON {promotion_candidate} (\"eval_run_id\")",
        f"""
        CREATE TABLE IF NOT EXISTS {promotion_decision} (
          "promotion_decision_id" TEXT PRIMARY KEY,
          "promotion_candidate_id" TEXT NOT NULL REFERENCES {promotion_candidate} ("promotion_candidate_id"),
          "decision_type" TEXT NOT NULL,
          "decision_status" TEXT NOT NULL,
          "decided_by" TEXT,
          "decided_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "decision_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "status_detail" TEXT
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_decision_candidate\" ON {promotion_decision} (\"promotion_candidate_id\")",
        f"""
        CREATE TABLE IF NOT EXISTS {promotion_activation} (
          "activation_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "from_config_version_id" TEXT REFERENCES {config_version} ("config_version_id"),
          "to_config_version_id" TEXT NOT NULL REFERENCES {config_version} ("config_version_id"),
          "promotion_decision_id" TEXT NOT NULL REFERENCES {promotion_decision} ("promotion_decision_id"),
          "activated_by" TEXT,
          "activated_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "activation_status" TEXT NOT NULL DEFAULT 'activated',
          "activation_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "status_detail" TEXT,
          UNIQUE ("model_id", "promotion_decision_id")
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_activation_model_time\" ON {promotion_activation} (\"model_id\", \"activated_at\")",
        f"""
        CREATE TABLE IF NOT EXISTS {promotion_rollback} (
          "rollback_id" TEXT PRIMARY KEY,
          "model_id" TEXT NOT NULL,
          "from_config_version_id" TEXT NOT NULL REFERENCES {config_version} ("config_version_id"),
          "to_config_version_id" TEXT REFERENCES {config_version} ("config_version_id"),
          "promotion_decision_id" TEXT REFERENCES {promotion_decision} ("promotion_decision_id"),
          "rollback_status" TEXT NOT NULL DEFAULT 'requested',
          "requested_by" TEXT,
          "requested_at" TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          "completed_at" TIMESTAMPTZ,
          "rollback_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb,
          "status_detail" TEXT
        )
        """,
        f"CREATE INDEX IF NOT EXISTS \"idx_model_promotion_rollback_model_status\" ON {promotion_rollback} (\"model_id\", \"rollback_status\")",
    ]
