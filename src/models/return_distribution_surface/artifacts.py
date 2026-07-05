"""Artifact writers for tradable-time return distribution surfaces."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .surface import DistributionSurfaceResult, TargetLabelRow, summarize_surface_result


def write_surface_artifacts(
    *,
    output_dir: Path,
    symbol: str,
    source_table: str,
    source_timeframe: str | None,
    source_range: Mapping[str, str],
    anchor_minutes: int,
    bar_rows_loaded: int,
    bucket_close_count: int,
    label_rows: Sequence[TargetLabelRow],
    result: DistributionSurfaceResult,
) -> dict[str, Any]:
    """Write one surface artifact directory and return its summary payload."""

    output_dir.mkdir(parents=True, exist_ok=True)
    surface_csv = output_dir / "surface.csv"
    _write_surface_csv(surface_csv, result)
    summary = summarize_surface_result(
        symbol=symbol,
        source_table=source_table,
        source_timeframe=source_timeframe,
        source_range=source_range,
        anchor_minutes=anchor_minutes,
        bar_rows_loaded=bar_rows_loaded,
        bucket_close_count=bucket_close_count,
        label_rows=label_rows,
        result=result,
        surface_csv=str(surface_csv),
    )
    (output_dir / "surface_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "validation_rows.json").write_text(
        json.dumps(result.validation_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "cdf_rows.json").write_text(
        json.dumps(result.cdf_rows, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return summary


def write_surface_bundle_manifest(
    *,
    output_dir: Path,
    surfaces: Sequence[Mapping[str, Any]],
    request: Mapping[str, Any],
    chain_smoke: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Write a bundle manifest for a symbol/window surface batch."""

    manifest = {
        "contract_type": "tradable_time_return_distribution_surface_bundle_manifest",
        "request": dict(request),
        "surface_count": len(surfaces),
        "surfaces": [dict(surface) for surface in surfaces],
        "chain_smoke": list(chain_smoke or []),
        "side_effects": {
            "provider_call_performed": False,
            "broker_execution_performed": False,
            "account_mutation_performed": False,
            "model_activation_performed": False,
            "sql_mutation_performed": False,
            "storage_source_mutation_performed": False,
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "surface_bundle_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return manifest


def _write_surface_csv(path: Path, result: DistributionSurfaceResult) -> None:
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
