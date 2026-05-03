#!/usr/bin/env python3
"""Run a development DB smoke test for the MarketRegimeModel chain.

The smoke path uses deterministic fixture market bars, writes temporary
component-owned tables to the configured development database, writes the Layer 1
primary model and support-artifact tables, reads the feature and model rows back
from SQL, runs the dry-run evaluation artifact builder, and cleans the
development tables by default.

It does not call market-data providers, read provider secrets, or promote a
model. Use ``--keep-db`` only when inspecting the temporary development tables.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_URL_FILE = Path("/root/secrets/openclaw/database-url")
DEFAULT_TRADING_DATA_SRC = Path("/root/projects/trading-data/src")
DEFAULT_UNIVERSE_CSV = Path("/root/projects/trading-storage/main/shared/market_regime_etf_universe.csv")
DEFAULT_COMBINATIONS_CSV = Path("/root/projects/trading-storage/main/shared/market_regime_relative_strength_combinations.csv")
ET = ZoneInfo("America/New_York")

SOURCE_SCHEMA = "trading_data"
SOURCE_TABLE = "source_01_market_regime"
FEATURE_SCHEMA = "trading_data"
FEATURE_TABLE = "feature_01_market_regime"
MODEL_SCHEMA = "trading_model"
MODEL_TABLE = "model_01_market_regime"
EXPLAINABILITY_TABLE = "model_01_market_regime_explainability"
DIAGNOSTICS_TABLE = "model_01_market_regime_diagnostics"


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    value = os.environ.get("OPENCLAW_DATABASE_URL", "").strip()
    if value:
        return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _load_modules(trading_data_src: Path):
    sys.path.insert(0, str(trading_data_src))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    from data_feature.feature_01_market_regime import generator as feature_generator  # type: ignore
    from models.model_01_market_regime.evaluation import build_evaluation_artifacts, summarize_artifacts
    from models.model_01_market_regime import generator as model_generator

    return feature_generator, model_generator, build_evaluation_artifacts, summarize_artifacts


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [{str(k): str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]


def _stable_symbol_number(symbol: str) -> int:
    return int(hashlib.sha256(symbol.encode("utf-8")).hexdigest()[:8], 16)


def _symbol_close(symbol: str, index: int) -> float:
    seed = _stable_symbol_number(symbol)
    base = 40.0 + seed % 180
    slope = 0.03 + ((seed // 17) % 19) / 400.0
    cycle = math.sin(index / (5.0 + (seed % 7))) * (0.8 + (seed % 11) / 10.0)
    stress = math.cos(index / (11.0 + (seed % 5))) * 0.4
    return max(5.0, base + slope * index + cycle + stress)


def _bar(symbol: str, timeframe: str, timestamp: datetime, close: float) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "timestamp": timestamp.isoformat(),
        "bar_open": close * 0.997,
        "bar_high": close * 1.006,
        "bar_low": close * 0.994,
        "bar_close": close,
        "bar_volume": 100000.0 + (_stable_symbol_number(symbol) % 10000),
    }


def _symbols(universe_rows: Sequence[Mapping[str, str]], combination_rows: Sequence[Mapping[str, str]]) -> list[str]:
    values: set[str] = set()
    for row in universe_rows:
        symbol = str(row.get("symbol") or "").strip().upper()
        if symbol:
            values.add(symbol)
    for row in combination_rows:
        for key in ("numerator_symbol", "denominator_symbol"):
            symbol = str(row.get(key) or "").strip().upper()
            if symbol:
                values.add(symbol)
    return sorted(values)


def build_fixture_bars(
    *,
    universe_rows: Sequence[Mapping[str, str]],
    combination_rows: Sequence[Mapping[str, str]],
    start_date: date,
    daily_days: int,
    snapshot_days: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    symbols = _symbols(universe_rows, combination_rows)
    bars: list[dict[str, Any]] = []
    snapshot_times: list[str] = []
    snapshot_start = daily_days - snapshot_days
    for index in range(daily_days):
        current_date = start_date + timedelta(days=index)
        daily_time = datetime.combine(current_date, time(0, 0), tzinfo=ET)
        snapshot_time = datetime.combine(current_date, time(16, 0), tzinfo=ET)
        if index >= snapshot_start:
            snapshot_times.append(snapshot_time.isoformat())
        for symbol in symbols:
            close = _symbol_close(symbol, index)
            bars.append(_bar(symbol, "1Day", daily_time, close))
            if index >= snapshot_start:
                bars.append(_bar(symbol, "30Min", snapshot_time - timedelta(minutes=30), close * 0.999))
                bars.append(_bar(symbol, "30Min", snapshot_time, close * 1.001))
    return bars, snapshot_times


def _sql_literal(value: Any, *, jsonb: bool = False) -> str:
    if value is None:
        return "NULL"
    if jsonb:
        return "'" + json.dumps(value, sort_keys=True, default=str).replace("'", "''") + "'::jsonb"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return repr(float(value)) if isinstance(value, float) else str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _ident(value: str) -> str:
    if not value or not value.replace("_", "").isalnum():
        raise ValueError(f"unsafe identifier: {value!r}")
    return '"' + value + '"'


def _qualified(schema: str, table: str) -> str:
    return f"{_ident(schema)}.{_ident(table)}"


def _run_psql(database_url: str, sql: str, *, capture: bool = False) -> str:
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
    if result.stderr and not capture:
        print(result.stderr, file=sys.stderr, end="")
    return result.stdout


def _insert_rows(database_url: str, *, schema: str, table: str, rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> None:
    if not rows:
        return
    qualified = _qualified(schema, table)
    quoted_columns = ", ".join(_ident(column) for column in columns)
    values: list[str] = []
    for row in rows:
        values.append(
            "(" + ", ".join(_sql_literal(row.get(column), jsonb=column.endswith("_payload_json")) for column in columns) + ")"
        )
    _run_psql(database_url, f"INSERT INTO {qualified} ({quoted_columns}) VALUES\n" + ",\n".join(values) + ";\n")


def _create_source_table(database_url: str) -> None:
    _run_psql(
        database_url,
        f"""
        CREATE SCHEMA IF NOT EXISTS {_ident(SOURCE_SCHEMA)};
        DROP TABLE IF EXISTS {_qualified(SOURCE_SCHEMA, SOURCE_TABLE)};
        CREATE TABLE {_qualified(SOURCE_SCHEMA, SOURCE_TABLE)} (
          symbol TEXT NOT NULL,
          timeframe TEXT NOT NULL,
          timestamp TIMESTAMPTZ NOT NULL,
          bar_open DOUBLE PRECISION,
          bar_high DOUBLE PRECISION,
          bar_low DOUBLE PRECISION,
          bar_close DOUBLE PRECISION,
          bar_volume DOUBLE PRECISION,
          PRIMARY KEY (symbol, timeframe, timestamp)
        );
        """,
    )


def _create_feature_table(database_url: str) -> list[str]:
    columns = ["snapshot_time", "feature_payload_json"]
    _run_psql(
        database_url,
        f"""
        CREATE SCHEMA IF NOT EXISTS {_ident(FEATURE_SCHEMA)};
        DROP TABLE IF EXISTS {_qualified(FEATURE_SCHEMA, FEATURE_TABLE)};
        CREATE TABLE {_qualified(FEATURE_SCHEMA, FEATURE_TABLE)} (
          {_ident('snapshot_time')} TIMESTAMPTZ PRIMARY KEY,
          {_ident('feature_payload_json')} JSONB NOT NULL DEFAULT '{{}}'::jsonb
        );
        """,
    )
    return columns


def _feature_storage_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "snapshot_time": row["snapshot_time"],
            "feature_payload_json": {key: value for key, value in row.items() if key != "snapshot_time"},
        }
        for row in rows
    ]


def _flatten_feature_payload_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
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


def _create_model_table(database_url: str, columns: Sequence[str]) -> None:
    column_sql = [f"{_ident('available_time')} TIMESTAMPTZ PRIMARY KEY"]
    column_sql.extend(f"{_ident(column)} DOUBLE PRECISION" for column in columns if column != "available_time")
    _run_psql(
        database_url,
        f"""
        CREATE SCHEMA IF NOT EXISTS {_ident(MODEL_SCHEMA)};
        DROP TABLE IF EXISTS {_qualified(MODEL_SCHEMA, MODEL_TABLE)};
        CREATE TABLE {_qualified(MODEL_SCHEMA, MODEL_TABLE)} (
          {', '.join(column_sql)}
        );
        """,
    )


def _create_explainability_table(database_url: str) -> list[str]:
    columns = ["available_time", "factor_name", "factor_value", "explanation_payload_json"]
    _run_psql(
        database_url,
        f"""
        CREATE SCHEMA IF NOT EXISTS {_ident(MODEL_SCHEMA)};
        DROP TABLE IF EXISTS {_qualified(MODEL_SCHEMA, EXPLAINABILITY_TABLE)};
        CREATE TABLE {_qualified(MODEL_SCHEMA, EXPLAINABILITY_TABLE)} (
          {_ident('available_time')} TIMESTAMPTZ NOT NULL,
          {_ident('factor_name')} TEXT NOT NULL,
          {_ident('factor_value')} DOUBLE PRECISION,
          {_ident('explanation_payload_json')} JSONB NOT NULL,
          PRIMARY KEY ({_ident('available_time')}, {_ident('factor_name')})
        );
        """,
    )
    return columns


def _create_diagnostics_table(database_url: str) -> list[str]:
    columns = ["available_time", "present_factor_count", "missing_factor_count", "data_quality_score", "diagnostic_payload_json"]
    _run_psql(
        database_url,
        f"""
        CREATE SCHEMA IF NOT EXISTS {_ident(MODEL_SCHEMA)};
        DROP TABLE IF EXISTS {_qualified(MODEL_SCHEMA, DIAGNOSTICS_TABLE)};
        CREATE TABLE {_qualified(MODEL_SCHEMA, DIAGNOSTICS_TABLE)} (
          {_ident('available_time')} TIMESTAMPTZ PRIMARY KEY,
          {_ident('present_factor_count')} INTEGER NOT NULL,
          {_ident('missing_factor_count')} INTEGER NOT NULL,
          {_ident('data_quality_score')} DOUBLE PRECISION,
          {_ident('diagnostic_payload_json')} JSONB NOT NULL
        );
        """,
    )
    return columns


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
        capture=True,
    )
    return [json.loads(line) for line in output.splitlines() if line.strip().startswith("{")]


def _cleanup(database_url: str) -> None:
    _run_psql(
        database_url,
        f"""
        DROP TABLE IF EXISTS {_qualified(FEATURE_SCHEMA, FEATURE_TABLE)};
        DROP TABLE IF EXISTS {_qualified(SOURCE_SCHEMA, SOURCE_TABLE)};
        DROP TABLE IF EXISTS {_qualified(MODEL_SCHEMA, DIAGNOSTICS_TABLE)};
        DROP TABLE IF EXISTS {_qualified(MODEL_SCHEMA, EXPLAINABILITY_TABLE)};
        DROP TABLE IF EXISTS {_qualified(MODEL_SCHEMA, MODEL_TABLE)};
        """,
    )


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    feature_generator, model_generator, build_evaluation_artifacts, summarize_artifacts = _load_modules(args.trading_data_src)
    database_url = _database_url(args.database_url)
    universe_rows = _read_csv_rows(args.universe_csv)
    combination_rows = _read_csv_rows(args.combinations_csv)
    bar_rows, snapshot_times = build_fixture_bars(
        universe_rows=universe_rows,
        combination_rows=combination_rows,
        start_date=args.start_date,
        daily_days=args.daily_days,
        snapshot_days=args.snapshot_days,
    )

    try:
        _create_source_table(database_url)
        _insert_rows(
            database_url,
            schema=SOURCE_SCHEMA,
            table=SOURCE_TABLE,
            rows=bar_rows,
            columns=("symbol", "timeframe", "timestamp", "bar_open", "bar_high", "bar_low", "bar_close", "bar_volume"),
        )
        inputs = feature_generator.build_inputs(
            bar_rows=bar_rows,
            universe_rows=universe_rows,
            combination_rows=combination_rows,
        )
        feature_rows = feature_generator.generate_rows(inputs, snapshot_times=snapshot_times)
        feature_columns = _create_feature_table(database_url)
        _insert_rows(database_url, schema=FEATURE_SCHEMA, table=FEATURE_TABLE, rows=_feature_storage_rows(feature_rows), columns=feature_columns)

        model_rows = model_generator.generate_rows(feature_rows, min_history=args.min_history)
        explainability_rows = model_generator.build_explainability_rows(model_rows)
        diagnostics_rows = model_generator.build_diagnostics_rows(model_rows)
        _create_model_table(database_url, model_generator.OUTPUT_COLUMNS)
        _insert_rows(database_url, schema=MODEL_SCHEMA, table=MODEL_TABLE, rows=model_rows, columns=model_generator.OUTPUT_COLUMNS)
        explainability_columns = _create_explainability_table(database_url)
        _insert_rows(database_url, schema=MODEL_SCHEMA, table=EXPLAINABILITY_TABLE, rows=explainability_rows, columns=explainability_columns)
        diagnostics_columns = _create_diagnostics_table(database_url)
        _insert_rows(database_url, schema=MODEL_SCHEMA, table=DIAGNOSTICS_TABLE, rows=diagnostics_rows, columns=diagnostics_columns)

        db_feature_storage_rows = _fetch_json_rows(database_url, schema=FEATURE_SCHEMA, table=FEATURE_TABLE, order_column="snapshot_time")
        db_feature_rows = _flatten_feature_payload_rows(db_feature_storage_rows)
        db_model_rows = _fetch_json_rows(database_url, schema=MODEL_SCHEMA, table=MODEL_TABLE, order_column="available_time")
        artifacts = build_evaluation_artifacts(feature_rows=db_feature_rows, model_rows=db_model_rows, model_config_hash="development_smoke")
        summary = summarize_artifacts(artifacts)
        evaluation_write_policy = summary.pop("write_policy", None)
        summary.update(
            {
                "source_rows": len(bar_rows),
                "feature_rows": len(db_feature_rows),
                "model_rows": len(db_model_rows),
                "explainability_rows": len(explainability_rows),
                "diagnostics_rows": len(diagnostics_rows),
                "database_write_policy": "development_tables_written_then_cleaned" if not args.keep_db else "development_tables_kept_for_inspection",
                "evaluation_artifact_write_policy": evaluation_write_policy,
                "cleanup_policy": "cleanup_after_run" if not args.keep_db else "keep_db_requested",
            }
        )
        return summary
    finally:
        if not args.keep_db:
            _cleanup(database_url)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", help="PostgreSQL URL. Defaults to OPENCLAW_DATABASE_URL or the local OpenClaw DB secret file.")
    parser.add_argument("--trading-data-src", type=Path, default=DEFAULT_TRADING_DATA_SRC)
    parser.add_argument("--universe-csv", type=Path, default=DEFAULT_UNIVERSE_CSV)
    parser.add_argument("--combinations-csv", type=Path, default=DEFAULT_COMBINATIONS_CSV)
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2025, 1, 1))
    parser.add_argument("--daily-days", type=int, default=230)
    parser.add_argument("--snapshot-days", type=int, default=60)
    parser.add_argument("--min-history", type=int, default=20)
    parser.add_argument("--keep-db", action="store_true", help="Leave development tables in the database for inspection instead of cleaning them.")
    args = parser.parse_args(argv)

    summary = run_smoke(args)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    if not args.keep_db:
        print("CLEANUP COMPLETE: development source/feature/model tables were removed after verification.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
