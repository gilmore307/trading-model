import json
from pathlib import Path

from src.runners.build_trading_overview_backtest import _trade_ledger_from_signals


def test_trade_ledger_extracts_closed_trade_from_signal_sequence():
    signals = [
        {'ts': 1, 'timestamp': 't1', 'close': 100.0, 'position': 0, 'action': 'hold'},
        {'ts': 2, 'timestamp': 't2', 'close': 101.0, 'position': 1, 'action': 'enter_long'},
        {'ts': 3, 'timestamp': 't3', 'close': 103.0, 'position': 1, 'action': 'hold'},
        {'ts': 4, 'timestamp': 't4', 'close': 104.0, 'position': 0, 'action': 'exit_to_flat'},
    ]
    ledger = _trade_ledger_from_signals(signals, {2: 'trend', 4: 'transition'}, family='moving_average', variant_id='v1')
    assert len(ledger) == 1
    assert ledger[0]['entry_state'] == 'trend'
    assert ledger[0]['exit_state'] == 'transition'
    assert ledger[0]['pnl_pct'] > 0
