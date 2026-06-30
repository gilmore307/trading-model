#!/usr/bin/env python3
"""Generate ResidualEventGovernanceModel rows from local JSON/JSONL rows."""
from __future__ import annotations

import argparse
import json
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import database_url_file

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from model_governance.model_output_support import write_model_output_with_support
from models.model_06_residual_event_governance import MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {
    "6_resolved_reason_codes",
    "event_risk_intervention",
    "residual_event_governance_diagnostics",
}
PRIMARY_KEY = ("event_risk_intervention_ref",)
EXPLAINABILITY_COLUMNS = {"event_risk_intervention"}
DIAGNOSTICS_COLUMNS = {"6_resolved_reason_codes", "residual_event_governance_diagnostics"}
TEXT_6_COLUMNS = {"6_resolved_intervention_action", "6_resolved_risk_horizon"}
PROGRESS_HEARTBEAT_SECONDS = 60.0


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _quote_column_identifier(identifier: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL column identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


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
        "source": "model_06_residual_event_governance_database_generator",
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
    def __init__(
        self,
        *,
        node_id: str,
        node_label: str,
        current_activity: str,
        processed_count: int | None = None,
        expected_count: int | None = None,
    ) -> None:
        self.node_id = node_id
        self.node_label = node_label
        self.current_activity = current_activity
        self.processed_count = processed_count
        self.expected_count = expected_count
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name=f"{node_id}_progress_heartbeat", daemon=True)

    def __enter__(self) -> "_ProgressHeartbeat":
        self._write()
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._stop.set()
        self._thread.join(timeout=1.0)

    def update(
        self,
        *,
        node_id: str | None = None,
        node_label: str | None = None,
        current_activity: str | None = None,
        processed_count: int | None = None,
        expected_count: int | None = None,
    ) -> None:
        with self._lock:
            if node_id is not None:
                self.node_id = node_id
            if node_label is not None:
                self.node_label = node_label
            if current_activity is not None:
                self.current_activity = current_activity
            if processed_count is not None:
                self.processed_count = processed_count
            if expected_count is not None:
                self.expected_count = expected_count
        self._write()

    def _snapshot(self) -> tuple[str, str, str, int | None, int | None]:
        with self._lock:
            return self.node_id, self.node_label, self.current_activity, self.processed_count, self.expected_count

    def _write(self) -> None:
        node_id, node_label, current_activity, processed_count, expected_count = self._snapshot()
        _write_stage_progress(
            node_id=node_id,
            node_label=node_label,
            current_activity=current_activity,
            processed_count=processed_count,
            expected_count=expected_count,
        )

    def _run(self) -> None:
        while not self._stop.wait(PROGRESS_HEARTBEAT_SECONDS):
            self._write()


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


def _column_type(column: str) -> str:
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("6_"):
        return "TEXT" if column in TEXT_6_COLUMNS else "DOUBLE PRECISION"
    return "TEXT"


def _ensure_table(cursor: Any, *, target_schema: str, target_table: str, columns: Sequence[str]) -> None:
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    column_defs = ",\n          ".join(f"{_quote_column_identifier(column)} {_column_type(column)}" for column in columns)
    pk_sql = ", ".join(_quote_column_identifier(column) for column in PRIMARY_KEY)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {_qualified(target_schema, target_table)} ({column_defs}, PRIMARY KEY ({pk_sql}))")
    for column in columns:
        cursor.execute(f"ALTER TABLE {_qualified(target_schema, target_table)} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} {_column_type(column)}")


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


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows), encoding="utf-8")


def _fetch_database_input_rows(cursor: Any, *, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('u."available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('u."available_time"::timestamptz < %s::timestamptz')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"""
        SELECT
            u."available_time",
            u."tradeable_time",
            u."target_candidate_id",
            u."background_context_state_ref",
            u."target_context_state_ref",
            u."event_state_vector_ref",
            u."unified_decision_vector_ref",
            e."unified_decision_vector",
            e."direct_underlying_intent",
            o."option_expression_plan_ref",
            oe."option_expression_plan"
        FROM {_qualified("trading_model", "model_04_unified_decision")} AS u
        LEFT JOIN {_qualified("trading_model", "model_04_unified_decision_explainability")} AS e
            ON e."unified_decision_vector_ref" = u."unified_decision_vector_ref"
        LEFT JOIN {_qualified("trading_model", "model_05_option_expression")} AS o
            ON o."unified_decision_vector_ref" = u."unified_decision_vector_ref"
        LEFT JOIN {_qualified("trading_model", "model_05_option_expression_explainability")} AS oe
            ON oe."option_expression_plan_ref" = o."option_expression_plan_ref"
        {where_sql}
        ORDER BY u."available_time"::timestamptz ASC, u."target_candidate_id" ASC
        """,
        params,
    )
    rows: list[dict[str, Any]] = []
    for raw in cursor.fetchall():
        row = dict(raw)
        row["event_observations"] = []
        rows.append(row)
    return rows


def generate_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
) -> int:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            with _ProgressHeartbeat(
                node_id="fetch_database_input_rows",
                node_label="Fetch database input rows",
                current_activity="Generating M06 residual-event-governance rows from database inputs",
                processed_count=0,
                expected_count=1,
            ) as progress:
                input_rows = _fetch_database_input_rows(cursor, source_start=source_start, source_end=source_end)
                progress.update(
                    current_activity=f"Fetched {len(input_rows)} M04/M05 input rows for M06 residual-event governance",
                    processed_count=1,
                    expected_count=3,
                )
                progress.update(
                    node_id="generate_model_rows",
                    node_label="Generate model rows",
                    current_activity=f"Generating {len(input_rows)} M06 residual-event-governance rows",
                    processed_count=0,
                    expected_count=max(len(input_rows), 1),
                )
                model_rows = generate_rows(input_rows, model_version=model_version)
                progress.update(
                    node_id="write_model_rows",
                    node_label="Write model rows",
                    current_activity=f"Writing {len(model_rows)} M06 residual-event-governance rows",
                    processed_count=0,
                    expected_count=max(len(model_rows), 1),
                )
                _write_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
                progress.update(
                    node_id="model_rows_written",
                    node_label="Model rows written",
                    current_activity=f"Wrote {len(model_rows)} M06 residual-event-governance rows",
                    processed_count=len(model_rows),
                    expected_count=max(len(model_rows), 1),
                )
    if output_jsonl:
        _write_jsonl(output_jsonl, model_rows)
    return len(model_rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/NDJSON or JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_06_residual_event_governance")
    args = parser.parse_args(argv)

    if args.from_database:
        count = generate_from_database(
            database_url=_database_url(args.database_url),
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
    rows = generate_layer("models.model_06_residual_event_governance", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
