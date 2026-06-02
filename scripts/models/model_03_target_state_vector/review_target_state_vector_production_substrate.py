#!/usr/bin/env python3
"""Build and review the real Layer 3 production-evaluation substrate.

This script is the reproducible form of the Layer 3 acceptance follow-up: read
point-in-time Layer 3 target-state feature rows from PostgreSQL, generate
compact ``model_03_target_state_vector`` rows, persist the model table, build
promotion-evaluation artifacts, and ask Codex CLI for a strict review
artifact.

It does not persist manager-control-plane promotion decisions or activate
configs. Durable decision, activation, and rollback ownership lives in
`trading-manager`.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from model_governance.common.sql import database_url, quote_identifier
from model_governance.codex_cli import DEFAULT_CODEX_MODEL, invoke_codex_cli
from model_governance.promotion import build_model_config_ref, build_promotion_candidate_evidence
from model_governance.promotion.agent_review import extract_json_object, validate_promotion_review, build_review_artifact_from_review
from models.model_03_target_state_vector import evaluation, generator

DEFAULT_FEATURE_SCHEMA = "trading_data"
DEFAULT_FEATURE_TABLE = "m03_target_state_vector_feature_generation"
DEFAULT_MODEL_SCHEMA = "trading_model"
DEFAULT_MODEL_TABLE = "model_03_target_state_vector"
DEFAULT_MODEL_ID = evaluation.DEFAULT_MODEL_ID
DEFAULT_MODEL_VERSION = "model_03_target_state_vector"
DEFAULT_CONFIG_HASH = "target_context_state_contract_production_eval_20260508"
PRIMARY_JSON_MODEL_COLUMNS: set[str] = set()
EXPLAINABILITY_JSON_MODEL_COLUMNS = {"target_context_state", "target_state_embedding", "explanation_payload_json"}
DIAGNOSTICS_JSON_MODEL_COLUMNS = {"diagnostic_payload_json"}
TEXT_MODEL_COLUMNS = {
    "available_time",
    "tradeable_time",
    "target_candidate_id",
    "model_id",
    "model_version",
    "market_context_state_ref",
    "sector_context_state_ref",
    "target_context_state_ref",
    "state_cluster_id",
}
RETIRED_PRIMARY_COLUMNS = ("target_context_state", "target_state_embedding", "state_cluster_id", "state_quality_diagnostics")


def _primary_column_type(column: str) -> str:
    if column in PRIMARY_JSON_MODEL_COLUMNS:
        return "JSONB"
    if column == "available_time" or column == "tradeable_time":
        return "TIMESTAMPTZ"
    if column in TEXT_MODEL_COLUMNS:
        return "TEXT"
    if column == "3_evidence_count":
        return "INTEGER"
    return "DOUBLE PRECISION"


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:
        raise SystemExit("psycopg is required for SQL production-substrate review; install psycopg[binary].") from error
    return psycopg, dict_row


def read_feature_rows(*, db_url: str, schema: str, table: str, start: str | None, end: str | None) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[str] = []
    if start:
        clauses.append("available_time >= %s")
        params.append(start)
    if end:
        clauses.append("available_time < %s")
        params.append(end)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = (
        f"SELECT * FROM {quote_identifier(schema)}.{quote_identifier(table)}"
        f"{where} ORDER BY target_candidate_id, available_time"
    )
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [dict(row) for row in cur.fetchall()]
    if not rows:
        raise ValueError("no Layer 3 feature rows matched the requested production-eval window")
    return rows


def persist_model_rows(*, db_url: str, schema: str, table: str, rows: Sequence[Mapping[str, Any]]) -> None:
    columns = list(generator.OUTPUT_COLUMNS)
    ddl_columns = []
    for column in columns:
        ddl_columns.append(f"{quote_identifier(column)} {_primary_column_type(column)}")
    q_table = f"{quote_identifier(schema)}.{quote_identifier(table)}"
    primary_key = ", ".join(quote_identifier(column) for column in ("target_candidate_id", "available_time", "model_version"))
    placeholders = ["%s::jsonb" if column in PRIMARY_JSON_MODEL_COLUMNS else "%s" for column in columns]
    updates = ", ".join(
        f"{quote_identifier(column)} = EXCLUDED.{quote_identifier(column)}"
        for column in columns
        if column not in {"target_candidate_id", "available_time", "model_version"}
    )
    insert_sql = (
        f"INSERT INTO {q_table} ({', '.join(quote_identifier(column) for column in columns)}) "
        f"VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT ({primary_key}) DO UPDATE SET {updates}"
    )
    values = [
        tuple(json.dumps(row.get(column), sort_keys=True, default=str) if column in PRIMARY_JSON_MODEL_COLUMNS else row.get(column) for column in columns)
        for row in rows
    ]
    psycopg, _dict_row = _load_psycopg()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema)}")
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {q_table} "
                f"({', '.join(ddl_columns)}, PRIMARY KEY ({primary_key}))"
            )
            for column in columns:
                cur.execute(f"ALTER TABLE {q_table} ADD COLUMN IF NOT EXISTS {quote_identifier(column)} {_primary_column_type(column)}")
            for column in RETIRED_PRIMARY_COLUMNS:
                cur.execute(f"ALTER TABLE {q_table} DROP COLUMN IF EXISTS {quote_identifier(column)}")
            cur.executemany(insert_sql, values)
        conn.commit()


def _support_column_type(column: str, json_columns: set[str]) -> str:
    if column in json_columns:
        return "JSONB"
    if column in {"available_time"}:
        return "TIMESTAMPTZ"
    if column in {"3_evidence_count", "present_score_output_count", "missing_score_output_count"}:
        return "INTEGER"
    if column.startswith("3_"):
        return "DOUBLE PRECISION"
    return "TEXT"


def persist_support_rows(
    *,
    db_url: str,
    schema: str,
    table: str,
    rows: Sequence[Mapping[str, Any]],
    json_columns: set[str],
) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    q_table = f"{quote_identifier(schema)}.{quote_identifier(table)}"
    primary_key_columns = ("target_candidate_id", "available_time", "model_version")
    primary_key = ", ".join(quote_identifier(column) for column in primary_key_columns)
    ddl_columns = [f"{quote_identifier(column)} {_support_column_type(column, json_columns)}" for column in columns]
    placeholders = ["%s::jsonb" if column in json_columns else "%s" for column in columns]
    updates = ", ".join(
        f"{quote_identifier(column)} = EXCLUDED.{quote_identifier(column)}"
        for column in columns
        if column not in primary_key_columns
    )
    insert_sql = (
        f"INSERT INTO {q_table} ({', '.join(quote_identifier(column) for column in columns)}) "
        f"VALUES ({', '.join(placeholders)}) "
        f"ON CONFLICT ({primary_key}) DO UPDATE SET {updates}"
    )
    values = [
        tuple(json.dumps(row.get(column), sort_keys=True, default=str) if column in json_columns else row.get(column) for column in columns)
        for row in rows
    ]
    psycopg, _dict_row = _load_psycopg()
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema)}")
            cur.execute(f"CREATE TABLE IF NOT EXISTS {q_table} ({', '.join(ddl_columns)}, PRIMARY KEY ({primary_key}))")
            for column in columns:
                cur.execute(f"ALTER TABLE {q_table} ADD COLUMN IF NOT EXISTS {quote_identifier(column)} {_support_column_type(column, json_columns)}")
            cur.executemany(insert_sql, values)
        conn.commit()


def to_persistence_artifacts(artifacts: evaluation.EvaluationArtifacts) -> dict[str, list[dict[str, Any]]]:
    rows = artifacts.as_table_rows()
    return {
        "model_dataset_request": [
            {
                **row,
                "completed_at": row.get("required_data_end_time"),
                "status_detail": "real database evaluation substrate generated for Layer 3",
            }
            for row in rows["model_dataset_request"]
        ],
        "model_dataset_snapshot": rows["model_dataset_snapshot"],
        "model_dataset_split": rows["model_dataset_split"],
        "model_eval_label": [
            {
                "label_id": row["label_id"],
                "snapshot_id": row["snapshot_id"],
                "label_name": row["label_name"],
                "target_symbol": row["target_symbol"],
                "horizon": row["label_horizon"],
                "available_time": row["label_payload_json"]["feature_available_time"],
                "label_time": row["label_available_time"],
                "label_value": row["label_value"],
                "label_payload_json": row["label_payload_json"],
            }
            for row in rows["model_eval_label"]
        ],
        "model_eval_run": [
            {
                "eval_run_id": row["eval_run_id"],
                "model_id": row["model_id"],
                "snapshot_id": row["snapshot_id"],
                "run_name": "production_promotion_evaluation",
                "model_version": DEFAULT_MODEL_VERSION,
                "config_hash": DEFAULT_CONFIG_HASH,
                "run_status": row["eval_status"],
                "run_payload_json": row["eval_payload_json"],
                "completed_at": row["eval_completed_at"],
                "status_detail": "real database Layer 3 evaluation completed",
            }
            for row in rows["model_eval_run"]
        ],
        "model_promotion_metric": [
            {
                "metric_id": row["metric_id"].replace("mdmet_", "mpmet_l3_"),
                "eval_run_id": row["eval_run_id"],
                "split_id": None,
                "label_name": "future_target_tradeable_path",
                "target_symbol": "",
                "horizon": "all",
                "factor_name": "target_state_vector",
                "metric_name": row["metric_name"],
                "metric_value": row["metric_value"],
                "metric_payload_json": row["metric_payload_json"],
            }
            for row in rows["model_promotion_metric"]
        ],
    }


def build_summary(*, feature_rows: Sequence[Mapping[str, Any]], model_rows: Sequence[Mapping[str, Any]], artifacts: evaluation.EvaluationArtifacts, persistence_rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    metrics = artifacts.eval_metrics
    threshold_rows = [row for row in metrics if str(row.get("metric_name", "")).startswith("threshold:")]
    metric_value_summary = {
        str(row["metric_name"]): {"value": row.get("metric_value")}
        for row in metrics
        if not str(row.get("metric_name", "")).startswith("threshold:")
    }
    threshold_results = {
        str(row["metric_name"]).replace("threshold:", ""): {"actual": row.get("metric_value"), **dict(row.get("metric_payload_json") or {})}
        for row in threshold_rows
    }
    threshold_summary = evaluation.summarize_threshold_results(metrics)
    return {
        "eval_run_id": persistence_rows["model_eval_run"][0]["eval_run_id"],
        "snapshot_id": persistence_rows["model_dataset_snapshot"][0]["snapshot_id"],
        "model_id": DEFAULT_MODEL_ID,
        "write_policy": "database_persisted_production_eval_substrate",
        "evidence_source": "real_database_evaluation",
        "feature_row_count": len(feature_rows),
        "model_row_count": len(model_rows),
        "eval_label_count": len(persistence_rows["model_eval_label"]),
        "dataset_split_count": len(persistence_rows["model_dataset_split"]),
        "metric_value_summary": metric_value_summary,
        "threshold_results": threshold_results,
        "acceptance_thresholds": {key: value.get("threshold") for key, value in threshold_results.items()},
        "baseline_summary": {key: value["value"] for key, value in metric_value_summary.items() if "improvement" in key or "abs_corr" in key},
        "stability_summary": {key: value["value"] for key, value in metric_value_summary.items() if "stability" in key},
        "leakage_summary": {
            "leakage_violation_count": metric_value_summary.get("leakage_violation_count", {}).get("value"),
            "identity_leakage_policy": "anonymous_target_candidate_id_only",
        },
        "calibration_summary": None,
        "upstream_dependency_status": {
            "model_01_market_regime": "deferred_after_real_evaluation",
            "model_02_sector_context": "deferred_after_real_evaluation",
        },
        "promotion_gate_state": threshold_summary["promotion_gate_state"],
        "failed_thresholds": threshold_summary["failed_thresholds"],
    }


def build_review_prompt(summary: Mapping[str, Any], config_row: Mapping[str, Any], candidate_row: Mapping[str, Any]) -> str:
    payload = {"evaluation_summary": summary, "config_version": config_row, "promotion_candidate": candidate_row}
    return (
        "You are the independent promotion reviewer for trading-model Layer 3 TargetStateVectorModel.\n"
        "Evaluate whether this candidate can be promoted. Be strict.\n\n"
        "Hard rules:\n"
        "- Return ONLY one JSON object. No markdown, no prose outside JSON.\n"
        "- Promotion requires real database evidence, point-in-time dataset snapshot, labels, metrics, thresholds, baseline comparison, split/refit stability, leakage checks, calibration evidence, and passed thresholds.\n"
        "- Do not approve if upstream dependency models are not production-approved/active. Layer 3 depends on Layer 1 and Layer 2 production-approved states.\n"
        "- Do not approve if evidence has only local fixture rows, missing labels/metrics, failed thresholds, missing leakage checks, missing stability, or missing calibration.\n"
        "- If evidence is insufficient or upstream dependencies are deferred, use decision_type='defer' and decision_status='deferred'.\n"
        "- A model-side review artifact is not a durable manager decision or active production pointer. Deferred/rejected reviews must not activate config.\n\n"
        "Required JSON schema:\n"
        "{\n  \"can_promote\": boolean,\n  \"decision_type\": \"approve\" | \"reject\" | \"defer\",\n  \"decision_status\": \"accepted\" | \"rejected\" | \"deferred\",\n  \"confidence\": number,\n  \"reasons\": [string],\n  \"blockers\": [string],\n  \"required_next_steps\": [string],\n  \"evidence_checks\": { string: boolean }\n}\n\n"
        "Evidence:\n"
        + json.dumps(payload, indent=2, sort_keys=True, default=str)
        + "\n"
    )


def extract_agent_text(stdout: str) -> str:
    stripped = stdout.strip()
    if not stripped:
        raise ValueError("codex cli returned empty stdout")
    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if isinstance(parsed, dict):
        for container in (parsed, parsed.get("result")):
            if isinstance(container, dict) and isinstance(container.get("payloads"), list):
                for payload in container["payloads"]:
                    if isinstance(payload, dict) and isinstance(payload.get("text"), str) and payload["text"].strip():
                        return payload["text"]
        for key in ("message", "reply", "response", "content", "text", "output"):
            value = parsed.get(key)
            if isinstance(value, str) and value.strip():
                return value
    return stripped


def invoke_agent(*, prompt: str, codex_bin: str, model: str | None, timeout_seconds: int) -> dict[str, Any]:
    return validate_promotion_review(extract_json_object(extract_agent_text(invoke_codex_cli(prompt=prompt, codex_bin=codex_bin, model=model, timeout_seconds=timeout_seconds))))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--feature-schema", default=DEFAULT_FEATURE_SCHEMA)
    parser.add_argument("--feature-table", default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--model-schema", default=DEFAULT_MODEL_SCHEMA)
    parser.add_argument("--model-table", default=DEFAULT_MODEL_TABLE)
    parser.add_argument("--explainability-table", help="Optional explainability artifact table. Defaults to <model-table>_explainability.")
    parser.add_argument("--diagnostics-table", help="Optional diagnostics artifact table. Defaults to <model-table>_diagnostics.")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--config-hash", default=DEFAULT_CONFIG_HASH)
    parser.add_argument("--proposed-by", default="target_state_vector_production_eval_script")
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--artifacts-output", type=Path)
    parser.add_argument("--review-output", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Build evidence and prompt but do not call agent or write manager-control-plane rows.")
    parser.add_argument("--model", default=DEFAULT_CODEX_MODEL)
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--codex-bin", default="codex")
    args = parser.parse_args(argv)

    db_url = database_url(args.database_url)
    feature_rows = read_feature_rows(db_url=db_url, schema=args.feature_schema, table=args.feature_table, start=args.source_start, end=args.source_end)
    model_rows = generator.generate_rows(feature_rows)
    if not args.dry_run:
        persist_model_rows(db_url=db_url, schema=args.model_schema, table=args.model_table, rows=model_rows)
        persist_support_rows(
            db_url=db_url,
            schema=args.model_schema,
            table=args.explainability_table or f"{args.model_table}_explainability",
            rows=generator.build_explainability_rows(model_rows),
            json_columns=EXPLAINABILITY_JSON_MODEL_COLUMNS,
        )
        persist_support_rows(
            db_url=db_url,
            schema=args.model_schema,
            table=args.diagnostics_table or f"{args.model_table}_diagnostics",
            rows=generator.build_diagnostics_rows(model_rows),
            json_columns=DIAGNOSTICS_JSON_MODEL_COLUMNS,
        )
    artifacts = evaluation.build_evaluation_artifacts(
        feature_rows=feature_rows,
        model_rows=model_rows,
        purpose="production_promotion_evaluation",
        request_status="completed",
        write_policy="dry_run_no_database_writes" if args.dry_run else "database_persisted_production_eval_substrate",
        evidence_source="real_database_evaluation",
    )
    persistence_rows = to_persistence_artifacts(artifacts)
    summary = build_summary(feature_rows=feature_rows, model_rows=model_rows, artifacts=artifacts, persistence_rows=persistence_rows)
    config_row = build_model_config_ref(
        model_id=DEFAULT_MODEL_ID,
        model_version=DEFAULT_MODEL_VERSION,
        config_hash=args.config_hash,
        config_payload={"promotion_gate_source": str(args.summary_output or "generated_summary")},
    )
    candidate_row = build_promotion_candidate_evidence(
        model_id=DEFAULT_MODEL_ID,
        config_ref_id=config_row["config_ref_id"],
        eval_run_id=summary["eval_run_id"],
        proposed_by=args.proposed_by,
        candidate_payload={"evaluation_summary": summary},
    )
    prompt = build_review_prompt(summary, config_row, candidate_row)

    if args.summary_output:
        args.summary_output.parent.mkdir(parents=True, exist_ok=True)
        args.summary_output.write_text(json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    if args.artifacts_output:
        args.artifacts_output.parent.mkdir(parents=True, exist_ok=True)
        args.artifacts_output.write_text(json.dumps(persistence_rows, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    if args.dry_run:
        print(json.dumps({"summary": summary, "model_config_ref": config_row, "promotion_candidate": candidate_row, "agent_prompt": prompt}, indent=2, sort_keys=True, default=str))
        print("DRY RUN ONLY: no model rows, support rows, agent review, or manager promotion request were written.")
        return 0

    review = invoke_agent(
        prompt=prompt,
        codex_bin=args.codex_bin,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
    )
    review_artifact = build_review_artifact_from_review(candidate_ref=candidate_row["candidate_ref"], review=review)
    payload = {"model_config_ref": config_row, "promotion_candidate": candidate_row, "agent_review": review, "promotion_review_artifact": review_artifact}
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    if args.review_output:
        args.review_output.parent.mkdir(parents=True, exist_ok=True)
        args.review_output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    print("REVIEW ARTIFACT ONLY: manager control-plane request/decision/activation must be handled in trading-manager.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
