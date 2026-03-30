from src.research.market_state import (
    build_crypto_market_state_dataset,
    build_ma_candidate_dataset,
    build_ma_performance_cube,
    build_market_state_rows,
    classify_market_state,
    parameter_region_for_variant,
    write_jsonl_rows,
)


def _candles(closes: list[float]):
    rows = []
    base_ts = 1700000000000
    for i, close in enumerate(closes):
        rows.append({
            'ts': base_ts + i * 60_000,
            'timestamp': f'2024-01-01T00:{i:02d}:00+00:00',
            'open': close - 0.5,
            'high': close + 1.0,
            'low': close - 1.0,
            'close': close,
            'vol': 100 + i,
            'volCcyQuote': 100000 + i * 1000,
        })
    return rows


def test_classify_market_state_supports_core_buckets():
    assert classify_market_state(trend_return=0.05, range_width=0.04, volatility=0.002, volume_burst=0.5) == 'trend'
    assert classify_market_state(trend_return=0.0, range_width=0.008, volatility=0.001, volume_burst=0.2) == 'compression'
    assert classify_market_state(trend_return=0.0, range_width=0.015, volatility=0.002, volume_burst=0.2) == 'range'
    assert classify_market_state(trend_return=0.0, range_width=0.03, volatility=0.005, volume_burst=2.5) == 'shock'


def test_build_market_state_rows_emits_features_and_labels():
    rows = build_market_state_rows(_candles([100 + i * 0.2 for i in range(120)]))
    assert len(rows) > 0
    sample = rows[-1]
    assert 'market_state' in sample
    assert 'trend_return_60' in sample
    assert 'range_width_30' in sample
    assert sample['market_state'] in {'trend', 'range', 'compression', 'shock', 'transition'}


def test_parameter_region_for_variant_groups_threshold_and_speed():
    assert parameter_region_for_variant('ema_close_50_200_te020_tx010').startswith('slow_windows')
    assert parameter_region_for_variant('ema_close_10_30_te010_tx000').endswith('mid_threshold')


def test_build_candidate_dataset_and_cube_work_together():
    candles = _candles([100, 101, 102, 103, 104, 103, 102, 101, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127, 128, 129, 130, 131,
                       132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161])
    states = build_market_state_rows(candles)
    variants = [
        {'fast_window': 5, 'slow_window': 20, 'threshold_enter_pct': 0.0005, 'threshold_exit_pct': 0.0, 'ma_type': 'EMA', 'price_source': 'close'},
        {'fast_window': 20, 'slow_window': 60, 'threshold_enter_pct': 0.001, 'threshold_exit_pct': 0.0005, 'ma_type': 'SMA', 'price_source': 'close'},
    ]
    dataset = build_ma_candidate_dataset(candles, variants, horizon_bars=5)
    assert len(dataset) > 0
    cube = build_ma_performance_cube(states, dataset)
    assert cube['summary']['cell_count'] > 0
    assert cube['rows'][0]['family'] == 'moving_average'


def test_build_crypto_market_state_dataset_aligns_funding_and_basis_asof():
    candles = _candles([100 + i * 0.2 for i in range(120)])
    funding_rows = [
        {'ts': candles[0]['ts'] - 60_000, 'fundingRate': 0.0001},
        {'ts': candles[80]['ts'], 'fundingRate': 0.0002},
    ]
    basis_rows = [
        {'ts': candles[70]['ts'], 'basisPct': 0.0015},
        {'ts': candles[75]['ts'], 'basisPct': 0.0018},
    ]
    dataset = build_crypto_market_state_dataset(candles, funding_rows=funding_rows, basis_rows=basis_rows)
    assert len(dataset) > 0
    near_sample = next(row for row in dataset if row['ts'] == candles[80]['ts'])
    assert near_sample['dataset_version'] == 'crypto_market_state_dataset_v1'
    assert near_sample['market_state'] in {'trend', 'range', 'compression', 'shock', 'transition'}
    assert near_sample['funding_rate'] == 0.0002
    assert near_sample['basis_pct'] == 0.0018
    assert near_sample['basis_age_min'] is not None

    late_sample = dataset[-1]
    assert late_sample['funding_rate'] == 0.0002
    assert late_sample['basis_pct'] is None


def test_write_jsonl_rows_writes_expected_lines(tmp_path):
    target = write_jsonl_rows([{'a': 1}, {'a': 2}], tmp_path / 'x.jsonl')
    lines = target.read_text(encoding='utf-8').splitlines()
    assert len(lines) == 2
