#!/usr/bin/env python3
"""Generate model_01_market_regime rows from feature SQL rows."""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLUMN_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9_]+$")


def _load_generator():
    return importlib.import_module("models.model_01_market_regime.generator")


def _load_psycopg():
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover - environment guard
        raise SystemExit("psycopg is required for SQL generation; install psycopg[binary].") from error
    return psycopg, dict_row


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _quote_identifier(identifier: str) -> str:
    if not IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _quote_column_identifier(identifier: str) -> str:
    """Quote a reviewed output column name.

    Model-facing contracts use compact layer prefixes such as ``1_`` and
    ``2_``. Physical SQL columns preserve those canonical names; numeric-leading
    names are safe because every column identifier is quoted and restricted to
    alphanumeric/underscore characters.
    """

    if not COLUMN_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"unsafe SQL column identifier: {identifier!r}")
    return '"' + identifier.replace('"', '""') + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_quote_identifier(schema)}.{_quote_identifier(table)}"


def fetch_derived_rows(
    cursor: Any,
    *,
    source_schema: str,
    source_table: str,
    source_start: str | None = None,
    source_end: str | None = None,
) -> list[dict[str, Any]]:
    where: list[str] = []
    params: list[Any] = []
    if source_start:
        where.append("snapshot_time >= %s")
        params.append(source_start)
    if source_end:
        where.append("snapshot_time <= %s")
        params.append(source_end)
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    cursor.execute(
        f"SELECT * FROM {_qualified(source_schema, source_table)}{where_sql} ORDER BY snapshot_time ASC",
        params,
    )
    rows: list[dict[str, Any]] = []
    for source_row in cursor.fetchall():
        row = dict(source_row)
        payload = row.pop("feature_payload_json", None)
        if isinstance(payload, str):
            payload = json.loads(payload)
        if isinstance(payload, Mapping):
            row.update(payload)
        rows.append(row)
    return rows


def write_model_rows_sql(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
) -> None:
    if not rows:
        return
    generator = _load_generator()
    columns = list(generator.OUTPUT_COLUMNS)
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          "available_time" TIMESTAMPTZ PRIMARY KEY
        )
        """
    )
    sql_columns = list(columns)
    for column in sql_columns:
        if column == "available_time":
            continue
        cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS {_quote_column_identifier(column)} DOUBLE PRECISION")

    quoted_columns = [_quote_column_identifier(column) for column in sql_columns]
    placeholders = ", ".join(["%s"] * len(columns))
    update_sql = ", ".join(
        f"{_quote_column_identifier(column)} = EXCLUDED.{_quote_column_identifier(column)}"
        for column in sql_columns
        if column != "available_time"
    )
    insert_sql = f"""
        INSERT INTO {qualified_table} ({", ".join(quoted_columns)})
        VALUES ({placeholders})
        ON CONFLICT ("available_time") DO UPDATE SET {update_sql}
    """
    for row in rows:
        cursor.execute(insert_sql, [row.get(column) for column in columns])


def write_explainability_rows_sql(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
) -> None:
    if not rows:
        return
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          "available_time" TIMESTAMPTZ NOT NULL,
          "factor_name" TEXT NOT NULL,
          "factor_value" DOUBLE PRECISION,
          "explanation_payload_json" JSONB NOT NULL,
          PRIMARY KEY ("available_time", "factor_name")
        )
        """
    )
    insert_sql = f"""
        INSERT INTO {qualified_table} ("available_time", "factor_name", "factor_value", "explanation_payload_json")
        VALUES (%s, %s, %s, %s::jsonb)
        ON CONFLICT ("available_time", "factor_name") DO UPDATE SET
          "factor_value" = EXCLUDED."factor_value",
          "explanation_payload_json" = EXCLUDED."explanation_payload_json"
    """
    for row in rows:
        cursor.execute(
            insert_sql,
            [
                row.get("available_time"),
                row.get("factor_name"),
                row.get("factor_value"),
                json.dumps(row.get("explanation_payload_json", {}), sort_keys=True),
            ],
        )


