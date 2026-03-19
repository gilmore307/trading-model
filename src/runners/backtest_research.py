from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.research.dataset_builder import write_jsonl
from src.research.export import render_research_report_markdown
from src.research.replay import build_dataset_from_snapshot_rows, load_snapshot_jsonl
from src.research.reporting import build_research_report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run an offline research backtest pipeline from historical snapshot jsonl.')
    parser.add_argument('--input', type=str, required=True, help='Historical snapshot jsonl (standard research rows or regime_local_cycle artifacts).')
    parser.add_argument('--dataset-out', type=str, default='logs/research/backtest_dataset.jsonl')
    parser.add_argument('--report-json-out', type=str, default='logs/research/backtest_report.json')
    parser.add_argument('--report-md-out', type=str, default='logs/research/backtest_report.md')
    parser.add_argument('--forward-field', type=str, default='fwd_ret_1h')
    parser.add_argument('--horizons', type=str, default=None, help='Optional horizons, e.g. fwd_ret_15m=1,fwd_ret_1h=3')
    return parser


def _parse_horizons(value: str | None) -> dict[str, int] | None:
    if not value:
        return None
    result: dict[str, int] = {}
    for item in value.split(','):
        item = item.strip()
        if not item:
            continue
        name, steps = item.split('=', 1)
        result[name.strip()] = int(steps.strip())
    return result or None


def main() -> None:
    args = build_arg_parser().parse_args()
    horizons = _parse_horizons(args.horizons)
    rows = load_snapshot_jsonl(args.input)
    dataset = build_dataset_from_snapshot_rows(rows, horizons=horizons)

    dataset_path = Path(args.dataset_out)
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(dataset, dataset_path)

    report = build_research_report(dataset, forward_field=args.forward_field, forward_fields=list((horizons or {}).keys()) or None)

    report_json_path = Path(args.report_json_out)
    report_json_path.parent.mkdir(parents=True, exist_ok=True)
    report_json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    report_md_path = Path(args.report_md_out)
    report_md_path.parent.mkdir(parents=True, exist_ok=True)
    report_md_path.write_text(render_research_report_markdown(report), encoding='utf-8')

    print(json.dumps({
        'dataset': str(dataset_path),
        'report_json': str(report_json_path),
        'report_md': str(report_md_path),
        'row_count': len(dataset),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
