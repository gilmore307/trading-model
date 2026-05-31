#!/usr/bin/env python3
"""Diagnose Layer 1 MarketRegimeModel promotion substrate gaps.

Default mode is a fixture dry run. ``--from-database`` performs read-only SQL
queries against source, feature, and model tables and writes no rows.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from zoneinfo import ZoneInfo

from model_runtime.config import database_url_file
from models.model_01_market_regime.evaluation import (
    DEFAULT_FEATURE_SCHEMA,
    DEFAULT_FEATURE_TABLE,
    DEFAULT_MODEL_SCHEMA,
    DEFAULT_MODEL_TABLE,
)
from models.model_01_market_regime.substrate_diagnostics import diagnose_substrate

ET = ZoneInfo("America/New_York")
DEFAULT_DB_URL_FILE = database_url_file()
DEFAULT_SOURCE_SCHEMA = "trading_data"
DEFAULT_SOURCE_TABLE = "m01_market_regime_data_acquisition"
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


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


def _ident(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_ident(schema)}.{_ident(table)}"


def _run_psql(database_url: str, sql: str) -> str:
    result = subprocess.run(
        ["psql", database_url, "-v", "ON_ERROR_STOP=1", "-q", "-At"],
        input=sql,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        if result.stdout:
            print(result.stdout, file=sys.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        raise SystemExit(result.returncode)
    return result.stdout


def _fetch_json_rows(database_url: str, *, schema: str, table: str, order_column: str) -> list[dict[str, Any]]:
    output = _run_psql(
        database_url,
        f"""
        SELECT row_to_json(t)::text
        FROM (
          SELECT * FROM {_qualified(schema, table)}
          ORDER BY {_ident(order_column)} ASC
        ) AS t;
        """,
    )
    return [json.loads(line) for line in output.splitlines() if line.strip().startswith("{")]


def _fetch_source_symbol_rows(
    database_url: str,
    *,
    schema: str,
    table: str,
    source_start: str | None,
    source_end: str | None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    if source_start:
        where.append(f"timestamp >= '{_sql_literal(source_start)}'::timestamptz")
    if source_end:
        where.append(f"timestamp < '{_sql_literal(source_end)}'::timestamptz")
    where_sql = "WHERE " + " AND ".join(where) if where else ""
    output = _run_psql(
        database_url,
        f"""
        WITH scoped AS (
          SELECT
            symbol,
            timeframe,
            timestamp,
            CASE
              WHEN lower(timeframe) IN ('1d', '1day', 'day', 'daily') THEN 1
              WHEN (timestamp AT TIME ZONE 'America/New_York')::time BETWEEN TIME '09:30' AND TIME '16:00'
               AND EXTRACT(MINUTE FROM timestamp AT TIME ZONE 'America/New_York') IN (0, 30)
               AND EXTRACT(SECOND FROM timestamp AT TIME ZONE 'America/New_York') = 0
              THEN 1 ELSE 0
            END AS decision_row
          FROM {_qualified(schema, table)}
          {where_sql}
        )
        SELECT row_to_json(t)::text
        FROM (
          SELECT
            symbol,
            timeframe,
            COUNT(*) AS row_count,
            SUM(decision_row) AS decision_row_count,
            COUNT(DISTINCT CASE WHEN decision_row = 1 THEN (timestamp AT TIME ZONE 'America/New_York')::date END) AS decision_day_count,
            MIN(timestamp) AS start_time,
            MAX(timestamp) AS end_time
          FROM scoped
          GROUP BY symbol, timeframe
          ORDER BY symbol ASC, timeframe ASC
        ) AS t;
        """,
    )
    return [json.loads(line) for line in output.splitlines() if line.strip().startswith("{")]


def _sql_literal(value: str) -> str:
    return value.replace("'", "''")


def _flatten_feature_payload_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for row in rows:
        output = dict(row)
        payload = output.pop("feature_payload_json", None)
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, Mapping):
            output.update(payload)
        flattened.append(output)
    return flattened


def _fixture_rows() -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    source_rows = [
        {
            "symbol": "SPY",
            "timeframe": "30Min",
            "row_count": 10,
            "decision_row_count": 10,
            "decision_day_count": 2,
            "start_time": "2026-01-02T10:00:00-05:00",
            "end_time": "2026-01-03T16:00:00-05:00",
        }
    ]
    feature_rows = [
        {"snapshot_time": "2026-01-02T10:00:00-05:00", "spy_return_30m": 0.01},
        {"snapshot_time": "2026-01-02T10:30:00-05:00", "spy_return_30m": None},
    ]
    model_rows = [
        {
            "available_time": "2026-01-02T10:00:00-05:00",
            "1_market_direction_score": 0.1,
            "1_coverage_score": 0.1,
            "1_data_quality_score": 0.1,
        }
    ]
    return source_rows, feature_rows, model_rows


def _default_window_start() -> str:
    return datetime(2016, 1, 1, tzinfo=ET).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-database", action="store_true", help="Read current SQL source/feature/model substrate with read-only queries.")
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--source-schema", default=DEFAULT_SOURCE_SCHEMA)
    parser.add_argument("--source-table", default=DEFAULT_SOURCE_TABLE)
    parser.add_argument("--feature-schema", default=DEFAULT_FEATURE_SCHEMA)
    parser.add_argument("--feature-table", default=DEFAULT_FEATURE_TABLE)
    parser.add_argument("--model-schema", default=DEFAULT_MODEL_SCHEMA)
    parser.add_argument("--model-table", default=DEFAULT_MODEL_TABLE)
    parser.add_argument("--source-start", default=_default_window_start(), help="Optional lower source timestamp bound for aggregate source diagnostics.")
    parser.add_argument("--source-end", help="Optional upper source timestamp bound for aggregate source diagnostics. The bound is half-open.")
    parser.add_argument("--min-source-decision-days", type=int, default=252)
    parser.add_argument("--min-feature-signal-coverage", type=float, default=0.30)
    parser.add_argument("--output-json", type=Path, help="Optional local output path for the diagnostic summary.")
    args = parser.parse_args(argv)

    if args.from_database:
        database_url = _database_url(args.database_url)
        source_rows = _fetch_source_symbol_rows(
            database_url,
            schema=args.source_schema,
            table=args.source_table,
            source_start=args.source_start,
            source_end=args.source_end,
        )
        feature_rows = _flatten_feature_payload_rows(
            _fetch_json_rows(database_url, schema=args.feature_schema, table=args.feature_table, order_column="snapshot_time")
        )
        model_rows = _fetch_json_rows(database_url, schema=args.model_schema, table=args.model_table, order_column="available_time")
    else:
        source_rows, feature_rows, model_rows = _fixture_rows()

    payload = diagnose_substrate(
        source_symbol_rows=source_rows,
        feature_rows=feature_rows,
        model_rows=model_rows,
        min_source_decision_days=args.min_source_decision_days,
        min_feature_signal_coverage=args.min_feature_signal_coverage,
    )
    text = json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"
    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(text, encoding="utf-8")
        print(f"wrote substrate diagnostic to {args.output_json}", file=sys.stderr)
    else:
        print(text, end="")
    if args.from_database:
        print("READ ONLY: database rows were read, but no source, feature, model, evaluation, or promotion rows were written.", file=sys.stderr)
    else:
        print("DRY RUN ONLY: no database connection was opened and no rows were written.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
