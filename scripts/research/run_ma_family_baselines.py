from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.family_registry import family_config
from src.research.ma_family import summarize_ma_family


def load_rows(path: Path) -> list[dict]:
    rows = []
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run MA family baseline summaries on normalized candle JSONL.')
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path('reports/research/ma_family_baselines.json'))
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    rows = load_rows(args.input)
    config = family_config('moving_average')
    if config is None:
        raise RuntimeError('missing moving_average family config')
    baseline_variants = summarize_ma_family(rows, config['baseline_variants'])
    summary = {
        'family': 'moving_average',
        'phase_goal': config['phase_goal'],
        'row_count': len(rows),
        'baseline_variants': baseline_variants,
        'family_champion': baseline_variants[0] if baseline_variants else None,
        'dynamic_parameter_targets': config['dynamic_parameter_targets'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(json.dumps({'output': str(args.output), 'row_count': len(rows), 'variant_count': len(summary['baseline_variants'])}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
