from src.research.bollinger_family import backtest_bollinger_variant, build_bollinger_reversion_signals


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


def test_build_bollinger_signals_can_enter_reversion_trade():
    rows = _rows_from_closes([100, 100, 100, 100, 100, 95, 96, 97, 98, 99, 100])
    signals = build_bollinger_reversion_signals(rows, window=5, std_mult=1.5, exit_z=0.5, direction='long', price_source='close')
    actions = [row['action'] for row in signals]
    assert 'enter_long' in actions


def test_backtest_bollinger_variant_reports_equity_metrics():
    rows = _rows_from_closes([100, 100, 100, 100, 100, 95, 96, 97, 98, 99, 100, 101, 102])
    result = backtest_bollinger_variant(rows, window=5, std_mult=1.5, exit_z=0.5, direction='long', price_source='close')
    assert result['family'] == 'bollinger_reversion'
    assert result['final_equity'] > 0.0
    assert result['total_return'] > -1.0
