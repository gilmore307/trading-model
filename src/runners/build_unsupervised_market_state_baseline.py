from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.research.unsupervised import (
    FEATURE_COLUMNS,
    build_cluster_summary,
    cluster_separation_summary,
    evaluate_cluster_parameter_separation,
    feature_matrix,
    kmeans,
    load_sampled_state_rows,
)

DEFAULT_STATE_DATASET = 'data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl'
DEFAULT_UTILITY_DATASET = 'data/intermediate/parameter_utility/ma_parameter_utility_dataset_v1.jsonl'
DEFAULT_OUT = 'data/derived/unsupervised_market_state_baseline_v1.json'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Run a simple unsupervised market-state clustering baseline and evaluate MA parameter-region separation.')
    parser.add_argument('--state-dataset', default=DEFAULT_STATE_DATASET)
    parser.add_argument('--utility-dataset', default=DEFAULT_UTILITY_DATASET)
    parser.add_argument('--out', default=DEFAULT_OUT)
    parser.add_argument('--sample-every', type=int, default=30, help='Subsample market-state rows before clustering.')
    parser.add_argument('--clusters', type=int, default=5)
    parser.add_argument('--iterations', type=int, default=25)
    parser.add_argument('--seed', type=int, default=7)
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    rows = load_sampled_state_rows(args.state_dataset, args.sample_every)
    x = feature_matrix(rows)
    labels, centers = kmeans(x, clusters=args.clusters, iterations=args.iterations, seed=args.seed)
    cluster_summary = build_cluster_summary(rows, labels)
    cube_rows = evaluate_cluster_parameter_separation(rows, labels, args.utility_dataset)
    separation_summary = cluster_separation_summary(cube_rows)

    output = {
        'method': 'kmeans_numpy_baseline',
        'state_dataset': args.state_dataset,
        'utility_dataset': args.utility_dataset,
        'sample_every': args.sample_every,
        'clusters': args.clusters,
        'iterations': args.iterations,
        'seed': args.seed,
        'feature_columns': FEATURE_COLUMNS,
        'sampled_state_rows': len(rows),
        'cluster_summary': cluster_summary,
        'cluster_parameter_region_cube': cube_rows,
        'cluster_separation_summary': separation_summary,
    }
    Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({
        'output': args.out,
        'sampled_state_rows': len(rows),
        'cluster_count': len(cluster_summary),
        'cube_rows': len(cube_rows),
        'cluster_separation_summary': separation_summary,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
