from __future__ import annotations

from collections.abc import Iterable
from statistics import mean
from typing import Any


def moving_average(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    if window <= 0:
        raise ValueError('window must be positive')
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= window:
            running -= values[i - window]
        if i + 1 < window:
            out.append(None)
        else:
            out.append(running / window)
    return out


def build_ma_baseline_signals(rows: list[dict[str, Any]], *, fast_window: int, slow_window: int) -> list[dict[str, Any]]:
    closes = [float(row['close']) for row in rows]
    fast = moving_average(closes, fast_window)
    slow = moving_average(closes, slow_window)
    output: list[dict[str, Any]] = []
    prev_state: str | None = None
    for row, fast_ma, slow_ma in zip(rows, fast, slow, strict=False):
        state = None
        action = 'hold'
        if fast_ma is not None and slow_ma is not None:
            state = 'bullish' if fast_ma > slow_ma else 'bearish' if fast_ma < slow_ma else 'flat'
            if prev_state is not None and state != prev_state:
                action = 'enter_long' if state == 'bullish' else 'enter_short' if state == 'bearish' else 'hold'
        output.append({
            'ts': row['ts'],
            'timestamp': row['timestamp'],
            'close': float(row['close']),
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'state': state,
            'action': action,
            'variant': f'ma_{fast_window}_{slow_window}',
        })
        if state is not None:
            prev_state = state
    return output


def backtest_ma_variant(rows: list[dict[str, Any]], *, fast_window: int, slow_window: int) -> dict[str, Any]:
    signals = build_ma_baseline_signals(rows, fast_window=fast_window, slow_window=slow_window)
    if not signals:
        return {
            'variant_id': f'ma_{fast_window}_{slow_window}',
            'fast_window': fast_window,
            'slow_window': slow_window,
            'signal_count': 0,
            'trade_count': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': None,
            'avg_trade_return': None,
            'avg_ma_spread': None,
        }

    position = 0
    equity = 1.0
    peak = 1.0
    max_drawdown = 0.0
    trade_returns: list[float] = []
    current_trade_entry_equity: float | None = None

    actionable = [row for row in signals if row['action'] != 'hold']
    spreads = [abs(float(row['fast_ma']) - float(row['slow_ma'])) for row in signals if row['fast_ma'] is not None and row['slow_ma'] is not None]

    for i in range(1, len(signals)):
        prev = signals[i - 1]
        row = signals[i]
        if row['action'] == 'enter_long':
            if position != 0 and current_trade_entry_equity is not None:
                trade_returns.append((equity / current_trade_entry_equity) - 1.0)
            position = 1
            current_trade_entry_equity = equity
        elif row['action'] == 'enter_short':
            if position != 0 and current_trade_entry_equity is not None:
                trade_returns.append((equity / current_trade_entry_equity) - 1.0)
            position = -1
            current_trade_entry_equity = equity

        prev_close = float(prev['close'])
        close = float(row['close'])
        if prev_close > 0 and position != 0:
            ret = ((close / prev_close) - 1.0) * position
            equity *= (1.0 + ret)
            peak = max(peak, equity)
            drawdown = (equity / peak) - 1.0
            max_drawdown = min(max_drawdown, drawdown)

    if position != 0 and current_trade_entry_equity is not None:
        trade_returns.append((equity / current_trade_entry_equity) - 1.0)

    win_rate = None if not trade_returns else (sum(1 for x in trade_returns if x > 0) / len(trade_returns))
    avg_trade_return = None if not trade_returns else mean(trade_returns)

    return {
        'variant_id': f'ma_{fast_window}_{slow_window}',
        'fast_window': fast_window,
        'slow_window': slow_window,
        'signal_count': len(actionable),
        'trade_count': len(trade_returns),
        'total_return': equity - 1.0,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'avg_trade_return': avg_trade_return,
        'avg_ma_spread': None if not spreads else mean(spreads),
    }


def summarize_ma_variant(rows: list[dict[str, Any]], *, fast_window: int, slow_window: int) -> dict[str, Any]:
    return backtest_ma_variant(rows, fast_window=fast_window, slow_window=slow_window)


def summarize_ma_family(rows: list[dict[str, Any]], variants: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    results = [
        summarize_ma_variant(rows, fast_window=int(variant['fast_window']), slow_window=int(variant['slow_window']))
        for variant in variants
    ]
    results.sort(key=lambda row: (row['total_return'], -(abs(row['max_drawdown']))), reverse=True)
    return results
