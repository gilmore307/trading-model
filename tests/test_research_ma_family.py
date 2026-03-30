from src.research.ma_family import backtest_ma_variant, build_ma_baseline_signals, price_source_value


def _rows_from_closes(closes: list[float]):
    rows = []
    base_ts = 1700000000000
    for i, close in enumerate(closes):
        rows.append({
            'ts': base_ts + i * 60_000,
            'timestamp': f'2024-01-01T00:{i:02d}:00+00:00',
            'open': float(close) - 0.5,
            'high': float(close) + 1.0,
            'low': float(close) - 1.0,
            'close': float(close),
        })
    return rows


def test_price_source_value_supports_multiple_inputs():
    row = {'open': 99.0, 'high': 102.0, 'low': 98.0, 'close': 100.0}
    assert price_source_value(row, 'close') == 100.0
    assert price_source_value(row, 'open') == 99.0
    assert price_source_value(row, 'hl2') == 100.0
    assert round(price_source_value(row, 'hlc3'), 6) == round((102.0 + 98.0 + 100.0) / 3.0, 6)
    assert round(price_source_value(row, 'ohlc4'), 6) == round((99.0 + 102.0 + 98.0 + 100.0) / 4.0, 6)


def test_build_ma_signals_supports_flat_zone_threshold():
    rows = _rows_from_closes([100, 100.1, 100.2, 100.21, 100.22, 100.21, 100.2, 100.19, 100.18, 100.17])
    signals = build_ma_baseline_signals(rows, fast_window=2, slow_window=3, threshold_enter_pct=0.001, threshold_exit_pct=0.0005, ma_type='EMA', price_source='hlc3')
    positions = [row['position'] for row in signals if row['fast_ma'] is not None and row['slow_ma'] is not None]
    assert 0 in positions


def test_backtest_ma_variant_reports_equity_metrics_without_forced_costs():
    rows = _rows_from_closes([100, 101, 102, 103, 102, 101, 100, 99, 100, 101, 102, 103])
    result = backtest_ma_variant(rows, fast_window=2, slow_window=3, threshold_enter_pct=0.0, threshold_exit_pct=0.0, ma_type='SMA', price_source='close')
    assert result['trade_count'] >= 1
    assert result['initial_equity'] == 1.0
    assert result['final_equity'] > 0.0
    assert result['total_return'] > -1.0


def test_hysteresis_thresholds_expose_parameter_metadata():
    rows = _rows_from_closes([100, 101, 102, 103, 102, 101, 100, 99, 100, 101, 102, 103])
    filtered = backtest_ma_variant(rows, fast_window=2, slow_window=3, threshold_enter_pct=0.002, threshold_exit_pct=0.001, ma_type='WMA', price_source='ohlc4')
    assert filtered['threshold_enter_pct'] == 0.002
    assert filtered['threshold_exit_pct'] == 0.001
    assert filtered['ma_type'] == 'WMA'
    assert filtered['price_source'] == 'ohlc4'
    assert filtered['signal_count'] >= 0


def test_exit_threshold_can_flatten_without_immediate_reversal():
    rows = _rows_from_closes([100, 102, 104, 106, 105, 104.5, 104.3, 104.2, 104.1, 104.0])
    signals = build_ma_baseline_signals(rows, fast_window=2, slow_window=4, threshold_enter_pct=0.01, threshold_exit_pct=0.002, ma_type='SMA', price_source='close')
    actions = [row['action'] for row in signals]
    assert 'enter_long' in actions
    assert 'exit_to_flat' in actions
