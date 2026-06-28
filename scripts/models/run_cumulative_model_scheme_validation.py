#!/usr/bin/env python3
"""Validate the selected cumulative residual MLP scheme over historical folds.

This script is model-side experiment evidence only. It reads existing
point-in-time rows, writes a local scheme-validation artifact, and never promotes,
activates, calls providers, mutates SQL, or touches broker/account state.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from model_governance.historical_current_chain_evaluation import (
    BASELINE_FEATURE_NAMES,
    build_historical_current_chain_examples,
    load_historical_rows_from_database,
)
from model_governance.training import build_cumulative_model_scheme_validation_receipt
from model_runtime.config import database_url_file, model_storage_root


DEFAULT_DB_URL_FILE = database_url_file()
SOURCE_PROXY_FEATURE_NAMES = (
    "log_reference_price",
    "intrabar_return",
    "high_low_range",
    "vwap_deviation",
    "log_bar_volume",
    "log_trade_count",
    "log_dollar_volume",
    "spread_bps_scaled",
    "quote_mid_deviation",
    "minute_of_day_sin",
    "minute_of_day_cos",
    "day_of_week_scaled",
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url")
    parser.add_argument(
        "--input-mode",
        choices=("target_state_source_proxy", "current_chain_features"),
        default="target_state_source_proxy",
        help="Use lightweight anonymous source-state vectors for first scheme validation, or full current-chain feature rows.",
    )
    parser.add_argument("--target-symbol", default=None, help="Optional debug filter. Omit for multi-symbol experiment evidence.")
    parser.add_argument("--minimum-symbols", type=int, default=3)
    parser.add_argument("--start-time", default="2016-01-01T00:00:00-05:00")
    parser.add_argument("--end-time", default="2016-08-01T00:00:00-04:00")
    parser.add_argument("--limit", type=int, default=3000)
    parser.add_argument("--per-month-limit", type=int, default=400)
    parser.add_argument("--label-horizon-days", type=int, default=7)
    parser.add_argument("--train-months", type=int, default=4)
    parser.add_argument("--validation-months", type=int, default=1)
    parser.add_argument("--run-id")
    parser.add_argument("--output-json", type=Path)
    args = parser.parse_args(argv)

    run_id = args.run_id or "cumulative_model_scheme_validation_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    target_symbol = args.target_symbol.strip().upper() if args.target_symbol else None
    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(_database_url(args.database_url), row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            if args.input_mode == "current_chain_features":
                rows = load_historical_rows_from_database(
                    cursor,
                    start_time=args.start_time,
                    end_time=args.end_time,
                    limit=args.limit,
                    per_month_limit=args.per_month_limit,
                    label_horizon_days=args.label_horizon_days,
                )
                target_rows = (
                    [row for row in rows if str(row.source_row.get("symbol") or "").strip().upper() == target_symbol]
                    if target_symbol
                    else rows
                )
                examples, blocked_rows = build_historical_current_chain_examples(target_rows)
                feature_names = BASELINE_FEATURE_NAMES
                label_proxy = "current_chain_utility_score_1W"
                source_row_count = len(rows)
                target_source_row_count = len(target_rows)
            else:
                examples, blocked_rows, source_row_count, target_source_row_count = load_source_proxy_examples_from_database(
                    cursor,
                    start_time=args.start_time,
                    end_time=args.end_time,
                    limit=args.limit,
                    per_month_limit=args.per_month_limit,
                    label_horizon_days=args.label_horizon_days,
                    target_symbol=target_symbol,
                )
                feature_names = SOURCE_PROXY_FEATURE_NAMES
                label_proxy = "target_state_source_proxy_7d_forward_return"
    receipt = build_cumulative_model_scheme_validation_receipt(
        examples,
        run_id=run_id,
        feature_names=feature_names,
        label_proxy=label_proxy,
        train_months=args.train_months,
        validation_months=args.validation_months,
        minimum_symbols=args.minimum_symbols,
    )
    receipt.update(
        {
            "source_window": {
                "start_time": args.start_time,
                "end_time": args.end_time,
                "label_horizon_days": args.label_horizon_days,
            },
            "input_mode": args.input_mode,
            "target_symbol_filter": target_symbol,
            "source_row_counts": {
                "source_rows": source_row_count,
                "target_source_rows": target_source_row_count,
                "generated_examples": len(examples),
                "blocked_examples": len(blocked_rows),
            },
            "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        }
    )

    output_path = args.output_json or default_output_path(run_id)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "succeeded",
                "contract_type": receipt.get("contract_type"),
                "output_json": str(output_path),
                "run_id": run_id,
            },
            sort_keys=True,
        )
    )
    return 0


def default_output_path(run_id: str) -> Path:
    return model_storage_root() / "cumulative_model_scheme_validation" / run_id / "scheme_validation_receipt.json"


def load_source_proxy_examples_from_database(
    cursor: Any,
    *,
    start_time: str,
    end_time: str,
    limit: int,
    per_month_limit: int,
    label_horizon_days: int,
    target_symbol: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int, int]:
    """Build lightweight anonymous examples directly from target-state source rows."""

    symbol_clause = "AND da.symbol = %s" if target_symbol else ""
    params: list[Any] = [start_time, end_time, label_horizon_days]
    if target_symbol:
        params.insert(2, target_symbol)
    params.extend([per_month_limit, limit])
    cursor.execute(
        f"""
        WITH source_rows AS (
          SELECT
            da.target_candidate_id,
            da.symbol,
            da.available_time,
            da.timestamp,
            da.bar_open,
            da.bar_high,
            da.bar_low,
            da.bar_close,
            da.bar_volume,
            da.bar_vwap,
            da.bar_trade_count,
            da.dollar_volume,
            da.avg_bid,
            da.avg_ask,
            da.spread_bps,
            date_trunc('day', da.available_time) AS sample_day,
            row_number() OVER (
              PARTITION BY date_trunc('month', da.available_time), date_trunc('day', da.available_time), da.symbol
              ORDER BY da.available_time, da.target_candidate_id
            ) AS daily_symbol_rank
          FROM trading_data.model_03_target_state_vector_data_acquisition da
          WHERE da.available_time >= %s::timestamptz
            AND da.available_time < %s::timestamptz
            {symbol_clause}
            AND da.bar_close IS NOT NULL
        ),
        daily_sample AS (
          SELECT
            source_rows.*,
            row_number() OVER (
              PARTITION BY date_trunc('month', available_time)
              ORDER BY daily_symbol_rank, sample_day, symbol, available_time
            ) AS month_row_number
          FROM source_rows
        )
        SELECT
          daily_sample.*,
          future_bar.available_time AS label_time,
          future_bar.bar_close AS future_close
        FROM daily_sample
        LEFT JOIN LATERAL (
          SELECT available_time, bar_close
          FROM trading_data.model_03_target_state_vector_data_acquisition future_da
          WHERE future_da.target_candidate_id = daily_sample.target_candidate_id
            AND future_da.available_time >= daily_sample.available_time + (%s::text || ' days')::interval
            AND future_da.bar_close IS NOT NULL
          ORDER BY future_da.available_time
          LIMIT 1
        ) future_bar ON TRUE
        WHERE daily_sample.month_row_number <= %s
        ORDER BY daily_sample.available_time, daily_sample.symbol, daily_sample.target_candidate_id
        LIMIT %s
        """,
        tuple(params),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    examples: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        try:
            example = _source_proxy_example(row)
        except Exception as error:  # pragma: no cover - evidence path
            blocked.append({"row_index": index, "error": str(error), "symbol": row.get("symbol")})
            continue
        examples.append(example)
    return examples, blocked, len(rows), len(rows)


def _source_proxy_example(row: dict[str, Any]) -> dict[str, Any]:
    available_time = _parse_dt(row["available_time"])
    close = _float(row.get("bar_close"))
    future_close = _float(row.get("future_close"))
    if close <= 0:
        raise ValueError("bar_close must be positive")
    label = None
    label_matured = future_close > 0
    if label_matured:
        future_return = (future_close - close) / close
        label = _clip01(0.5 + future_return * 5.0)
    feature_vector = _source_proxy_feature_vector(row, available_time=available_time, close=close)
    return {
        "available_time": available_time.isoformat(),
        "fold_key": f"{available_time.year:04d}-{available_time.month:02d}",
        "target_candidate_id": str(row.get("target_candidate_id") or ""),
        "routing_symbol": str(row.get("symbol") or "").upper(),
        "feature_vector": feature_vector,
        "label_payload": {
            "utility_score_1W": label,
            "label_matured": label_matured,
            "label_time": None if row.get("label_time") is None else _parse_dt(row["label_time"]).isoformat(),
        },
    }


def _source_proxy_feature_vector(row: dict[str, Any], *, available_time: datetime, close: float) -> list[float]:
    open_price = _float(row.get("bar_open"), close)
    high = _float(row.get("bar_high"), close)
    low = _float(row.get("bar_low"), close)
    vwap = _float(row.get("bar_vwap"), close)
    volume = _float(row.get("bar_volume"))
    trade_count = _float(row.get("bar_trade_count"))
    dollar_volume = _float(row.get("dollar_volume"))
    spread_bps = _float(row.get("spread_bps"), 10.0)
    bid = _float(row.get("avg_bid"), close)
    ask = _float(row.get("avg_ask"), close)
    minute_of_day = available_time.hour * 60 + available_time.minute
    return [
        math.log(max(close, 1e-9)),
        _safe_return(close, open_price),
        (high - low) / close if close else 0.0,
        _safe_return(close, vwap),
        math.log1p(max(volume, 0.0)),
        math.log1p(max(trade_count, 0.0)),
        math.log1p(max(dollar_volume, 0.0)),
        spread_bps / 1000.0,
        ((bid + ask) / 2.0 - close) / close if close and bid > 0 and ask > 0 else 0.0,
        math.sin(2.0 * math.pi * minute_of_day / 1440.0),
        math.cos(2.0 * math.pi * minute_of_day / 1440.0),
        available_time.weekday() / 6.0,
    ]


def _safe_return(left: float, right: float) -> float:
    return (left - right) / right if right else 0.0


def _float(value: Any, default: float = 0.0) -> float:
    try:
        output = float(value)
    except (TypeError, ValueError):
        return default
    return output if math.isfinite(output) else default


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


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


def _load_psycopg() -> tuple[Any, Any]:
    try:
        import psycopg  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except ModuleNotFoundError as error:  # pragma: no cover
        raise SystemExit("psycopg is required for cumulative model scheme validation; install psycopg[binary].") from error
    return psycopg, dict_row


if __name__ == "__main__":
    raise SystemExit(main())
