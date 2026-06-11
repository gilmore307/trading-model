#!/usr/bin/env python3
"""Generate UnifiedDecisionModel rows from local JSON/JSONL or database rows."""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_runtime.config import database_url_file

from model_governance.local_layer_scripts import FIXTURE_INPUT_ROWS, generate_layer, read_rows, write_rows
from model_governance.model_output_support import write_model_output_with_support
from models.model_04_unified_decision import MODEL_SURFACE, MODEL_VERSION, generate_rows

DEFAULT_DB_URL_FILE = database_url_file()
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")
JSON_COLUMNS = {"4_resolved_reason_codes", "unified_decision_vector", "direct_underlying_intent", "unified_decision_diagnostics"}
PRIMARY_KEY = ("unified_decision_vector_ref",)
EXPLAINABILITY_COLUMNS = {"unified_decision_vector", "direct_underlying_intent"}
DIAGNOSTICS_COLUMNS = {"4_resolved_reason_codes", "unified_decision_diagnostics"}
TEXT_4_COLUMNS = {"4_resolved_decision_horizon", "4_resolved_underlying_action_type", "4_resolved_action_side"}


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
    if column.startswith("4_"):
        return "TEXT" if column in TEXT_4_COLUMNS else "DOUBLE PRECISION"
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
        where.append('t."available_time"::timestamptz >= %s::timestamptz')
        params.append(source_start)
    if source_end:
        where.append('t."available_time"::timestamptz < %s::timestamptz')
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute("SELECT to_regclass(%s) AS table_ref", ("trading_model.model_04_event_failure_risk",))
    exists = cursor.fetchone()
    if isinstance(exists, Mapping):
        event_table_exists = exists.get("table_ref") is not None
    else:
        event_table_exists = bool(exists and exists[0] is not None)
    event_select_sql = ""
    event_join_sql = ""
    if event_table_exists:
        event_select_sql = ',\n              to_jsonb(e) AS "event_state_vector"'
        event_join_sql = f"""
            LEFT JOIN {_qualified('trading_model', 'model_04_event_failure_risk')} AS e
              ON e."target_candidate_id" = t."target_candidate_id"
             AND e."available_time"::timestamptz = t."available_time"::timestamptz
        """
    cursor.execute(
        f"""
        SELECT
          t.*,
          q."symbol" AS "underlying_symbol",
          q."bar_close" AS "underlying_reference_price",
          q."last_bid",
          q."last_ask",
          q."avg_spread",
          q."spread_bps",
          q."dollar_volume",
          to_jsonb(t) AS "target_context_state"
          {event_select_sql}
        FROM {_qualified('trading_model', 'model_03_target_state_vector')} AS t
        LEFT JOIN {_qualified('trading_data', 'm03_target_state_vector_data_acquisition')} AS q
          ON q."target_candidate_id" = t."target_candidate_id"
         AND q."available_time" = t."available_time"::timestamptz
        {event_join_sql}
        {where_sql}
        ORDER BY t."available_time"::timestamptz ASC, t."target_candidate_id" ASC
        """,
        params,
    )
    return [dict(row) for row in cursor.fetchall()]


def _model_04_input_rows(source_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in source_rows:
        target = row.get("target_context_state") if isinstance(row.get("target_context_state"), Mapping) else dict(row)
        event = row.get("event_state_vector") if isinstance(row.get("event_state_vector"), Mapping) else {}
        reference_price = row.get("underlying_reference_price")
        bid = row.get("last_bid")
        ask = row.get("last_ask")
        spread_bps = row.get("spread_bps")
        rows.append(
            {
                "available_time": row.get("available_time"),
                "tradeable_time": row.get("tradeable_time") or row.get("available_time"),
                "target_candidate_id": row.get("target_candidate_id"),
                "target_context_state_ref": row.get("target_context_state_ref"),
                "event_state_vector_ref": row.get("event_failure_risk_vector_ref"),
                "target_context_state": target,
                "event_state_vector": event,
                "quality_calibration_state": {
                    "data_quality_score": row.get("3_state_quality_score", 0.70),
                    "walk_forward_reliability_score": 0.65,
                    "out_of_distribution_score": 0.15,
                },
                "portfolio_exposure_state": {"gross_exposure_capacity_score": 0.85, "correlation_concentration_score": 0.20},
                "account_capacity_state": {"cash_capacity_score": 0.78, "drawdown_pressure_score": 0.12},
                "current_underlying_position_state": {"current_underlying_exposure_score": 0.0},
                "pending_underlying_order_state": {"pending_underlying_exposure_score": 0.0, "pending_fill_probability_estimate": 0.0},
                "cost_friction_state": {"spread_cost_estimate": 0.001, "slippage_cost_estimate": 0.001, "fee_cost_estimate": 0.0005, "turnover_cost_estimate": 0.001},
                "underlying_quote_state": {
                    "reference_price": reference_price,
                    "bid_price": bid,
                    "ask_price": ask,
                    "halt_status": "active",
                    "quote_snapshot_ref": None if not row.get("underlying_symbol") else f"m03_target_state_vector_data_acquisition:{row.get('target_candidate_id')}:{row.get('available_time')}",
                },
                "underlying_liquidity_state": {
                    "spread_bps": spread_bps,
                    "dollar_volume": row.get("dollar_volume"),
                    "liquidity_score": 0.95,
                },
                "underlying_borrow_state": {"short_borrow_status": "available"},
                "risk_budget_state": {"risk_budget_available_score": 0.95},
                "policy_gate_state": {"direct_underlying_action_allowed": True, "preferred_decision_horizon": "1W"},
            }
        )
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
            source_rows = _fetch_database_input_rows(cursor, source_start=source_start, source_end=source_end)
            model_rows = generate_rows(_model_04_input_rows(source_rows), model_version=model_version)
            _write_sql(cursor, model_rows, target_schema=target_schema, target_table=target_table)
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
    parser.add_argument("--target-table", default="model_04_unified_decision")
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
    rows = generate_layer("models.model_04_unified_decision", input_rows, model_version=args.model_version)
    write_rows(rows, args.output_jsonl)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
