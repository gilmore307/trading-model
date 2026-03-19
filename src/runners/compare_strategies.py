from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.evaluators import build_strategy_regime_matrix


def load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build a minimal strategy x regime comparison matrix from regime_dataset jsonl.')
    parser.add_argument('--input', type=str, default='logs/research/regime_dataset.jsonl')
    parser.add_argument('--forward-field', type=str, default='fwd_ret_1h')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    rows = load_jsonl(args.input)
    matrix = build_strategy_regime_matrix(rows, forward_field=args.forward_field)
    print(json.dumps(matrix, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
