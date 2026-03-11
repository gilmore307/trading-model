from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.market.models import Bar, DerivativesSnapshot, LiquidationEvent, MarketSnapshot, OrderBookTop, TickerSnapshot, TradePrint


@dataclass(slots=True)
class TrendView:
    symbol: str
    updated_at: datetime
    bars_1m: list[Bar]
    bars_5m: list[Bar]
    bars_1h: list[Bar]
    bars_4h: list[Bar]
    ticker: TickerSnapshot | None


@dataclass(slots=True)
class MeanRevView:
    symbol: str
    updated_at: datetime
    bars_1m: list[Bar]
    bars_5m: list[Bar]
    bars_15m: list[Bar]
    ticker: TickerSnapshot | None


@dataclass(slots=True)
class CompressionView:
    symbol: str
    updated_at: datetime
    bars_1m: list[Bar]
    bars_15m: list[Bar]
    derivatives: DerivativesSnapshot | None
    ticker: TickerSnapshot | None


@dataclass(slots=True)
class CrowdedView:
    symbol: str
    updated_at: datetime
    bars_1m: list[Bar]
    bars_5m: list[Bar]
    ticker: TickerSnapshot | None
    derivatives: DerivativesSnapshot | None


@dataclass(slots=True)
class RealtimeView:
    symbol: str
    updated_at: datetime
    ticker: TickerSnapshot | None
    top: OrderBookTop | None
    recent_trades: list[TradePrint]
    recent_liquidations: list[LiquidationEvent]
    derivatives: DerivativesSnapshot | None


def build_trend_view(snapshot: MarketSnapshot) -> TrendView:
    return TrendView(
        symbol=snapshot.symbol,
        updated_at=snapshot.updated_at,
        bars_1m=snapshot.bars.get('1m', []),
        bars_5m=snapshot.bars.get('5m', []),
        bars_1h=snapshot.bars.get('1h', []),
        bars_4h=snapshot.bars.get('4h', []),
        ticker=snapshot.ticker,
    )


def build_meanrev_view(snapshot: MarketSnapshot) -> MeanRevView:
    return MeanRevView(
        symbol=snapshot.symbol,
        updated_at=snapshot.updated_at,
        bars_1m=snapshot.bars.get('1m', []),
        bars_5m=snapshot.bars.get('5m', []),
        bars_15m=snapshot.bars.get('15m', []),
        ticker=snapshot.ticker,
    )


def build_compression_view(snapshot: MarketSnapshot) -> CompressionView:
    return CompressionView(
        symbol=snapshot.symbol,
        updated_at=snapshot.updated_at,
        bars_1m=snapshot.bars.get('1m', []),
        bars_15m=snapshot.bars.get('15m', []),
        derivatives=snapshot.derivatives,
        ticker=snapshot.ticker,
    )


def build_crowded_view(snapshot: MarketSnapshot) -> CrowdedView:
    return CrowdedView(
        symbol=snapshot.symbol,
        updated_at=snapshot.updated_at,
        bars_1m=snapshot.bars.get('1m', []),
        bars_5m=snapshot.bars.get('5m', []),
        ticker=snapshot.ticker,
        derivatives=snapshot.derivatives,
    )


def build_realtime_view(snapshot: MarketSnapshot) -> RealtimeView:
    return RealtimeView(
        symbol=snapshot.symbol,
        updated_at=snapshot.updated_at,
        ticker=snapshot.ticker,
        top=snapshot.top,
        recent_trades=snapshot.recent_trades,
        recent_liquidations=snapshot.recent_liquidations,
        derivatives=snapshot.derivatives,
    )
