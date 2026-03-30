from __future__ import annotations

from collections.abc import Iterable
from statistics import mean
from typing import Any

from src.research.ma_family import DEFAULT_FEE_BPS, DEFAULT_SLIPPAGE_BPS, price_source_value


def _variant_id(*, breakout_window: int, exit_window: int, direction: str, confirm_bars: int, price_source: str) -> str:
    return f'donchian_{direction}_{price_source}_bw{breakout_window:03d}_ew{exit_window:03d}_cb{confirm_bars:02d}'


def build_donchian_breakout_signals(
    rows: list[dict[str, Any]],
    *,
    breakout_window: int,
    exit_window: int,
    direction: str = 'both',
    confirm_bars: int = 1,
    price_source: str = 'close',
) -> list[dict[str, Any]]:
    if breakout_window <= 1:
        raise ValueError('breakout_window must be > 1')
    if exit_window <= 0:
        raise ValueError('exit_window must be positive')
    if confirm_bars <= 0:
        raise ValueError('confirm_bars must be positive')

    prices = [price_source_value(row, price_source) for row in rows]
    highs = [float(row.get('high', row['close'])) for row in rows]
    lows = [float(row.get('low', row['close'])) for row in rows]

    out: list[dict[str, Any]] = []
    prev_position = 0
    breakout_streak_up = 0
    breakout_streak_down = 0

    for i, row in enumerate(rows):
        position = prev_position
        upper_breakout = None
        lower_breakout = None
        upper_exit = None
        lower_exit = None
        price = prices[i]

        if i >= breakout_window:
            upper_breakout = max(highs[i - breakout_window : i])
            lower_breakout = min(lows[i - breakout_window : i])
        if i >= exit_window:
            upper_exit = max(highs[i - exit_window : i])
            lower_exit = min(lows[i - exit_window : i])

        if upper_breakout is not None and price > upper_breakout:
            breakout_streak_up += 1
        else:
            breakout_streak_up = 0

        if lower_breakout is not None and price < lower_breakout:
            breakout_streak_down += 1
        else:
            breakout_streak_down = 0

        if prev_position == 0:
            if direction in {'both', 'long'} and breakout_streak_up >= confirm_bars:
                position = 1
            elif direction in {'both', 'short'} and breakout_streak_down >= confirm_bars:
                position = -1
        elif prev_position == 1:
            if direction in {'both', 'short'} and breakout_streak_down >= confirm_bars:
                position = -1
            elif lower_exit is not None and price < lower_exit:
                position = 0
        elif prev_position == -1:
            if direction in {'both', 'long'} and breakout_streak_up >= confirm_bars:
                position = 1
            elif upper_exit is not None and price > upper_exit:
                position = 0

        action = 'hold'
        if position != prev_position:
            if position == 1:
                action = 'enter_long'
            elif position == -1:
                action = 'enter_short'
            else:
                action = 'exit_to_flat'

        out.append({
            'ts': row['ts'],
            'timestamp': row['timestamp'],
            'close': float(row['close']),
            'basis_price': price,
            'price_source': price_source,
            'breakout_window': breakout_window,
            'exit_window': exit_window,
            'confirm_bars': confirm_bars,
            'direction': direction,
            'upper_breakout': upper_breakout,
            'lower_breakout': lower_breakout,
            'upper_exit': upper_exit,
            'lower_exit': lower_exit,
            'position': position,
            'action': action,
            'variant': _variant_id(
                breakout_window=breakout_window,
                exit_window=exit_window,
                direction=direction,
                confirm_bars=confirm_bars,
                price_source=price_source,
            ),
        })
        prev_position = position
    return out


def _turnover_units(previous_position: int, next_position: int) -> int:
    if previous_position == next_position:
        return 0
    if previous_position == 0 and next_position != 0:
        return 1
    if previous_position != 0 and next_position == 0:
        return 1
    return 2


def backtest_donchian_variant(
    rows: list[dict[str, Any]],
    *,
    breakout_window: int,
    exit_window: int,
    direction: str = 'both',
    confirm_bars: int = 1,
    price_source: str = 'close',
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    signals = build_donchian_breakout_signals(
        rows,
        breakout_window=breakout_window,
        exit_window=exit_window,
        direction=direction,
        confirm_bars=confirm_bars,
        price_source=price_source,
    )
    variant_id = _variant_id(
        breakout_window=breakout_window,
        exit_window=exit_window,
        direction=direction,
        confirm_bars=confirm_bars,
        price_source=price_source,
    )
    if not signals:
        return {
            'variant_id': variant_id,
            'family': 'donchian_breakout',
            'breakout_window': breakout_window,
            'exit_window': exit_window,
            'direction': direction,
            'confirm_bars': confirm_bars,
            'price_source': price_source,
            'signal_count': 0,
            'trade_count': 0,
            'turnover_count': 0,
            'initial_equity': initial_equity,
            'final_equity': initial_equity,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'win_rate': None,
            'avg_trade_return': None,
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
        'family': 'donchian_breakout',
        'breakout_window': breakout_window,
        'exit_window': exit_window,
        'direction': direction,
        'confirm_bars': confirm_bars,
        'price_source': price_source,
        'signal_count': len(actionable),
        'trade_count': len(trade_returns),
        'turnover_count': turnover_count,
        'initial_equity': initial_equity,
        'final_equity': equity,
        'total_return': (equity / initial_equity) - 1.0,
        'max_drawdown': max_drawdown,
        'win_rate': win_rate,
        'avg_trade_return': avg_trade_return,
    }


def summarize_donchian_family(rows: list[dict[str, Any]], variants: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    results = [
        backtest_donchian_variant(
            rows,
            breakout_window=int(variant['breakout_window']),
            exit_window=int(variant['exit_window']),
            direction=str(variant.get('direction', 'both')),
            confirm_bars=int(variant.get('confirm_bars', 1)),
            price_source=str(variant.get('price_source', 'close')),
        )
        for variant in variants
    ]
    results.sort(key=lambda row: (row['total_return'], -(abs(row['max_drawdown']))), reverse=True)
    return results
