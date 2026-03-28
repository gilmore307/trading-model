from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.export import render_market_state_report_markdown

DEFAULT_STATE_DATASET = 'data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl'
DEFAULT_UTILITY_DATASET = 'data/intermediate/parameter_utility/strategy_parameter_utility_dataset_v1.jsonl'
DEFAULT_OUT_JSON = 'reports/research/family_market_state_report.json'
DEFAULT_OUT_MD = 'reports/research/family_market_state_report.md'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Build state × family × parameter-region report from a unified strategy utility dataset.')
    parser.add_argument('--state-dataset', default=DEFAULT_STATE_DATASET)
    parser.add_argument('--utility-dataset', default=DEFAULT_UTILITY_DATASET)
    parser.add_argument('--output-json', default=DEFAULT_OUT_JSON)
    parser.add_argument('--output-md', default=DEFAULT_OUT_MD)
    return parser


def _load_state_map(path: Path) -> tuple[dict[int, str], dict[str, int], int]:
    state_by_ts: dict[int, str] = {}
    state_counts: dict[str, int] = {}
    row_count = 0
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row_count += 1
            ts = row.get('ts')
            state = row.get('market_state')
            if ts is None or state is None:
                continue
            state = str(state)
            state_by_ts[int(ts)] = state
            state_counts[state] = state_counts.get(state, 0) + 1
    return state_by_ts, state_counts, row_count


def main() -> None:
    args = build_arg_parser().parse_args()
    state_by_ts, state_counts, state_row_count = _load_state_map(Path(args.state_dataset))

    grouped: dict[tuple[str, str, str], dict[str, float | int]] = {}
    family_state_scores: dict[tuple[str, str], dict[str, float | int]] = {}
    utility_row_count = 0

    with Path(args.utility_dataset).open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            utility_row_count += 1
            ts = row.get('ts')
            if ts is None:
                continue
            state = state_by_ts.get(int(ts))
            family = row.get('family')
            parameter_region = row.get('parameter_region')
            utility = row.get('utility_1h')
            if state is None or family is None or parameter_region is None or utility is None:
                continue

            key = (state, str(family), str(parameter_region))
            bucket = grouped.setdefault(key, {'sum_utility': 0.0, 'count': 0, 'positive': 0})
            bucket['sum_utility'] += float(utility)
            bucket['count'] += 1
            if float(utility) > 0:
                bucket['positive'] += 1

            family_key = (state, str(family))
            family_bucket = family_state_scores.setdefault(family_key, {'sum_utility': 0.0, 'count': 0, 'positive': 0})
            family_bucket['sum_utility'] += float(utility)
            family_bucket['count'] += 1
            if float(utility) > 0:
                family_bucket['positive'] += 1

    cube_rows = []
    for (state, family, parameter_region), bucket in sorted(grouped.items()):
        count = int(bucket['count'])
        cube_rows.append({
            'market_state': state,
            'family': family,
            'parameter_region': parameter_region,
            'sample_count': count,
            'avg_utility_1h': float(bucket['sum_utility']) / count,
            'positive_rate': int(bucket['positive']) / count,
        })

    family_state_summary: dict[str, list[dict[str, float | int | str]]] = {}
    for (state, family), bucket in sorted(family_state_scores.items()):
        count = int(bucket['count'])
        row = {
            'family': family,
            'sample_count': count,
            'avg_utility_1h': float(bucket['sum_utility']) / count,
            'positive_rate': int(bucket['positive']) / count,
        }
        family_state_summary.setdefault(state, []).append(row)
    for state, rows in family_state_summary.items():
        rows.sort(key=lambda row: row['avg_utility_1h'], reverse=True)

    report = {
        'summary': {
            'state_row_count': state_row_count,
            'utility_row_count': utility_row_count,
        },
        'state_counts': state_counts,
        'family_state_summary': family_state_summary,
        'performance_cube': {
            'summary': {
                'state_count': len({row['market_state'] for row in cube_rows}),
                'family_count': len({row['family'] for row in cube_rows}),
                'parameter_region_count': len({row['parameter_region'] for row in cube_rows}),
                'cell_count': len(cube_rows),
                'utility_field': 'utility_1h',
            },
            'rows': cube_rows,
        },
    }

    out_json = Path(args.output_json)
    out_md = Path(args.output_md)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    out_md.write_text(render_market_state_report_markdown(report), encoding='utf-8')
    print(json.dumps({
        'output_json': str(out_json),
        'output_md': str(out_md),
        'cube_cell_count': report['performance_cube']['summary']['cell_count'],
        'utility_row_count': utility_row_count,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
