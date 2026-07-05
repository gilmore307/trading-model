"""Read-only SQL loaders for tradable-time return distribution surfaces."""

from __future__ import annotations

import json
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import dict_row

from model_runtime.config import database_url_file

ET = ZoneInfo("America/New_York")

ALLOWED_SOURCE_TABLES = {
    "m01": "trading_data.model_01_market_regime_data_acquisition",
    "m03": "trading_data.model_03_target_state_vector_data_acquisition",
}


def load_pit_bars(
    *,
    symbol: str,
    start: str,
    end: str,
    source: str,
    timeframe: str | None,
) -> list[dict[str, Any]]:
    """Load point-in-time bars for one symbol/window without mutating SQL."""

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
    raise RuntimeError("database URL not found")
