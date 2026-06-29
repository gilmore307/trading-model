#!/usr/bin/env python3
"""Train the fold-scoped M05 after-cost alpha confidence artifact."""
from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence

import psycopg
from psycopg.rows import dict_row

from model_runtime.config import database_url_file


MODEL_ID = "model_05_alpha_confidence"
MODEL_VERSION = "fold_supervised_after_cost_alpha"
CONTRACT_TYPE = "after_cost_alpha_model"
HORIZONS = ("10min", "1h", "1D", "1W")
DEFAULT_DB_URL_FILE = database_url_file()
DEFAULT_CANDIDATE_UNIVERSE_PATH = Path("/root/projects/trading-storage/main/shared/historical_candidate_universe.csv")
FEATURE_NAMES = (
    "2_target_direction_score_1D",
    "2_target_trend_quality_score_1D",
    "2_target_path_stability_score_1D",
    "2_target_noise_score_1D",
    "2_target_transition_risk_score_1D",
    "2_context_support_quality_score_1D",
    "2_tradability_score_1D",
    "2_target_direction_score_1W",
    "2_target_trend_quality_score_1W",
    "2_tradability_score_1W",
)
HORIZON_DELTAS = {
    "10min": timedelta(minutes=10),
    "1h": timedelta(hours=1),
    "1D": timedelta(days=1),
    "1W": timedelta(days=7),
}
DEFAULT_MAX_SAMPLES_PER_SYMBOL = 5000


