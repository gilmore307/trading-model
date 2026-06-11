#!/usr/bin/env python3
"""Train direct after-cost Layer 5 alpha score artifacts from local or SQL rows."""
from __future__ import annotations

import argparse
import bisect
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

from model_governance.local_layer_scripts import read_rows, write_payload
from model_runtime.config import database_url_file
from models.model_05_alpha_confidence.training import train_after_cost_alpha_model
from models.model_05_alpha_confidence.contract import HORIZONS

sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_model_05_alpha_confidence import (  # type: ignore[import-not-found]
    _decision_rows,
    _fetch_market_feature_rows,
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
    parser.add_argument("--target-symbol", help="Optional selected target symbol filter via model_03_target_state_vector_data_acquisition.")
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
    _validate_non_degenerate_after_cost_artifact(artifact)
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
                table="model_03_target_state_vector_data_acquisition",
                source_start=source_start,
                source_end=source_end,
                target_symbol=target_symbol,
                order_by="available_time::timestamptz ASC, target_candidate_id ASC",
            )
            target_candidate_ids = sorted({str(row["target_candidate_id"]) for row in source_03_rows if row.get("target_candidate_id")})
            event_failure_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="model_04_unified_decision",
                source_start=source_start,
                source_end=source_end,
                target_candidate_ids=target_candidate_ids if target_symbol else None,
                order_by="available_time::timestamptz ASC, target_candidate_id ASC",
            )
            model_03_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="model_02_target_state",
                source_start=source_start,
                source_end=source_end,
                target_candidate_ids=target_candidate_ids if target_symbol else None,
                order_by="available_time::timestamptz ASC, target_candidate_id ASC",
            )
            model_02_rows = _fetch_rows(
                cursor,
                schema="trading_model",
                table="model_02_sector_context_model_generation",
                source_start=source_start,
                source_end=source_end,
                order_by="available_time::timestamptz ASC, sector_or_industry_symbol ASC",
            )
            model_01_rows = _fetch_market_feature_rows(cursor, source_start=source_start, source_end=source_end)
    source_target_rows = _target_state_rows_from_source_bars(source_03_rows)
    if source_target_rows:
        model_03_rows = source_target_rows
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


