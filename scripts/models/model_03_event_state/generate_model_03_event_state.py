#!/usr/bin/env python3
"""Generate EventStateModel rows from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from collections import deque
from collections.abc import Iterator, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from model_runtime.config import database_url_file

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from model_governance.model_output_support import write_model_output_with_support
from model_governance.progress_months import month_progress, month_progress_from_rows
from models.model_03_event_state import MODEL_SURFACE, MODEL_VERSION, generate_rows

COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {"event_state_vector", "event_state_diagnostics"}
TEXT_3_COLUMNS: set[str] = set()
PRIMARY_KEY = ("event_state_vector_ref",)
EXPLAINABILITY_COLUMNS = {"event_state_vector"}
DIAGNOSTICS_COLUMNS = {"event_state_diagnostics"}
DEFAULT_DB_URL_FILE = database_url_file()
DATABASE_BATCH_SIZE = 5000
DEFAULT_EVENT_LOOKBACK_DAYS = 7


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
    month_progress_payload: Mapping[str, Any] | None = None,
) -> None:
    env = _progress_env()
    if env is None:
        return
    progress_root, worker_id, task_uid, stage_id = env
    progress_root.mkdir(parents=True, exist_ok=True)
    now = _utc_now_iso()
    split_name = os.environ.get("TRADING_MODEL_DATASET_SPLIT_NAME", "").strip()
    split_policy = os.environ.get("TRADING_MODEL_DATASET_SPLIT_POLICY", "").strip()
    extra: dict[str, Any] = {
        "progress_basis": "chronological 12+3+3 train/validation/test month coverage required by the walk-forward fold",
        "source": "model_03_event_state_database_generator",
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
    if month_progress_payload:
        extra["month_progress"] = dict(month_progress_payload)
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
        "stage_id": stage_id,
        "status": "running",
        "task_uid": task_uid,
        "unit_label": "rows",
        "updated_at_utc": now,
        "worker_id": worker_id,
    }
    path = progress_root / f"{_safe_worker_id(worker_id)}.json"
    temp_path = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp_path, path)


def _column_type(column: str) -> str:
    if not COLUMN_IDENTIFIER_RE.match(column):
        raise ValueError(f"unsafe SQL column identifier: {column!r}")
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("3_"):
        return "TEXT" if column in TEXT_3_COLUMNS else "DOUBLE PRECISION"
    return "TEXT"


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


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]], *, append: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with path.open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _database_input_where(*, source_start: str | None, source_end: str | None, alias: str = "t") -> tuple[str, list[Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append(f'{alias}."available_time" >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append(f'{alias}."available_time" < %s::timestamptz')
        params.append(source_end)
    return (" WHERE " + " AND ".join(where) if where else ""), params


def _count_database_target_rows(
    cursor: Any,
    *,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None,
) -> int:
    where_sql, params = _database_input_where(source_start=source_start, source_end=source_end, alias="t")
    if target_symbol:
        where_sql += (" AND " if where_sql else " WHERE ") + 'upper(q."symbol") = %s'
        params.append(target_symbol.strip().upper())
    cursor.execute(
        f"""
        SELECT COUNT(*) AS row_count
        FROM trading_model.model_02_target_state AS t
        LEFT JOIN trading_data.model_03_target_state_vector_data_acquisition AS q
          ON q.target_candidate_id = t.target_candidate_id
         AND q.available_time = t.available_time
        {where_sql}
        """,
        params,
    )
    row = cursor.fetchone()
    if isinstance(row, Mapping):
        return int(row.get("row_count") or 0)
    return int(row[0] or 0)


def _fetch_event_rows(
    cursor: Any,
    *,
    source_start: str | None,
    source_end: str | None,
    event_lookback_days: int,
) -> list[dict[str, Any]]:
    where, params = _database_input_where(source_start=source_start, source_end=source_end, alias="e")
    if source_start and event_lookback_days > 0:
        where = where.replace('e."available_time" >= %s::timestamptz', 'e."available_time" >= (%s::timestamptz - %s::interval)', 1)
        params.insert(1, f"{event_lookback_days} days")
    cursor.execute(
        f"""
        SELECT *
        FROM trading_data.model_03_event_state_data_acquisition AS e
        {where}
        ORDER BY e.available_time ASC, e.event_id ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _execute_target_query(
    cursor: Any,
    *,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None,
) -> None:
    where_sql, params = _database_input_where(source_start=source_start, source_end=source_end, alias="t")
    if target_symbol:
        where_sql += (" AND " if where_sql else " WHERE ") + 'upper(q."symbol") = %s'
        params.append(target_symbol.strip().upper())
    cursor.execute(
        f"""
        SELECT
          t.*,
          q.symbol AS symbol_for_join_only,
          e.target_context_state
        FROM trading_model.model_02_target_state AS t
        LEFT JOIN trading_data.model_03_target_state_vector_data_acquisition AS q
          ON q.target_candidate_id = t.target_candidate_id
         AND q.available_time = t.available_time
        LEFT JOIN trading_model.model_02_target_state_explainability AS e
          ON e.target_context_state_ref = t.target_context_state_ref
        {where_sql}
        ORDER BY t.available_time ASC, t.target_candidate_id ASC
        """,
        params,
    )


