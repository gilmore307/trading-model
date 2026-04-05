from __future__ import annotations

import argparse
import json

from trading_model.contracts.types import PipelineConfig
from trading_model.pipeline.run_pipeline import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run trading-model pipeline")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--data-month", action="append", dest="data_months", required=True)
    parser.add_argument("--strategy-month", action="append", dest="strategy_months", required=True)
    parser.add_argument("--output-root", default="outputs")
    parser.add_argument("--method", choices=["gmm", "kmeans"], default="gmm")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    config = PipelineConfig(
        symbol=args.symbol,
        data_months=args.data_months,
        strategy_months=args.strategy_months,
        output_root=args.output_root,
        discovery={"method": args.method},
    )
    discovery_result, evaluation_result = run_pipeline(config)
    print(
        json.dumps(
            {
                "discovery": discovery_result.model_dump(mode="json"),
                "evaluation": evaluation_result.model_dump(mode="json"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