def build_rejection_artifact(
    *,
    source_start: str | None,
    source_end: str | None,
    all_horizons: bool,
    from_database: bool,
    generated_at_utc: str | None = None,
) -> dict[str, Any]:
    """Build a non-model receipt explaining why training cannot emit an artifact."""

    horizons = list(HORIZONS if all_horizons else ("1W",))
    return {
        "contract_type": "after_cost_alpha_training_rejected",
        "schema_version": "2026-06-23",
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "horizons": horizons,
        "source_window": {
            "source_start": source_start,
            "source_end": source_end,
        },
        "training_summary": {
            "training_mode": "supervised_fit_required",
            "source": "database" if from_database else "local",
            "sample_count": 0,
            "reason": "fold-scoped supervised after-cost alpha labels are required before replay",
        },
        "safety": {
            "provider_calls_performed": False,
            "model_activation_performed": False,
            "broker_execution_performed": False,
            "account_mutation_performed": False,
            "sql_mutation_performed": False,
        },
        "generated_at_utc": generated_at_utc or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def rejection_receipt_path(output_path: Path) -> Path:
    return output_path.with_name(output_path.name + ".training_rejection.json")


def _database_url(explicit: str | None) -> str:
    if explicit:
        return explicit
    for env_name in ("OPENCLAW_DATABASE_URL", "TRADING_MODEL_DATABASE_URL", "DATABASE_URL"):
        value = str(__import__("os").environ.get(env_name, "")).strip()
        if value:
            return value
    if DEFAULT_DB_URL_FILE.exists():
        return DEFAULT_DB_URL_FILE.read_text(encoding="utf-8").strip()
    raise SystemExit(f"database URL not supplied and {DEFAULT_DB_URL_FILE} does not exist")


def _parse_time(value: str | None) -> datetime:
    if not value:
        raise SystemExit("source window is required for fold-scoped training")
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _sql_time(value: datetime) -> str:
    return value.isoformat()


def _load_candidate_symbols(path: Path | None, *, fallback_symbol: str) -> tuple[str, ...]:
    if path is None or not path.exists():
        return (fallback_symbol,)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        symbols: list[str] = []
        for row in reader:
            status = str(row.get("replay_candidate_status") or row.get("status") or "active").strip().lower()
            if status and status not in {"active", "accepted", "enabled"}:
                continue
            asset_class = str(row.get("asset_class") or "us_equity").strip().lower()
            if asset_class and asset_class not in {"us_equity", "equity"}:
                continue
            symbol = str(row.get("symbol") or row.get("target_ref") or row.get("target_symbol") or "").strip().upper()
            if symbol and symbol not in symbols:
                symbols.append(symbol)
    return tuple(symbols or (fallback_symbol,))


def _bar_close(row: Mapping[str, Any]) -> float:
    return float(row["close"])


def _bar_volume(row: Mapping[str, Any]) -> float:
    return float(row["volume"] or 0.0)


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _clip_signed(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _daily_return(rows: Sequence[Mapping[str, Any]], index: int) -> float:
    if index <= 0:
        return 0.0
    previous = _bar_close(rows[index - 1])
    current = _bar_close(rows[index])
    return (current - previous) / previous if previous > 0 else 0.0


def _window_return(rows: Sequence[Mapping[str, Any]], index: int, window: int) -> float:
    if index < window:
        return 0.0
    previous = _bar_close(rows[index - window])
    current = _bar_close(rows[index])
    return (current - previous) / previous if previous > 0 else 0.0


def _volume_rank(rows: Sequence[Mapping[str, Any]], index: int, window: int) -> float:
    start = max(0, index - window + 1)
    volumes = [_bar_volume(row) for row in rows[start : index + 1]]
    if not volumes:
        return 0.0
    current = _bar_volume(rows[index])
    return sum(1 for volume in volumes if volume <= current) / len(volumes)


def _target_context_features(rows: Sequence[Mapping[str, Any]], index: int) -> dict[str, float]:
    momentum_7d = _window_return(rows, index, 7)
    momentum_30d = _window_return(rows, index, 30)
    daily = _daily_return(rows, index)
    direction_1d = _clip_signed(daily * 8.0 + momentum_7d * 3.0)
    direction_1w = _clip_signed(momentum_7d * 4.0 + momentum_30d)
    trend_quality = _clip01(0.5 + abs(momentum_7d) * 8.0 + abs(momentum_30d) * 2.0)
    liquidity = _volume_rank(rows, index, 30)
    return {
        "2_target_direction_score_1D": direction_1d,
        "2_target_trend_quality_score_1D": trend_quality,
        "2_target_path_stability_score_1D": _clip01(0.65 - abs(daily) * 4.0),
        "2_target_noise_score_1D": _clip01(abs(daily) * 4.0),
        "2_target_transition_risk_score_1D": _clip01(abs(daily - momentum_7d) * 2.0),
        "2_context_support_quality_score_1D": 0.60,
        "2_tradability_score_1D": liquidity,
        "2_target_direction_score_1W": direction_1w,
        "2_target_trend_quality_score_1W": trend_quality,
        "2_tradability_score_1W": liquidity,
    }


def _select_evenly(indices: Sequence[int], max_count: int) -> list[int]:
    if max_count <= 0 or len(indices) <= max_count:
        return list(indices)
    step = len(indices) / float(max_count)
    return [indices[min(len(indices) - 1, int(offset * step))] for offset in range(max_count)]


def _load_training_rows(
    *,
    database_url: str,
    target_symbol: str,
    candidate_universe_path: Path | None,
    source_start: str,
    source_end: str,
    horizon: str,
    cost_bps: float,
    max_samples_per_symbol: int,
) -> tuple[list[dict[str, float]], list[int], dict[str, Any]]:
    start = _parse_time(source_start)
    end = _parse_time(source_end)
    horizon_delta = HORIZON_DELTAS[horizon]
    symbols = _load_candidate_symbols(candidate_universe_path, fallback_symbol=target_symbol)
    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        bars = conn.execute(
            """
            select symbol, timestamp, bar_close as close, bar_volume as volume
            from trading_data.model_03_target_state_vector_data_acquisition
            where symbol = any(%s)
              and timestamp >= %s
              and timestamp < %s
              and bar_close > 0
            order by symbol, timestamp
            """,
            (list(symbols), _sql_time(start - timedelta(days=45)), _sql_time(end + horizon_delta + timedelta(days=2))),
        ).fetchall()
    cost_fraction = cost_bps / 10000.0
    features: list[dict[str, float]] = []
    labels: list[int] = []
    realized_returns: list[float] = []
    bars_by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in symbols}
    for row in bars:
        symbol = str(row["symbol"]).upper()
        bars_by_symbol.setdefault(symbol, []).append(dict(row))
    symbols_with_samples: list[str] = []
    for symbol, symbol_rows in sorted(bars_by_symbol.items()):
        if len(symbol_rows) < 40:
            continue
        bar_times = [row["timestamp"] for row in symbol_rows]
        eligible = [
            index
            for index, row in enumerate(symbol_rows)
            if row["timestamp"] >= start
            and row["timestamp"] < end
            and bisect.bisect_left(bar_times, row["timestamp"] + horizon_delta) < len(symbol_rows)
        ]
        selected_indices = _select_evenly(eligible, max_samples_per_symbol)
        if selected_indices:
            symbols_with_samples.append(symbol)
        for row_index in selected_indices:
            row = symbol_rows[row_index]
            close = _bar_close(row)
            future_index = bisect.bisect_left(bar_times, row["timestamp"] + horizon_delta)
            future_close = _bar_close(symbol_rows[future_index])
            realized_return = (future_close - close) / close - cost_fraction
            feature_row = _target_context_features(symbol_rows, row_index)
            features.append({name: float(feature_row.get(name, 0.0)) for name in FEATURE_NAMES})
            labels.append(1 if realized_return > 0 else 0)
            realized_returns.append(realized_return)
    summary = {
        "candidate_training_target": target_symbol,
        "training_universe_scope": "fixed_historical_candidate_universe",
        "training_universe_symbol_count": len(symbols),
        "symbols_with_samples": symbols_with_samples,
        "symbols_with_sample_count": len(symbols_with_samples),
        "max_samples_per_symbol": max_samples_per_symbol,
        "source_row_count": sum(len(rows) for rows in bars_by_symbol.values()),
        "bar_row_count": len(bars),
        "sample_count": len(labels),
        "positive_count": sum(labels),
        "negative_count": len(labels) - sum(labels),
        "mean_realized_after_cost_return": (sum(realized_returns) / len(realized_returns)) if realized_returns else None,
    }
    return features, labels, summary


def _standardize(features: list[dict[str, float]]) -> tuple[list[list[float]], dict[str, float], dict[str, float]]:
    means: dict[str, float] = {}
    scales: dict[str, float] = {}
    for name in FEATURE_NAMES:
        values = [row[name] for row in features]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        scale = math.sqrt(variance) or 1.0
        means[name] = mean
        scales[name] = scale
    matrix = [[(row[name] - means[name]) / scales[name] for name in FEATURE_NAMES] for row in features]
    return matrix, means, scales


def _train_logistic_model(features: list[dict[str, float]], labels: list[int]) -> dict[str, Any]:
    matrix, means, scales = _standardize(features)
    weights = [0.0 for _ in FEATURE_NAMES]
    positive_rate = max(1e-6, min(1 - 1e-6, sum(labels) / len(labels)))
    intercept = math.log(positive_rate / (1.0 - positive_rate))
    learning_rate = 0.05
    regularization = 0.001
    for _epoch in range(80):
        grad_w = [0.0 for _ in FEATURE_NAMES]
        grad_b = 0.0
        for row, label in zip(matrix, labels, strict=True):
            z_value = intercept + sum(weight * value for weight, value in zip(weights, row, strict=True))
            prediction = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z_value))))
            error = prediction - label
            grad_b += error
            for index, value in enumerate(row):
                grad_w[index] += error * value
        count = float(len(labels))
        intercept -= learning_rate * grad_b / count
        for index, weight in enumerate(weights):
            weights[index] -= learning_rate * ((grad_w[index] / count) + regularization * weight)
    return {
        "model_family": "logistic_regression",
        "default_horizon": "1D",
        "feature_names": list(FEATURE_NAMES),
        "coefficients": [round(value, 10) for value in weights],
        "intercept": round(intercept, 10),
        "feature_means": {name: round(value, 10) for name, value in means.items()},
        "feature_scales": {name: round(value, 10) for name, value in scales.items()},
    }


