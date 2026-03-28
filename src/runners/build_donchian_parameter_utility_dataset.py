from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.donchian_family import build_donchian_breakout_signals
from src.research.family_registry import family_config
from src.research.market_state import load_jsonl_rows, write_jsonl_rows

DEFAULT_OKX_CANDLES = 'data/raw/okx/candles/BTC-USDT-SWAP/1m/BTC-USDT-SWAP_1m.jsonl'
DEFAULT_OUT = 'data/intermediate/parameter_utility/donchian_parameter_utility_dataset_v1.jsonl'


def _forward_return(closes: list[float], start: int, horizon: int) -> float | None:
    end = start + horizon
    if start < 0 or end >= len(closes):
        return None
    entry = closes[start]
    exit_ = closes[end]
    if entry <= 0:
        return None
    return (exit_ / entry) - 1.0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build donchian_parameter_utility_dataset_v1 from historical candles and Donchian family baseline variants.')
    parser.add_argument('--candles', default=DEFAULT_OKX_CANDLES)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--sample-every', type=int, default=15)
    parser.add_argument('--max-variants', type=int, default=72)
    parser.add_argument('--horizon-bars', type=int, default=60)
    return parser


def parameter_region_for_donchian(variant_id: str | None) -> str:
    if not variant_id:
        return 'unknown'
    if '_bw080_' in variant_id or '_bw050_' in variant_id:
        breakout_band = 'slow_breakout'
    elif '_bw030_' in variant_id:
        breakout_band = 'mid_breakout'
    else:
        breakout_band = 'fast_breakout'
    if '_cb02' in variant_id:
        confirm_band = 'confirmed'
    else:
        confirm_band = 'aggressive'
    return f'{breakout_band}__{confirm_band}'


def main() -> None:
    args = build_arg_parser().parse_args()
    candles = load_jsonl_rows(args.candles)
    if args.sample_every > 1:
        candles = [row for idx, row in enumerate(candles) if idx % args.sample_every == 0]

    family = family_config('donchian_breakout')
    if family is None:
        raise RuntimeError('donchian_breakout family config not found')
    variants = list(family['baseline_variants'])
    if args.max_variants > 0:
        variants = variants[: args.max_variants]

    closes = [float(row['close']) for row in candles]
    dataset = []
    for variant in variants:
        signals = build_donchian_breakout_signals(
            candles,
            breakout_window=int(variant['breakout_window']),
            exit_window=int(variant['exit_window']),
            direction=str(variant.get('direction', 'both')),
            confirm_bars=int(variant.get('confirm_bars', 1)),
            price_source=str(variant.get('price_source', 'close')),
        )
        for i, signal in enumerate(signals):
            forward_ret = _forward_return(closes, i, args.horizon_bars)
            if forward_ret is None:
                continue
            position = int(signal.get('position', 0) or 0)
            utility = forward_ret * position
            dataset.append({
                'ts': signal.get('ts'),
                'timestamp': signal.get('timestamp'),
                'family': 'donchian_breakout',
                'variant_id': signal.get('variant'),
                'parameter_region': parameter_region_for_donchian(signal.get('variant')),
                'position': position,
                'forward_return_1h': forward_ret,
                'utility_1h': utility,
                'breakout_window': variant.get('breakout_window'),
                'exit_window': variant.get('exit_window'),
                'direction': variant.get('direction', 'both'),
                'confirm_bars': variant.get('confirm_bars', 1),
                'price_source': variant.get('price_source', 'close'),
            })
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
