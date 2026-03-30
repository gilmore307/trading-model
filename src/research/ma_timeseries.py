from __future__ import annotations

from typing import Any

from src.research.ma_family import build_ma_baseline_signals


def build_ma_equity_curve(
    rows: list[dict[str, Any]],
    *,
    fast_window: int,
    slow_window: int,
    threshold_enter_pct: float = 0.0,
    threshold_exit_pct: float = 0.0,
    ma_type: str = 'SMA',
    price_source: str = 'close',
    initial_equity: float = 1.0,
) -> list[dict[str, Any]]:
    signals = build_ma_baseline_signals(
        rows,
        fast_window=fast_window,
        slow_window=slow_window,
        threshold_enter_pct=threshold_enter_pct,
        threshold_exit_pct=threshold_exit_pct,
        ma_type=ma_type,
        price_source=price_source,
    )
    if not signals:
        return []

    equity = float(initial_equity)
    peak = equity
    position = 0
    curve: list[dict[str, Any]] = []
    curve.append({
        'ts': signals[0]['ts'],
        'timestamp': signals[0]['timestamp'],
        'equity': equity,
        'drawdown': 0.0,
        'position': 0,
        'action': signals[0]['action'],
        'close': signals[0]['close'],
    })
    for i in range(1, len(signals)):
        prev = signals[i - 1]
        row = signals[i]
        prev_close = float(prev['close'])
        close = float(row['close'])
        if prev_close > 0 and position != 0:
            equity *= (1.0 + (((close / prev_close) - 1.0) * position))
        desired_position = int(row.get('position', 0) or 0)
        position = desired_position
        peak = max(peak, equity)
        drawdown = 0.0 if peak <= 0 else (equity / peak) - 1.0
        curve.append({
            'ts': row['ts'],
            'timestamp': row['timestamp'],
            'equity': equity,
            'drawdown': drawdown,
            'position': position,
            'action': row['action'],
            'close': close,
        })
    return curve