def _target_state_rows_from_source_bars(source_03_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows_by_candidate: dict[str, list[Mapping[str, Any]]] = {}
    for row in source_03_rows:
        candidate = str(row.get("target_candidate_id") or "")
        if candidate and _safe_float(row.get("bar_close")) is not None and row.get("available_time"):
            rows_by_candidate.setdefault(candidate, []).append(row)
    output: list[dict[str, Any]] = []
    for candidate, rows in rows_by_candidate.items():
        sorted_rows = sorted(rows, key=lambda item: _parse_time(item["available_time"]))
        symbol = str(sorted_rows[0].get("symbol") or "").upper()
        for index, row in enumerate(sorted_rows):
            close = _safe_float(row.get("bar_close"))
            if close is None or close <= 0:
                continue
            available_time = _iso(row["available_time"])
            state = _source_bar_target_state(
                target=symbol,
                rows=sorted_rows,
                index=index,
                candidate=candidate,
                reference_price=close,
            )
            output.append(
                {
                    "available_time": available_time,
                    "tradeable_time": available_time,
                    "target_candidate_id": candidate,
                    "target_context_state_ref": state["model_ref"],
                    **state,
                }
            )
    output.sort(key=lambda row: (_parse_time(row["available_time"]), str(row.get("target_candidate_id") or "")))
    return output


def _source_bar_target_state(
    *,
    target: str,
    rows: Sequence[Mapping[str, Any]],
    index: int,
    candidate: str,
    reference_price: float,
) -> dict[str, Any]:
    momentum_7d = _window_return(rows, index, 7)
    momentum_30d = _window_return(rows, index, 30)
    daily = _daily_return(rows, index)
    direction_1d = _clip_signed(daily * 8.0 + momentum_7d * 3.0)
    direction_1w = _clip_signed(momentum_7d * 4.0 + momentum_30d)
    trend_quality = _clip01(0.5 + abs(momentum_7d) * 8.0 + abs(momentum_30d) * 2.0)
    liquidity = _volume_rank(rows, index, 30)
    return {
        "model_ref": f"training_source_bar_target_state/{target}/{candidate}/{_iso(rows[index]['available_time'])}",
        "target_ref": target,
        "target_candidate_id": candidate,
        "3_target_direction_score_10min": direction_1d,
        "3_target_direction_score_1h": direction_1d,
        "3_target_direction_score_1D": direction_1d,
        "3_target_direction_score_1W": direction_1w,
        "3_target_trend_quality_score_10min": trend_quality,
        "3_target_trend_quality_score_1h": trend_quality,
        "3_target_trend_quality_score_1D": trend_quality,
        "3_target_trend_quality_score_1W": trend_quality,
        "3_target_path_stability_score_10min": _clip01(0.65 - abs(daily) * 4.0),
        "3_target_path_stability_score_1h": _clip01(0.65 - abs(daily) * 4.0),
        "3_target_path_stability_score_1D": _clip01(0.65 - abs(daily) * 4.0),
        "3_target_path_stability_score_1W": _clip01(0.65 - abs(momentum_7d) * 2.0),
        "3_target_noise_score_10min": _clip01(abs(daily) * 4.0),
        "3_target_noise_score_1h": _clip01(abs(daily) * 4.0),
        "3_target_noise_score_1D": _clip01(abs(daily) * 4.0),
        "3_target_noise_score_1W": _clip01(abs(momentum_7d) * 2.0),
        "3_target_transition_risk_score_10min": _clip01(abs(daily - momentum_7d) * 2.0),
        "3_target_transition_risk_score_1h": _clip01(abs(daily - momentum_7d) * 2.0),
        "3_target_transition_risk_score_1D": _clip01(abs(daily - momentum_7d) * 2.0),
        "3_target_transition_risk_score_1W": _clip01(abs(momentum_7d - momentum_30d) * 2.0),
        "3_context_direction_alignment_score_10min": direction_1d,
        "3_context_direction_alignment_score_1h": direction_1d,
        "3_context_direction_alignment_score_1D": direction_1d,
        "3_context_direction_alignment_score_1W": direction_1w,
        "3_context_support_quality_score_10min": 0.60,
        "3_context_support_quality_score_1h": 0.60,
        "3_context_support_quality_score_1D": 0.60,
        "3_context_support_quality_score_1W": 0.60,
        "3_tradability_score_10min": liquidity,
        "3_tradability_score_1h": liquidity,
        "3_tradability_score_1D": liquidity,
        "3_tradability_score_1W": liquidity,
        "3_target_liquidity_tradability_score": liquidity,
        "3_state_quality_score": 0.70,
        "current_price": reference_price,
        "last_price": reference_price,
        "mark_price": reference_price,
    }


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
    if score is None and isinstance(target, Mapping):
        score = _safe_float(target.get(f"2_target_direction_score_{horizon}"))
    return -1.0 if score is not None and score < 0 else 1.0


def _validate_non_degenerate_after_cost_artifact(artifact: Mapping[str, Any]) -> None:
    artifacts = artifact.get("artifacts_by_horizon")
    if isinstance(artifacts, Mapping):
        artifact_items = [(str(horizon), horizon_artifact) for horizon, horizon_artifact in artifacts.items()]
    else:
        artifact_items = [(str(artifact.get("horizon") or "unknown"), artifact)]
    degenerate = [
        horizon
        for horizon, horizon_artifact in artifact_items
        if not isinstance(horizon_artifact, Mapping) or _lightgbm_artifact_is_degenerate(horizon_artifact)
    ]
    if degenerate:
        raise SystemExit(
            "Layer 5 after-cost alpha training produced degenerate LightGBM artifacts with no usable split structure: "
            + ", ".join(sorted(degenerate))
        )


def _lightgbm_artifact_is_degenerate(artifact: Mapping[str, Any]) -> bool:
    model_text = str(artifact.get("booster_model") or "")
    if not model_text.strip():
        return True
    saw_tree = False
    saw_split = False
    for line in model_text.splitlines():
        if line.startswith("Tree="):
            saw_tree = True
        elif line.startswith("num_leaves="):
            try:
                if int(line.split("=", 1)[1].strip()) > 1:
                    saw_split = True
            except ValueError:
                continue
        elif line.startswith("split_feature=") and line.split("=", 1)[1].strip():
            saw_split = True
    return not (saw_tree and saw_split)


def _daily_return(rows: Sequence[Mapping[str, Any]], index: int) -> float:
    if index <= 0:
        return 0.0
    previous = _safe_float(rows[index - 1].get("bar_close"))
    current = _safe_float(rows[index].get("bar_close"))
    return (current - previous) / previous if previous and current is not None and previous > 0 else 0.0


def _window_return(rows: Sequence[Mapping[str, Any]], index: int, window: int) -> float:
    if index < window:
        return 0.0
    previous = _safe_float(rows[index - window].get("bar_close"))
    current = _safe_float(rows[index].get("bar_close"))
    return (current - previous) / previous if previous and current is not None and previous > 0 else 0.0


def _volume_rank(rows: Sequence[Mapping[str, Any]], index: int, window: int) -> float:
    start = max(0, index - window + 1)
    volumes = [_safe_float(row.get("bar_volume")) for row in rows[start : index + 1]]
    clean_volumes = [volume for volume in volumes if volume is not None]
    current = _safe_float(rows[index].get("bar_volume"))
    if not clean_volumes or current is None:
        return 0.0
    return sum(1 for volume in clean_volumes if volume <= current) / len(clean_volumes)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clip_signed(value: float) -> float:
    return max(-1.0, min(1.0, value))


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
