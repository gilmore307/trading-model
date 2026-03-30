from __future__ import annotations

from collections.abc import Iterable
from statistics import mean, pstdev
from typing import Any

from src.research.ma_family import DEFAULT_FEE_BPS, DEFAULT_SLIPPAGE_BPS, price_source_value


def _variant_id(*, window: int, std_mult: float, exit_z: float, direction: str, price_source: str) -> str:
    mult_tag = int(round(std_mult * 10))
    exit_tag = int(round(exit_z * 10))
    return f'bollinger_{direction}_{price_source}_w{window:03d}_m{mult_tag:02d}_e{exit_tag:02d}'


def _rolling_mean_std(values: list[float], window: int) -> tuple[list[float | None], list[float | None]]:
    means: list[float | None] = []
    stds: list[float | None] = []
    for i in range(len(values)):
        if i + 1 < window:
            means.append(None)
            stds.append(None)
            continue
        chunk = values[i - window + 1 : i + 1]
        means.append(mean(chunk))
        stds.append(pstdev(chunk) if len(chunk) >= 2 else 0.0)
    return means, stds


def build_bollinger_reversion_signals(
    rows: list[dict[str, Any]],
    *,
    window: int,
    std_mult: float = 2.0,
    exit_z: float = 0.5,
    direction: str = 'both',
    price_source: str = 'close',
) -> list[dict[str, Any]]:
    prices = [price_source_value(row, price_source) for row in rows]
    means, stds = _rolling_mean_std(prices, window)
    out: list[dict[str, Any]] = []
    prev_position = 0

    for row, price, mid, std in zip(rows, prices, means, stds, strict=False):
        position = prev_position
        z_score = None
        upper_band = None
        lower_band = None
        if mid is not None and std is not None:
            upper_band = mid + std_mult * std
            lower_band = mid - std_mult * std
            if std > 0:
                z_score = (price - mid) / std
            else:
                z_score = 0.0
            if prev_position == 0:
                if direction in {'both', 'long'} and lower_band is not None and price < lower_band:
                    position = 1
                elif direction in {'both', 'short'} and upper_band is not None and price > upper_band:
                    position = -1
            elif prev_position == 1:
                if z_score is not None and z_score >= -exit_z:
                    position = 0
            elif prev_position == -1:
                if z_score is not None and z_score <= exit_z:
                    position = 0
        else:
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
            'window': window,
            'std_mult': std_mult,
            'exit_z': exit_z,
            'direction': direction,
            'mid_band': mid,
            'upper_band': upper_band,
            'lower_band': lower_band,
            'z_score': z_score,
            'position': position,
            'action': action,
            'variant': _variant_id(window=window, std_mult=std_mult, exit_z=exit_z, direction=direction, price_source=price_source),
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


def backtest_bollinger_variant(
    rows: list[dict[str, Any]],
    *,
    window: int,
    std_mult: float = 2.0,
    exit_z: float = 0.5,
    direction: str = 'both',
    price_source: str = 'close',
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    initial_equity: float = 1.0,
) -> dict[str, Any]:
    signals = build_bollinger_reversion_signals(
        rows,
        window=window,
        std_mult=std_mult,
        exit_z=exit_z,
        direction=direction,
        price_source=price_source,
    )
    variant_id = _variant_id(window=window, std_mult=std_mult, exit_z=exit_z, direction=direction, price_source=price_source)
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
        'family': 'bollinger_reversion',
        'window': window,
        'std_mult': std_mult,
        'exit_z': exit_z,
        'direction': direction,
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


def summarize_bollinger_family(rows: list[dict[str, Any]], variants: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    results = [
        backtest_bollinger_variant(
            rows,
            window=int(variant['window']),
            std_mult=float(variant.get('std_mult', 2.0)),
            exit_z=float(variant.get('exit_z', 0.5)),
            direction=str(variant.get('direction', 'both')),
            price_source=str(variant.get('price_source', 'close')),
        )
        for variant in variants
    ]
    results.sort(key=lambda row: (row['total_return'], -(abs(row['max_drawdown']))), reverse=True)
    return results
