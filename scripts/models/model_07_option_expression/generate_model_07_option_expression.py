#!/usr/bin/env python3
"""Generate deterministic OptionExpressionModel rows from local JSON/JSONL or database rows.

This is a stable local entrypoint. It supports JSON/JSONL input and deliberately
does not activate production promotion state. The database path is safe for the
Layer 8 no-provider case: it consumes completed Layer 7 rows and emits
``no_option_expression`` rows when Layer 7 selected no underlying trade.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from models.model_07_option_expression import MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
PRIMARY_KEY = ("option_expression_plan_ref",)
JSON_COLUMNS = {
    "7_resolved_no_option_reason_codes",
    "7_resolved_reason_codes",
    "pending_option_exposure_context",
    "expression_vector",
    "option_expression_plan",
}
TEXT_8_COLUMNS = {
    "7_resolved_expression_type",
    "7_resolved_option_right",
    "7_resolved_dominant_horizon",
    "7_resolved_selected_contract_ref",
}


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
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


def _fetch_layer_7_rows(cursor: Any, *, source_start: str | None, source_end: str | None) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("available_time::timestamptz >= %s::timestamptz")
        params.append(source_start)
    if source_end:
        where.append("available_time::timestamptz < %s::timestamptz")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"""
        SELECT *
        FROM {_qualified('trading_model', 'model_06_underlying_action')}
        {where_sql}
        ORDER BY available_time::timestamptz ASC, target_candidate_id ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _layer_8_input_rows(layer_7_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in layer_7_rows:
        underlying_plan = _coerce_json_mapping(row.get("underlying_action_plan"))
        rows.append(
            {
                "available_time": row.get("available_time"),
                "tradeable_time": row.get("tradeable_time") or row.get("available_time"),
                "target_candidate_id": row.get("target_candidate_id"),
                "underlying_action_plan_ref": row.get("underlying_action_plan_ref"),
                "underlying_action_plan": underlying_plan,
                "layer_8_underlying_handoff": underlying_plan.get("handoff_to_layer_8", {}),
                "market_context_state": {},
                "event_context_vector": {},
                "option_expression_policy": {},
                "option_contract_candidates": [],
                "option_chain_snapshot_ref": None,
                "option_quote_available_time": None,
                "underlying_quote_snapshot_ref": None,
                "underlying_reference_price": None,
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
    if not rows:
        return
    columns = list(rows[0].keys())
    _ensure_table(cursor, target_schema=target_schema, target_table=target_table, columns=columns)
    placeholders = ["%s::jsonb" if column in JSON_COLUMNS else "%s" for column in columns]
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in columns
        if column not in PRIMARY_KEY
    )
    insert_sql = f"""
        INSERT INTO {_qualified(target_schema, target_table)} ({", ".join(_quote_column_identifier(column) for column in columns)})
        VALUES ({", ".join(placeholders)})
        ON CONFLICT ({", ".join(_quote_column_identifier(column) for column in PRIMARY_KEY)}) DO UPDATE SET {update_sql}
    """
    for row in rows:
        cursor.execute(
            insert_sql,
            [json.dumps(row.get(column), sort_keys=True, default=str) if column in JSON_COLUMNS else row.get(column) for column in columns],
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
            layer_7_rows = _fetch_layer_7_rows(cursor, source_start=source_start, source_end=source_end)
            model_rows = generate_rows(_layer_8_input_rows(layer_7_rows), model_version=model_version)
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
    parser.add_argument("--target-table", default="model_07_option_expression")
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
    rows = generate_layer("models.model_07_option_expression", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
