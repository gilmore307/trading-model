#!/usr/bin/env python3
"""Train direct after-cost Layer 5 alpha score artifacts from local or SQL rows."""
from __future__ import annotations

import argparse
import bisect
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping

from model_governance.local_layer_scripts import read_rows, write_payload
from model_runtime.config import database_url_file
from models.model_05_alpha_confidence.training import train_after_cost_alpha_model
from models.model_05_alpha_confidence.contract import HORIZONS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_model_05_alpha_confidence import (  # type: ignore[import-not-found]
    _decision_rows,
    _fetch_rows,
    _iso,
    _load_psycopg,
    _parse_time,
)


DEFAULT_DB_URL_FILE = database_url_file()
HORIZON_DELTAS = {
    "10min": timedelta(minutes=10),
    "1h": timedelta(hours=1),
    "1D": timedelta(days=1),
    "1W": timedelta(days=7),
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-jsonl", type=Path, help="JSON/JSONL rows containing point-in-time Layer 5 inputs plus after-cost labels.")
    parser.add_argument("--output-json", "--output", dest="output_json", type=Path, required=True, help="Where to write the trained artifact.")
    parser.add_argument("--horizon", default="1W")
    parser.add_argument("--all-horizons", action="store_true", help="Train one artifact per accepted Layer 5 horizon and write an artifact bundle.")
    parser.add_argument("--label-field", help="Optional explicit realized after-cost return label field.")
    parser.add_argument("--return-scale", type=float, default=0.02)
    parser.add_argument("--iterations", type=int, default=700)
    parser.add_argument("--learning-rate", type=float, default=0.08)
    parser.add_argument("--l2", type=float, default=0.001)
    parser.add_argument("--from-database", action="store_true")
    parser.add_argument("--database-url")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-symbol", help="Optional selected target symbol filter via m03_target_state_vector_data_acquisition.")
    parser.add_argument("--cost-bps", type=float, default=5.0)
    args = parser.parse_args(argv)

    if args.from_database:
        rows = read_training_rows_from_database(
            database_url=_database_url(args.database_url),
            source_start=args.source_start,
            source_end=args.source_end,
            target_symbol=args.target_symbol,
            cost_bps=args.cost_bps,
        )
    else:
        if args.training_jsonl is None:
            parser.error("--training-jsonl is required unless --from-database is used")
        rows = read_rows(args.training_jsonl)

    horizons = HORIZONS if args.all_horizons else (args.horizon,)
    if len(horizons) == 1:
        artifact = train_after_cost_alpha_model(
            rows,
            horizon=horizons[0],
            label_field=args.label_field,
            return_scale=args.return_scale,
            iterations=args.iterations,
            learning_rate=args.learning_rate,
            l2=args.l2,
        )
    else:
        artifact = {
            "schema_version": "layer_05_after_cost_alpha_model_bundle",
            "model_id": "alpha_confidence_model",
            "score_semantics": "0.5_after_cost_neutral__above_positive_edge__below_negative_edge",
            "artifacts_by_horizon": {
                horizon: train_after_cost_alpha_model(
                    rows,
                    horizon=horizon,
                    label_field=args.label_field or f"after_cost_return_{horizon}",
                    return_scale=args.return_scale,
                    iterations=args.iterations,
                    learning_rate=args.learning_rate,
                    l2=args.l2,
                )
                for horizon in horizons
            },
            "training_row_count": len(rows),
            "source_start": args.source_start,
            "source_end": args.source_end,
            "target_symbol": (args.target_symbol or "").upper(),
            "cost_bps": args.cost_bps,
        }
    write_payload(_json_safe(artifact), args.output_json)
    return 0


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    import os

    for env_name in ("TRADING_MODEL_DATABASE_URL", "OPENCLAW_DATABASE_URL"):
        value = os.environ.get(env_name, "").strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def read_training_rows_from_database(
    *,
    database_url: str,
    source_start: str | None,
    source_end: str | None,
    target_symbol: str | None,
    cost_bps: float,
) -> list[dict[str, Any]]:
    """Build Layer 5 training rows from point-in-time model inputs and future source bars."""

    psycopg, dict_row = _load_psycopg()
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cursor:
            source_03_rows = _fetch_rows(
                cursor,
                schema="trading_data",
                table="m03_target_state_vector_data_acquisition",
                source_start=source_start,
                source_end=source_end,
                target_symbol=target_symbol,
                order_by="available_time::timestamptz ASC, target_candidate_id ASC",
            )
            target_candidate_ids = sorted({str(row["target_candidate_id"]) for row in source_03_rows if row.get("target_candidate_id")})
            event_failure_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="model_04_event_failure_risk",
                source_start=source_start,
                source_end=source_end,
                target_candidate_ids=target_candidate_ids if target_symbol else None,
                order_by="available_time::timestamptz ASC, target_candidate_id ASC",
            )
            model_03_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="model_03_target_state_vector",
                source_start=source_start,
                source_end=source_end,
                target_candidate_ids=target_candidate_ids if target_symbol else None,
                order_by="available_time::timestamptz ASC, target_candidate_id ASC",
            )
            model_02_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="m02_sector_context_model_generation",
                source_start=source_start,
                source_end=source_end,
                order_by="available_time::timestamptz ASC, sector_or_industry_symbol ASC",
            )
            model_01_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="m01_market_regime_model_generation",
                source_start=source_start,
                source_end=source_end,
                order_by="available_time::timestamptz ASC",
            )
    rows = _decision_rows(
        event_failure_rows=event_failure_rows,
        model_03_rows=model_03_rows,
        source_03_rows=source_03_rows,
        model_02_rows=model_02_rows,
        model_01_rows=model_01_rows,
    )
    labeled = attach_after_cost_return_labels(rows, source_03_rows=source_03_rows, cost_bps=cost_bps)
    if not labeled:
        raise SystemExit("Layer 5 database training produced zero rows with after-cost labels")
    return labeled


