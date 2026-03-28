from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_LABELS = 'data/intermediate/market_state/unsupervised_market_state_labels_v1.jsonl'
DEFAULT_UTILITY = 'data/intermediate/parameter_utility/ma_parameter_utility_dataset_v1.jsonl'
DEFAULT_OUT = 'data/derived/unsupervised_market_state_evaluation_v1.json'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Evaluate timestamp-level unsupervised labels against MA parameter-region utility separation.')
    parser.add_argument('--labels', default=DEFAULT_LABELS)
    parser.add_argument('--utility-dataset', default=DEFAULT_UTILITY)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--symbol', default='BTC-USDT-SWAP')
    return parser


def _load_cluster_by_ts(path: Path, symbol: str | None) -> dict[int, int]:
    out: dict[int, int] = {}
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if symbol and row.get('symbol') != symbol:
                continue
            ts = row.get('ts')
            cluster_id = row.get('cluster_id')
            if ts is None or cluster_id is None:
                continue
            out[int(ts)] = int(cluster_id)
    return out


def _evaluate(cluster_by_ts: dict[int, int], utility_path: Path) -> tuple[list[dict], list[dict], dict]:
    agg: dict[tuple[int, str], dict] = defaultdict(lambda: {'count': 0, 'sum_utility': 0.0, 'positive': 0})
    matched_rows = 0
    with utility_path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ts = row.get('ts')
            parameter_region = row.get('parameter_region')
            utility = row.get('utility_1h')
            if ts is None or parameter_region is None or utility is None:
                continue
            cluster_id = cluster_by_ts.get(int(ts))
            if cluster_id is None:
                continue
            matched_rows += 1
            key = (cluster_id, parameter_region)
            agg[key]['count'] += 1
            agg[key]['sum_utility'] += float(utility)
            if float(utility) > 0:
                agg[key]['positive'] += 1

    cube_rows = []
    by_cluster: dict[int, list[dict]] = defaultdict(list)
    for (cluster_id, parameter_region), bucket in sorted(agg.items()):
        row = {
            'cluster_id': cluster_id,
            'parameter_region': parameter_region,
            'sample_count': bucket['count'],
            'avg_utility_1h': bucket['sum_utility'] / bucket['count'],
            'positive_rate': bucket['positive'] / bucket['count'],
        }
        cube_rows.append(row)
        by_cluster[cluster_id].append(row)

    separation_summary = []
    weighted_spread_sum = 0.0
    weighted_count_sum = 0
    for cluster_id, rows in sorted(by_cluster.items()):
        ordered = sorted(rows, key=lambda row: row['avg_utility_1h'], reverse=True)
        best = ordered[0]
        worst = ordered[-1]
        cluster_sample_count = sum(int(row['sample_count']) for row in rows)
        spread = float(best['avg_utility_1h']) - float(worst['avg_utility_1h'])
        weighted_spread_sum += spread * cluster_sample_count
        weighted_count_sum += cluster_sample_count
        separation_summary.append({
            'cluster_id': cluster_id,
            'cluster_sample_count': cluster_sample_count,
            'best_region': best['parameter_region'],
            'best_avg_utility_1h': best['avg_utility_1h'],
            'worst_region': worst['parameter_region'],
            'worst_avg_utility_1h': worst['avg_utility_1h'],
            'spread_best_minus_worst': spread,
        })

    summary = {
        'matched_utility_rows': matched_rows,
        'cube_cell_count': len(cube_rows),
        'cluster_count': len(by_cluster),
        'weighted_avg_cluster_spread': (weighted_spread_sum / weighted_count_sum) if weighted_count_sum else 0.0,
    }
    return cube_rows, separation_summary, summary


def main() -> None:
    args = build_arg_parser().parse_args()
    cluster_by_ts = _load_cluster_by_ts(Path(args.labels), args.symbol)
    cube_rows, separation_summary, summary = _evaluate(cluster_by_ts, Path(args.utility_dataset))
    output = {
        'labels': args.labels,
        'utility_dataset': args.utility_dataset,
        'symbol': args.symbol,
        'summary': summary,
        'cluster_parameter_region_cube': cube_rows,
        'cluster_separation_summary': separation_summary,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'out': str(out), 'summary': summary}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
