from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.dataset_builder import build_research_row, write_jsonl
from src.research.replay import build_dataset_from_snapshot_rows, load_snapshot_jsonl
from src.runners.regime_runner import BtcRegimeRunner


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build a minimal regime research dataset.')
    parser.add_argument('--cycles', type=int, default=10, help='Number of sequential live snapshots to capture when replay is not used.')
    parser.add_argument('--out', type=str, default='logs/research/regime_dataset.jsonl', help='Output jsonl path relative to repo root.')
    parser.add_argument('--replay-jsonl', type=str, default=None, help='Optional jsonl file containing historical regime snapshots to replay into a dataset.')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    if args.replay_jsonl:
        rows = load_snapshot_jsonl(args.replay_jsonl)
        dataset = build_dataset_from_snapshot_rows(rows)
        out_path = write_jsonl(dataset, Path(args.out))
        print(out_path)
        return

    runner = BtcRegimeRunner()
    rows = []
    for _ in range(max(1, args.cycles)):
        output = runner.run_once()
        rows.append(build_research_row(output=output))
    out_path = write_jsonl(rows, Path(args.out))
    print(out_path)


if __name__ == '__main__':
    main()