def attach_after_cost_return_labels(
    rows: list[dict[str, Any]],
    *,
    source_03_rows: list[Mapping[str, Any]],
    cost_bps: float,
) -> list[dict[str, Any]]:
    bars_by_candidate: dict[str, list[Mapping[str, Any]]] = {}
    for row in source_03_rows:
        candidate = str(row.get("target_candidate_id") or "")
        if candidate and _safe_float(row.get("bar_close")) is not None and row.get("available_time"):
            bars_by_candidate.setdefault(candidate, []).append(row)
    bar_indexes_by_candidate: dict[str, tuple[list[Any], list[Mapping[str, Any]]]] = {}
    for candidate, bars in bars_by_candidate.items():
        bars.sort(key=lambda item: _parse_time(item["available_time"]))
        bar_indexes_by_candidate[candidate] = (
            [_parse_time(item["available_time"]) for item in bars],
            bars,
        )

    labeled: list[dict[str, Any]] = []
    for row in rows:
        bar_index = bar_indexes_by_candidate.get(str(row.get("target_candidate_id") or ""))
        if not bar_index:
            continue
        available_time = _parse_time(row["available_time"])
        bar_times, bars = bar_index
        current = _latest_bar_at_or_before(bar_times, bars, available_time)
        current_close = _safe_float((current or {}).get("bar_close"))
        if current is None or current_close is None or current_close <= 0:
            continue
        output = dict(row)
        for horizon, delta in HORIZON_DELTAS.items():
            future = _first_bar_at_or_after(bar_times, bars, available_time + delta)
            future_close = _safe_float((future or {}).get("bar_close"))
            if future is None or future_close is None:
                continue
            orientation = _direction_orientation(row, horizon)
            gross_return = (future_close / current_close - 1.0) * orientation
            output[f"after_cost_return_{horizon}"] = gross_return - (cost_bps / 10_000.0)
            output[f"after_cost_label_time_{horizon}"] = _iso(future["available_time"])
        if any(f"after_cost_return_{horizon}" in output for horizon in HORIZONS):
            labeled.append(output)
    return labeled


def _latest_bar_at_or_before(times: list[Any], rows: list[Mapping[str, Any]], timestamp: Any) -> Mapping[str, Any] | None:
    index = bisect.bisect_right(times, timestamp) - 1
    if index < 0:
        return None
    return rows[index]


def _first_bar_at_or_after(times: list[Any], rows: list[Mapping[str, Any]], timestamp: Any) -> Mapping[str, Any] | None:
    index = bisect.bisect_left(times, timestamp)
    if index >= len(rows):
        return None
    return rows[index]


def _direction_orientation(row: Mapping[str, Any], horizon: str) -> float:
    target = row.get("target_context_state")
    score = _safe_float(target.get(f"3_target_direction_score_{horizon}") if isinstance(target, Mapping) else None)
    return -1.0 if score is not None and score < 0 else 1.0


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(nested) for key, nested in value.items()}
    if isinstance(value, list):
        return [_json_safe(nested) for nested in value]
    try:
        json.dumps(value)
    except TypeError:
        return str(value)
    return value


if __name__ == "__main__":
    raise SystemExit(main())
