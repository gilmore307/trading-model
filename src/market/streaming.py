from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from src.market.models import LiquidationEvent, OrderBookTop, TradePrint


@dataclass(slots=True)
class StreamingCapabilities:
    book_ticker: bool = True
    depth: bool = True
    trades: bool = True
    liquidation: bool = True
    mark_price: bool = True


class ShockStreamAdapter:
    """Placeholder streaming adapter for future shock/realtime ingestion.

    This file intentionally defines the event normalization surface first.
    Concrete websocket transport will be added later.
    """

    def normalize_trade(self, *, price: float, size: float, side: str | None = None) -> TradePrint:
        return TradePrint(ts=datetime.now(UTC), price=price, size=size, side=side)

    def normalize_top(self, *, bid_price: float, bid_size: float, ask_price: float, ask_size: float) -> OrderBookTop:
        return OrderBookTop(
            ts=datetime.now(UTC),
            bid_price=bid_price,
            bid_size=bid_size,
            ask_price=ask_price,
            ask_size=ask_size,
        )

    def normalize_liquidation(self, *, side: str | None, price: float | None, size: float | None, notional: float | None) -> LiquidationEvent:
        return LiquidationEvent(
            ts=datetime.now(UTC),
            side=side,
            price=price,
            size=size,
            notional=notional,
        )
