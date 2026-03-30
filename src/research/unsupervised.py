from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

FEATURE_COLUMNS = [
    'return_5m',
    'return_15m',
    'return_1h',
    'trend_return_60',
    'range_width_30',
    'realized_vol_30',
    'volume_burst_z_30',
    'funding_rate',
    'basis_pct',
]


def safe_float(value: Any) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return 0.0
    if math.isnan(x) or math.isinf(x):
        return 0.0
    return x


def load_sampled_state_rows(path: str | Path, sample_every: int) -> list[dict[str, Any]]:
    rows = []
    with Path(path).open('r', encoding='utf-8') as handle:
        for idx, line in enumerate(handle):
            line = line.strip()
            if not line:
                continue
            if sample_every > 1 and idx % sample_every != 0:
                continue
            rows.append(json.loads(line))
    return rows


def feature_matrix(rows: list[dict[str, Any]], *, feature_columns: list[str] | None = None) -> np.ndarray:
    matrix, _, _ = feature_matrix_with_stats(rows, feature_columns=feature_columns)
    return matrix


def feature_matrix_with_stats(rows: list[dict[str, Any]], *, feature_columns: list[str] | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cols = feature_columns or FEATURE_COLUMNS
    matrix = np.array([[safe_float(row.get(col)) for col in cols] for row in rows], dtype=float)
    means = matrix.mean(axis=0)
    stds = matrix.std(axis=0)
    stds[stds == 0] = 1.0
    return (matrix - means) / stds, means, stds


def normalize_rows(rows: list[dict[str, Any]], means: np.ndarray, stds: np.ndarray, *, feature_columns: list[str] | None = None) -> np.ndarray:
    cols = feature_columns or FEATURE_COLUMNS
    matrix = np.array([[safe_float(row.get(col)) for col in cols] for row in rows], dtype=float)
    safe_stds = stds.copy()
    safe_stds[safe_stds == 0] = 1.0
    return (matrix - means) / safe_stds


def kmeans(x: np.ndarray, *, clusters: int, iterations: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    if len(x) < clusters:
        raise ValueError(f'not enough rows for clusters={clusters}')
    init_idx = rng.choice(len(x), size=clusters, replace=False)
    centers = x[init_idx].copy()
    labels = np.zeros(len(x), dtype=int)
    for _ in range(max(1, iterations)):
        distances = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
        labels = distances.argmin(axis=1)
        new_centers = centers.copy()
        for k in range(clusters):
            mask = labels == k
            if mask.any():
                new_centers[k] = x[mask].mean(axis=0)
            else:
                new_centers[k] = x[rng.integers(0, len(x))]
        if np.allclose(new_centers, centers):
            centers = new_centers
            break
        centers = new_centers
    return labels, centers


def assign_nearest_labels(rows: list[dict[str, Any]], centers: np.ndarray, *, feature_columns: list[str] | None = None, means: np.ndarray | None = None, stds: np.ndarray | None = None) -> list[int]:
    if means is not None and stds is not None:
        x = normalize_rows(rows, means, stds, feature_columns=feature_columns)
    else:
        x = feature_matrix(rows, feature_columns=feature_columns)
    distances = ((x[:, None, :] - centers[None, :, :]) ** 2).sum(axis=2)
    labels = distances.argmin(axis=1)
    return [int(x) for x in labels.tolist()]


def build_cluster_summary(rows: list[dict[str, Any]], labels: np.ndarray, *, feature_columns: list[str] | None = None) -> list[dict[str, Any]]:
    cols = feature_columns or FEATURE_COLUMNS
    grouped: dict[int, dict[str, Any]] = defaultdict(lambda: {'count': 0, 'sums': defaultdict(float)})
    for row, label in zip(rows, labels, strict=False):
        bucket = grouped[int(label)]
        bucket['count'] += 1
        for col in cols:
            bucket['sums'][col] += safe_float(row.get(col))
    out = []
    for label, bucket in sorted(grouped.items()):
        count = bucket['count']
        out.append({
            'cluster_id': label,
            'sample_count': count,
            'feature_means': {col: bucket['sums'][col] / count for col in cols},
        })
    return out


def evaluate_cluster_parameter_separation(rows: list[dict[str, Any]], labels: np.ndarray, utility_path: str | Path) -> list[dict[str, Any]]:
    cluster_by_ts = {int(row['ts']): int(label) for row, label in zip(rows, labels, strict=False)}
    agg: dict[tuple[int, str], dict[str, Any]] = defaultdict(lambda: {'count': 0, 'sum_utility': 0.0, 'positive': 0})
    with Path(utility_path).open('r', encoding='utf-8') as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            cluster_id = cluster_by_ts.get(int(row['ts']))
            parameter_region = row.get('parameter_region')
            utility = row.get('utility_1h')
            if cluster_id is None or parameter_region is None or utility is None:
                continue
            key = (cluster_id, parameter_region)
            agg[key]['count'] += 1
            agg[key]['sum_utility'] += float(utility)
            if float(utility) > 0:
                agg[key]['positive'] += 1
    out = []
    for (cluster_id, parameter_region), bucket in sorted(agg.items()):
        out.append({
            'cluster_id': cluster_id,
            'parameter_region': parameter_region,
            'sample_count': bucket['count'],
            'avg_utility_1h': bucket['sum_utility'] / bucket['count'],
            'positive_rate': bucket['positive'] / bucket['count'],
        })
    return out


def cluster_separation_summary(cube_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in cube_rows:
        by_cluster[int(row['cluster_id'])].append(row)
    out = []
    for cluster_id, rows in sorted(by_cluster.items()):
        ordered = sorted(rows, key=lambda row: row['avg_utility_1h'], reverse=True)
        best = ordered[0]
        worst = ordered[-1]
        out.append({
            'cluster_id': cluster_id,
            'best_region': best['parameter_region'],
            'best_avg_utility_1h': best['avg_utility_1h'],
            'worst_region': worst['parameter_region'],
            'worst_avg_utility_1h': worst['avg_utility_1h'],
            'spread_best_minus_worst': best['avg_utility_1h'] - worst['avg_utility_1h'],
        })
    return out


def build_timestamp_cluster_labels(rows: list[dict[str, Any]], labels: list[int], *, method: str, feature_columns: list[str] | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
    cols = feature_columns or FEATURE_COLUMNS
    out = []
    for row, label in zip(rows, labels, strict=False):
        out.append({
            'ts': row.get('ts'),
            'timestamp': row.get('timestamp'),
            'symbol': symbol or row.get('symbol'),
            'cluster_id': int(label),
            'method': method,
            'feature_columns': cols,
            'market_state': row.get('market_state'),
        })
    return out
