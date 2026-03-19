from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.grid_search import build_parameter_search_plan
from src.research.parameter_spaces import parameter_space_for
from src.runners.compare_strategies import load_jsonl


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build a minimal parameter-search plan for a strategy/regime pair.')
    parser.add_argument('--input', type=str, default='logs/research/regime_dataset.jsonl')
    parser.add_argument('--regime', type=str, required=True)
    parser.add_argument('--strategy', type=str, required=True)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    rows = load_jsonl(args.input)
    plan = build_parameter_search_plan(
        regime=args.regime,
        strategy=args.strategy,
        space=parameter_space_for(args.strategy),
        rows=rows,
    )
    print(json.dumps(plan, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
