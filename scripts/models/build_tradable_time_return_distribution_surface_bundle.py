#!/usr/bin/env python3
"""Build a read-only bundle of tradable-time return distribution surfaces."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from model_governance.current_chain import run_current_chain
from models.return_distribution_surface import (
    ALLOWED_SOURCE_TABLES,
    bucket_regular_session_closes,
    build_tradable_time_label_rows,
    fit_tradable_time_distribution_surface,
    load_pit_bars,
    write_surface_artifacts,
    write_surface_bundle_manifest,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols, such as AAPL,MSFT,NVDA.")
    parser.add_argument("--start", help="Inclusive YYYY-MM-DD start. Required when --months is omitted.")
    parser.add_argument("--end", help="Exclusive YYYY-MM-DD end. Required when --months is omitted.")
    parser.add_argument("--months", help="Comma-separated YYYY-MM walk-forward windows. Overrides --start/--end.")
    parser.add_argument("--source", choices=sorted(ALLOWED_SOURCE_TABLES), default="m03")
    parser.add_argument("--timeframe", default="1Min")
    parser.add_argument("--anchor-minutes", type=int, default=10)
    parser.add_argument("--max-trading-minutes", type=int, default=1170)
    parser.add_argument("--fit-mode", choices=("baseline", "context"), default="context")
    parser.add_argument("--run-chain-smoke", action="store_true", help="Run the local M04/M05 handoff smoke for each built summary.")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    symbols = _parse_csv(args.symbols)
    windows = _windows(args)
    output_dir = Path(args.output_dir)
    surfaces: list[dict[str, Any]] = []
    chain_smoke: list[dict[str, Any]] = []
    for symbol in symbols:
        for window in windows:
            surface_entry, summary = _build_one_surface(
                symbol=symbol,
                window=window,
                source=args.source,
                timeframe=args.timeframe,
                anchor_minutes=args.anchor_minutes,
                max_trading_minutes=args.max_trading_minutes,
                fit_mode=args.fit_mode,
                output_dir=output_dir / symbol.lower() / _window_slug(window),
            )
            surfaces.append(surface_entry)
            if args.run_chain_smoke and summary:
                chain_smoke.append(_run_chain_smoke(symbol=symbol, summary=summary, surface_dir=Path(surface_entry["artifact_dir"])))
    manifest = write_surface_bundle_manifest(
        output_dir=output_dir,
        surfaces=surfaces,
        chain_smoke=chain_smoke,
        request={
            "symbols": symbols,
            "windows": windows,
            "source": args.source,
            "source_table": ALLOWED_SOURCE_TABLES[args.source],
            "timeframe": args.timeframe if args.source == "m01" else None,
            "anchor_minutes": args.anchor_minutes,
            "max_trading_minutes": args.max_trading_minutes,
            "fit_mode": args.fit_mode,
            "chain_smoke_requested": bool(args.run_chain_smoke),
        },
    )
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


def _build_one_surface(
    *,
    symbol: str,
    window: dict[str, str],
    source: str,
    timeframe: str,
    anchor_minutes: int,
    max_trading_minutes: int,
    fit_mode: str,
    output_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    rows = load_pit_bars(
        symbol=symbol,
        start=window["start"],
        end=window["end_exclusive"],
        source=source,
        timeframe=timeframe,
    )
    closes = bucket_regular_session_closes(rows, bucket_minutes=anchor_minutes, symbol=symbol)
    label_rows = build_tradable_time_label_rows(
        closes,
        anchor_minutes=anchor_minutes,
        max_trading_minutes=max_trading_minutes,
    )
    entry: dict[str, Any] = {
        "symbol": symbol.upper(),
        "window": dict(window),
        "artifact_dir": str(output_dir),
        "bar_rows_loaded": len(rows),
        "bucket_close_count": len(closes),
        "label_row_count": len(label_rows),
    }
    if not label_rows:
        entry.update({"status": "blocked_no_label_rows", "surface_summary_path": None})
        return entry, None
    result = fit_tradable_time_distribution_surface(label_rows, fit_mode=fit_mode)
    summary = write_surface_artifacts(
        output_dir=output_dir,
        symbol=symbol,
        source_table=ALLOWED_SOURCE_TABLES[source],
        source_timeframe=timeframe if source == "m01" else None,
        source_range={"start": window["start"], "end_exclusive": window["end_exclusive"]},
        anchor_minutes=anchor_minutes,
        bar_rows_loaded=len(rows),
        bucket_close_count=len(closes),
        label_rows=label_rows,
        result=result,
    )
    entry.update(
        {
            "status": "ready",
            "surface_summary_path": str(output_dir / "surface_summary.json"),
            "mean_abs_coverage_error": summary["evaluation"]["mean_abs_coverage_error"],
            "cdf_monotone_failures": summary["evaluation"]["cdf_monotone_failures"],
            "quantile_crossing_repairs": summary["fit"]["quantile_crossing_repairs"],
        }
    )
    return entry, summary


def _run_chain_smoke(*, symbol: str, summary: dict[str, Any], surface_dir: Path) -> dict[str, Any]:
    payload = run_current_chain(
        input_payload={
            "routing_symbol": symbol.upper(),
            "anonymous_target_feature_vector": {"symbol": symbol.upper()},
            "tradable_time_return_distribution_surface_summary": summary,
        },
        evidence_source="tradable_time_return_distribution_surface_bundle_smoke",
    )
    receipt = payload["receipt"]
    receipt_path = surface_dir / "current_chain_surface_handoff_receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return {
        "symbol": symbol.upper(),
        "surface_summary_path": str(surface_dir / "surface_summary.json"),
        "receipt_path": str(receipt_path),
        "chain_status": receipt["chain_status"],
        "blocking_reasons": receipt["blocking_reasons"],
        "handoff_checks_passed": all(check["passed"] for check in receipt["handoff_checks"]),
    }


def _parse_csv(value: str) -> list[str]:
    items = [item.strip().upper() for item in value.split(",") if item.strip()]
    if not items:
        raise SystemExit("at least one symbol is required")
    return items


def _windows(args: argparse.Namespace) -> list[dict[str, str]]:
    if args.months:
        return [_month_window(month) for month in _parse_csv(args.months)]
    if not args.start or not args.end:
        raise SystemExit("--start and --end are required when --months is omitted")
    return [{"start": args.start, "end_exclusive": args.end}]


def _month_window(month: str) -> dict[str, str]:
    year_s, month_s = month.split("-", 1)
    year = int(year_s)
    month_i = int(month_s)
    if month_i < 1 or month_i > 12:
        raise ValueError(f"invalid month: {month!r}")
    start = date(year, month_i, 1)
    end = date(year + (1 if month_i == 12 else 0), 1 if month_i == 12 else month_i + 1, 1)
    return {"start": start.isoformat(), "end_exclusive": end.isoformat()}


def _window_slug(window: dict[str, str]) -> str:
    return f"{window['start']}_to_{window['end_exclusive']}"


if __name__ == "__main__":
    raise SystemExit(main())
