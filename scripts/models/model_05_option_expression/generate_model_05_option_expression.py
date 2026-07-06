#!/usr/bin/env python3
"""Generate deterministic OptionExpressionModel rows from local JSON/JSONL or database rows.

This is a stable local entrypoint. It supports JSON/JSONL input and deliberately
does not activate production promotion state. The database path is safe for the
M05 no-provider case: it consumes completed M04 rows and emits
``no_option_expression`` rows when M04 selected no underlying trade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from model_runtime.config import database_url_file

from model_governance.model_output_support import write_model_output_with_support
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from model_governance.progress_months import month_progress, month_progress_from_rows
from models.model_05_option_expression import CANDIDATE_SET_OUTPUT, MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
PRIMARY_KEY = ("option_expression_plan_ref",)
JSON_COLUMNS = {
    "5_resolved_no_option_reason_codes",
    "5_resolved_reason_codes",
    "pending_option_exposure_context",
    "expression_vector",
    CANDIDATE_SET_OUTPUT,
    "option_expression_plan",
}
EXPLAINABILITY_COLUMNS = {"pending_option_exposure_context", "expression_vector", CANDIDATE_SET_OUTPUT, "option_expression_plan"}
DIAGNOSTICS_COLUMNS = {"5_resolved_no_option_reason_codes", "5_resolved_reason_codes"}
TEXT_5_COLUMNS = {
    "5_resolved_expression_type",
    "5_resolved_option_right",
    "5_resolved_option_surface_status",
    "5_resolved_dominant_horizon",
    "5_resolved_selected_contract_ref",
}
PROGRESS_HEARTBEAT_SECONDS = 60.0
DATABASE_BATCH_SIZE = 500
OPTION_CANDIDATE_SNAPSHOT_TYPES = ("entry", "source_cache")
ET = ZoneInfo("America/New_York")


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
    month_progress_payload: Mapping[str, Any] | None = None,
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
        "source": "model_05_option_expression_database_generator",
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
        month_progress_payload: Mapping[str, Any] | None = None,
    ) -> None:
        self.node_id = node_id
        self.node_label = node_label
        self.current_activity = current_activity
        self.processed_count = processed_count
        self.expected_count = expected_count
        self.month_progress_payload = month_progress_payload
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
        month_progress_payload: Mapping[str, Any] | None = None,
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
            if month_progress_payload is not None:
                self.month_progress_payload = month_progress_payload
        self._write()

    def _snapshot(self) -> tuple[str, str, str, int | None, int | None, Mapping[str, Any] | None]:
        with self._lock:
            return self.node_id, self.node_label, self.current_activity, self.processed_count, self.expected_count, self.month_progress_payload

    def _write(self) -> None:
        node_id, node_label, current_activity, processed_count, expected_count, month_progress_payload = self._snapshot()
        _write_stage_progress(
            node_id=node_id,
            node_label=node_label,
            current_activity=current_activity,
            processed_count=processed_count,
            expected_count=expected_count,
            month_progress_payload=month_progress_payload,
        )

    def _run(self) -> None:
        while not self._stop.wait(PROGRESS_HEARTBEAT_SECONDS):
            self._write()


def _column_type(column: str) -> str:
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("5_"):
        return "TEXT" if column in TEXT_5_COLUMNS else "DOUBLE PRECISION"
    return "TEXT"


def _coerce_json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str) and value.strip():
        try:
            loaded = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return dict(loaded) if isinstance(loaded, Mapping) else {}
    return {}


def _model_04_support_exists(cursor: Any) -> bool:
    explainability_table = "model_04_unified_decision_explainability"
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"trading_model.{explainability_table}",))
    exists = cursor.fetchone()
    if isinstance(exists, Mapping):
        return exists.get("table_ref") is not None
    return bool(exists and exists[0] is not None)


def _model_04_select_sql(*, source_start: str | None, source_end: str | None, support_exists: bool) -> tuple[str, list[Any]]:
    explainability_table = "model_04_unified_decision_explainability"
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('u."available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('u."available_time"::timestamptz < %s::timestamptz')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    if support_exists:
        sql = f"""
            SELECT
              u."available_time",
              u."tradeable_time",
              u."target_candidate_id",
              u."unified_decision_vector_ref",
              s."symbol" AS "underlying_symbol",
              s."bar_close" AS "underlying_reference_price",
              e."direct_underlying_intent"
            FROM {_qualified('trading_model', 'model_04_unified_decision')} AS u
            LEFT JOIN {_qualified('trading_data', 'model_03_target_state_vector_data_acquisition')} AS s
              ON s."target_candidate_id" = u."target_candidate_id"
             AND s."available_time" = u."available_time"::timestamptz
            LEFT JOIN {_qualified('trading_model', explainability_table)} AS e
              ON e."unified_decision_vector_ref" = u."unified_decision_vector_ref"
            {where_sql}
            ORDER BY u."available_time"::timestamptz ASC, u."target_candidate_id" ASC
            """
    else:
        sql = f"""
            SELECT
              u."available_time",
              u."tradeable_time",
              u."target_candidate_id",
              u."unified_decision_vector_ref",
              s."symbol" AS "underlying_symbol",
              s."bar_close" AS "underlying_reference_price"
            FROM {_qualified('trading_model', 'model_04_unified_decision')} AS u
            LEFT JOIN {_qualified('trading_data', 'model_03_target_state_vector_data_acquisition')} AS s
              ON s."target_candidate_id" = u."target_candidate_id"
             AND s."available_time" = u."available_time"::timestamptz
            {where_sql}
            ORDER BY u."available_time"::timestamptz ASC, u."target_candidate_id" ASC
            """
    return sql, params


def _fetch_model_04_rows(cursor: Any, *, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    sql, params = _model_04_select_sql(
        source_start=source_start,
        source_end=source_end,
        support_exists=_model_04_support_exists(cursor),
    )
    cursor.execute(sql, params)
    return [dict(row) for row in cursor.fetchall()]


def _fetch_option_candidate_rows(
    cursor: Any,
    *,
    source_start: str | None,
    source_end: str | None,
    model_04_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    feature_table = "model_05_option_expression_feature_generation"
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"trading_data.{feature_table}",))
    exists = cursor.fetchone()
    if isinstance(exists, Mapping):
        table_exists = exists.get("table_ref") is not None
    else:
        table_exists = bool(exists and exists[0] is not None)
    if not table_exists:
        return []
    snapshot_type_sql = "lower(coalesce(f.\"snapshot_type\", '')) = ANY(%s)"
    where: list[str] = [snapshot_type_sql]
    snapshot_type_params = [list(OPTION_CANDIDATE_SNAPSHOT_TYPES)]
    params: list[Any] = [*snapshot_type_params]
    if source_start:
        where.append('f."snapshot_time" >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('f."snapshot_time" < %s::timestamptz')
        params.append(source_end)
    from_sql = f"FROM {_qualified('trading_data', feature_table)} AS f"
    if model_04_rows is not None:
        keys = sorted(
            {
                (str(row.get("underlying_symbol") or "").upper(), row.get("available_time"))
                for row in model_04_rows
                if row.get("underlying_symbol") and row.get("available_time")
            },
            key=lambda item: (item[0], _time_key(item[1])),
        )
        if not keys:
            return []
        cursor.execute(
            """
            CREATE TEMP TABLE IF NOT EXISTS m05_option_candidate_keys (
              underlying TEXT NOT NULL,
              snapshot_time TIMESTAMPTZ NOT NULL,
              PRIMARY KEY (underlying, snapshot_time)
            ) ON COMMIT DROP
            """
        )
        cursor.execute("TRUNCATE m05_option_candidate_keys")
        cursor.executemany(
            """
            INSERT INTO m05_option_candidate_keys (underlying, snapshot_time)
            VALUES (%s, %s::timestamptz)
            ON CONFLICT DO NOTHING
            """,
            keys,
        )
        cursor.execute("ANALYZE m05_option_candidate_keys")
        where = [snapshot_type_sql]
        params = [*snapshot_type_params]
        from_sql = f"""
        FROM m05_option_candidate_keys AS k
        JOIN LATERAL (
          SELECT
            f."underlying",
            f."snapshot_time",
            f."snapshot_type",
            f."option_symbol",
            f."feature_payload_json",
            f."feature_quality_diagnostics"
          FROM {_qualified('trading_data', feature_table)} AS f
          WHERE f."underlying" = k.underlying
            AND f."snapshot_time" = k.snapshot_time
        ) AS f ON TRUE
        """
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"""
        SELECT
          f."underlying",
          f."snapshot_time",
          f."snapshot_type",
          f."option_symbol",
          f."feature_payload_json",
          f."feature_quality_diagnostics"
        {from_sql}
        {where_sql}
        ORDER BY f."underlying" ASC, f."snapshot_time" ASC, f."option_symbol" ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _parse_time(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _time_key(value: Any) -> str:
    parsed = _parse_time(value)
    return parsed.isoformat() if parsed is not None else str(value or "")


def _stable_option_expression_plan_ref(row: Mapping[str, Any], *, model_version: str) -> str:
    parsed_time = _parse_time(row.get("available_time") or row.get("decision_time") or row.get("tradeable_time"))
    if parsed_time is None:
        parsed_time = datetime(1970, 1, 1, tzinfo=ET)
    if parsed_time.tzinfo is None:
        parsed_time = parsed_time.replace(tzinfo=ET)
    available_time = parsed_time.astimezone(ET).isoformat()
    target_candidate_id = str(row.get("target_candidate_id") or "").strip()
    digest = hashlib.sha256("|".join((target_candidate_id, available_time, model_version)).encode("utf-8")).hexdigest()[:16]
    return f"oep_{digest}"


def _existing_model_refs(
    cursor: Any,
    refs: Sequence[str],
    *,
    target_schema: str,
    target_table: str,
) -> set[str]:
    if not refs:
        return set()
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"{target_schema}.{target_table}",))
    exists = cursor.fetchone()
    table_exists = exists.get("table_ref") is not None if isinstance(exists, Mapping) else bool(exists and exists[0] is not None)
    if not table_exists:
        return set()
    cursor.execute(
        f"""
        SELECT "option_expression_plan_ref"
        FROM {_qualified(target_schema, target_table)}
        WHERE "option_expression_plan_ref" = ANY(%s)
        """,
        (list(refs),),
    )
    return {str(row["option_expression_plan_ref"] if isinstance(row, Mapping) else row[0]) for row in cursor.fetchall()}


