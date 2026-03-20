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
            'close': row['close'],
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'state': state,
            'action': action,
            'variant': f'ma_{fast_window}_{slow_window}',
        })
        if state is not None:
            prev_state = state
    return output


def summarize_ma_variant(rows: list[dict[str, Any]], *, fast_window: int, slow_window: int) -> dict[str, Any]:
    signals = build_ma_baseline_signals(rows, fast_window=fast_window, slow_window=slow_window)
    actionable = [row for row in signals if row['action'] != 'hold']
    spreads = [abs(float(row['fast_ma']) - float(row['slow_ma'])) for row in signals if row['fast_ma'] is not None and row['slow_ma'] is not None]
    return {
        'variant_id': f'ma_{fast_window}_{slow_window}',
        'fast_window': fast_window,
        'slow_window': slow_window,
        'signal_count': len(actionable),
        'avg_ma_spread': None if not spreads else mean(spreads),
    }


def summarize_ma_family(rows: list[dict[str, Any]], variants: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        summarize_ma_variant(rows, fast_window=int(variant['fast_window']), slow_window=int(variant['slow_window']))
        for variant in variants
    ]
