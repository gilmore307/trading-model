#!/usr/bin/env python3
"""Generate deterministic OptionExpressionModel rows from local JSON/JSONL or database rows.

This is a stable local entrypoint. It supports JSON/JSONL input and deliberately
does not activate production promotion state. The database path is safe for the
Layer 9 no-provider case: it consumes completed Layer 8 rows and emits
``no_option_expression`` rows when Layer 8 selected no underlying trade.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import database_url_file

from model_governance.model_output_support import write_model_output_with_support
from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_09_option_expression import MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
PRIMARY_KEY = ("option_expression_plan_ref",)
JSON_COLUMNS = {
    "9_resolved_no_option_reason_codes",
    "9_resolved_reason_codes",
    "pending_option_exposure_context",
    "expression_vector",
    "option_expression_plan",
}
EXPLAINABILITY_COLUMNS = {"pending_option_exposure_context", "expression_vector", "option_expression_plan"}
DIAGNOSTICS_COLUMNS = {"9_resolved_no_option_reason_codes", "9_resolved_reason_codes"}
TEXT_9_COLUMNS = {
    "9_resolved_expression_type",
    "9_resolved_option_right",
    "9_resolved_option_surface_status",
    "9_resolved_dominant_horizon",
    "9_resolved_selected_contract_ref",
}


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
    if column.startswith("9_"):
        return "TEXT" if column in TEXT_9_COLUMNS else "DOUBLE PRECISION"
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


def _fetch_layer_8_rows(cursor: Any, *, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('u."available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('u."available_time"::timestamptz < %s::timestamptz')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    explainability_table = "model_08_underlying_action_explainability"
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"trading_model.{explainability_table}",))
    exists = cursor.fetchone()
    if isinstance(exists, Mapping):
        support_exists = exists.get("table_ref") is not None
    else:
        support_exists = bool(exists and exists[0] is not None)
    if support_exists:
        cursor.execute(
            f"""
            SELECT
              u.*,
              s."symbol" AS "underlying_symbol",
              s."bar_close" AS "underlying_reference_price",
              e."underlying_action_vector",
              e."underlying_action_plan"
            FROM {_qualified('trading_model', 'model_08_underlying_action')} AS u
            LEFT JOIN {_qualified('trading_data', 'source_03_target_state')} AS s
              ON s."target_candidate_id" = u."target_candidate_id"
             AND s."available_time" = u."available_time"::timestamptz
            LEFT JOIN {_qualified('trading_model', explainability_table)} AS e
              ON e."underlying_action_plan_ref" = u."underlying_action_plan_ref"
            {where_sql}
            ORDER BY u."available_time"::timestamptz ASC, u."target_candidate_id" ASC
            """,
            params,
        )
    else:
        cursor.execute(
            f"""
            SELECT
              u.*,
              s."symbol" AS "underlying_symbol",
              s."bar_close" AS "underlying_reference_price"
            FROM {_qualified('trading_model', 'model_08_underlying_action')} AS u
            LEFT JOIN {_qualified('trading_data', 'source_03_target_state')} AS s
              ON s."target_candidate_id" = u."target_candidate_id"
             AND s."available_time" = u."available_time"::timestamptz
            {where_sql}
            ORDER BY u."available_time"::timestamptz ASC, u."target_candidate_id" ASC
            """,
            params,
        )
    return [dict(row) for row in cursor.fetchall()]


def _fetch_option_candidate_rows(cursor: Any, *, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    feature_table = "m09_option_expression_feature_generation"
    cursor.execute("SELECT to_regclass(%s) AS table_ref", (f"trading_data.{feature_table}",))
    exists = cursor.fetchone()
    if isinstance(exists, Mapping):
        table_exists = exists.get("table_ref") is not None
    else:
        table_exists = bool(exists and exists[0] is not None)
    if not table_exists:
        return []
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append('f."snapshot_time" >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('f."snapshot_time" < %s::timestamptz')
        params.append(source_end)
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
        FROM {_qualified('trading_data', feature_table)} AS f
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


def _candidate_index(candidate_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in candidate_rows:
        if str(row.get("snapshot_type") or "entry").lower() != "entry":
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


def _layer_9_input_rows(layer_8_rows: Sequence[Mapping[str, Any]], option_candidate_rows: Sequence[Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    candidates_by_underlying_time = _candidate_index(option_candidate_rows or [])
    rows: list[dict[str, Any]] = []
    for row in layer_8_rows:
        underlying_plan = _coerce_json_mapping(row.get("underlying_action_plan"))
        available_time = row.get("available_time")
        underlying = str(row.get("underlying_symbol") or "").upper()
        option_candidates = candidates_by_underlying_time.get((underlying, _time_key(available_time)), [])
        option_chain_snapshot_ref = None if not option_candidates else f"m09_option_expression_feature_generation:{underlying}:{_time_key(available_time)}"
        option_surface_status = "optionable_chain_available" if option_candidates else "optionable_chain_missing"
        rows.append(
            {
                "available_time": available_time,
                "tradeable_time": row.get("tradeable_time") or available_time,
                "target_candidate_id": row.get("target_candidate_id"),
                "underlying_action_plan_ref": row.get("underlying_action_plan_ref"),
                "underlying_action_plan": underlying_plan,
                "layer_8_underlying_handoff": underlying_plan.get("handoff_to_layer_9") or underlying_plan.get("handoff_to_layer_9", {}),
                "market_context_state": {},
                "event_context_vector": {},
                "option_expression_policy": {},
                "option_contract_candidates": option_candidates,
                "option_surface_status": option_surface_status,
                "option_chain_snapshot_ref": option_chain_snapshot_ref,
                "option_quote_available_time": available_time if option_candidates else None,
                "underlying_quote_snapshot_ref": None if not underlying else f"source_03_target_state:{row.get('target_candidate_id')}:{_time_key(available_time)}",
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
            layer_8_rows = _fetch_layer_8_rows(cursor, source_start=source_start, source_end=source_end)
            option_candidate_rows = _fetch_option_candidate_rows(cursor, source_start=source_start, source_end=source_end)
            model_rows = generate_rows(_layer_9_input_rows(layer_8_rows, option_candidate_rows), model_version=model_version)
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
    parser.add_argument("--target-table", default="model_09_option_expression")
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
    rows = generate_layer("models.model_09_option_expression", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