def build_model_artifact(
    *,
    target_symbol: str,
    source_start: str,
    source_end: str,
    horizons: list[str],
    label_horizon: str,
    cost_bps: float,
    features: list[dict[str, float]],
    labels: list[int],
    label_summary: dict[str, Any],
) -> dict[str, Any]:
    score_model = _train_logistic_model(features, labels)
    positive_rate = label_summary["positive_count"] / label_summary["sample_count"]
    return {
        "contract_type": CONTRACT_TYPE,
        "schema_version": "2026-06-23",
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "model_type": "fold_supervised_after_cost_alpha_logistic",
        "target_symbol": target_symbol,
        "horizons": horizons,
        "score_model": score_model,
        "selected_thresholds": {
            "minimum_entry_alpha_confidence": 0.5,
            "minimum_trade_intensity": 0.05,
        },
        "label_definition": {
            "label_name": "underlying_after_cost_return_positive",
            "label_horizon": label_horizon,
            "cost_bps": cost_bps,
            "positive_when": "future_underlying_return_after_cost_gt_0",
        },
        "source_window": {
            "source_start": source_start,
            "source_end": source_end,
        },
        "training_summary": {
            "training_mode": "supervised_fit",
            "source": "database",
            "sample_count": label_summary["sample_count"],
            "positive_count": label_summary["positive_count"],
            "negative_count": label_summary["negative_count"],
            "positive_rate": round(positive_rate, 10),
            "candidate_training_target": label_summary.get("candidate_training_target", target_symbol),
            "training_universe_scope": label_summary.get("training_universe_scope"),
            "training_universe_symbol_count": label_summary.get("training_universe_symbol_count"),
            "symbols_with_sample_count": label_summary.get("symbols_with_sample_count"),
            "symbols_with_samples": label_summary.get("symbols_with_samples"),
            "max_samples_per_symbol": label_summary.get("max_samples_per_symbol"),
            "source_row_count": label_summary["source_row_count"],
            "bar_row_count": label_summary["bar_row_count"],
            "mean_realized_after_cost_return": label_summary["mean_realized_after_cost_return"],
        },
        "safety": {
            "provider_calls_performed": False,
            "model_activation_performed": False,
            "broker_execution_performed": False,
            "account_mutation_performed": False,
            "sql_mutation_performed": False,
        },
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-database", action="store_true", help="Record that the request is tied to database-backed fold scope.")
    parser.add_argument("--all-horizons", action="store_true", help="Emit the current model decision horizon grid.")
    parser.add_argument("--source-start")
    parser.add_argument("--source-end")
    parser.add_argument("--target-symbol", required=True)
    parser.add_argument("--candidate-universe-path", type=Path, default=DEFAULT_CANDIDATE_UNIVERSE_PATH)
    parser.add_argument("--max-samples-per-symbol", type=int, default=DEFAULT_MAX_SAMPLES_PER_SYMBOL)
    parser.add_argument("--database-url")
    parser.add_argument("--label-horizon", choices=tuple(HORIZON_DELTAS), default="1D")
    parser.add_argument("--cost-bps", type=float, default=10.0)
    parser.add_argument("--output-json", type=Path, required=True)
    args = parser.parse_args(argv)

    target_symbol = args.target_symbol.strip().upper()
    horizons = list(HORIZONS if args.all_horizons else (args.label_horizon,))
    try:
        features, labels, label_summary = _load_training_rows(
            database_url=_database_url(args.database_url),
            target_symbol=target_symbol,
            candidate_universe_path=args.candidate_universe_path,
            source_start=args.source_start,
            source_end=args.source_end,
            horizon=args.label_horizon,
            cost_bps=args.cost_bps,
            max_samples_per_symbol=args.max_samples_per_symbol,
        )
    except Exception as exc:
        artifact = build_rejection_artifact(
            source_start=args.source_start,
            source_end=args.source_end,
            all_horizons=args.all_horizons,
            from_database=args.from_database,
        )
        message = {
            "status": "failed",
            "reason_code": "after_cost_alpha_supervised_training_labels_missing",
            "reason": f"{type(exc).__name__}: {exc}",
            "output_json": str(args.output_json),
            "contract_type": artifact["contract_type"],
            "training_summary": artifact["training_summary"],
        }
        write_artifact(rejection_receipt_path(args.output_json), artifact | message)
        print(json.dumps(message, sort_keys=True), file=sys.stderr)
        return 2
    if len(labels) < 100 or len(set(labels)) < 2:
        artifact = build_rejection_artifact(
            source_start=args.source_start,
            source_end=args.source_end,
            all_horizons=args.all_horizons,
            from_database=args.from_database,
        )
        artifact["training_summary"].update(label_summary)
        message = {
            "status": "failed",
            "reason_code": "after_cost_alpha_supervised_training_labels_missing",
            "output_json": str(args.output_json),
            "contract_type": artifact["contract_type"],
            "training_summary": artifact["training_summary"],
        }
        write_artifact(rejection_receipt_path(args.output_json), artifact | message)
        print(json.dumps(message, sort_keys=True), file=sys.stderr)
        return 2
    model = build_model_artifact(
        target_symbol=target_symbol,
        source_start=args.source_start,
        source_end=args.source_end,
        horizons=horizons,
        label_horizon=args.label_horizon,
        cost_bps=args.cost_bps,
        features=features,
        labels=labels,
        label_summary=label_summary,
    )
    write_artifact(args.output_json, model)
    rejection_path = rejection_receipt_path(args.output_json)
    if rejection_path.exists():
        rejection_path.unlink()
    print(
        json.dumps(
            {
                "status": "succeeded",
                "reason_code": "after_cost_alpha_supervised_training_completed",
                "output_json": str(args.output_json),
                "sample_count": len(labels),
                "positive_count": sum(labels),
                "target_symbol": target_symbol,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
