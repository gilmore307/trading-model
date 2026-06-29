#!/usr/bin/env python3
"""Generate TargetStateModel rows from local JSON/JSONL rows or database features."""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

from model_runtime.config import database_url_file
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from model_governance.model_output_support import write_model_output_with_support
from models.model_02_target_state import MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {"target_context_state", "target_state_diagnostics"}
PRIMARY_KEY = ("target_context_state_ref",)
EXPLAINABILITY_COLUMNS = {"target_context_state"}
DIAGNOSTICS_COLUMNS = {"target_state_diagnostics"}
TEXT_2_COLUMNS: set[str] = set()
PROGRESS_HEARTBEAT_SECONDS = 60.0
DATABASE_BATCH_SIZE = 1000


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _column_type(column: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(column):
        raise ValueError(f"unsafe SQL column identifier: {column!r}")
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("2_"):
        return "TEXT" if column in TEXT_2_COLUMNS else "DOUBLE PRECISION"
    return "TEXT"


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_worker_id(worker_id: str) -> str:
    return "".join(char if char.isalnum() or char in {"_", "-"} else "_" for char in worker_id) or "worker"


def _progress_env() -> tuple[Path, str, str, str] | None:
    root = os.environ.get("TRADING_MANAGER_TASK_PROGRESS_ROOT", "").strip()
    worker_id = os.environ.get("TRADING_MANAGER_TASK_PROGRESS_WORKER_ID", "").strip()
    task_uid = os.environ.get("TRADING_MANAGER_TASK_PROGRESS_TASK_UID", "").strip()
    stage_id = os.environ.get("TRADING_MANAGER_TASK_PROGRESS_STAGE_ID", "").strip()
    if not all((root, worker_id, task_uid, stage_id)):
        return None
    return Path(root), worker_id, task_uid, stage_id


def _write_stage_progress(
    *,
    node_id: str,
    node_label: str,
    current_activity: str,
    processed_count: int | None = None,
    expected_count: int | None = None,
) -> None:
    env = _progress_env()
    if env is None:
        return
    progress_root, worker_id, task_uid, stage_id = env
    progress_root.mkdir(parents=True, exist_ok=True)
    path = progress_root / f"{_safe_worker_id(worker_id)}.json"
    now = _utc_now_iso()
    split_name = os.environ.get("TRADING_MODEL_DATASET_SPLIT_NAME", "").strip()
    split_policy = os.environ.get("TRADING_MODEL_DATASET_SPLIT_POLICY", "").strip()
    extra: dict[str, Any] = {
        "progress_basis": "chronological 12+3+3 train/validation/test month coverage required by the walk-forward fold",
        "source": "model_02_target_state_database_generator",
    }
    if split_name or split_policy:
        extra["dataset_split"] = {
            key: value
            for key, value in {
                "split_name": split_name,
                "split_policy": split_policy,
            }.items()
            if value
        }
    payload: dict[str, Any] = {
        "activity_details": [],
        "contract_type": "manager_worker_task_progress",
        "current_activity": current_activity,
        "elapsed_seconds": None,
        "expected_count": expected_count,
        "expected_seconds": None,
        "extra": extra,
        "nodes": [
            {
                "elapsed_seconds": None,
                "expected_count": expected_count,
                "expected_seconds": None,
                "node_id": node_id,
                "node_label": node_label,
                "processed_count": processed_count,
                "status": "running",
                "updated_at_utc": now,
            }
        ],
        "processed_count": processed_count,
        "progress_basis": extra["progress_basis"],
        "progress_source": "active_progress_file",
        "stage_id": stage_id,
        "status": "running",
        "task_uid": task_uid,
        "unit_label": "rows",
        "updated_at_utc": now,
        "worker_id": worker_id,
    }
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


class _ProgressHeartbeat:
    def __init__(self, *, node_id: str, node_label: str, current_activity: str) -> None:
        self.node_id = node_id
        self.node_label = node_label
        self.current_activity = current_activity
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"{node_id}_progress_heartbeat", daemon=True)

    def __enter__(self) -> "_ProgressHeartbeat":
        _write_stage_progress(node_id=self.node_id, node_label=self.node_label, current_activity=self.current_activity)
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def _run(self) -> None:
        while not self._stop.wait(PROGRESS_HEARTBEAT_SECONDS):
            _write_stage_progress(node_id=self.node_id, node_label=self.node_label, current_activity=self.current_activity)


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
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit("psycopg is required for SQL generation; install psycopg[binary].") from error
    return psycopg, dict_row