def _iter_database_input_row_batches(
    cursor: Any,
    *,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None,
    events: Sequence[Mapping[str, Any]],
    event_lookback_days: int,
    batch_size: int = DATABASE_BATCH_SIZE,
) -> Iterator[list[dict[str, Any]]]:
    _execute_target_query(cursor, source_start=source_start, source_end=source_end, target_symbol=target_symbol)
    active_events: deque[Mapping[str, Any]] = deque()
    event_index = 0
    lookback = timedelta(days=max(event_lookback_days, 0))
    batch: list[dict[str, Any]] = []
    while True:
        raw_rows = cursor.fetchmany(batch_size)
        if not raw_rows:
            break
        for raw in raw_rows:
            row = dict(raw)
            available_time = row["available_time"]
            while event_index < len(events) and events[event_index]["available_time"] <= available_time:
                active_events.append(events[event_index])
                event_index += 1
            if lookback.total_seconds() > 0:
                cutoff = available_time - lookback
                while active_events and active_events[0]["available_time"] < cutoff:
                    active_events.popleft()
            row["events"] = [dict(event) for event in active_events]
            batch.append(row)
            if len(batch) >= batch_size:
                yield batch
                batch = []
    if batch:
        yield batch


def generate_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
    event_lookback_days: int,
) -> int:
    psycopg, dict_row = _load_psycopg()
    total_count = 0
    if output_jsonl and output_jsonl.exists():
        output_jsonl.unlink()
    with psycopg.connect(database_url, row_factory=dict_row) as read_conn, psycopg.connect(database_url, row_factory=dict_row) as write_conn:
        with read_conn.cursor(name="model_03_event_state_input_rows") as read_cursor, write_conn.cursor() as write_cursor:
            input_count = _count_database_target_rows(
                write_cursor,
                source_start=source_start,
                source_end=source_end,
                target_symbol=target_symbol,
            )
            if input_count <= 0:
                raise ValueError("at least one M03 event state input row is required")
            _write_stage_progress(
                node_id="fetch_database_input_rows",
                node_label="Fetch database input rows",
                current_activity="Streaming M03 event-state input rows",
                processed_count=0,
                expected_count=input_count,
                month_progress_payload=month_progress(source_start=source_start, source_end=source_end),
            )
            events = _fetch_event_rows(
                write_cursor,
                source_start=source_start,
                source_end=source_end,
                event_lookback_days=event_lookback_days,
            )
            for source_rows in _iter_database_input_row_batches(
                read_cursor,
                source_start=source_start,
                source_end=source_end,
                target_symbol=target_symbol,
                events=events,
                event_lookback_days=event_lookback_days,
            ):
                model_rows = generate_rows(source_rows, model_version=model_version)
                _write_sql(write_cursor, model_rows, target_schema=target_schema, target_table=target_table)
                write_conn.commit()
                if output_jsonl:
                    _write_jsonl(output_jsonl, model_rows, append=True)
                total_count += len(model_rows)
                _write_stage_progress(
                    node_id="model_rows_written",
                    node_label="Model rows written",
                    current_activity=f"Wrote {total_count}/{input_count} M03 event-state rows",
                    processed_count=total_count,
                    expected_count=input_count,
                    month_progress_payload=month_progress_from_rows(source_rows, source_start=source_start, source_end=source_end),
                )
                print(f"wrote {total_count}/{input_count} M03 event-state rows", flush=True)
            _write_stage_progress(
                node_id="model_rows_written",
                node_label="Model rows written",
                current_activity=f"Wrote {total_count}/{input_count} M03 event-state rows",
                processed_count=total_count,
                expected_count=input_count,
                month_progress_payload=month_progress(source_start=source_start, source_end=source_end, completed=True),
            )
    return total_count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/NDJSON or JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-symbol")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_03_event_state")
    parser.add_argument("--event-lookback-days", type=int, default=DEFAULT_EVENT_LOOKBACK_DAYS)
    args = parser.parse_args(argv)

    if args.from_database:
        count = generate_from_database(
            database_url=_database_url(args.database_url),
            source_start=args.source_start,
            source_end=args.source_end,
            target_symbol=args.target_symbol,
            target_schema=args.target_schema,
            target_table=args.target_table,
            model_version=args.model_version,
            output_jsonl=args.output_jsonl,
            event_lookback_days=args.event_lookback_days,
        )
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0

    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_03_event_state", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
