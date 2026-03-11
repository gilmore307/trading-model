from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean, pstdev

from src.features.models import FeatureSnapshot
from src.market.models import Bar, MarketSnapshot


def _closes(bars: list[Bar], n: int | None = None) -> list[float]:
    rows = [float(b.close) for b in bars]
    return rows[-n:] if n else rows


def _ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    k = 2 / (period + 1)
    ema = mean(values[:period])
    for v in values[period:]:
        ema = (v * k) + (ema * (1 - k))
    return ema


def _ema_slope(values: list[float], period: int, lookback: int = 3) -> float | None:
    if len(values) < period + lookback:
        return None
    now = _ema(values, period)
    prev = _ema(values[:-lookback], period)
    if now is None or prev is None:
        return None
    return now - prev


def _adx_like(bars: list[Bar], period: int = 14) -> float | None:
    if len(bars) < period + 1:
        return None
    trs = []
    plus_dm = []
    minus_dm = []
    for prev, curr in zip(bars[:-1], bars[1:]):
        up = curr.high - prev.high
        down = prev.low - curr.low
        plus_dm.append(max(up, 0.0) if up > down else 0.0)
        minus_dm.append(max(down, 0.0) if down > up else 0.0)
        tr = max(curr.high - curr.low, abs(curr.high - prev.close), abs(curr.low - prev.close))
        trs.append(tr)
    trs = trs[-period:]
    plus_dm = plus_dm[-period:]
    minus_dm = minus_dm[-period:]
    atr = sum(trs) / period if period else 0.0
    if atr == 0:
        return 0.0
    plus_di = 100 * ((sum(plus_dm) / period) / atr)
    minus_di = 100 * ((sum(minus_dm) / period) / atr)
    denom = plus_di + minus_di
    if denom == 0:
        return 0.0
    return 100 * abs(plus_di - minus_di) / denom


def _bollinger_bandwidth_pct(values: list[float], period: int = 20, mult: float = 2.0) -> float | None:
    if len(values) < period:
        return None
    window = values[-period:]
    mid = mean(window)
    sd = pstdev(window)
    if mid == 0:
        return None
    upper = mid + mult * sd
    lower = mid - mult * sd
    return (upper - lower) / mid


