#!/usr/bin/env python3
"""Build and review the real Layer 3 production-evaluation substrate.

This script is the reproducible form of the Layer 3 closeout follow-up: read
point-in-time ``feature_03_target_state_vector`` rows from PostgreSQL, generate
compact ``model_03_target_state_vector`` rows, persist the model table, build
promotion-evaluation artifacts, ask the reviewer agent for a strict decision,
and optionally persist the reviewed deferred/approved decision.

It intentionally does not activate configs by default. Deferred/rejected
reviews never activate configs.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from model_governance.common.sql import database_url, quote_identifier
from model_governance.promotion import build_config_version_row, build_promotion_candidate_row
from model_governance.promotion.agent_review import extract_json_object, validate_promotion_review, build_decision_row_from_review
from model_governance.promotion.persistence import render_promotion_persistence_sql, run_psql
from models.model_03_target_state_vector import evaluation, generator

DEFAULT_FEATURE_SCHEMA = "trading_data"
DEFAULT_FEATURE_TABLE = "feature_03_target_state_vector"
DEFAULT_MODEL_SCHEMA = "trading_model"
DEFAULT_MODEL_TABLE = "model_03_target_state_vector"
DEFAULT_MODEL_ID = evaluation.DEFAULT_MODEL_ID
DEFAULT_MODEL_VERSION = "model_03_target_state_vector"
DEFAULT_CONFIG_HASH = "target_context_state_v1_contract_production_eval_20260508"
JSON_MODEL_COLUMNS = {"target_context_state", "target_state_embedding", "state_quality_diagnostics"}
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


def read_feature_rows(*, db_url: str, schema: str, table: str, start: str | None, end: str | None) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[str] = []
    if start:
        clauses.append("available_time >= %s")
        params.append(start)
    if end:
        clauses.append("available_time <= %s")
        params.append(end)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    sql = (
        f"SELECT * FROM {quote_identifier(schema)}.{quote_identifier(table)}"
        f"{where} ORDER BY target_candidate_id, available_time"
    )
    with psycopg.connect(db_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            rows = [dict(row) for row in cur.fetchall()]
    if not rows:
        raise ValueError("no Layer 3 feature rows matched the requested production-eval window")
    return rows


def persist_model_rows(*, db_url: str, schema: str, table: str, rows: Sequence[Mapping[str, Any]]) -> None:
    score_columns = sorted({key for row in rows for key in row if key.startswith("3_")})
    columns = [
        "available_time",
        "tradeable_time",
        "target_candidate_id",
        "model_id",
        "model_version",
        "market_context_state_ref",
        "sector_context_state_ref",
        "target_context_state_ref",
        *score_columns,
        "target_context_state",
        "target_state_embedding",
        "state_cluster_id",
        "state_quality_diagnostics",
    ]
    ddl_columns = []
    for column in columns:
        if column in JSON_MODEL_COLUMNS:
            kind = "JSONB"
        elif column in TEXT_MODEL_COLUMNS:
            kind = "TEXT"
        else:
            kind = "DOUBLE PRECISION"
        ddl_columns.append(f"{quote_identifier(column)} {kind}")
    q_table = f"{quote_identifier(schema)}.{quote_identifier(table)}"
    primary_key = ", ".join(quote_identifier(column) for column in ("target_candidate_id", "available_time", "model_version"))
    placeholders = ["%s::jsonb" if column in JSON_MODEL_COLUMNS else "%s" for column in columns]
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
        tuple(json.dumps(row.get(column), sort_keys=True, default=str) if column in JSON_MODEL_COLUMNS else row.get(column) for column in columns)
        for row in rows
    ]
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {quote_identifier(schema)}")
            cur.execute(
                f"CREATE TABLE IF NOT EXISTS {q_table} "
                f"({', '.join(ddl_columns)}, PRIMARY KEY ({primary_key}))"
            )
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
        "- A review decision is not an active production pointer. Deferred/rejected decisions must not activate config.\n\n"
        "Required JSON schema:\n"
        "{\n  \"can_promote\": boolean,\n  \"decision_type\": \"approve\" | \"reject\" | \"defer\",\n  \"decision_status\": \"accepted\" | \"rejected\" | \"deferred\",\n  \"confidence\": number,\n  \"reasons\": [string],\n  \"blockers\": [string],\n  \"required_next_steps\": [string],\n  \"evidence_checks\": { string: boolean }\n}\n\n"
        "Evidence:\n"
        + json.dumps(payload, indent=2, sort_keys=True, default=str)
        + "\n"
    )


def extract_agent_text(stdout: str) -> str:
    stripped = stdout.strip()
    if not stripped:
        raise ValueError("openclaw agent returned empty stdout")
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


def invoke_agent(*, prompt: str, openclaw_bin: str, agent: str, model: str | None, thinking: str, timeout_seconds: int) -> dict[str, Any]:
    command = [openclaw_bin, "agent", "--agent", agent, "--message", prompt, "--json", "--thinking", thinking, "--timeout", str(timeout_seconds)]
    if model:
        command.extend(["--model", model])
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return validate_promotion_review(extract_json_object(extract_agent_text(result.stdout)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument("--feature-schema", default=DEFAULT_FEATURE_SCHEMA)
    parser.add_argument("--feature-table", default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--model-schema", default=DEFAULT_MODEL_SCHEMA)
    parser.add_argument("--model-table", default=DEFAULT_MODEL_TABLE)
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--config-hash", default=DEFAULT_CONFIG_HASH)
    parser.add_argument("--proposed-by", default="target_state_vector_production_eval_script")
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--artifacts-output", type=Path)
    parser.add_argument("--review-output", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Build evidence and prompt but do not call agent or write governance rows.")
    parser.add_argument("--write-decision", action="store_true", help="Persist evaluation artifacts, config, candidate, and reviewed decision.")
    parser.add_argument("--activate-approved-config", action="store_true", help="Activate only if the review is an accepted approval. Deferred/rejected decisions never activate.")
    parser.add_argument("--agent", default="trader")
    parser.add_argument("--model")
    parser.add_argument("--thinking", default="high")
    parser.add_argument("--timeout-seconds", type=int, default=600)
    parser.add_argument("--openclaw-bin", default="openclaw")
    args = parser.parse_args(argv)

    db_url = database_url(args.database_url)
    feature_rows = read_feature_rows(db_url=db_url, schema=args.feature_schema, table=args.feature_table, start=args.source_start, end=args.source_end)
    model_rows = generator.generate_rows(feature_rows)
    persist_model_rows(db_url=db_url, schema=args.model_schema, table=args.model_table, rows=model_rows)
    artifacts = evaluation.build_evaluation_artifacts(
        feature_rows=feature_rows,
        model_rows=model_rows,
        purpose="production_promotion_evaluation",
        request_status="completed",
        write_policy="database_persisted_production_eval_substrate",
        evidence_source="real_database_evaluation",
    )
    persistence_rows = to_persistence_artifacts(artifacts)
    summary = build_summary(feature_rows=feature_rows, model_rows=model_rows, artifacts=artifacts, persistence_rows=persistence_rows)
    config_row = build_config_version_row(
        model_id=DEFAULT_MODEL_ID,
        model_version=DEFAULT_MODEL_VERSION,
        config_hash=args.config_hash,
        config_payload={"promotion_gate_source": str(args.summary_output or "generated_summary")},
    )
    candidate_row = build_promotion_candidate_row(
        model_id=DEFAULT_MODEL_ID,
        config_version_id=config_row["config_version_id"],
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
        print(json.dumps({"summary": summary, "config_version": config_row, "promotion_candidate": candidate_row, "agent_prompt": prompt}, indent=2, sort_keys=True, default=str))
        print("DRY RUN ONLY: model rows were generated/persisted, but no agent review or promotion decision was written.")
        return 0

    review = invoke_agent(
        prompt=prompt,
        openclaw_bin=args.openclaw_bin,
        agent=args.agent,
        model=args.model,
        thinking=args.thinking,
        timeout_seconds=args.timeout_seconds,
    )
    decision_row = build_decision_row_from_review(promotion_candidate_id=candidate_row["promotion_candidate_id"], review=review)
    payload = {"config_version": config_row, "promotion_candidate": candidate_row, "agent_review": review, "promotion_decision": decision_row}
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    if args.review_output:
        args.review_output.parent.mkdir(parents=True, exist_ok=True)
        args.review_output.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    if args.write_decision:
        sql = render_promotion_persistence_sql(
            evaluation_artifacts=persistence_rows,
            config_version_row=config_row,
            promotion_candidate_row=candidate_row,
            promotion_decision_row=decision_row,
            schema=args.model_schema,
            activate_approved_config=args.activate_approved_config,
        )
        run_psql(db_url, sql)
        print(f"persisted promotion decision {decision_row['promotion_decision_id']} for candidate {candidate_row['promotion_candidate_id']}")
        if args.activate_approved_config and review["can_promote"]:
            print(f"activated config {config_row['config_version_id']}")
        elif args.activate_approved_config:
            print("activation skipped because decision was not an accepted approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
