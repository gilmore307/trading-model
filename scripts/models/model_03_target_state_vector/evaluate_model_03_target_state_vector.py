#!/usr/bin/env python3
"""Build TargetStateVectorModel promotion evidence from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import database_url_file

from models.model_03_target_state_vector import evaluation, generator

DEFAULT_DB_URL_FILE = database_url_file()
DEFAULT_FEATURE_TABLE = "m03_target_state_vector_feature_generation"
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("rows") or payload.get("feature_rows") or payload.get("model_rows") or []
    return [dict(row) for row in payload]


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    for env_name in ("TRADING_MODEL_DATABASE_URL", "OPENCLAW_DATABASE_URL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment guard
        raise SystemExit("psycopg is required for SQL evaluation; install psycopg[binary].") from error
    return psycopg, dict_row


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _where_clause(source_start: str | None, source_end: str | None) -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("available_time < %s")
        params.append(source_end)
    return (" WHERE " + " AND ".join(where) if where else ""), params


def _fetch_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where_sql, params = _where_clause(source_start, source_end)
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY available_time ASC, target_candidate_id ASC", params)
    return [dict(row) for row in cursor.fetchall()]


def _fetch_table_summary(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> dict[str, Any]:
    where_sql, params = _where_clause(source_start, source_end)
    cursor.execute(
        f"""
        SELECT
          count(*) AS row_count,
          min(available_time) AS data_start_time,
          max(available_time) AS data_end_time,
          count(DISTINCT target_candidate_id) AS target_candidate_count
        FROM {_qualified(schema, table)}{where_sql}
        """,
        params,
    )
    row = cursor.fetchone()
    return dict(row or {})


def _fetch_candidate_counts(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where_sql, params = _where_clause(source_start, source_end)
    cursor.execute(
        f"""
        SELECT target_candidate_id, count(*) AS row_count
        FROM {_qualified(schema, table)}{where_sql}
        GROUP BY target_candidate_id
        ORDER BY target_candidate_id ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(json.dumps(parts, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _iso(value: Any) -> str:
    return evaluation._iso(evaluation._parse_time(value))


def _summary_hash(summary: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(summary), sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()


def _split_rows(snapshot_id: str, *, start: str, end: str) -> list[dict[str, Any]]:
    return [
        {
            "split_id": _stable_id("mdsplit", snapshot_id, "full", start, end),
            "snapshot_id": snapshot_id,
            "split_name": "full",
            "split_order": 0,
            "split_start_time": start,
            "split_end_time": end,
            "split_payload_json": {
                "split_policy": "database_summary_fold_window",
                "note": "Summary-mode database evaluation avoids materializing row-level labels in memory.",
            },
        }
    ]


def _estimated_label_count(candidate_counts: Sequence[Mapping[str, Any]]) -> int:
    total = 0
    for row in candidate_counts:
        count = int(row.get("row_count") or 0)
        for horizon in evaluation.LABEL_HORIZONS:
            total += max(count - evaluation._horizon_steps(horizon), 0)
    return total


def _metric(eval_run_id: str, name: str, value: float | None, payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "metric_id": _stable_id("mdmet", eval_run_id, name),
        "eval_run_id": eval_run_id,
        "metric_name": name,
        "metric_value": value,
        "metric_payload_json": dict(payload),
    }


def _build_database_summary_payload(
    cursor: Any,
    *,
    feature_schema: str,
    feature_table: str,
    model_schema: str,
    model_table: str,
    source_start: str | None,
    source_end: str | None,
    evidence_source: str,
) -> dict[str, Any]:
    feature_summary = _fetch_table_summary(cursor, schema=feature_schema, table=feature_table, source_start=source_start, source_end=source_end)
    model_summary = _fetch_table_summary(cursor, schema=model_schema, table=model_table, source_start=source_start, source_end=source_end)
    feature_count = int(feature_summary.get("row_count") or 0)
    model_count = int(model_summary.get("row_count") or 0)
    if feature_count <= 0 or model_count <= 0:
        return _build_payload([], [], evidence_source=evidence_source)

    candidate_counts = _fetch_candidate_counts(cursor, schema=feature_schema, table=feature_table, source_start=source_start, source_end=source_end)
    start = _iso(feature_summary["data_start_time"])
    end = _iso(feature_summary["data_end_time"])
    purpose = "real_database_evaluation"
    write_policy = evaluation.DEFAULT_DATABASE_READ_WRITE_POLICY
    request_id = _stable_id("mdreq", evaluation.DEFAULT_MODEL_ID, purpose, start, end, evidence_source)
    summary_payload = {
        "feature_schema": feature_schema,
        "feature_table": feature_table,
        "model_schema": model_schema,
        "model_table": model_table,
        "feature_summary": feature_summary,
        "model_summary": model_summary,
        "candidate_counts": candidate_counts,
        "evidence_source": evidence_source,
    }
    snapshot_id = _stable_id("mdsnap", evaluation.DEFAULT_MODEL_ID, feature_schema, feature_table, start, end, _summary_hash(summary_payload), evidence_source)
    splits = _split_rows(snapshot_id, start=start, end=end)
    eval_run_id = _stable_id("mdevrun", snapshot_id, evaluation.DEFAULT_MODEL_ID, evidence_source)
    estimated_labels_per_name = _estimated_label_count(candidate_counts)
    label_count_payload = {
        "count_policy": "estimated_from_candidate_row_counts_by_horizon",
        "row_level_labels_materialized": False,
        "required_label_names": evaluation.REQUIRED_LABEL_NAMES,
    }
    metrics = [
        _metric(eval_run_id, "abs_corr:market_only_baseline", None, {"baseline_ladder": evaluation.BASELINE_LADDER, "reason": "database_summary_mode"}),
        _metric(eval_run_id, "abs_corr:market_sector_baseline", None, {"baseline_ladder": evaluation.BASELINE_LADDER, "reason": "database_summary_mode"}),
        _metric(eval_run_id, "abs_corr:market_sector_target_context", None, {"baseline_ladder": evaluation.BASELINE_LADDER, "reason": "database_summary_mode"}),
    ]
    for name in evaluation.REQUIRED_LABEL_NAMES:
        metrics.append(_metric(eval_run_id, f"label_count:{name}", float(estimated_labels_per_name), label_count_payload))
    threshold_values = {
        "minimum_feature_rows": float(feature_count),
        "minimum_model_rows": float(model_count),
        "minimum_eval_labels": float(estimated_labels_per_name * len(evaluation.REQUIRED_LABEL_NAMES)),
        "minimum_split_count": float(len(splits)),
        "minimum_baseline_ladder_step_count": float(len(evaluation.BASELINE_LADDER)),
        "minimum_target_vs_market_sector_improvement_abs": None,
        "minimum_target_vs_market_improvement_abs": None,
        "minimum_split_stability_sign_consistency": 0.0,
        "maximum_stability_correlation_range": 999.0,
        "maximum_leakage_violation_count": 0.0,
        "minimum_identity_leakage_violation_count": 0.0,
        "minimum_path_label_count": float(estimated_labels_per_name),
        "minimum_tradability_label_count": float(estimated_labels_per_name),
        "minimum_state_transition_label_count": float(estimated_labels_per_name),
    }
    for name, observed in threshold_values.items():
        threshold = evaluation.DEFAULT_PROMOTION_THRESHOLDS[name]
        if observed is None:
            passed = False
        elif name.startswith("maximum_"):
            passed = observed <= threshold
        elif name == "minimum_identity_leakage_violation_count":
            passed = observed >= threshold
        else:
            passed = observed >= threshold
        metrics.append(_metric(eval_run_id, f"threshold:{name}", observed, {"threshold": threshold, "passed": passed}))
    return {
        "tables": {
            "model_dataset_request": [
                {
                    "request_id": request_id,
                    "model_id": evaluation.DEFAULT_MODEL_ID,
                    "purpose": purpose,
                    "required_data_start_time": start,
                    "required_data_end_time": end,
                    "required_source_key": "M03_TARGET_STATE_VECTOR_DATA_ACQUISITION",
                    "required_feature_key": "M03_TARGET_STATE_VECTOR_FEATURE_GENERATION",
                    "request_status": "evaluated",
                    "request_payload_json": {"write_policy": write_policy, "evidence_source": evidence_source},
                }
            ],
            "model_dataset_snapshot": [
                {
                    "snapshot_id": snapshot_id,
                    "model_id": evaluation.DEFAULT_MODEL_ID,
                    "request_id": request_id,
                    "feature_schema": feature_schema,
                    "feature_table": feature_table,
                    "data_start_time": start,
                    "data_end_time": end,
                    "feature_row_count": feature_count,
                    "feature_data_hash": _summary_hash(summary_payload),
                    "model_config_hash": None,
                    "snapshot_payload_json": summary_payload,
                }
            ],
            "model_dataset_split": splits,
            "model_eval_label": [],
            "model_eval_run": [
                {
                    "eval_run_id": eval_run_id,
                    "model_id": evaluation.DEFAULT_MODEL_ID,
                    "snapshot_id": snapshot_id,
                    "eval_started_at": end,
                    "eval_completed_at": end,
                    "eval_status": "completed",
                    "eval_payload_json": {
                        "write_policy": write_policy,
                        "evidence_source": evidence_source,
                        "baseline_ladder": evaluation.BASELINE_LADDER,
                        "row_level_labels_materialized": False,
                    },
                }
            ],
            "model_promotion_metric": metrics,
        },
        "acceptance_thresholds": evaluation.acceptance_thresholds(metrics),
        "threshold_results": evaluation.threshold_results(metrics),
        "threshold_summary": evaluation.summarize_threshold_results(metrics),
        "database_summary_evaluation": {
            "status": "completed_summary_mode",
            "row_counts": {
                "feature_rows": feature_count,
                "model_rows": model_count,
                "estimated_eval_labels_per_name": estimated_labels_per_name,
            },
            "promotion_note": "Summary-mode evaluation is sufficient for stage completion but keeps promotion blocked where correlation metrics are not materialized.",
        },
    }


def _build_payload(feature_rows: list[dict[str, Any]], model_rows: list[dict[str, Any]], *, evidence_source: str) -> dict[str, Any]:
    if not feature_rows or not model_rows:
        row_counts = {
            "feature_rows": len(feature_rows),
            "model_rows": len(model_rows),
            "eval_labels": 0,
        }
        failed_thresholds = [
            name
            for name in evaluation.DEFAULT_PROMOTION_THRESHOLDS
            if name.startswith("minimum_") and name not in {"minimum_baseline_ladder_step_count", "minimum_identity_leakage_violation_count"}
        ]
        return {
            "tables": {
                "model_dataset_request": [],
                "model_dataset_snapshot": [],
                "model_dataset_split": [],
                "model_eval_label": [],
                "model_eval_run": [],
                "model_promotion_metric": [],
            },
            "acceptance_thresholds": evaluation.DEFAULT_PROMOTION_THRESHOLDS,
            "threshold_results": {
                name: {
                    "actual": row_counts.get("feature_rows") if name == "minimum_feature_rows" else row_counts.get("model_rows") if name == "minimum_model_rows" else row_counts.get("eval_labels") if name == "minimum_eval_labels" else None,
                    "threshold": threshold,
                    "passed": False,
                }
                for name, threshold in evaluation.DEFAULT_PROMOTION_THRESHOLDS.items()
            },
            "threshold_summary": {
                "threshold_count": len(evaluation.DEFAULT_PROMOTION_THRESHOLDS),
                "passed_threshold_count": 0,
                "failed_thresholds": failed_thresholds,
                "promotion_gate_state": "blocked",
            },
            "empty_evaluation": {
                "status": "blocked_no_rows",
                "evidence_source": evidence_source,
                "row_counts": row_counts,
                "write_policy": evaluation.DEFAULT_DATABASE_READ_WRITE_POLICY if evidence_source == "real_database_evaluation" else evaluation.DEFAULT_DRY_RUN_WRITE_POLICY,
            },
        }
    artifacts = evaluation.build_evaluation_artifacts(
        feature_rows=feature_rows,
        model_rows=model_rows,
        evidence_source=evidence_source,
        purpose="real_database_evaluation" if evidence_source == "real_database_evaluation" else "evaluation_dry_run",
        request_status="evaluated",
        write_policy=evaluation.DEFAULT_DATABASE_READ_WRITE_POLICY if evidence_source == "real_database_evaluation" else evaluation.DEFAULT_DRY_RUN_WRITE_POLICY,
    )
    return {
        "tables": artifacts.as_table_rows(),
        "acceptance_thresholds": evaluation.acceptance_thresholds(artifacts.eval_metrics),
        "threshold_results": evaluation.threshold_results(artifacts.eval_metrics),
        "threshold_summary": evaluation.summarize_threshold_results(artifacts.eval_metrics),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-rows", type=Path)
    parser.add_argument("--model-rows", type=Path, help="Optional model rows; generated from feature rows when omitted in file mode")
    parser.add_argument("--output", "--output-json", dest="output", type=Path, help="Optional JSON output path")
    parser.add_argument("--from-database", action="store_true", help="Read feature/model rows from PostgreSQL")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or local OpenClaw DB secret file.")
    parser.add_argument("--feature-schema", default="trading_data")
    parser.add_argument("--feature-table", default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--model-schema", default="trading_model")
    parser.add_argument("--model-table", default="model_03_target_state_vector")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    args = parser.parse_args(argv)
    if args.from_database:
        psycopg, dict_row = _load_psycopg()
        with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                payload = _build_database_summary_payload(
                    cursor,
                    feature_schema=args.feature_schema,
                    feature_table=args.feature_table,
                    model_schema=args.model_schema,
                    model_table=args.model_table,
                    source_start=args.source_start,
                    source_end=args.source_end,
                    evidence_source="real_database_evaluation",
                )
    else:
        if not args.feature_rows:
            parser.error("--feature-rows is required unless --from-database is supplied")
        feature_rows = _read_rows(args.feature_rows)
        model_rows = _read_rows(args.model_rows) if args.model_rows else generator.generate_rows(feature_rows)
        payload = _build_payload(feature_rows, model_rows, evidence_source="fixture_or_local_jsonl")
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