def _fetch_database_input_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('"available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('"available_time"::timestamptz < %s::timestamptz')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"""
        SELECT
          "available_time",
          "tradeable_time",
          "target_candidate_id",
          "market_context_state_ref" AS "background_context_state_ref",
          "market_state_features" AS "background_context_state",
          "target_state_features" AS "anonymous_target_feature_vector",
          "sector_state_features",
          "cross_state_features",
          "feature_quality_diagnostics"
        FROM {_qualified(source_schema, source_table)}
        {where_sql}
        ORDER BY "available_time"::timestamptz ASC, "target_candidate_id" ASC
        """,
        params,
    )
    return _model_02_input_rows(cursor.fetchall())


def _execute_database_input_query(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
) -> None:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('"available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('"available_time"::timestamptz < %s::timestamptz')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"""
        SELECT
          "available_time",
          "tradeable_time",
          "target_candidate_id",
          "market_context_state_ref" AS "background_context_state_ref",
          "market_state_features" AS "background_context_state",
          "target_state_features" AS "anonymous_target_feature_vector",
          "sector_state_features",
          "cross_state_features",
          "feature_quality_diagnostics"
        FROM {_qualified(source_schema, source_table)}
        {where_sql}
        ORDER BY "available_time"::timestamptz ASC, "target_candidate_id" ASC
        """,
        params,
    )


def _iter_database_input_row_batches(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
    batch_size: int | None = None,
) -> Iterator[list[dict[str, Any]]]:
    _execute_database_input_query(
        cursor,
        source_schema=source_schema,
        source_table=source_table,
        source_start=source_start,
        source_end=source_end,
    )
    effective_batch_size = batch_size or DATABASE_BATCH_SIZE
    while True:
        rows = cursor.fetchmany(effective_batch_size)
        if not rows:
            break
        yield _model_02_input_rows(rows)


def _model_02_input_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        features = dict(row.get("anonymous_target_feature_vector") or {})
        features.setdefault("sector_state_features", row.get("sector_state_features") or {})
        features.setdefault("cross_state_features", row.get("cross_state_features") or {})
        features.setdefault("feature_quality_diagnostics", row.get("feature_quality_diagnostics") or {})
        rows.append(
            {
                "available_time": row.get("available_time"),
                "tradeable_time": row.get("tradeable_time") or row.get("available_time"),
                "target_candidate_id": row.get("target_candidate_id"),
                "background_context_state_ref": row.get("background_context_state_ref"),
                "background_context_state": row.get("background_context_state") or {},
                "anonymous_target_feature_vector": features,
            }
        )
    return rows


def _write_sql(cursor: Any, rows: Sequence[Mapping[str, Any]], *, target_schema: str, target_table: str) -> None:
    write_model_output_with_support(
        cursor,
        rows,
        target_schema=target_schema,
        target_table=target_table,
        primary_key=PRIMARY_KEY,
        explainability_columns=EXPLAINABILITY_COLUMNS,
        diagnostics_columns=DIAGNOSTICS_COLUMNS,
    )


def generate_from_database(
    *,
    database_url: str,
    source_schema: str,
    source_table: str,
    source_start: str | None,
    source_end: str | None,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    total_count = 0
    output_rows: list[dict[str, Any]] = []
    with psycopg.connect(database_url, row_factory=dict_row) as read_conn, psycopg.connect(database_url, row_factory=dict_row) as write_conn:
        with read_conn.cursor(name="model_02_target_state_input_rows") as read_cursor, write_conn.cursor() as write_cursor:
            with _ProgressHeartbeat(
                node_id="fetch_database_input_rows",
                node_label="Fetch database input rows",
                current_activity="Streaming M02 target-state feature rows",
            ):
                for input_rows in _iter_database_input_row_batches(
                    read_cursor,
                    source_schema=source_schema,
                    source_table=source_table,
                    source_start=source_start,
                    source_end=source_end,
                ):
                    model_rows = generate_rows(input_rows, model_version=model_version)
                    _write_sql(write_cursor, model_rows, target_schema=target_schema, target_table=target_table)
                    if output_jsonl:
                        output_rows.extend(model_rows)
                    total_count += len(model_rows)
                    _write_stage_progress(
                        node_id="model_rows_written",
                        node_label="Model rows written",
                        current_activity=f"Wrote {total_count} M02 target-state rows",
                        processed_count=total_count,
                    )
    if output_jsonl:
        write_rows(output_rows, output_jsonl)
    return total_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/NDJSON or JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-schema", default="trading_data")
    parser.add_argument("--source-table", default="model_03_target_state_vector_feature_generation")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_02_target_state")
    args = parser.parse_args(argv)

    if args.from_database:
        count = generate_from_database(
            database_url=_database_url(args.database_url),
            source_schema=args.source_schema,
            source_table=args.source_table,
            source_start=args.source_start,
            source_end=args.source_end,
            target_schema=args.target_schema,
            target_table=args.target_table,
            model_version=args.model_version,
            output_jsonl=args.output_jsonl,
        )
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0

    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_02_target_state", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
