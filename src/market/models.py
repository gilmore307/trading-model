from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class Bar:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass(slots=True)
class TickerSnapshot:
    ts: datetime
    last: float | None = None
    bid: float | None = None
    ask: float | None = None
    mark: float | None = None
    index: float | None = None


@dataclass(slots=True)
class OrderBookTop:
    ts: datetime
    bid_price: float | None = None
    bid_size: float | None = None
    ask_price: float | None = None
    ask_size: float | None = None


@dataclass(slots=True)
class DerivativesSnapshot:
    ts: datetime
    funding_rate: float | None = None
    next_funding_time: datetime | None = None
    open_interest: float | None = None
    basis_pct: float | None = None


@dataclass(slots=True)
class TradePrint:
    ts: datetime
    price: float
    size: float
    side: str | None = None


@dataclass(slots=True)
class LiquidationEvent:
    ts: datetime
    side: str | None = None
    price: float | None = None
    size: float | None = None
    notional: float | None = None


@dataclass(slots=True)
class MarketSnapshot:
    symbol: str
    updated_at: datetime
    ticker: TickerSnapshot | None = None
    top: OrderBookTop | None = None
    derivatives: DerivativesSnapshot | None = None
    derivatives_history: list[DerivativesSnapshot] = field(default_factory=list)
    bars: dict[str, list[Bar]] = field(default_factory=dict)
    recent_trades: list[TradePrint] = field(default_factory=list)
    recent_liquidations: list[LiquidationEvent] = field(default_factory=list)