def _realized_vol(values: list[float], period: int = 20) -> float | None:
    if len(values) < period + 1:
        return None
    rets = []
    for a, b in zip(values[-period - 1 : -1], values[-period:]):
        if a <= 0 or b <= 0:
            continue
        rets.append(math.log(b / a))
    if len(rets) < max(5, period // 2):
        return None
    return pstdev(rets)


def _vwap(bars: list[Bar], period: int = 20) -> float | None:
    if len(bars) < period:
        return None
    window = bars[-period:]
    numer = 0.0
    denom = 0.0
    for b in window:
        typical = (b.high + b.low + b.close) / 3.0
        vol = b.volume or 0.0
        numer += typical * vol
        denom += vol
    if denom == 0:
        return None
    return numer / denom


def _zscore(values: list[float]) -> float | None:
    if len(values) < 5:
        return None
    mu = mean(values)
    sd = pstdev(values)
    if sd == 0:
        return 0.0
    return (values[-1] - mu) / sd


def _percentile_rank(series: list[float], value: float | None) -> float | None:
    if value is None or not series:
        return None
    below = sum(1 for x in series if x <= value)
    return below / len(series)


def _accel(series: list[float], short: int = 3, long: int = 12) -> float | None:
    if len(series) < max(short, long) or long <= short:
        return None
    short_avg = mean(series[-short:])
    long_avg = mean(series[-long:])
    if long_avg == 0:
        return None
    return (short_avg - long_avg) / abs(long_avg)


@dataclass(slots=True)
class FeatureEngine:
    trend_timeframe: str = "15m"
    range_timeframe: str = "15m"
    event_timeframe: str = "1m"
    layer_name: str = "generic"

    def build(self, snapshot: MarketSnapshot) -> FeatureSnapshot:
        event_bars = snapshot.bars.get(self.event_timeframe, [])
        main_bars = snapshot.bars.get(self.range_timeframe, []) or event_bars
        trend_bars = snapshot.bars.get(self.trend_timeframe, []) or main_bars
        closes = _closes(main_bars)
        trend_closes = _closes(trend_bars)
        event_closes = _closes(event_bars)
        last_price = snapshot.ticker.last if snapshot.ticker and snapshot.ticker.last is not None else (closes[-1] if closes else None)

        bandwidth = _bollinger_bandwidth_pct(closes, period=20)
        realized_vol = _realized_vol(closes, period=20)
        vol_history = []
        if len(closes) >= 60:
            for i in range(20, len(closes)):
                x = _realized_vol(closes[: i + 1], period=20)
                if x is not None:
                    vol_history.append(x)
        vwap = _vwap(main_bars, period=20)
        vwap_dev_z = None
        if vwap is not None and last_price is not None and vwap != 0:
            deviations = []
            for b in main_bars[-20:]:
                deviations.append((b.close - vwap) / vwap)
            if deviations:
                z = _zscore(deviations)
                vwap_dev_z = z

        liquidation_notional = sum(float(x.notional or 0.0) for x in snapshot.recent_liquidations[-20:]) if snapshot.recent_liquidations else 0.0
        liquidation_count = len(snapshot.recent_liquidations)
        trade_sizes = [float(x.size) for x in snapshot.recent_trades[-50:]] if snapshot.recent_trades else []
        trade_notional = sum(float(x.price) * float(x.size) for x in snapshot.recent_trades[-50:]) if snapshot.recent_trades else 0.0
        event_realized_vol = _realized_vol(event_closes, period=20) if event_closes else None
        event_vol_history = []
        if len(event_closes) >= 60:
            for i in range(20, len(event_closes)):
                x = _realized_vol(event_closes[: i + 1], period=20)
                if x is not None:
                    event_vol_history.append(x)
        imbalance = None
        if snapshot.top and snapshot.top.bid_size is not None and snapshot.top.ask_size is not None:
            denom = float(snapshot.top.bid_size) + float(snapshot.top.ask_size)
            if denom > 0:
                imbalance = (float(snapshot.top.bid_size) - float(snapshot.top.ask_size)) / denom

        funding_series = [float(x.funding_rate) for x in snapshot.derivatives_history if x.funding_rate is not None]
        oi_series = [float(x.open_interest) for x in snapshot.derivatives_history if x.open_interest is not None]
        basis_series = [float(x.basis_pct) for x in snapshot.derivatives_history if x.basis_pct is not None]

        realized_vol_pct = _percentile_rank(event_vol_history if self.layer_name == 'event_1m' else vol_history, event_realized_vol if self.layer_name == 'event_1m' else realized_vol)
        funding_pctile = None
        oi_accel = None
        basis_deviation_pct = None
        if snapshot.derivatives is not None:
            funding_pctile = _percentile_rank(funding_series, snapshot.derivatives.funding_rate) if funding_series else None
            oi_accel = _accel(oi_series, short=3, long=12) if len(oi_series) >= 12 else None
            if snapshot.derivatives.basis_pct is not None:
                basis_deviation_pct = snapshot.derivatives.basis_pct
                if len(basis_series) >= 5:
                    basis_mean = mean(basis_series)
                    basis_deviation_pct = snapshot.derivatives.basis_pct - basis_mean

        liquidation_score = min(1.0, liquidation_notional / 100000.0) if liquidation_notional else 0.0
        if liquidation_count >= 3:
            liquidation_score = max(liquidation_score, min(1.0, liquidation_count / 10.0))
        trade_burst_score = 0.0
        if trade_notional:
            trade_burst_score = min(1.0, trade_notional / 5000000.0)
        if len(trade_sizes) >= 20:
            trade_burst_score = max(trade_burst_score, min(1.0, len(trade_sizes) / 50.0))

        return FeatureSnapshot(
            ts=snapshot.updated_at,
            symbol=snapshot.symbol,
            layer=self.layer_name,
            source_timeframe=self.event_timeframe if self.layer_name == 'event_1m' else self.range_timeframe,
            last_price=last_price,
            adx=_adx_like(trend_bars, period=14),
            ema20_slope=_ema_slope(trend_closes, 20, lookback=3),
            ema50_slope=_ema_slope(trend_closes, 50, lookback=3),
            bollinger_bandwidth_pct=bandwidth,
            realized_vol_pct=realized_vol_pct if realized_vol_pct is not None else (event_realized_vol if self.layer_name == 'event_1m' else realized_vol),
            vwap_deviation_z=vwap_dev_z,
            funding_pctile=funding_pctile,
            oi_accel=oi_accel,
            basis_deviation_pct=basis_deviation_pct,
            liquidation_spike_score=liquidation_score,
            orderbook_imbalance=imbalance,
            trade_burst_score=trade_burst_score,
            meta={
                'bars_main': float(len(main_bars)),
                'bars_trend': float(len(trend_bars)),
                'bars_event': float(len(event_bars)),
                'trade_count_window': float(len(trade_sizes)),
                'trade_notional_window': float(trade_notional),
                'liquidation_count_window': float(liquidation_count),
                'liquidation_notional_window': float(liquidation_notional),
                'derivatives_history_len': float(len(snapshot.derivatives_history)),
            },
        )
