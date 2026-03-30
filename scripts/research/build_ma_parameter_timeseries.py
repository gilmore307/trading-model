from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.family_registry import family_config
from src.research.jsonl_utils import load_jsonl_rows
from src.research.ma_timeseries import build_ma_equity_curve


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build MA parameter timeseries artifact for dashboard visualization.')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('reports/research/ma_parameter_timeseries.json'))
    parser.add_argument('--limit-variants', type=int, default=12)
    parser.add_argument('--downsample-step', type=int, default=240)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    rows = load_jsonl_rows(args.input, skip_invalid=True)
    config = family_config('moving_average') or {}
    variants = (config.get('baseline_variants') or [])[: args.limit_variants]
    payload = {
        'family': 'moving_average',
        'source': str(args.input),
        'variant_count': len(variants),
        'downsample_step': args.downsample_step,
        'series': {},
    }
    for variant in variants:
        curve = build_ma_equity_curve(
            rows,
            fast_window=int(variant['fast_window']),
            slow_window=int(variant['slow_window']),
            threshold_enter_pct=float(variant.get('threshold_enter_pct', variant.get('threshold_pct', 0.0))),
            threshold_exit_pct=float(variant.get('threshold_exit_pct', 0.0)),
            ma_type=str(variant.get('ma_type', 'SMA')),
            price_source=str(variant.get('price_source', 'close')),
        )
        slim = curve[:: max(1, args.downsample_step)]
        if curve and (not slim or slim[-1]['ts'] != curve[-1]['ts']):
            slim.append(curve[-1])
        payload['series'][variant['variant_id']] = {
            'params': variant,
            'points': slim,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(json.dumps({
        'output': str(args.output),
        'variant_count': payload['variant_count'],
        'series_keys': list(payload['series'].keys())[:5],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
