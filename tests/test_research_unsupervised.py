import numpy as np

from src.research.unsupervised import (
    FEATURE_COLUMNS,
    assign_nearest_labels,
    build_timestamp_cluster_labels,
    feature_matrix,
    kmeans,
)


def _row(ts: int, ret: float, state: str = 'trend'):
    return {
        'ts': ts,
        'timestamp': f'2024-01-01T00:00:{ts % 60:02d}+00:00',
        'symbol': 'BTC-USDT-SWAP',
        'market_state': state,
        'return_5m': ret,
        'return_15m': ret * 2,
        'return_1h': ret * 4,
        'trend_return_60': ret * 4,
        'range_width_30': abs(ret) * 10 + 0.01,
        'realized_vol_30': abs(ret) * 2 + 0.001,
        'volume_burst_z_30': 1.0 if ret > 0 else -1.0,
        'funding_rate': 0.0001 if ret > 0 else -0.0001,
        'basis_pct': 0.0002 if ret > 0 else -0.0002,
    }


def test_assign_nearest_labels_projects_full_rows_to_fitted_centers():
    sampled_rows = [
        _row(1, -0.02, 'shock'),
        _row(2, -0.015, 'shock'),
        _row(3, 0.02, 'trend'),
        _row(4, 0.025, 'trend'),
    ]
    x = feature_matrix(sampled_rows)
    sampled_labels, centers = kmeans(x, clusters=2, iterations=20, seed=7)
    assert len(np.unique(sampled_labels)) == 2

    full_rows = sampled_rows + [_row(5, -0.018, 'shock'), _row(6, 0.03, 'trend')]
    full_labels = assign_nearest_labels(full_rows, centers)
    assert len(full_labels) == len(full_rows)
    assert full_labels[0] == full_labels[1]
    assert full_labels[2] == full_labels[3]
    assert full_labels[4] == full_labels[0]
    assert full_labels[5] == full_labels[2]


def test_build_timestamp_cluster_labels_preserves_ts_and_symbol():
    rows = [_row(10, 0.01), _row(11, -0.01, 'range')]
    labels = [1, 0]
    out = build_timestamp_cluster_labels(rows, labels, method='unit-test', feature_columns=FEATURE_COLUMNS)
    assert out[0]['ts'] == 10
    assert out[0]['cluster_id'] == 1
    assert out[0]['symbol'] == 'BTC-USDT-SWAP'
    assert out[1]['market_state'] == 'range'
    assert out[1]['feature_columns'] == FEATURE_COLUMNS
