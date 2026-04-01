from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.bollinger_family import build_bollinger_reversion_signals
from src.research.family_registry import family_config
from src.research.jsonl_utils import load_jsonl_rows
from src.research.market_state import write_jsonl_rows

DEFAULT_OKX_CANDLES = 'data/raw/BTC-USDT-SWAP/candles/BTC-USDT-SWAP.jsonl'
DEFAULT_OUT = 'data/intermediate/parameter_utility/bollinger_parameter_utility_dataset_v1.jsonl'


def _forward_return(closes: list[float], start: int, horizon: int) -> float | None:
    end = start + horizon
    if start < 0 or end >= len(closes):
        return None
    entry = closes[start]
    exit_ = closes[end]
    if entry <= 0:
        return None
    return (exit_ / entry) - 1.0


def parameter_region_for_bollinger(variant_id: str | None) -> str:
    if not variant_id:
        return 'unknown'
    if '_m25_' in variant_id:
        width_band = 'wide_bands'
    else:
        width_band = 'base_bands'
    if '_e10' in variant_id:
        exit_band = 'slow_exit'
    elif '_e05' in variant_id:
        exit_band = 'mid_exit'
    else:
        exit_band = 'fast_exit'
    return f'{width_band}__{exit_band}'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build bollinger_parameter_utility_dataset_v1 from historical candles and Bollinger family baseline variants.')
    parser.add_argument('--candles', default=DEFAULT_OKX_CANDLES)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--sample-every', type=int, default=15)
    parser.add_argument('--max-variants', type=int, default=48)
    parser.add_argument('--horizon-bars', type=int, default=60)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    candles = load_jsonl_rows(Path(args.candles), skip_invalid=True)
    if args.sample_every > 1:
        candles = [row for idx, row in enumerate(candles) if idx % args.sample_every == 0]
    family = family_config('bollinger_reversion')
    if family is None:
        raise RuntimeError('bollinger_reversion family config not found')
    variants = list(family['baseline_variants'])
    if args.max_variants > 0:
        variants = variants[: args.max_variants]

    closes = [float(row['close']) for row in candles]
    dataset = []
    for variant in variants:
        signals = build_bollinger_reversion_signals(
            candles,
            window=int(variant['window']),
            std_mult=float(variant.get('std_mult', 2.0)),
            exit_z=float(variant.get('exit_z', 0.5)),
            direction=str(variant.get('direction', 'both')),
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
                'family': 'bollinger_reversion',
                'variant_id': signal.get('variant'),
                'parameter_region': parameter_region_for_bollinger(signal.get('variant')),
                'position': position,
                'forward_return_1h': forward_ret,
                'utility_1h': utility,
                'window': variant.get('window'),
                'std_mult': variant.get('std_mult', 2.0),
                'exit_z': variant.get('exit_z', 0.5),
                'direction': variant.get('direction', 'both'),
                'price_source': variant.get('price_source', 'close'),
            })
    out_path = write_jsonl_rows(dataset, args.out)
    print(json.dumps({'output': str(out_path), 'rows': len(dataset), 'candles_used': len(candles), 'variants_used': len(variants), 'sample_every': args.sample_every, 'horizon_bars': args.horizon_bars}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