def write_diagnostics_rows_sql(
    cursor: Any,
    rows: Sequence[Mapping[str, Any]],
    *,
    target_schema: str,
    target_table: str,
) -> None:
    if not rows:
        return
    qualified_table = _qualified(target_schema, target_table)
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {_quote_identifier(target_schema)}")
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {qualified_table} (
          "available_time" TIMESTAMPTZ PRIMARY KEY,
          "present_state_output_count" INTEGER,
          "missing_state_output_count" INTEGER,
          "data_quality_score" DOUBLE PRECISION,
          "diagnostic_payload_json" JSONB NOT NULL DEFAULT '{{}}'::jsonb
        )
        """
    )
    cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS \"present_state_output_count\" INTEGER")
    cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS \"missing_state_output_count\" INTEGER")
    cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS \"data_quality_score\" DOUBLE PRECISION")
    cursor.execute(f"ALTER TABLE {qualified_table} ADD COLUMN IF NOT EXISTS \"diagnostic_payload_json\" JSONB NOT NULL DEFAULT '{{}}'::jsonb")
    schema_literal = target_schema.replace("'", "''")
    table_literal = target_table.replace("'", "''")
    cursor.execute(
        f"""
        DO $$
        BEGIN
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = '{schema_literal}'
              AND table_name = '{table_literal}'
              AND column_name = 'present_factor_count'
          ) THEN
            ALTER TABLE {qualified_table} ALTER COLUMN "present_factor_count" DROP NOT NULL;
          END IF;
          IF EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = '{schema_literal}'
              AND table_name = '{table_literal}'
              AND column_name = 'missing_factor_count'
          ) THEN
            ALTER TABLE {qualified_table} ALTER COLUMN "missing_factor_count" DROP NOT NULL;
          END IF;
        END $$
        """
    )
    insert_sql = f"""
        INSERT INTO {qualified_table} ("available_time", "present_state_output_count", "missing_state_output_count", "data_quality_score", "diagnostic_payload_json")
        VALUES (%s, %s, %s, %s, %s::jsonb)
        ON CONFLICT ("available_time") DO UPDATE SET
          "present_state_output_count" = EXCLUDED."present_state_output_count",
          "missing_state_output_count" = EXCLUDED."missing_state_output_count",
          "data_quality_score" = EXCLUDED."data_quality_score",
          "diagnostic_payload_json" = EXCLUDED."diagnostic_payload_json"
    """
    for row in rows:
        cursor.execute(
            insert_sql,
            [
                row.get("available_time"),
                row.get("present_state_output_count"),
                row.get("missing_state_output_count"),
                row.get("data_quality_score"),
                json.dumps(row.get("diagnostic_payload_json", {}), sort_keys=True),
            ],
        )


def generate_sql(
    *,
    database_url: str,
    source_schema: str,
    source_table: str,
    target_schema: str,
    target_table: str,
    explainability_table: str,
    diagnostics_table: str,
    source_start: str | None,
    source_end: str | None,
    lookback: int,
    min_history: int,
) -> int:
    generator = _load_generator()
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            feature_rows = fetch_derived_rows(
                cursor,
                source_schema=source_schema,
                source_table=source_table,
                source_start=source_start,
                source_end=source_end,
            )
            rows = generator.generate_rows(feature_rows, lookback=lookback, min_history=min_history)
            write_model_rows_sql(cursor, rows, target_schema=target_schema, target_table=target_table)
            write_explainability_rows_sql(
                cursor,
                generator.build_explainability_rows(rows),
                target_schema=target_schema,
                target_table=explainability_table,
            )
            write_diagnostics_rows_sql(
                cursor,
                generator.build_diagnostics_rows(rows),
                target_schema=target_schema,
                target_table=diagnostics_table,
            )
            return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--source-schema", default="trading_data")
    parser.add_argument("--source-table", default="feature_01_market_regime")
    parser.add_argument("--target-schema", default="trading_model")
    parser.add_argument("--target-table", default="model_01_market_regime")
    parser.add_argument("--explainability-table", help="Optional explainability artifact table. Defaults to <target-table>_explainability.")
    parser.add_argument("--diagnostics-table", help="Optional diagnostics artifact table. Defaults to <target-table>_diagnostics.")
    parser.add_argument("--source-start", help="Optional lower timestamp bound for derived rows. Include enough lookback for rolling factors.")
    parser.add_argument("--source-end", help="Optional upper timestamp bound for derived rows.")
    generator = _load_generator()
    parser.add_argument("--lookback", type=int, default=generator.STANDARDIZATION.lookback)
    parser.add_argument("--min-history", type=int, default=generator.STANDARDIZATION.min_history)
    args = parser.parse_args(argv)

    row_count = generate_sql(
        database_url=_database_url(args.database_url),
        source_schema=args.source_schema,
        source_table=args.source_table,
        target_schema=args.target_schema,
        target_table=args.target_table,
        explainability_table=args.explainability_table or f"{args.target_table}_explainability",
        diagnostics_table=args.diagnostics_table or f"{args.target_table}_diagnostics",
        source_start=args.source_start,
        source_end=args.source_end,
        lookback=args.lookback,
        min_history=args.min_history,
    )
    print(
        f"generated {row_count} rows into {args.target_schema}.{args.target_table} "
        f"with support artifacts {args.target_schema}.{args.explainability_table or args.target_table + '_explainability'} "
        f"and {args.target_schema}.{args.diagnostics_table or args.target_table + '_diagnostics'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
