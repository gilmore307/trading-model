from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_INPUTS = [
    'data/intermediate/parameter_utility/ma_parameter_utility_dataset_v1.jsonl',
    'data/intermediate/parameter_utility/donchian_parameter_utility_dataset_v1.jsonl',
]
DEFAULT_OUT = 'data/intermediate/parameter_utility/strategy_parameter_utility_dataset_v1.jsonl'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Combine family-specific utility datasets into strategy_parameter_utility_dataset_v1.')
    parser.add_argument('--input', action='append', dest='inputs', default=[])
    parser.add_argument('--out', default=DEFAULT_OUT)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    inputs = args.inputs or DEFAULT_INPUTS
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    family_counts: dict[str, int] = {}
    total_rows = 0

    with out_path.open('w', encoding='utf-8') as out:
        for input_path in inputs:
            path = Path(input_path)
            with path.open('r', encoding='utf-8') as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    out.write(json.dumps(row, ensure_ascii=False) + '\n')
                    family = str(row.get('family') or 'unknown')
                    family_counts[family] = family_counts.get(family, 0) + 1
                    total_rows += 1

    print(json.dumps({
        'output': str(out_path),
        'rows': total_rows,
        'family_counts': family_counts,
        'input_count': len(inputs),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
