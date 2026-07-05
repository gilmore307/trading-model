#!/usr/bin/env python3
"""Run a read-only tradable-time return distribution surface pilot."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from model_runtime.config import database_url_file
from models.return_distribution_surface import (
    bucket_regular_session_closes,
    build_tradable_time_label_rows,
    fit_tradable_time_distribution_surface,
    summarize_pilot_result,
)

ET = ZoneInfo("America/New_York")
ALLOWED_SOURCE_TABLES = {
    "m01": "trading_data.model_01_market_regime_data_acquisition",
    "m03": "trading_data.model_03_target_state_vector_data_acquisition",
}


def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


def _et_datetime(day, t: time) -> datetime:
    return datetime.combine(day, t, tzinfo=ET)


def _database_url() -> str:
    path = database_url_file()
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    fallback = Path("/root/secrets/trading_storage_postgres.json")
    if fallback.exists():
        payload = json.loads(fallback.read_text(encoding="utf-8"))
        dsn = str(payload.get("dsn") or payload.get("database_url") or payload.get("url") or "").strip()
        if dsn:
            return dsn
    raise SystemExit("database URL not found")


def _load_bars(*, symbol: str, start: str, end: str, source: str, timeframe: str | None) -> list[dict[str, Any]]:
    start_date = _parse_date(start)
    end_date = _parse_date(end)
    table = ALLOWED_SOURCE_TABLES[source]
    timeframe_clause = "AND timeframe = %s" if source == "m01" and timeframe else ""
    params: list[Any] = [symbol.upper(), _et_datetime(start_date, time(0, 0)), _et_datetime(end_date, time(0, 0))]
    if timeframe_clause:
        params.append(timeframe)
    available_expr = "timestamp AS available_time" if source == "m01" else "available_time"
    with psycopg.connect(_database_url(), row_factory=dict_row) as conn:
        rows = conn.execute(
            f"""
            SELECT symbol, timestamp, {available_expr}, bar_close
            FROM {table}
            WHERE symbol = %s
              AND timestamp >= %s
              AND timestamp < %s
              {timeframe_clause}
              AND bar_close > 0
            ORDER BY timestamp ASC
            """,
            tuple(params),
        ).fetchall()
    return [dict(row) for row in rows]


def _write_surface_csv(path: Path, result) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    quantile_keys = [f"p{int(level * 100):02d}" for level in result.quantile_levels]
    cdf_keys = [f"cdf_le_{threshold:+.2%}" for threshold in result.cdf_thresholds]
    cdf_by_tau = {row["tau_trading_minutes"]: row for row in result.cdf_rows}
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["tau_trading_minutes", *quantile_keys, *cdf_keys, "cdf_monotone"],
        )
        writer.writeheader()
        for tau in result.horizon_axis_minutes:
            writer.writerow(
                {
                    "tau_trading_minutes": tau,
                    **result.surface_quantiles[tau],
                    **{key: cdf_by_tau[tau][key] for key in cdf_keys},
                    "cdf_monotone": cdf_by_tau[tau]["cdf_monotone"],
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="SPY")
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2025-02-01")
    parser.add_argument("--source", choices=sorted(ALLOWED_SOURCE_TABLES), default="m01")
    parser.add_argument("--timeframe", default="1Min")
    parser.add_argument("--anchor-minutes", type=int, default=10)
    parser.add_argument("--max-trading-minutes", type=int, default=1170)
    parser.add_argument("--fit-mode", choices=("baseline", "context"), default="context")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    rows = _load_bars(
        symbol=args.symbol,
        start=args.start,
        end=args.end,
        source=args.source,
        timeframe=args.timeframe,
    )
    closes = bucket_regular_session_closes(rows, bucket_minutes=args.anchor_minutes, symbol=args.symbol)
    label_rows = build_tradable_time_label_rows(
        closes,
        anchor_minutes=args.anchor_minutes,
        max_trading_minutes=args.max_trading_minutes,
    )
    result = fit_tradable_time_distribution_surface(label_rows, fit_mode=args.fit_mode)
    output_dir.mkdir(parents=True, exist_ok=True)
    surface_csv = output_dir / "surface.csv"
    _write_surface_csv(surface_csv, result)
    summary = summarize_pilot_result(
        symbol=args.symbol,
        source_table=ALLOWED_SOURCE_TABLES[args.source],
        source_timeframe=args.timeframe if args.source == "m01" else None,
        source_range={"start": args.start, "end_exclusive": args.end},
        anchor_minutes=args.anchor_minutes,
        bar_rows_loaded=len(rows),
        bucket_close_count=len(closes),
        label_rows=label_rows,
        result=result,
        surface_csv=str(surface_csv),
    )
    (output_dir / "pilot_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "validation_rows.json").write_text(json.dumps(result.validation_rows, indent=2, sort_keys=True), encoding="utf-8")
    (output_dir / "cdf_rows.json").write_text(json.dumps(result.cdf_rows, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
