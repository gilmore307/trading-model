from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class FeatureSnapshot:
    ts: datetime
    symbol: str
    layer: str = "generic"
    source_timeframe: str | None = None
    last_price: float | None = None
    adx: float | None = None
    ema20_slope: float | None = None
    ema50_slope: float | None = None
    bollinger_bandwidth_pct: float | None = None
    realized_vol_pct: float | None = None
    vwap_deviation_z: float | None = None
    funding_pctile: float | None = None
    oi_accel: float | None = None
    basis_deviation_pct: float | None = None
    liquidation_spike_score: float | None = None
    orderbook_imbalance: float | None = None
    trade_burst_score: float | None = None
    meta: dict[str, float | str | None] = field(default_factory=dict)
