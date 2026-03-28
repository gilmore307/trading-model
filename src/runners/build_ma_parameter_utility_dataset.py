from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.family_registry import family_config
from src.research.market_state import build_ma_candidate_dataset, load_jsonl_rows, write_jsonl_rows

DEFAULT_OKX_CANDLES = 'data/raw/okx/candles/BTC-USDT-SWAP/1m/BTC-USDT-SWAP_1m_20220101_now.jsonl'
DEFAULT_OUT = 'data/intermediate/parameter_utility/ma_parameter_utility_dataset_v1.jsonl'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build ma_parameter_utility_dataset_v1 from historical candles and MA family baseline variants.')
    parser.add_argument('--candles', default=DEFAULT_OKX_CANDLES)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--sample-every', type=int, default=15, help='Keep every Nth candle before MA-variant evaluation to control first-pass dataset size.')
    parser.add_argument('--max-variants', type=int, default=60, help='Optional cap on MA baseline variants for first-pass generation.')
    parser.add_argument('--horizon-bars', type=int, default=60)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    candles = load_jsonl_rows(args.candles)
    if args.sample_every > 1:
        candles = [row for idx, row in enumerate(candles) if idx % args.sample_every == 0]

    ma = family_config('moving_average')
    if ma is None:
        raise RuntimeError('moving_average family config not found')
    variants = list(ma['baseline_variants'])
    if args.max_variants > 0:
        variants = variants[: args.max_variants]

    dataset = build_ma_candidate_dataset(candles, variants, horizon_bars=args.horizon_bars)
    out_path = write_jsonl_rows(dataset, args.out)
    summary = {
        'output': str(out_path),
        'rows': len(dataset),
        'candles_used': len(candles),
        'variants_used': len(variants),
        'sample_every': args.sample_every,
        'horizon_bars': args.horizon_bars,
        'start_ts': None if not dataset else dataset[0]['ts'],
        'end_ts': None if not dataset else dataset[-1]['ts'],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
