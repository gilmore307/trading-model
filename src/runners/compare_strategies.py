from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.reporting import build_research_report


def load_jsonl(path: str | Path) -> list[dict]:
    rows = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build a minimal regime research report from regime_dataset jsonl.')
    parser.add_argument('--input', type=str, default='logs/research/regime_dataset.jsonl')
    parser.add_argument('--forward-field', type=str, default='fwd_ret_1h')
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    rows = load_jsonl(args.input)
    report = build_research_report(rows, forward_field=args.forward_field)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
