from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.export import render_market_state_report_markdown
from src.research.family_registry import family_config
from src.research.jsonl_utils import load_jsonl_rows
from src.research.reporting import build_market_state_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build market-state report and first State × Family × Parameter Region cube from candle JSONL.')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-json', type=Path, default=Path('reports/research/market_state_report.json'))
    parser.add_argument('--output-md', type=Path, default=Path('reports/research/market_state_report.md'))
    parser.add_argument('--family', type=str, default='moving_average')
    parser.add_argument('--limit-variants', type=int, default=24)
    parser.add_argument('--horizon-bars', type=int, default=60)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    candles = load_jsonl_rows(args.input, skip_invalid=True)
    config = family_config(args.family)
    if config is None:
        raise RuntimeError(f'missing family config: {args.family}')
    variants = (config.get('baseline_variants') or [])[: args.limit_variants]
    report = build_market_state_report(candles, variants, horizon_bars=args.horizon_bars)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    args.output_md.write_text(render_market_state_report_markdown(report))
    print(json.dumps({
        'output_json': str(args.output_json),
        'output_md': str(args.output_md),
        'state_row_count': report['summary']['state_row_count'],
        'candidate_row_count': report['summary']['candidate_row_count'],
        'cube_cell_count': report['performance_cube']['summary']['cell_count'],
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
