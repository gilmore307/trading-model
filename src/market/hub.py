from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

from src.market.models import (
    Bar,
    DerivativesSnapshot,
    LiquidationEvent,
    MarketSnapshot,
    OrderBookTop,
    TickerSnapshot,
    TradePrint,
)
from src.market.views import (
    CompressionView,
    CrowdedView,
    MeanRevView,
    RealtimeView,
    TrendView,
    build_compression_view,
    build_crowded_view,
    build_meanrev_view,
    build_realtime_view,
    build_trend_view,
)


@dataclass(slots=True)
class HubRetention:
    bars_per_timeframe: int = 500
    recent_trades: int = 500
    recent_liquidations: int = 200
    derivatives_history: int = 500


class MarketDataHub:
    def __init__(self, retention: HubRetention | None = None):
        self.retention = retention or HubRetention()
        self._bars: dict[str, dict[str, deque[Bar]]] = defaultdict(lambda: defaultdict(lambda: deque(maxlen=self.retention.bars_per_timeframe)))
        self._ticker: dict[str, TickerSnapshot] = {}
        self._top: dict[str, OrderBookTop] = {}
        self._derivatives: dict[str, DerivativesSnapshot] = {}
        self._derivatives_history: dict[str, deque[DerivativesSnapshot]] = defaultdict(lambda: deque(maxlen=self.retention.derivatives_history))
        self._trades: dict[str, deque[TradePrint]] = defaultdict(lambda: deque(maxlen=self.retention.recent_trades))
        self._liquidations: dict[str, deque[LiquidationEvent]] = defaultdict(lambda: deque(maxlen=self.retention.recent_liquidations))
        self._updated_at: dict[str, datetime] = {}

    def ingest_bar(self, symbol: str, timeframe: str, bar: Bar) -> None:
        bars = self._bars[symbol][timeframe]
        if bars and bars[-1].ts == bar.ts:
            bars[-1] = bar
        else:
            bars.append(bar)
        self._updated_at[symbol] = bar.ts

    def ingest_ticker(self, symbol: str, ticker: TickerSnapshot) -> None:
        self._ticker[symbol] = ticker
        self._updated_at[symbol] = ticker.ts

    def ingest_top(self, symbol: str, top: OrderBookTop) -> None:
        self._top[symbol] = top
        self._updated_at[symbol] = top.ts

    def ingest_derivatives(self, symbol: str, derivatives: DerivativesSnapshot) -> None:
        self._derivatives[symbol] = derivatives
        rows = self._derivatives_history[symbol]
        if rows and rows[-1].ts == derivatives.ts:
            rows[-1] = derivatives
        else:
            rows.append(derivatives)
        self._updated_at[symbol] = derivatives.ts

    def ingest_trade(self, symbol: str, trade: TradePrint) -> None:
        self._trades[symbol].append(trade)
        self._updated_at[symbol] = trade.ts

    def ingest_liquidation(self, symbol: str, event: LiquidationEvent) -> None:
        self._liquidations[symbol].append(event)
        self._updated_at[symbol] = event.ts

    def ingest_realtime_batch(
        self,
        symbol: str,
        *,
        top: OrderBookTop | None = None,
        trades: Iterable[TradePrint] | None = None,
        liquidations: Iterable[LiquidationEvent] | None = None,
    ) -> None:
        if top is not None:
            self.ingest_top(symbol, top)
        for trade in trades or []:
            self.ingest_trade(symbol, trade)
        for event in liquidations or []:
            self.ingest_liquidation(symbol, event)

    def snapshot(self, symbol: str) -> MarketSnapshot:
        return MarketSnapshot(
            symbol=symbol,
            updated_at=self._updated_at[symbol],
            ticker=self._ticker.get(symbol),
            top=self._top.get(symbol),
            derivatives=self._derivatives.get(symbol),
            derivatives_history=list(self._derivatives_history[symbol]),
            bars={tf: list(rows) for tf, rows in self._bars[symbol].items()},
            recent_trades=list(self._trades[symbol]),
            recent_liquidations=list(self._liquidations[symbol]),
        )

    def trend_view(self, symbol: str) -> TrendView:
        return build_trend_view(self.snapshot(symbol))

    def meanrev_view(self, symbol: str) -> MeanRevView:
        return build_meanrev_view(self.snapshot(symbol))

    def compression_view(self, symbol: str) -> CompressionView:
        return build_compression_view(self.snapshot(symbol))

    def crowded_view(self, symbol: str) -> CrowdedView:
        return build_crowded_view(self.snapshot(symbol))

    def realtime_view(self, symbol: str) -> RealtimeView:
        return build_realtime_view(self.snapshot(symbol))
