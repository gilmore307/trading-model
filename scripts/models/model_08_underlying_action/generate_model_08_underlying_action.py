#!/usr/bin/env python3
"""Generate UnderlyingActionModel rows from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import database_url_file

from model_governance.model_output_support import write_model_output_with_support
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_08_underlying_action import MODEL_ID, MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {"8_resolved_reason_codes", "underlying_action_vector", "underlying_action_plan"}
PRIMARY_KEY = ("underlying_action_plan_ref",)
EXPLAINABILITY_COLUMNS = {"underlying_action_vector", "underlying_action_plan"}
DIAGNOSTICS_COLUMNS = {"8_resolved_reason_codes"}
TEXT_8_COLUMNS = {"8_resolved_underlying_action_type", "8_resolved_action_side", "8_resolved_dominant_horizon"}


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


def _column_type(column: str) -> str:
    if column in JSON_COLUMNS:
        return "JSONB"
    if column.startswith("8_"):
        return "TEXT" if column in TEXT_8_COLUMNS else "DOUBLE PRECISION"
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


def _fetch_rows(cursor: Any, *, schema: str, table: str, source_start: str | None, source_end: str | None, order_by: str) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(f"SELECT * FROM {_qualified(schema, table)}{where_sql} ORDER BY {order_by}", params)
    return [dict(row) for row in cursor.fetchall()]


def _prefixed_payload(row: Mapping[str, Any], prefix: str, json_column: str) -> dict[str, Any]:
    payload = _coerce_json_mapping(row.get(json_column))
    payload.update({str(key): value for key, value in row.items() if str(key).startswith(prefix) and value is not None})
    return payload


def _iso(value: Any) -> str:
    return str(value or "").strip().replace("Z", "+00:00")


def _source_rows_by_candidate_time(source_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    return {
        (str(row.get("target_candidate_id")), _iso(row.get("available_time"))): row
        for row in source_rows
        if row.get("target_candidate_id") and row.get("available_time")
    }


def _decision_rows(
    *,
    projection_rows: Sequence[Mapping[str, Any]],
    alpha_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]] = (),
) -> list[dict[str, Any]]:
    alpha_by_ref = {str(row.get("alpha_confidence_vector_ref")): row for row in alpha_rows if row.get("alpha_confidence_vector_ref")}
    source_by_candidate_time = _source_rows_by_candidate_time(source_rows)
    rows: list[dict[str, Any]] = []
    for projection in projection_rows:
        alpha_ref = str(projection.get("alpha_confidence_vector_ref") or "")
        alpha = alpha_by_ref.get(alpha_ref)
        if not alpha:
            continue
        source = source_by_candidate_time.get((str(projection.get("target_candidate_id")), _iso(projection.get("available_time"))))
        reference_price = source.get("bar_close") if source else None
        if reference_price in (None, ""):
            continue
        rows.append(
            {
                "available_time": projection.get("available_time"),
                "tradeable_time": projection.get("tradeable_time") or projection.get("available_time"),
                "target_candidate_id": projection.get("target_candidate_id"),
                "alpha_confidence_vector_ref": alpha_ref,
                "position_projection_vector_ref": projection.get("position_projection_vector_ref"),
                "alpha_confidence_vector": _prefixed_payload(alpha, "5_", "alpha_confidence_vector"),
                "position_projection_vector": _prefixed_payload(projection, "7_", "position_projection_vector"),
                "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
                "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
                "underlying_quote_state": {
                    "reference_price": reference_price,
                    "last_price": reference_price,
                    "close_price": reference_price,
                    "symbol": source.get("symbol") if source else None,
                    "halt_status": "active",
                    "quote_snapshot_ref": f"model_03_target_state_vector_data_acquisition:{projection.get('target_candidate_id')}:{_iso(projection.get('available_time'))}",
                },
                "underlying_liquidity_state": {"spread_bps": 10.0, "dollar_volume": 50000000.0, "liquidity_score": 0.90},
                "underlying_borrow_state": {"short_borrow_status": "available"},
                "risk_budget_state": {"risk_budget_fit_score": 0.75, "risk_budget_available_score": 0.75},
                "policy_gate_state": {"direct_underlying_action_allowed": True},
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
            projection_rows = _fetch_rows(cursor, schema="trading_model", table="model_07_position_projection", source_start=source_start, source_end=source_end, order_by="available_time::timestamptz ASC, target_candidate_id ASC")
            alpha_rows = _fetch_rows(cursor, schema="trading_model", table="model_05_alpha_confidence", source_start=source_start, source_end=source_end, order_by="available_time::timestamptz ASC, target_candidate_id ASC")
            source_rows = _fetch_rows(cursor, schema="trading_data", table="model_03_target_state_vector_data_acquisition", source_start=source_start, source_end=source_end, order_by="available_time::timestamptz ASC, target_candidate_id ASC")
            decisions = _decision_rows(projection_rows=projection_rows, alpha_rows=alpha_rows, source_rows=source_rows)
            if not decisions:
                raise SystemExit("Layer 8 database generation found no projection rows with matching Layer 5 alpha and source target-state price rows")
            model_rows = generate_rows(decisions, model_version=model_version)
            _write_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
    if output_jsonl:
        _write_jsonl(output_jsonl, model_rows)
    return len(model_rows)


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
    parser.add_argument("--target-table", default="model_08_underlying_action")
    args = parser.parse_args(argv)
    if args.from_database:
        count = generate_from_database(database_url=_database_url(args.database_url), source_start=args.source_start, source_end=args.source_end, target_schema=args.target_schema, target_table=args.target_table, model_version=args.model_version, output_jsonl=args.output_jsonl)
        print(f"generated {count} rows into {args.target_schema}.{args.target_table}")
        return 0
    input_rows = read_rows(args.input_jsonl) if args.input_jsonl else FIXTURE_INPUT_ROWS[MODEL_SURFACE]
    rows = generate_layer("models.model_08_underlying_action", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
