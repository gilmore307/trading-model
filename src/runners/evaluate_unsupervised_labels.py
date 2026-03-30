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
DEFAULT_UTILITY = 'data/intermediate/parameter_utility/strategy_parameter_utility_dataset_v1.jsonl'
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


def _evaluate(cluster_by_ts: dict[int, int], utility_path: Path) -> tuple[list[dict], list[dict], list[dict], list[dict], dict]:
    region_agg: dict[tuple[int, str], dict] = defaultdict(lambda: {'count': 0, 'sum_utility': 0.0, 'positive': 0})
    family_agg: dict[tuple[int, str], dict] = defaultdict(lambda: {'count': 0, 'sum_utility': 0.0, 'positive': 0})
    variant_agg: dict[tuple[int, str, str], dict] = defaultdict(lambda: {'count': 0, 'sum_utility': 0.0, 'positive': 0})
    matched_rows = 0
    with utility_path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            ts = row.get('ts')
            parameter_region = row.get('parameter_region')
            family = row.get('family')
            variant_id = row.get('variant_id')
            utility = row.get('utility_1h')
            if ts is None or parameter_region is None or utility is None:
                continue
            cluster_id = cluster_by_ts.get(int(ts))
            if cluster_id is None:
                continue
            matched_rows += 1
            region_key = (cluster_id, str(parameter_region))
            region_agg[region_key]['count'] += 1
            region_agg[region_key]['sum_utility'] += float(utility)
            if float(utility) > 0:
                region_agg[region_key]['positive'] += 1
            if family is not None:
                family_key = (cluster_id, str(family))
                family_agg[family_key]['count'] += 1
                family_agg[family_key]['sum_utility'] += float(utility)
                if float(utility) > 0:
                    family_agg[family_key]['positive'] += 1
            if family is not None and variant_id is not None:
                variant_key = (cluster_id, str(family), str(variant_id))
                variant_agg[variant_key]['count'] += 1
                variant_agg[variant_key]['sum_utility'] += float(utility)
                if float(utility) > 0:
                    variant_agg[variant_key]['positive'] += 1

    cube_rows = []
    by_cluster: dict[int, list[dict]] = defaultdict(list)
    for (cluster_id, parameter_region), bucket in sorted(region_agg.items()):
        row = {
            'cluster_id': cluster_id,
            'parameter_region': parameter_region,
            'sample_count': bucket['count'],
            'avg_utility_1h': bucket['sum_utility'] / bucket['count'],
            'positive_rate': bucket['positive'] / bucket['count'],
        }
        cube_rows.append(row)
        by_cluster[cluster_id].append(row)

    family_cube_rows = []
    for (cluster_id, family), bucket in sorted(family_agg.items()):
        family_cube_rows.append({
            'cluster_id': cluster_id,
            'family': family,
            'sample_count': bucket['count'],
            'avg_utility_1h': bucket['sum_utility'] / bucket['count'],
            'positive_rate': bucket['positive'] / bucket['count'],
        })

    variant_cube_rows = []
    for (cluster_id, family, variant_id), bucket in sorted(variant_agg.items()):
        variant_cube_rows.append({
            'cluster_id': cluster_id,
            'family': family,
            'variant_id': variant_id,
            'sample_count': bucket['count'],
            'avg_utility_1h': bucket['sum_utility'] / bucket['count'],
            'positive_rate': bucket['positive'] / bucket['count'],
        })

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
        family_rows = [row for row in family_cube_rows if int(row['cluster_id']) == cluster_id]
        variant_rows = [row for row in variant_cube_rows if int(row['cluster_id']) == cluster_id]
        best_family = sorted(family_rows, key=lambda row: row['avg_utility_1h'], reverse=True)[0] if family_rows else None
        best_variant = sorted(variant_rows, key=lambda row: row['avg_utility_1h'], reverse=True)[0] if variant_rows else None
        separation_summary.append({
            'cluster_id': cluster_id,
            'cluster_sample_count': cluster_sample_count,
            'best_region': best['parameter_region'],
            'best_avg_utility_1h': best['avg_utility_1h'],
            'worst_region': worst['parameter_region'],
            'worst_avg_utility_1h': worst['avg_utility_1h'],
            'spread_best_minus_worst': spread,
            'best_family': None if best_family is None else best_family['family'],
            'best_family_avg_utility_1h': None if best_family is None else best_family['avg_utility_1h'],
            'best_variant': None if best_variant is None else best_variant['variant_id'],
            'best_variant_family': None if best_variant is None else best_variant['family'],
            'best_variant_avg_utility_1h': None if best_variant is None else best_variant['avg_utility_1h'],
        })

    summary = {
        'matched_utility_rows': matched_rows,
        'cube_cell_count': len(cube_rows),
        'cluster_count': len(by_cluster),
        'family_cube_cell_count': len(family_cube_rows),
        'variant_cube_cell_count': len(variant_cube_rows),
        'weighted_avg_cluster_spread': (weighted_spread_sum / weighted_count_sum) if weighted_count_sum else 0.0,
    }
    return cube_rows, family_cube_rows, variant_cube_rows, separation_summary, summary


def main() -> None:
    args = build_arg_parser().parse_args()
    cluster_by_ts = _load_cluster_by_ts(Path(args.labels), args.symbol)
    cube_rows, family_cube_rows, variant_cube_rows, separation_summary, summary = _evaluate(cluster_by_ts, Path(args.utility_dataset))
    output = {
        'labels': args.labels,
        'utility_dataset': args.utility_dataset,
        'symbol': args.symbol,
        'summary': summary,
        'cluster_parameter_region_cube': cube_rows,
        'cluster_family_cube': family_cube_rows,
        'cluster_variant_cube': variant_cube_rows,
        'cluster_separation_summary': separation_summary,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'out': str(out), 'summary': summary}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
