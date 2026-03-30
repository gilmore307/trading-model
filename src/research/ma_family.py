from __future__ import annotations

import math
from collections.abc import Iterable
from statistics import mean
from typing import Any


DEFAULT_FEE_BPS = 0.0
DEFAULT_SLIPPAGE_BPS = 0.0


def price_source_value(row: dict[str, Any], source: str) -> float:
    open_ = float(row.get('open', row['close']))
    high = float(row.get('high', row['close']))
    low = float(row.get('low', row['close']))
    close = float(row['close'])
    if source == 'open':
        return open_
    if source == 'hl2':
        return (high + low) / 2.0
    if source == 'hlc3':
        return (high + low + close) / 3.0
    if source == 'ohlc4':
        return (open_ + high + low + close) / 4.0
    return close


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


def exponential_moving_average(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    if window <= 0:
        raise ValueError('window must be positive')
    alpha = 2.0 / (window + 1.0)
    ema = None
    for i, value in enumerate(values):
        if ema is None:
            ema = value
        else:
            ema = (alpha * value) + ((1.0 - alpha) * ema)
        out.append(None if i + 1 < window else ema)
    return out


def weighted_moving_average(values: list[float], window: int) -> list[float | None]:
    out: list[float | None] = []
    if window <= 0:
        raise ValueError('window must be positive')
    weights = list(range(1, window + 1))
    denom = sum(weights)
    for i in range(len(values)):
        if i + 1 < window:
            out.append(None)
            continue
        chunk = values[i - window + 1 : i + 1]
        out.append(sum(v * w for v, w in zip(chunk, weights, strict=False)) / denom)
    return out


def hull_moving_average(values: list[float], window: int) -> list[float | None]:
    if window <= 1:
        return values[:]  # type: ignore[return-value]
    half = max(1, window // 2)
    sqrt_window = max(1, int(math.sqrt(window)))
    wma_half = weighted_moving_average(values, half)
    wma_full = weighted_moving_average(values, window)
    diff_series: list[float] = []
    for a, b, v in zip(wma_half, wma_full, values, strict=False):
        diff_series.append(v if a is None or b is None else (2.0 * a) - b)
    return weighted_moving_average(diff_series, sqrt_window)


def compute_ma(values: list[float], window: int, ma_type: str) -> list[float | None]:
    ma_type = ma_type.upper()
    if ma_type == 'EMA':
        return exponential_moving_average(values, window)
    if ma_type == 'WMA':
        return weighted_moving_average(values, window)
    if ma_type == 'HMA':
        return hull_moving_average(values, window)
    return moving_average(values, window)


def _variant_id(*, fast_window: int, slow_window: int, threshold_enter_pct: float, threshold_exit_pct: float, ma_type: str, price_source: str) -> str:
    enter_bps = int(round(threshold_enter_pct * 10_000))
    exit_bps = int(round(threshold_exit_pct * 10_000))
    return f'{ma_type.lower()}_{price_source}_{fast_window}_{slow_window}_te{enter_bps:03d}_tx{exit_bps:03d}'


def build_ma_baseline_signals(
    rows: list[dict[str, Any]],
    *,
    fast_window: int,
    slow_window: int,
    threshold_enter_pct: float = 0.0,
    threshold_exit_pct: float = 0.0,
    ma_type: str = 'SMA',
    price_source: str = 'close',
) -> list[dict[str, Any]]:
    prices = [price_source_value(row, price_source) for row in rows]
    fast = compute_ma(prices, fast_window, ma_type)
    slow = compute_ma(prices, slow_window, ma_type)
    output: list[dict[str, Any]] = []
    prev_position = 0
    for row, basis_price, fast_ma, slow_ma in zip(rows, prices, fast, slow, strict=False):
        position = prev_position
        spread_pct = None
        if fast_ma is not None and slow_ma not in (None, 0):
            spread_pct = (float(fast_ma) - float(slow_ma)) / float(slow_ma)
            if prev_position == 0:
                if spread_pct >= threshold_enter_pct:
                    position = 1
                elif spread_pct <= -threshold_enter_pct:
                    position = -1
            elif prev_position == 1:
                if spread_pct <= -threshold_enter_pct:
                    position = -1
                elif spread_pct <= threshold_exit_pct:
                    position = 0
            elif prev_position == -1:
                if spread_pct >= threshold_enter_pct:
                    position = 1
                elif spread_pct >= -threshold_exit_pct:
                    position = 0
        else:
            position = 0
        action = 'hold'
        if position != prev_position:
            if position == 1:
                action = 'enter_long'
            elif position == -1:
                action = 'enter_short'
            elif position == 0:
                action = 'exit_to_flat'
        output.append({
            'ts': row['ts'],
            'timestamp': row['timestamp'],
            'close': float(row['close']),
            'basis_price': basis_price,
            'price_source': price_source,
            'ma_type': ma_type,
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'spread_pct': spread_pct,
            'position': position,
            'action': action,
            'threshold_enter_pct': threshold_enter_pct,
            'threshold_exit_pct': threshold_exit_pct,
            'variant': _variant_id(
                fast_window=fast_window,
                slow_window=slow_window,
                threshold_enter_pct=threshold_enter_pct,
                threshold_exit_pct=threshold_exit_pct,
                ma_type=ma_type,
                price_source=price_source,
            ),
        })
        prev_position = position
    return output


def _turnover_units(previous_position: int, next_position: int) -> int:
    if previous_position == next_position:
        return 0
    if previous_position == 0 and next_position != 0:
        return 1
    if previous_position != 0 and next_position == 0:
        return 1
    return 2


def backtest_ma_variant(
    rows: list[dict[str, Any]],
    *,
    fast_window: int,
    slow_window: int,
    threshold_enter_pct: float = 0.0,
    threshold_exit_pct: float = 0.0,
    ma_type: str = 'SMA',
    price_source: str = 'close',
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    signals = build_ma_baseline_signals(
        rows,
        fast_window=fast_window,
        slow_window=slow_window,
        threshold_enter_pct=threshold_enter_pct,
        threshold_exit_pct=threshold_exit_pct,
        ma_type=ma_type,
        price_source=price_source,
    )
    variant_id = _variant_id(
        fast_window=fast_window,
        slow_window=slow_window,
        threshold_enter_pct=threshold_enter_pct,
        threshold_exit_pct=threshold_exit_pct,
        ma_type=ma_type,
        price_source=price_source,
    )
    if not signals:
        return {
            'variant_id': variant_id,
            'fast_window': fast_window,
            'slow_window': slow_window,
            'threshold_enter_pct': threshold_enter_pct,
            'threshold_exit_pct': threshold_exit_pct,
            'ma_type': ma_type,
            'price_source': price_source,
            'signal_count': 0,
            'trade_count': 0,
            'turnover_count': 0,
            'fee_bps': fee_bps,
            'slippage_bps': slippage_bps,
            'initial_equity': initial_equity,
            'final_equity': initial_equity,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': None,
            'avg_trade_return': None,
            'avg_ma_spread': None,
        }

    equity = float(initial_equity)
    peak = equity
    max_drawdown = 0.0
    position = 0
    trade_returns: list[float] = []
    trade_entry_equity: float | None = None
    turnover_count = 0
    total_cost_rate = (fee_bps + slippage_bps) / 10_000.0

    actionable = [row for row in signals if row['action'] != 'hold']
    spreads = [abs(float(row['spread_pct'])) for row in signals if row['spread_pct'] is not None]

    for i in range(1, len(signals)):
        prev = signals[i - 1]
        row = signals[i]
        prev_close = float(prev['close'])
        close = float(row['close'])
        if prev_close > 0 and position != 0:
            ret = ((close / prev_close) - 1.0) * position
            equity *= (1.0 + ret)
            peak = max(peak, equity)
            max_drawdown = min(max_drawdown, (equity / peak) - 1.0)

        desired_position = int(row['position'])
        turnover_units = _turnover_units(position, desired_position)
        if turnover_units > 0:
            if total_cost_rate > 0:
                equity *= max(0.0, 1.0 - (total_cost_rate * turnover_units))
            turnover_count += turnover_units
            if position != 0 and trade_entry_equity is not None:
                trade_returns.append((equity / trade_entry_equity) - 1.0)
            trade_entry_equity = equity if desired_position != 0 else None
            position = desired_position

    if position != 0 and trade_entry_equity is not None:
        trade_returns.append((equity / trade_entry_equity) - 1.0)

    win_rate = None if not trade_returns else (sum(1 for x in trade_returns if x > 0) / len(trade_returns))
    avg_trade_return = None if not trade_returns else mean(trade_returns)

    return {
        'variant_id': variant_id,
        'fast_window': fast_window,
        'slow_window': slow_window,
        'threshold_enter_pct': threshold_enter_pct,
        'threshold_exit_pct': threshold_exit_pct,
        'ma_type': ma_type,
        'price_source': price_source,
        'signal_count': len(actionable),
        'trade_count': len(trade_returns),
        'turnover_count': turnover_count,
        'fee_bps': fee_bps,
        'slippage_bps': slippage_bps,
        'initial_equity': initial_equity,
        'final_equity': equity,
        'total_return': (equity / initial_equity) - 1.0,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'avg_trade_return': avg_trade_return,
        'avg_ma_spread': None if not spreads else mean(spreads),
    }


def summarize_ma_variant(
    rows: list[dict[str, Any]],
    *,
    fast_window: int,
    slow_window: int,
    threshold_enter_pct: float = 0.0,
    threshold_exit_pct: float = 0.0,
    ma_type: str = 'SMA',
    price_source: str = 'close',
) -> dict[str, Any]:
    return backtest_ma_variant(
        rows,
        fast_window=fast_window,
        slow_window=slow_window,
        threshold_enter_pct=threshold_enter_pct,
        threshold_exit_pct=threshold_exit_pct,
        ma_type=ma_type,
        price_source=price_source,
    )


def summarize_ma_family(rows: list[dict[str, Any]], variants: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    results = [
        summarize_ma_variant(
            rows,
            fast_window=int(variant['fast_window']),
            slow_window=int(variant['slow_window']),
            threshold_enter_pct=float(variant.get('threshold_enter_pct', variant.get('threshold_pct', 0.0))),
            threshold_exit_pct=float(variant.get('threshold_exit_pct', 0.0)),
            ma_type=str(variant.get('ma_type', 'SMA')),
            price_source=str(variant.get('price_source', 'close')),
        )
        for variant in variants
    ]
    results.sort(key=lambda row: (row['total_return'], -(abs(row['max_drawdown']))), reverse=True)
    return results