def _filter_existing_input_rows(
    cursor: Any,
    input_rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
    model_version: str,
) -> tuple[list[dict[str, Any]], int]:
    refs_by_row = [
        (dict(row), _stable_option_expression_plan_ref(row, model_version=model_version))
        for row in input_rows
    ]
    existing_refs = _existing_model_refs(
        cursor,
        [ref for _, ref in refs_by_row],
        target_schema=target_schema,
        target_table=target_table,
    )
    return [row for row, ref in refs_by_row if ref not in existing_refs], len(existing_refs)


def _candidate_index(candidate_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in candidate_rows:
        if str(row.get("snapshot_type") or "entry").lower() not in OPTION_CANDIDATE_SNAPSHOT_TYPES:
            continue
        underlying = str(row.get("underlying") or "").upper()
        snapshot_time = _time_key(row.get("snapshot_time"))
        payload = _coerce_json_mapping(row.get("feature_payload_json"))
        diagnostics = _coerce_json_mapping(row.get("feature_quality_diagnostics"))
        contract_ref = str(row.get("option_symbol") or "")
        if not underlying or not snapshot_time or not contract_ref:
            continue
        option_right = payload.get("option_right") or payload.get("right") or payload.get("option_right_type")
        expiration = payload.get("expiration") or row.get("expiration")
        dte = payload.get("dte") or payload.get("days_to_expiration")
        mid = payload.get("mid_price") or payload.get("mid")
        implied_vol = payload.get("iv") or payload.get("implied_volatility") or payload.get("implied_vol")
        index.setdefault((underlying, snapshot_time), []).append(
            {
                "contract_ref": contract_ref,
                "option_symbol": contract_ref,
                "option_right": option_right,
                "right": option_right,
                "expiration": expiration,
                "dte": dte,
                "days_to_expiration": dte,
                "mid_price": mid,
                "mid": mid,
                "iv": implied_vol,
                "implied_volatility": implied_vol,
                "candidate_quality_diagnostics": diagnostics,
                **payload,
            }
        )
    return index


def _model_05_input_rows(model_04_rows: Sequence[Mapping[str, Any]], option_candidate_rows: Sequence[Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    candidates_by_underlying_time = _candidate_index(option_candidate_rows or [])
    rows: list[dict[str, Any]] = []
    for row in model_04_rows:
        direct_intent = _coerce_json_mapping(row.get("direct_underlying_intent"))
        available_time = row.get("available_time")
        underlying = str(row.get("underlying_symbol") or "").upper()
        option_candidates = candidates_by_underlying_time.get((underlying, _time_key(available_time)), [])
        option_chain_snapshot_ref = None if not option_candidates else f"model_05_option_expression_feature_generation:{underlying}:{_time_key(available_time)}"
        option_surface_status = "optionable_chain_available" if option_candidates else "optionable_chain_missing"
        rows.append(
            {
                "available_time": available_time,
                "tradeable_time": row.get("tradeable_time") or available_time,
                "target_candidate_id": row.get("target_candidate_id"),
                "unified_decision_vector_ref": row.get("unified_decision_vector_ref"),
                "direct_underlying_intent": direct_intent,
                "model_05_underlying_handoff": direct_intent.get("handoff_to_model_05", {}),
                "background_context_state": {},
                "event_state_vector": {},
                "option_expression_policy": {},
                "option_contract_candidates": option_candidates,
                "option_surface_status": option_surface_status,
                "option_chain_snapshot_ref": option_chain_snapshot_ref,
                "option_quote_available_time": available_time if option_candidates else None,
                "underlying_quote_snapshot_ref": None if not underlying else f"model_03_target_state_vector_data_acquisition:{row.get('target_candidate_id')}:{_time_key(available_time)}",
                "underlying_reference_price": row.get("underlying_reference_price"),
            }
        )
    return rows


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


def _append_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(json.dumps(row, sort_keys=True, default=str) + "\n" for row in rows)


def _database_batch_size() -> int:
    raw = os.environ.get("TRADING_MODEL_M05_DATABASE_BATCH_SIZE", "").strip()
    if not raw:
        return DATABASE_BATCH_SIZE
    try:
        value = int(raw)
    except ValueError:
        return DATABASE_BATCH_SIZE
    return max(1, value)


def generate_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    target_schema: str,
    target_table: str,
    model_version: str,
    output_jsonl: Path | None,
    resume_existing: bool = False,
) -> int:
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            with _ProgressHeartbeat(
                node_id="fetch_database_input_rows",
                node_label="Fetch database input rows",
                current_activity="Generating M05 option-expression rows from database inputs",
                processed_count=0,
                expected_count=1,
                month_progress_payload=month_progress(source_start=source_start, source_end=source_end),
            ) as progress:
                if output_jsonl:
                    _write_jsonl(output_jsonl, [])
                total_model_04_rows = 0
                total_model_rows = 0
                total_skipped_rows = 0
                batch_size = _database_batch_size()
                sql, params = _model_04_select_sql(
                    source_start=source_start,
                    source_end=source_end,
                    support_exists=_model_04_support_exists(cursor),
                )
                with conn.cursor(name="m05_model_04_input_rows", row_factory=dict_row) as model_04_cursor:
                    model_04_cursor.itersize = batch_size
                    model_04_cursor.execute(sql, params)
                    while True:
                        model_04_rows = [dict(row) for row in model_04_cursor.fetchmany(batch_size)]
                        if not model_04_rows:
                            break
                        total_model_04_rows += len(model_04_rows)
                        progress.update(
                            current_activity=f"Fetched {total_model_04_rows} M04 unified-decision rows",
                            processed_count=total_model_04_rows,
                            expected_count=None,
                            month_progress_payload=month_progress_from_rows(model_04_rows, source_start=source_start, source_end=source_end),
                        )
                        option_candidate_rows = _fetch_option_candidate_rows(
                            cursor,
                            source_start=source_start,
                            source_end=source_end,
                            model_04_rows=model_04_rows,
                        )
                        progress.update(
                            node_id="fetch_option_candidate_rows",
                            node_label="Fetch option candidate rows",
                            current_activity=f"Fetched {len(option_candidate_rows)} M05 option candidate rows for current batch",
                            processed_count=total_model_04_rows,
                            expected_count=None,
                            month_progress_payload=month_progress_from_rows(model_04_rows, source_start=source_start, source_end=source_end),
                        )
                        input_rows = _model_05_input_rows(model_04_rows, option_candidate_rows)
                        if resume_existing and input_rows:
                            input_rows, skipped_rows = _filter_existing_input_rows(
                                cursor,
                                input_rows,
                                target_schema=target_schema,
                                target_table=target_table,
                                model_version=model_version,
                            )
                            total_skipped_rows += skipped_rows
                            if skipped_rows:
                                progress.update(
                                    node_id="skip_existing_model_rows",
                                    node_label="Skip existing model rows",
                                    current_activity=f"Skipped {total_skipped_rows} existing M05 option-expression rows",
                                    processed_count=total_model_rows + total_skipped_rows,
                                    expected_count=None,
                                    month_progress_payload=month_progress_from_rows(model_04_rows, source_start=source_start, source_end=source_end),
                                )
                        progress.update(
                            node_id="build_model_input_rows",
                            node_label="Build model input rows",
                            current_activity=f"Built {len(input_rows)} M05 model input rows for current batch",
                            processed_count=total_model_04_rows,
                            expected_count=None,
                            month_progress_payload=month_progress_from_rows(input_rows, source_start=source_start, source_end=source_end),
                        )
                        if not input_rows:
                            model_rows = []
                        else:
                            row_update_interval = max(1, min(1000, len(input_rows) // 100 or 1))

                            def on_row_progress(processed_count: int, expected_count: int) -> None:
                                if processed_count == expected_count or processed_count % row_update_interval == 0:
                                    progress.update(
                                        node_id="generate_model_rows",
                                        node_label="Generate model rows",
                                        current_activity=f"Generated {total_model_rows + processed_count} M05 option-expression rows",
                                        processed_count=total_model_rows + processed_count,
                                        expected_count=None,
                                        month_progress_payload=month_progress_from_rows(input_rows, source_start=source_start, source_end=source_end),
                                    )

                            progress.update(
                                node_id="generate_model_rows",
                                node_label="Generate model rows",
                                current_activity=f"Generating next {len(input_rows)} M05 option-expression rows",
                                processed_count=total_model_rows,
                                expected_count=None,
                                month_progress_payload=month_progress_from_rows(input_rows, source_start=source_start, source_end=source_end),
                            )
                            model_rows = generate_rows(input_rows, model_version=model_version, progress_callback=on_row_progress)
                        progress.update(
                            node_id="write_model_rows",
                            node_label="Write model rows",
                            current_activity=f"Writing {len(model_rows)} M05 option-expression rows for current batch",
                            processed_count=total_model_rows,
                            expected_count=None,
                            month_progress_payload=month_progress_from_rows(input_rows, source_start=source_start, source_end=source_end),
                        )
                        _write_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
                        if output_jsonl and model_rows:
                            _append_jsonl(output_jsonl, model_rows)
                        total_model_rows += len(model_rows)
                progress.update(
                    node_id="model_rows_written",
                    node_label="Model rows written",
                    current_activity=f"Wrote {total_model_rows} M05 option-expression rows; skipped {total_skipped_rows} existing rows",
                    processed_count=total_model_rows + total_skipped_rows,
                    expected_count=max(total_model_rows + total_skipped_rows, 1),
                    month_progress_payload=month_progress(source_start=source_start, source_end=source_end, completed=True),
                )
    return total_model_rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, help="Local JSONL/JSON input rows. Defaults to a tiny fixture row.")
    parser.add_argument("--output-jsonl", type=Path, help="Optional output path; .jsonl writes newline-delimited JSON, otherwise JSON array.")
    parser.add_argument("--model-version", default=MODEL_VERSION)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_05_option_expression")
    parser.add_argument(
        "--resume-existing",
        action="store_true",
        help="Skip rows whose deterministic option_expression_plan_ref already exists in the target table.",
    )
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
            resume_existing=args.resume_existing,
        )
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0

    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_05_option_expression", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
