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
    assign_nearest_labels,
    build_timestamp_cluster_labels,
    feature_matrix_with_stats,
    kmeans,
    load_sampled_state_rows,
)

DEFAULT_STATE_DATASET = 'data/intermediate/market_state/crypto_market_state_dataset_v1.jsonl'
DEFAULT_OUT_JSONL = 'data/intermediate/market_state/unsupervised_market_state_labels_v1.jsonl'
DEFAULT_OUT_JSON = 'data/derived/unsupervised_market_state_labels_summary_v1.json'


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='Persist timestamp-level unsupervised market-state cluster labels.')
    parser.add_argument('--state-dataset', default=DEFAULT_STATE_DATASET)
    parser.add_argument('--out-jsonl', default=DEFAULT_OUT_JSONL)
    parser.add_argument('--out-json', default=DEFAULT_OUT_JSON)
    parser.add_argument('--sample-every', type=int, default=30, help='Subsample state rows to fit cluster centers, then assign every row to nearest center.')
    parser.add_argument('--clusters', type=int, default=5)
    parser.add_argument('--iterations', type=int, default=25)
    parser.add_argument('--seed', type=int, default=7)
    parser.add_argument('--symbol', default='BTC-USDT-SWAP')
    parser.add_argument('--batch-size', type=int, default=5000)
    return parser


def _iter_state_rows(path: Path, *, symbol: str | None):
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if symbol and row.get('symbol') != symbol:
                continue
            yield row



def _iter_batches(rows, batch_size: int):
    batch = []
    for row in rows:
        batch.append(row)
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch



def main() -> None:
    args = build_arg_parser().parse_args()
    sampled_rows = load_sampled_state_rows(args.state_dataset, args.sample_every)
    sampled_rows = [row for row in sampled_rows if not args.symbol or row.get('symbol') == args.symbol]
    x, means, stds = feature_matrix_with_stats(sampled_rows)
    sampled_labels, centers = kmeans(x, clusters=args.clusters, iterations=args.iterations, seed=args.seed)

    out_jsonl = Path(args.out_jsonl)
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    counts: dict[int, int] = {}
    persisted_row_count = 0
    centers_array = centers

    with out_jsonl.open('w', encoding='utf-8') as handle:
        for batch in _iter_batches(_iter_state_rows(Path(args.state_dataset), symbol=args.symbol), args.batch_size):
            batch_labels = assign_nearest_labels(batch, centers_array, feature_columns=FEATURE_COLUMNS, means=means, stds=stds)
            persisted_rows = build_timestamp_cluster_labels(
                batch,
                batch_labels,
                method='kmeans_numpy_baseline_nearest_center',
                feature_columns=FEATURE_COLUMNS,
                symbol=args.symbol,
            )
            for persisted in persisted_rows:
                handle.write(json.dumps(persisted, ensure_ascii=False) + '\n')
                label = int(persisted['cluster_id'])
                counts[label] = counts.get(label, 0) + 1
                persisted_row_count += 1

    summary = {
        'method': 'kmeans_numpy_baseline_nearest_center',
        'state_dataset': args.state_dataset,
        'symbol': args.symbol,
        'sample_every': args.sample_every,
        'clusters': args.clusters,
        'iterations': args.iterations,
        'seed': args.seed,
        'feature_columns': FEATURE_COLUMNS,
        'sampled_state_rows': len(sampled_rows),
        'persisted_label_rows': persisted_row_count,
        'cluster_counts': [{'cluster_id': cluster_id, 'row_count': row_count} for cluster_id, row_count in sorted(counts.items())],
        'centers': centers.tolist(),
        'labels_jsonl': str(out_jsonl),
    }
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    print(json.dumps({
        'out_jsonl': str(out_jsonl),
        'out_json': str(out_json),
        'sampled_state_rows': len(sampled_rows),
        'persisted_label_rows': persisted_row_count,
        'cluster_counts': summary['cluster_counts'],
        'sampled_label_rows': len(sampled_labels),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
