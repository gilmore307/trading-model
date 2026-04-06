from __future__ import annotations

import argparse
import json
from pathlib import Path

from trading_model.pipeline.multi_run import run_multi_symbol_summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run trading-model multi-symbol summary")
    parser.add_argument("--symbol", action="append", dest="symbols", required=True)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--variant-limit", type=int, default=12)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    summary = run_multi_symbol_summary(
        trading_data_root=Path("/root/.openclaw/workspace/projects/trading-data/data"),
        trading_strategy_root=Path("/root/.openclaw/workspace/projects/trading-strategy/data"),
        output_root=Path(args.output_root),
        symbols=args.symbols,
        variant_limit=args.variant_limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
