from src.research.donchian_family import backtest_donchian_variant, build_donchian_breakout_signals


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


def test_build_donchian_signals_can_enter_breakout():
    rows = _rows_from_closes([100, 101, 102, 103, 104, 106, 108, 109, 110])
    signals = build_donchian_breakout_signals(rows, breakout_window=3, exit_window=2, direction='long', confirm_bars=1, price_source='close')
    actions = [row['action'] for row in signals]
    assert 'enter_long' in actions


def test_backtest_donchian_variant_reports_equity_metrics():
    rows = _rows_from_closes([100, 101, 102, 103, 104, 106, 108, 107, 106, 105, 104, 103, 102, 101])
    result = backtest_donchian_variant(rows, breakout_window=3, exit_window=2, direction='both', confirm_bars=1, price_source='close')
    assert result['family'] == 'donchian_breakout'
    assert result['final_equity'] > 0.0
    assert result['total_return'] > -1.0
    assert result['signal_count'] >= 0
