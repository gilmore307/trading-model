from __future__ import annotations

import argparse
from pathlib import Path

from src.research.dataset_builder import build_research_row, write_jsonl
from src.runners.regime_runner import BtcRegimeRunner


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build a minimal regime research dataset from repeated regime snapshots.')
    parser.add_argument('--cycles', type=int, default=10, help='Number of sequential snapshots to capture.')
    parser.add_argument('--out', type=str, default='logs/research/regime_dataset.jsonl', help='Output jsonl path relative to repo root.')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    runner = BtcRegimeRunner()
    rows = []
    for _ in range(max(1, args.cycles)):
        output = runner.run_once()
        rows.append(build_research_row(output=output))
    out_path = write_jsonl(rows, Path(args.out))
    print(out_path)


if __name__ == '__main__':
    main()
